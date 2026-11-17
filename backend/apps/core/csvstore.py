"""A tiny typed CSV "database".

Each table is one CSV file in ``settings.DATA_ROOT`` with a header row. Rows are
frozen dataclasses; column types come from the dataclass annotations.

* ``Table.all()`` returns cached rows (cache invalidated by file mtime/size).
* ``Table.update(fn)`` rewrites the whole file atomically under the data lock.
* ``Table.append(*rows)`` appends to log tables under the data lock.

``data_lock()`` is an exclusive, re-entrant lock that works across threads
(``threading.RLock``) and processes (``fcntl.flock`` on ``DATA_ROOT/.lock``).
Wrap multi-table operations in it so they are serialized as a unit.
"""

from __future__ import annotations

import csv
import dataclasses
import fcntl
import io
import os
import threading
import types
import typing
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Generic, TypeVar

from django.conf import settings

R = TypeVar("R")

_thread_lock = threading.RLock()
_local = threading.local()


class CSVSchemaError(RuntimeError):
    """The CSV header on disk does not match the table definition."""


@contextmanager
def data_lock() -> Iterator[None]:
    """Exclusive re-entrant lock over all CSV (and content) writes."""
    with _thread_lock:
        depth = getattr(_local, "depth", 0)
        if depth == 0:
            root = Path(settings.DATA_ROOT)
            root.mkdir(parents=True, exist_ok=True)
            fh = open(root / ".lock", "a+")
            fcntl.flock(fh, fcntl.LOCK_EX)
            _local.fh = fh
        _local.depth = depth + 1
        try:
            yield
        finally:
            _local.depth -= 1
            if _local.depth == 0:
                fh = _local.fh
                fcntl.flock(fh, fcntl.LOCK_UN)
                fh.close()
                _local.fh = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- conversion


def _unwrap_optional(tp: Any) -> tuple[Any, bool]:
    origin = typing.get_origin(tp)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0], True
    return tp, False


def _to_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _from_cell(raw: str, tp: Any) -> Any:
    base, optional = _unwrap_optional(tp)
    if raw == "":
        if optional:
            return None
        if base is str:
            return ""
        if base is bool:
            return False
        if base in (int, float):
            return base(0)
        raise ValueError(f"empty value for required {base}")
    if base is str:
        return raw
    if base is bool:
        return raw in ("1", "true", "True", "yes")
    if base is int:
        return int(raw)
    if base is float:
        return float(raw)
    if base is datetime:
        dt = datetime.fromisoformat(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    if base is date:
        return date.fromisoformat(raw)
    raise TypeError(f"unsupported column type {tp!r}")


# --------------------------------------------------------------------- table


class Table(Generic[R]):
    def __init__(self, name: str, row_type: type[R], *, append_only: bool = False):
        assert dataclasses.is_dataclass(row_type), row_type
        self.name = name
        self.row_type = row_type
        self.append_only = append_only
        hints = typing.get_type_hints(row_type)
        self.columns = [f.name for f in dataclasses.fields(row_type)]
        self.types = {c: hints[c] for c in self.columns}
        self._cache: tuple[tuple[int, int, str], list[R]] | None = None
        self._cache_lock = threading.Lock()

    # paths -------------------------------------------------------------
    @property
    def path(self) -> Path:
        return Path(settings.DATA_ROOT) / f"{self.name}.csv"

    # reading -----------------------------------------------------------
    def _parse(self, text: str) -> list[R]:
        reader = csv.reader(io.StringIO(text))
        try:
            header = next(reader)
        except StopIteration:
            return []
        if header != self.columns:
            raise CSVSchemaError(
                f"{self.path}: header {header} does not match expected columns {self.columns}"
            )
        rows: list[R] = []
        for lineno, cells in enumerate(reader, start=2):
            if not cells:
                continue
            if len(cells) != len(self.columns):
                raise CSVSchemaError(f"{self.path}:{lineno}: expected {len(self.columns)} cells, got {len(cells)}")
            values = {c: _from_cell(v, self.types[c]) for c, v in zip(self.columns, cells)}
            rows.append(self.row_type(**values))
        return rows

    def _read_fresh(self) -> list[R]:
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        return self._parse(text)

    def all(self) -> list[R]:
        """All rows (cached). Rows are frozen; use ``update`` to change them."""
        try:
            st = self.path.stat()
        except FileNotFoundError:
            return []
        key = (st.st_mtime_ns, st.st_size, str(self.path))
        with self._cache_lock:
            if self._cache and self._cache[0] == key:
                return list(self._cache[1])
        rows = self._read_fresh()
        with self._cache_lock:
            self._cache = (key, rows)
        return list(rows)

    def filter(self, **criteria: Any) -> list[R]:
        return [r for r in self.all() if all(getattr(r, k) == v for k, v in criteria.items())]

    def first(self, **criteria: Any) -> R | None:
        for r in self.all():
            if all(getattr(r, k) == v for k, v in criteria.items()):
                return r
        return None

    # writing -----------------------------------------------------------
    def _serialize(self, rows: Iterable[R]) -> str:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(self.columns)
        for r in rows:
            w.writerow([_to_cell(getattr(r, c)) for c in self.columns])
        return buf.getvalue()

    def _atomic_write(self, text: str) -> None:
        path = self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)

    def update(self, fn: Callable[[list[R]], list[R] | None]) -> list[R]:
        """Load fresh rows, let ``fn`` return the new full list, write atomically.

        If ``fn`` returns None the rows are left unchanged (nothing is written).
        """
        with data_lock():
            rows = self._read_fresh()
            new_rows = fn(list(rows))
            if new_rows is None:
                return rows
            for r in new_rows:
                if not isinstance(r, self.row_type):
                    raise TypeError(f"{self.name}: expected {self.row_type.__name__}, got {type(r).__name__}")
            self._atomic_write(self._serialize(new_rows))
            return new_rows

    def append(self, *rows: R) -> None:
        if not rows:
            return
        with data_lock():
            path = self.path
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.stat().st_size > 0:
                with open(path, encoding="utf-8") as fh:
                    header = next(csv.reader([fh.readline()]), [])
                if header != self.columns:
                    raise CSVSchemaError(f"{path}: header {header} does not match {self.columns}")
                buf = io.StringIO()
                w = csv.writer(buf, lineterminator="\n")
                for r in rows:
                    w.writerow([_to_cell(getattr(r, c)) for c in self.columns])
                with open(path, "a", encoding="utf-8", newline="") as fh:
                    fh.write(buf.getvalue())
                    fh.flush()
                    os.fsync(fh.fileno())
            else:
                self._atomic_write(self._serialize(rows))

    def upsert(self, row: R, *, key: tuple[str, ...]) -> R:
        """Replace the row whose ``key`` columns match, or append it."""

        def apply(rows: list[R]) -> list[R]:
            kv = tuple(getattr(row, k) for k in key)
            for i, r in enumerate(rows):
                if tuple(getattr(r, k) for k in key) == kv:
                    rows[i] = row
                    return rows
            rows.append(row)
            return rows

        self.update(apply)
        return row
