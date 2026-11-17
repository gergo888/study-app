"""Dashboard numbers: XP, level, streak, due reviews, progress, recent activity."""

from __future__ import annotations

from collections import Counter
from datetime import timedelta

from django.utils import timezone

from apps.core import tables
from apps.core.csvstore import utcnow

from . import srs
from .services import level_for, total_xp


def _local_date(dt):
    return timezone.localtime(dt).date()


def streak_days() -> int:
    days = {_local_date(a.ts) for a in tables.activity.all()}
    today = timezone.localdate()
    d = today if today in days else today - timedelta(days=1)
    n = 0
    while d in days:
        n += 1
        d -= timedelta(days=1)
    return n


def due_counts() -> dict:
    now = utcnow()
    by_material: Counter[str] = Counter()
    by_kind: Counter[str] = Counter()
    for c in tables.cards.all():
        if srs.is_due(c, now):
            by_material[c.material] += 1
            by_kind[c.kind] += 1
    return {"total": sum(by_kind.values()), "by_kind": dict(by_kind), "by_material": dict(by_material)}


def dashboard() -> dict:
    xp_rows = tables.xp.all()
    today = timezone.localdate()
    xp_by_day: Counter = Counter()
    for r in xp_rows:
        xp_by_day[_local_date(r.ts)] += r.amount
    days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    chapters = tables.chapters.all()
    materials = tables.materials.all()
    recent = sorted(tables.activity.all(), key=lambda a: a.ts, reverse=True)[:12]
    titles = {(c.material, c.key): c.title for c in chapters}
    reviews_today = sum(1 for r in tables.review_log.all() if _local_date(r.ts) == today)
    return {
        **level_for(total_xp()),
        "xp_today": xp_by_day.get(today, 0),
        "streak": streak_days(),
        "reviews_today": reviews_today,
        "due": due_counts(),
        "chapters_total": len(chapters),
        "chapters_learned": sum(1 for c in chapters if c.status == "learned"),
        "materials": len(materials),
        "xp_by_day": [{"date": d.isoformat(), "xp": xp_by_day.get(d, 0)} for d in days],
        "recent": [
            {
                "ts": a.ts.isoformat(),
                "material": a.material,
                "chapter": a.chapter,
                "chapter_title": titles.get((a.material, a.chapter), a.chapter),
                "point_key": a.point_key,
                "kind": a.kind,
                "result": a.result,
            }
            for a in recent
        ],
    }
