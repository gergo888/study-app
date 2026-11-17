"""Validation rules for the content documents.

Errors block the app from writing a document. Warnings describe cross-document
gaps (a point without a flashcard, a quiz question for a deleted point) that the
UI shows and that ``check_content`` treats as failures for Claude Code.
"""

from __future__ import annotations

import re
from pathlib import Path

from .model import FlashcardDoc, Issue, QuizDoc, SummaryDoc

FIGURE_PATH_RE = re.compile(r"^figures/[A-Za-z0-9._-]+\.(png|jpe?g|gif|webp|svg)$")


def _required(issues: list[Issue], doc: str, line: int, label: str, value: str) -> None:
    if not value.strip():
        issues.append(Issue(line, f"{label} is empty", doc=doc))


def _figure(issues: list[Issue], doc: str, line: int, figure, chapter_dir: Path | None) -> None:
    if figure is None:
        return
    if not FIGURE_PATH_RE.match(figure.path):
        issues.append(Issue(line, f"figure path must be figures/<file>.png|jpg, got {figure.path!r}", doc=doc))
    elif chapter_dir is not None and not (chapter_dir / figure.path).is_file():
        issues.append(Issue(line, f"figure file not found: {figure.path}", doc=doc))


def validate_summary(doc: SummaryDoc, chapter_dir: Path | None = None) -> list[Issue]:
    issues: list[Issue] = []
    seen_sections: set[str] = set()
    seen_points: set[str] = set()
    for s in doc.sections:
        if s.key in seen_sections:
            issues.append(Issue(s.line, f"duplicate section id '{s.key}'", doc="summary"))
        seen_sections.add(s.key)
        _required(issues, "summary", s.line, f"section '{s.key}' English heading", s.heading_en)
        _required(issues, "summary", s.line, f"section '{s.key}' Hungarian heading (hu:)", s.heading_hu)
        if not s.points:
            issues.append(Issue(s.line, f"section '{s.key}' has no bullet points", severity="warning", doc="summary"))
        for p in s.points:
            if p.key in seen_points or p.key in seen_sections:
                issues.append(Issue(p.line, f"duplicate id '{p.key}'", doc="summary"))
            seen_points.add(p.key)
            _required(issues, "summary", p.line, f"point '{p.key}' English title", p.title_en)
            _required(issues, "summary", p.line, f"point '{p.key}' hu-title", p.title_hu)
            _required(issues, "summary", p.line, f"point '{p.key}' en", p.body_en)
            _required(issues, "summary", p.line, f"point '{p.key}' hu", p.body_hu)
            if not p.concepts:
                issues.append(Issue(p.line, f"point '{p.key}' has no concepts", doc="summary"))
            _figure(issues, "summary", p.line, p.figure, chapter_dir)
    return issues


def validate_flashcards(doc: FlashcardDoc, chapter_dir: Path | None = None) -> list[Issue]:
    issues: list[Issue] = []
    seen: set[str] = set()
    for c in doc.cards:
        if c.key in seen:
            issues.append(Issue(c.line, f"duplicate flashcard '{c.key}' (use '## {c.point_key} (2)' for extra cards)", doc="flashcards"))
        seen.add(c.key)
        for label, value in (("front-en", c.front_en), ("front-hu", c.front_hu), ("back-en", c.back_en), ("back-hu", c.back_hu)):
            _required(issues, "flashcards", c.line, f"flashcard '{c.key}' {label}", value)
        _figure(issues, "flashcards", c.line, c.figure, chapter_dir)
    return issues


def validate_quiz(doc: QuizDoc, chapter_dir: Path | None = None) -> list[Issue]:
    issues: list[Issue] = []
    seen: set[str] = set()
    for q in doc.questions:
        if q.key in seen:
            issues.append(Issue(q.line, f"duplicate quiz question '{q.key}' (use '## {q.point_key} (2)' for extra questions)", doc="quiz"))
        seen.add(q.key)
        _required(issues, "quiz", q.line, f"question '{q.key}' q-en", q.question_en)
        _required(issues, "quiz", q.line, f"question '{q.key}' q-hu", q.question_hu)
        if len(q.options) != 4:
            issues.append(Issue(q.line, f"question '{q.key}' must have exactly 4 options, has {len(q.options)}", doc="quiz"))
        if q.correct_index == -1:
            issues.append(Issue(q.line, f"question '{q.key}' has no correct option (mark one with [x])", doc="quiz"))
        elif q.correct_index == -2:
            issues.append(Issue(q.line, f"question '{q.key}' has more than one correct option", doc="quiz"))
        for i, opt in enumerate(q.options):
            if not opt.en.strip():
                issues.append(Issue(q.line, f"question '{q.key}' option {i + 1} is empty", doc="quiz"))
        if not q.why_en.strip() or not q.why_hu.strip():
            issues.append(Issue(q.line, f"question '{q.key}' has no explanation (why-en / why-hu)", severity="warning", doc="quiz"))
        _figure(issues, "quiz", q.line, q.figure, chapter_dir)
    return issues


def validate_links(summary: SummaryDoc | None, flashcards: FlashcardDoc | None, quiz: QuizDoc | None) -> list[Issue]:
    """Cross-document checks (warnings): every point has cards, every card has a point."""
    issues: list[Issue] = []
    if summary is None:
        return issues
    point_keys = {p.key for _, p in summary.all_points()}
    fc_points = {c.point_key for c in flashcards.cards} if flashcards else set()
    qz_points = {q.point_key for q in quiz.questions} if quiz else set()
    for _, p in summary.all_points():
        if p.key not in fc_points:
            issues.append(Issue(p.line, f"point '{p.key}' has no flashcard", severity="warning", doc="summary"))
        if p.key not in qz_points:
            issues.append(Issue(p.line, f"point '{p.key}' has no quiz question", severity="warning", doc="summary"))
    if flashcards:
        for c in flashcards.cards:
            if c.point_key not in point_keys:
                issues.append(Issue(c.line, f"flashcard '{c.key}' refers to unknown point '{c.point_key}'", severity="warning", doc="flashcards"))
    if quiz:
        for q in quiz.questions:
            if q.point_key not in point_keys:
                issues.append(Issue(q.line, f"quiz question '{q.key}' refers to unknown point '{q.point_key}'", severity="warning", doc="quiz"))
    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(i.severity == "error" for i in issues)
