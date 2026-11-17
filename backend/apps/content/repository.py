"""Reading and writing the chapter Markdown documents on disk.

Writes are atomic (temp file + os.replace), serialized by the data lock and
guarded by optimistic concurrency: the caller passes the sha256 of the version
it edited (``base_sha``); if the file changed since (e.g. Claude Code edited
it), ``Conflict`` is raised instead of silently overwriting.
"""

from __future__ import annotations

import hashlib
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apps.core.csvstore import data_lock
from apps.core.exceptions import Conflict, InvalidDocument
from apps.core.paths import chapter_dir

from .mdformat import parse, render, validate
from .mdformat.model import Issue

FILES = {"summary": "summary.md", "flashcards": "flashcards.md", "quiz": "quiz.md", "notes": "notes.md"}
PARSERS = {
    "summary": parse.parse_summary,
    "flashcards": parse.parse_flashcards,
    "quiz": parse.parse_quiz,
    "notes": parse.parse_note,
}
RENDERERS = {
    "summary": render.render_summary,
    "flashcards": render.render_flashcards,
    "quiz": render.render_quiz,
    "notes": render.render_note,
}
VALIDATORS = {
    "summary": validate.validate_summary,
    "flashcards": validate.validate_flashcards,
    "quiz": validate.validate_quiz,
}


@dataclass
class Loaded:
    kind: str
    path: Path
    exists: bool
    text: str
    sha: str | None
    doc: Any  # parsed document or None
    issues: list[Issue]

    @property
    def ok(self) -> bool:
        return self.exists and not validate.has_errors(self.issues)


_cache: dict[str, tuple[tuple[int, int], Loaded]] = {}
_cache_lock = threading.Lock()


def sha_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def doc_path(slug: str, key: str, kind: str) -> Path:
    if kind not in FILES:
        raise ValueError(f"unknown document kind {kind}")
    return chapter_dir(slug, key) / FILES[kind]


def parse_and_validate(kind: str, text: str, chapter: Path | None) -> tuple[Any, list[Issue]]:
    doc, issues = PARSERS[kind](text)
    if kind in VALIDATORS:
        issues = issues + VALIDATORS[kind](doc, chapter)
    return doc, issues


def load(slug: str, key: str, kind: str) -> Loaded:
    path = doc_path(slug, key, kind)
    try:
        st = path.stat()
    except FileNotFoundError:
        return Loaded(kind, path, False, "", None, None, [])
    stamp = (st.st_mtime_ns, st.st_size)
    cache_key = str(path)
    with _cache_lock:
        hit = _cache.get(cache_key)
        if hit and hit[0] == stamp:
            return hit[1]
    text = path.read_text(encoding="utf-8")
    doc, issues = parse_and_validate(kind, text, path.parent)
    loaded = Loaded(kind, path, True, text, sha_of(text), doc, issues)
    with _cache_lock:
        _cache[cache_key] = (stamp, loaded)
    return loaded


def current_sha(slug: str, key: str, kind: str) -> str | None:
    path = doc_path(slug, key, kind)
    try:
        return sha_of(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def write_text(slug: str, key: str, kind: str, text: str, base_sha: str | None, *, reindex: bool = True) -> str:
    """Validate and write a whole document. Returns the new sha."""
    from . import sync  # local import: sync imports repository

    path = doc_path(slug, key, kind)
    text = text.replace("\r\n", "\n")
    if not text.endswith("\n"):
        text += "\n"
    _, issues = parse_and_validate(kind, text, path.parent)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        raise InvalidDocument([i.as_dict() for i in errors])
    with data_lock():
        current = current_sha(slug, key, kind)
        if current is not None and current != base_sha:
            raise Conflict()
        if current is None and base_sha not in (None, ""):
            raise Conflict("The document was deleted in the meantime.")
        _atomic_write(path, text)
        if reindex and kind != "notes":
            sync.reindex(slug, key)
    return sha_of(text)


def write_doc(slug: str, key: str, kind: str, doc: Any, base_sha: str | None, *, reindex: bool = True) -> str:
    return write_text(slug, key, kind, RENDERERS[kind](doc), base_sha, reindex=reindex)


def default_meta(slug: str, key: str, chapter_title: str = "") -> dict:
    meta: dict = {"material": slug, "chapter": key}
    if chapter_title:
        meta["title"] = chapter_title
    return meta
