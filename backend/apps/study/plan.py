"""Study plan: spread the remaining chapters over study days, weighted by page count."""

from __future__ import annotations

from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone

from apps.core import tables
from apps.core.csvstore import data_lock
from apps.materials import services as material_services


def today() -> date:
    return timezone.localdate()


def study_days(start: date, weekdays: set[int], count: int | None = None, until: date | None = None) -> list[date]:
    days, d = [], start
    weekdays = weekdays or set(range(7))
    while True:
        if until is not None and d > until:
            break
        if d.weekday() in weekdays:
            days.append(d)
            if count is not None and len(days) >= count:
                break
        d += timedelta(days=1)
        if len(days) > 3650 or (until is None and count is None):
            break
    return days


def generate(slug: str, start: date, target: date | None, weekdays: set[int]) -> list[tables.PlanRow]:
    chapters = material_services.material_chapters(slug)
    if not chapters:
        raise ValueError("this material has no chapters yet")
    start = max(start, today()) if any(c.status != "learned" for c in chapters) else start
    with data_lock():
        existing = {r.chapter: r for r in tables.plan.filter(material=slug)}
        rows: list[tables.PlanRow] = []
        remaining = [c for c in chapters if c.status != "learned"]
        # Learned chapters keep their date (or the day they were learned).
        for c in chapters:
            if c.status == "learned":
                when = existing[c.key].scheduled_date if c.key in existing else (
                    timezone.localtime(c.learned_at).date() if c.learned_at else start
                )
                rows.append(tables.PlanRow(slug, c.key, c.order, when))

        if remaining:
            total_pages = sum(c.end_page - c.start_page + 1 for c in remaining)
            if target and target >= start:
                days = study_days(start, weekdays, until=target)
            else:
                pages_per_day = max(1, settings.DEFAULT_PAGES_PER_DAY)
                needed = max(1, -(-total_pages // pages_per_day))
                days = study_days(start, weekdays, count=needed)
            days = days or [start]
            cumulative = 0
            for c in remaining:
                idx = min(len(days) - 1, int(cumulative / total_pages * len(days)))
                rows.append(tables.PlanRow(slug, c.key, c.order, days[idx]))
                cumulative += c.end_page - c.start_page + 1

        rows.sort(key=lambda r: r.order)
        tables.plan.update(lambda all_rows: [r for r in all_rows if r.material != slug] + rows)
        material_services.update_material(
            slug,
            plan_start=start,
            plan_target=target,
            study_weekdays=",".join(str(d) for d in sorted(weekdays)),
        )
    return rows


def plan_status(slug: str) -> dict:
    chapters = {c.key: c for c in material_services.material_chapters(slug)}
    rows = sorted(tables.plan.filter(material=slug), key=lambda r: r.order)
    t = today()
    due_by_today = [r for r in rows if r.scheduled_date <= t]
    learned = [c for c in chapters.values() if c.status == "learned"]
    # Only chapters planned for *earlier* days count as behind; today's chapter is still on time.
    behind = sum(
        1 for r in rows if r.scheduled_date < t and chapters.get(r.chapter) and chapters[r.chapter].status != "learned"
    )
    next_up = next((c for c in sorted(chapters.values(), key=lambda c: c.order) if c.status != "learned"), None)
    return {
        "has_plan": bool(rows),
        "total": len(chapters),
        "learned": len(learned),
        "scheduled_by_today": len(due_by_today),
        "behind": behind,
        "on_track": behind == 0,
        "next_chapter": next_up.key if next_up else None,
        "items": {r.chapter: r.scheduled_date.isoformat() for r in rows},
    }
