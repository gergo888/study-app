"""In-memory model of the Markdown documents (see docs/CONTENT_FORMAT.md)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class Issue:
    line: int  # 1-based line in the file, 0 = whole document
    message: str
    severity: str = "error"  # error | warning
    doc: str = ""  # summary | flashcards | quiz | notes

    def as_dict(self) -> dict:
        return {"doc": self.doc, "line": self.line, "message": self.message, "severity": self.severity}

    def __str__(self) -> str:
        where = f"{self.doc}.md:{self.line}" if self.line else f"{self.doc}.md"
        return f"{where}: {self.severity}: {self.message}"


@dataclass
class Figure:
    path: str  # relative to the chapter folder, e.g. "figures/p0047-x1017.jpg"
    caption_en: str = ""
    caption_hu: str = ""


@dataclass
class Point:
    key: str
    title_en: str
    title_hu: str = ""
    body_en: str = ""
    body_hu: str = ""
    concepts: list[list[str]] = field(default_factory=list)
    figure: Figure | None = None
    line: int = field(default=0, compare=False)

    @property
    def content_hash(self) -> str:
        """Hash of what flashcards/quiz depend on (titles + bodies, not figure/concepts)."""
        return _hash(self.title_en, self.title_hu, self.body_en, self.body_hu)


@dataclass
class Section:
    key: str
    heading_en: str
    heading_hu: str = ""
    points: list[Point] = field(default_factory=list)
    line: int = field(default=0, compare=False)


@dataclass
class SummaryDoc:
    meta: dict = field(default_factory=dict)
    sections: list[Section] = field(default_factory=list)

    def all_points(self) -> list[tuple[Section, Point]]:
        return [(s, p) for s in self.sections for p in s.points]

    def find_point(self, key: str) -> tuple[Section, Point] | None:
        for s, p in self.all_points():
            if p.key == key:
                return s, p
        return None

    def find_section(self, key: str) -> Section | None:
        return next((s for s in self.sections if s.key == key), None)


@dataclass
class Flashcard:
    key: str  # point key, or "<point>.<n>" for extra cards
    point_key: str
    front_en: str = ""
    front_hu: str = ""
    back_en: str = ""
    back_hu: str = ""
    figure: Figure | None = None
    line: int = field(default=0, compare=False)

    @property
    def text_hash(self) -> str:
        fig = self.figure.path if self.figure else ""
        return _hash(self.front_en, self.front_hu, self.back_en, self.back_hu, fig)


@dataclass
class FlashcardDoc:
    meta: dict = field(default_factory=dict)
    cards: list[Flashcard] = field(default_factory=list)


@dataclass
class QuizOption:
    en: str
    hu: str = ""


@dataclass
class QuizQuestion:
    key: str
    point_key: str
    question_en: str = ""
    question_hu: str = ""
    options: list[QuizOption] = field(default_factory=list)
    correct_index: int = -1
    why_en: str = ""
    why_hu: str = ""
    figure: Figure | None = None
    line: int = field(default=0, compare=False)

    @property
    def text_hash(self) -> str:
        fig = self.figure.path if self.figure else ""
        opts = [f"{o.en}\x1e{o.hu}" for o in self.options]
        return _hash(self.question_en, self.question_hu, *opts, str(self.correct_index), self.why_en, self.why_hu, fig)


@dataclass
class QuizDoc:
    meta: dict = field(default_factory=dict)
    questions: list[QuizQuestion] = field(default_factory=list)


@dataclass
class NoteDoc:
    meta: dict = field(default_factory=dict)
    body: str = ""


def _hash(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]


def card_key(point_key: str, n: int | None) -> str:
    return point_key if not n or n == 1 else f"{point_key}.{n}"


def split_card_key(key: str) -> tuple[str, int]:
    if "." in key:
        point, n = key.rsplit(".", 1)
        if n.isdigit():
            return point, int(n)
    return key, 1
