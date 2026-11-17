"""Answer recording, XP, per-point progress and the "chapter learned" rules."""

from __future__ import annotations

import dataclasses
from collections import defaultdict

from django.conf import settings
from django.http import Http404

from apps.core import tables
from apps.core.csvstore import data_lock, utcnow
from apps.materials import services as material_services

from . import srs

ACTIVITY_KINDS = ("flashcard", "quiz", "reveal", "write")
RESULTS = ("correct", "partial", "wrong", "seen")
LEARNED_RULES = (("quiz", ("quiz",)), ("flashcards", ("flashcard",)), ("reveal", ("reveal", "write")))


def active_points(slug: str, key: str) -> list[tables.PointRow]:
    return sorted(
        (p for p in tables.points.filter(material=slug, chapter=key) if not p.archived), key=lambda p: p.order
    )


def point_progress(slug: str, key: str) -> dict[str, dict[str, dict]]:
    """{point_key: {kind: {"result": ..., "ts": ...}}} — latest result per activity kind."""
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for a in tables.activity.all():
        if a.material == slug and a.chapter == key:
            out[a.point_key][a.kind] = {"result": a.result, "ts": a.ts.isoformat()}
    return dict(out)


def check_learned(slug: str, key: str) -> str | None:
    """Mark the chapter learned if every point went through quiz, flashcards or reveal mode.

    Returns the rule that fired ("quiz" | "flashcards" | "reveal") or None.
    """
    points = {p.point_key for p in active_points(slug, key)}
    if not points:
        return None
    chapter = material_services.get_chapter(slug, key)
    if chapter.status == "learned":
        return None
    done: dict[str, set[str]] = defaultdict(set)
    for a in tables.activity.all():
        if a.material == slug and a.chapter == key:
            done[a.kind].add(a.point_key)
    for via, kinds in LEARNED_RULES:
        covered = set().union(*(done[k] for k in kinds))
        if points <= covered:
            material_services.set_chapter_status(slug, key, "learned", via=via)
            return via
    return None


def _log_activity(slug: str, key: str, point_key: str, kind: str, result: str, context: str) -> None:
    tables.activity.append(tables.ActivityRow(utcnow(), slug, key, point_key, kind, result, context))


def _bump_reading_status(slug: str, key: str) -> None:
    ch = material_services.get_chapter(slug, key)
    if ch.status == "not_started":
        material_services.set_chapter_status(slug, key, "reading")


def record_point_activity(slug: str, key: str, point_key: str, kind: str, result: str, context: str = "learn") -> dict:
    if kind not in ("reveal", "write") or result not in RESULTS:
        raise ValueError("kind must be reveal|write and result correct|partial|wrong|seen")
    with data_lock():
        if not any(p.point_key == point_key for p in active_points(slug, key)):
            raise Http404("point not found")
        _log_activity(slug, key, point_key, kind, result, context)
        _bump_reading_status(slug, key)
        learned = check_learned(slug, key)
    return {"chapter_learned": learned}


def record_answer(
    slug: str,
    key: str,
    kind: str,
    card_key: str,
    *,
    rating: int | None = None,
    selected_index: int | None = None,
    correct_index: int | None = None,
    context: str = "learn",
) -> dict:
    """Record a flashcard rating or a quiz answer: SRS, logs, XP, learned check."""
    if kind not in ("flashcard", "quiz"):
        raise ValueError("kind must be flashcard or quiz")
    now = utcnow()
    with data_lock():
        row = tables.cards.first(material=slug, chapter=key, kind=kind, card_key=card_key, archived=False)
        if row is None:
            raise Http404("card not found")
        if kind == "flashcard":
            if rating not in (1, 2, 3, 4):
                raise ValueError("rating must be 1..4")
            correct = rating != srs.AGAIN
        else:
            if selected_index is None or correct_index is None:
                raise ValueError("selected_index required")
            correct = selected_index == correct_index
            rating = srs.GOOD if correct else srs.AGAIN

        updated = srs.review(row, rating, now)
        tables.cards.upsert(updated, key=("material", "chapter", "kind", "card_key"))
        tables.review_log.append(
            tables.ReviewLogRow(now, slug, key, kind, card_key, rating, selected_index, correct, context)
        )
        _log_activity(slug, key, row.point_key, kind, "correct" if correct else "wrong", context)

        xp = 0
        if correct:
            xp = settings.XP_FLASHCARD_CORRECT if kind == "flashcard" else settings.XP_QUIZ_CORRECT
            if xp:
                tables.xp.append(tables.XPRow(now, xp, f"{kind}_correct", slug, key, card_key))
        _bump_reading_status(slug, key)
        learned = check_learned(slug, key)

    return {
        "correct": correct,
        "xp_awarded": xp,
        "total_xp": total_xp(),
        "due": updated.due.isoformat() if updated.due else None,
        "chapter_learned": learned,
    }


def total_xp() -> int:
    return sum(r.amount for r in tables.xp.all())


def level_for(xp: int) -> dict:
    """Level n starts at 50*(n-1)^2 XP: 0, 50, 200, 450, 800, ..."""
    level = 1
    while 50 * level**2 <= xp:
        level += 1
    floor, ceil = 50 * (level - 1) ** 2, 50 * level**2
    return {"level": level, "xp": xp, "level_floor": floor, "next_level_at": ceil, "progress": (xp - floor) / (ceil - floor)}


def reset_card(slug: str, key: str, kind: str, card_key: str) -> None:
    def apply(rows):
        for i, r in enumerate(rows):
            if (r.material, r.chapter, r.kind, r.card_key) == (slug, key, kind, card_key):
                rows[i] = dataclasses.replace(
                    r, fsrs_card_id=None, fsrs_state=None, step=None, stability=None, difficulty=None,
                    due=None, last_review=None, reps=0, lapses=0,
                )
        return rows

    tables.cards.update(apply)
