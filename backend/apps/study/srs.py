"""Spaced repetition (FSRS via the ``fsrs`` package), isolated behind two functions.

The scheduling state is stored as plain columns of ``cards.csv``. Swapping the
algorithm only requires changing this module.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime

from fsrs import Card, Rating, Scheduler

from apps.core.tables import CardRow

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4

_scheduler = Scheduler(desired_retention=0.9, enable_fuzzing=True)


def _to_fsrs(row: CardRow) -> Card:
    if row.fsrs_state is None:
        return Card()
    return Card.from_dict(
        {
            "card_id": row.fsrs_card_id or 0,
            "state": row.fsrs_state,
            "step": row.step,
            "stability": row.stability,
            "difficulty": row.difficulty,
            "due": row.due.isoformat() if row.due else None,
            "last_review": row.last_review.isoformat() if row.last_review else None,
        }
    )


def review(row: CardRow, rating: int, now: datetime) -> CardRow:
    """Apply one review and return the updated row."""
    card, _log = _scheduler.review_card(_to_fsrs(row), Rating(rating), review_datetime=now)
    return dataclasses.replace(
        row,
        fsrs_card_id=card.card_id,
        fsrs_state=int(card.state),
        step=card.step,
        stability=card.stability,
        difficulty=card.difficulty,
        due=card.due,
        last_review=card.last_review,
        reps=row.reps + 1,
        lapses=row.lapses + (1 if rating == AGAIN and row.reps > 0 else 0),
    )


def is_due(row: CardRow, now: datetime) -> bool:
    """Only cards that were studied at least once take part in reviews."""
    return not row.archived and row.reps > 0 and row.due is not None and row.due <= now
