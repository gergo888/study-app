"""All CSV tables of the app (the whole persistent state besides Markdown and PDFs).

Documented column by column in docs/DATA_FORMAT.md. Changing a dataclass here
changes the CSV header, so existing files must be migrated by hand.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .csvstore import Table


@dataclass(frozen=True)
class MaterialRow:
    slug: str
    title: str
    description: str
    pdf_path: str  # relative to MEDIA_ROOT, "" if no PDF yet
    pdf_name: str  # original file name
    page_count: int
    chapter_level: int  # outline level used for chapters (0 = not built)
    plan_start: date | None
    plan_target: date | None
    study_weekdays: str  # e.g. "0,1,2,3,4" (Mon=0)
    created_at: datetime


@dataclass(frozen=True)
class ChapterRow:
    material: str
    key: str  # e.g. "1A"; used in paths and URLs
    order: int
    code: str  # e.g. "Topic 1A"
    title: str
    group_title: str  # e.g. "Lesson 1"
    group_subtitle: str  # e.g. "Installing Motherboards and Connectors"
    start_page: int  # 1-based, inclusive
    end_page: int  # 1-based, inclusive
    status: str  # not_started | reading | read | learned
    read_at: datetime | None
    learned_at: datetime | None
    learned_via: str  # "" | quiz | flashcards | reveal | manual


@dataclass(frozen=True)
class PlanRow:
    material: str
    chapter: str
    order: int
    scheduled_date: date


@dataclass(frozen=True)
class DocIndexRow:
    material: str
    chapter: str
    kind: str  # summary | flashcards | quiz
    sha256: str
    parsed_ok: bool
    indexed_at: datetime


@dataclass(frozen=True)
class PointRow:
    material: str
    chapter: str
    point_key: str
    section_key: str
    order: int
    content_hash: str
    archived: bool


@dataclass(frozen=True)
class CardRow:
    material: str
    chapter: str
    kind: str  # flashcard | quiz
    card_key: str
    point_key: str
    text_hash: str
    basis_hash: str  # point content_hash the card was last written/confirmed against
    archived: bool
    # FSRS scheduling state (empty until first answer)
    fsrs_card_id: int | None
    fsrs_state: int | None  # 1 learning, 2 review, 3 relearning
    step: int | None
    stability: float | None
    difficulty: float | None
    due: datetime | None
    last_review: datetime | None
    reps: int
    lapses: int


@dataclass(frozen=True)
class ReviewLogRow:
    ts: datetime
    material: str
    chapter: str
    kind: str  # flashcard | quiz
    card_key: str
    rating: int  # FSRS rating 1..4
    selected_index: int | None  # quiz only
    correct: bool
    context: str  # learn | review


@dataclass(frozen=True)
class ActivityRow:
    ts: datetime
    material: str
    chapter: str
    point_key: str
    kind: str  # flashcard | quiz | reveal | write
    result: str  # correct | partial | wrong | seen
    context: str  # learn | review


@dataclass(frozen=True)
class XPRow:
    ts: datetime
    amount: int
    reason: str  # flashcard_correct | quiz_correct
    material: str
    chapter: str
    ref: str  # card key


materials = Table("materials", MaterialRow)
chapters = Table("chapters", ChapterRow)
plan = Table("plan", PlanRow)
doc_index = Table("doc_index", DocIndexRow)
points = Table("points", PointRow)
cards = Table("cards", CardRow)
review_log = Table("review_log", ReviewLogRow, append_only=True)
activity = Table("activity", ActivityRow, append_only=True)
xp = Table("xp", XPRow, append_only=True)

ALL_TABLES = [materials, chapters, plan, doc_index, points, cards, review_log, activity, xp]
