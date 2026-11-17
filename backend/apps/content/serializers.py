"""JSON shapes of the parsed documents for the API."""

from __future__ import annotations

from apps.core import tables

from .mdformat.model import Figure, Flashcard, Point, QuizQuestion


def file_url(slug: str, key: str, path: str) -> str:
    return f"/api/chapters/{slug}/{key}/files/{path}"


def figure_json(slug: str, key: str, fig: Figure | None) -> dict | None:
    if fig is None:
        return None
    return {"path": fig.path, "url": file_url(slug, key, fig.path), "caption_en": fig.caption_en, "caption_hu": fig.caption_hu}


def point_json(slug: str, key: str, p: Point) -> dict:
    return {
        "key": p.key,
        "title_en": p.title_en,
        "title_hu": p.title_hu,
        "body_en": p.body_en,
        "body_hu": p.body_hu,
        "concepts": p.concepts,
        "figure": figure_json(slug, key, p.figure),
    }


def card_states(slug: str, key: str, kind: str) -> dict[str, tables.CardRow]:
    return {r.card_key: r for r in tables.cards.filter(material=slug, chapter=key, kind=kind) if not r.archived}


def _srs(row: tables.CardRow | None) -> dict | None:
    if row is None:
        return None
    return {
        "reps": row.reps,
        "lapses": row.lapses,
        "due": row.due.isoformat() if row.due else None,
        "last_review": row.last_review.isoformat() if row.last_review else None,
    }


def flashcard_json(slug: str, key: str, c: Flashcard, state: tables.CardRow | None = None, stale: bool = False) -> dict:
    return {
        "key": c.key,
        "point_key": c.point_key,
        "front_en": c.front_en,
        "front_hu": c.front_hu,
        "back_en": c.back_en,
        "back_hu": c.back_hu,
        "figure": figure_json(slug, key, c.figure),
        "stale": stale,
        "srs": _srs(state),
    }


def question_json(slug: str, key: str, q: QuizQuestion, state: tables.CardRow | None = None, stale: bool = False) -> dict:
    return {
        "key": q.key,
        "point_key": q.point_key,
        "question_en": q.question_en,
        "question_hu": q.question_hu,
        "options": [{"en": o.en, "hu": o.hu} for o in q.options],
        "correct_index": q.correct_index,
        "why_en": q.why_en,
        "why_hu": q.why_hu,
        "figure": figure_json(slug, key, q.figure),
        "stale": stale,
        "srs": _srs(state),
    }
