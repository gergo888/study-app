import dataclasses
import multiprocessing
import threading
from datetime import date, datetime, timezone

import pytest

from apps.core.csvstore import CSVSchemaError, Table


@dataclasses.dataclass(frozen=True)
class Row:
    key: str
    n: int
    ratio: float | None
    flag: bool
    day: date | None
    ts: datetime | None


def make_table():
    return Table("things", Row)


def test_roundtrip_types():
    t = make_table()
    ts = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    rows = [Row("a,b \"quoted\"", 1, 0.25, True, date(2026, 1, 2), ts), Row("x", 0, None, False, None, None)]
    t.update(lambda _: rows)
    assert t.all() == rows


def test_append_creates_header_and_appends():
    t = make_table()
    t.append(Row("a", 1, None, False, None, None))
    t.append(Row("b", 2, None, True, None, None))
    assert [r.key for r in t.all()] == ["a", "b"]
    assert t.path.read_text().splitlines()[0] == "key,n,ratio,flag,day,ts"


def test_bad_header_fails_loudly():
    t = make_table()
    t.path.parent.mkdir(parents=True, exist_ok=True)
    t.path.write_text("key,count\nx,1\n")
    with pytest.raises(CSVSchemaError):
        t.all()


def test_failed_update_leaves_file_intact():
    t = make_table()
    t.update(lambda _: [Row("keep", 1, None, False, None, None)])

    def boom(rows):
        raise RuntimeError("crash in the middle")

    with pytest.raises(RuntimeError):
        t.update(boom)
    assert [r.key for r in t.all()] == ["keep"]
    assert not list(t.path.parent.glob(".things*.tmp"))


def test_concurrent_thread_updates_lose_nothing():
    t = make_table()
    t.update(lambda _: [Row("counter", 0, None, False, None, None)])

    def bump():
        for _ in range(25):
            t.update(lambda rows: [dataclasses.replace(rows[0], n=rows[0].n + 1)])

    threads = [threading.Thread(target=bump) for _ in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert t.all()[0].n == 200


def _bump_in_process(data_root, times):
    import django
    from django.conf import settings

    if not settings.configured:  # pragma: no cover - depends on start method
        django.setup()
    settings.DATA_ROOT = data_root
    t = make_table()
    for _ in range(times):
        t.update(lambda rows: [dataclasses.replace(rows[0], n=rows[0].n + 1)])


def test_concurrent_process_updates_lose_nothing(settings):
    t = make_table()
    t.update(lambda _: [Row("counter", 0, None, False, None, None)])
    ctx = multiprocessing.get_context("fork")
    procs = [ctx.Process(target=_bump_in_process, args=(settings.DATA_ROOT, 20)) for _ in range(4)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
        assert p.exitcode == 0
    assert t.all()[0].n == 80
