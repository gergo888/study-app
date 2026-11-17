"""Strict line-based parsers for the content Markdown files.

The grammar is documented in docs/CONTENT_FORMAT.md. Every parser returns
``(document, issues)``; issues carry 1-based line numbers. A document with
error-level issues must not be written by the app.
"""

from __future__ import annotations

import re

import yaml

from .model import (
    Figure,
    Flashcard,
    FlashcardDoc,
    Issue,
    NoteDoc,
    Point,
    QuizDoc,
    QuizOption,
    QuizQuestion,
    Section,
    SummaryDoc,
    card_key,
)

ID = r"[a-z0-9][a-z0-9-]*"
H1_RE = re.compile(r"^#\s+.*$")
SECTION_RE = re.compile(rf"^##\s+(?P<title>.+?)\s*\{{#(?P<key>{ID})\}}\s*$")
SECTION_HU_RE = re.compile(r"^hu:\s?(?P<value>.*)$")
POINT_RE = re.compile(rf"^-\s+\*\*(?P<title>.+?)\*\*\s*\{{#(?P<key>{ID})\}}\s*$")
POINT_FIELD_RE = re.compile(r"^ {2}-\s+(?P<name>[a-z][a-z-]*):(?:\s(?P<value>.*))?$")
CARD_HEAD_RE = re.compile(rf"^##\s+(?P<key>{ID})(?:\s+\((?P<n>\d+)\))?\s*$")
CARD_FIELD_RE = re.compile(r"^-\s+(?P<name>[a-z][a-z-]*):(?:\s(?P<value>.*))?$")
OPTION_RE = re.compile(r"^-\s+\[(?P<mark>[ xX])\]\s+(?P<text>.*)$")
FIGURE_RE = re.compile(r"^!\[(?P<caption>.*?)\]\((?P<path>[^)\s]+)\)$")
PAIR_SPLIT_RE = re.compile(r"(?<!\\) \| ")

POINT_FIELDS = {"hu-title", "en", "hu", "concepts", "figure"}
CARD_FIELDS = {"front-en", "front-hu", "back-en", "back-hu", "figure"}
QUIZ_FIELDS = {"q-en", "q-hu", "why-en", "why-hu", "figure"}


# ----------------------------------------------------------------- helpers


def split_front_matter(text: str, doc: str) -> tuple[dict, list[tuple[int, str]], list[Issue]]:
    """Returns (meta, [(lineno, line), ...] of the body, issues)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    issues: list[Issue] = []
    meta: dict = {}
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                try:
                    loaded = yaml.safe_load("\n".join(lines[1:i])) or {}
                    if isinstance(loaded, dict):
                        meta = loaded
                    else:
                        issues.append(Issue(1, "front matter must be a YAML mapping", doc=doc))
                except yaml.YAMLError as exc:
                    issues.append(Issue(1, f"invalid YAML front matter: {exc}", doc=doc))
                start = i + 1
                break
        else:
            issues.append(Issue(1, "front matter is not closed with '---'", doc=doc))
            start = len(lines)
    body = [(n + 1, lines[n]) for n in range(start, len(lines))]
    return meta, body, issues


def unescape_pipe(text: str) -> str:
    return text.replace("\\|", "|")


def split_pair(text: str) -> tuple[str, str]:
    """'English | Magyar' -> ('English', 'Magyar'); no separator -> same text twice."""
    parts = PAIR_SPLIT_RE.split(text, maxsplit=1)
    if len(parts) == 2:
        return unescape_pipe(parts[0].strip()), unescape_pipe(parts[1].strip())
    value = unescape_pipe(text.strip())
    return value, value


def parse_figure(value: str, lineno: int, doc: str, issues: list[Issue]) -> Figure | None:
    m = FIGURE_RE.match(value.strip())
    if not m:
        issues.append(Issue(lineno, "figure must look like ![English caption | Magyar felirat](figures/file.png)", doc=doc))
        return None
    en, hu = split_pair(m.group("caption"))
    return Figure(path=m.group("path"), caption_en=en, caption_hu=hu)


def parse_concepts(value: str) -> list[list[str]]:
    groups = []
    for group in value.split(";"):
        variants = [v.strip() for v in group.split("|") if v.strip()]
        if variants:
            groups.append(variants)
    return groups


class _FieldCollector:
    """Collects ``name: value`` fields with indented continuation lines."""

    def __init__(self, indent: int):
        self.indent = indent
        self.fields: dict[str, tuple[int, list[str]]] = {}
        self.current: str | None = None
        self.pending_blank = 0

    def start(self, name: str, value: str, lineno: int) -> None:
        self.fields[name] = (lineno, [value])
        self.current = name
        self.pending_blank = 0

    def continuation(self, line: str) -> bool:
        if self.current is None:
            return False
        if line.startswith(" " * self.indent):
            _, values = self.fields[self.current]
            values.extend([""] * self.pending_blank)
            values.append(line[self.indent :])
            self.pending_blank = 0
            return True
        return False

    def blank(self) -> None:
        if self.current is not None:
            self.pending_blank += 1

    def stop(self) -> None:
        self.current = None
        self.pending_blank = 0

    def get(self, name: str) -> str:
        if name not in self.fields:
            return ""
        return "\n".join(self.fields[name][1]).strip()

    def line_of(self, name: str, default: int) -> int:
        return self.fields[name][0] if name in self.fields else default


# ----------------------------------------------------------------- summary


def parse_summary(text: str) -> tuple[SummaryDoc, list[Issue]]:
    meta, body, issues = split_front_matter(text, "summary")
    doc = SummaryDoc(meta=meta)
    section: Section | None = None
    point: Point | None = None
    fields: _FieldCollector | None = None
    expect_section_hu = False

    def finish_point() -> None:
        nonlocal point, fields
        if point is None or fields is None:
            return
        for name in fields.fields:
            if name not in POINT_FIELDS:
                issues.append(Issue(fields.line_of(name, point.line), f"unknown point field '{name}'", doc="summary"))
        point.title_hu = fields.get("hu-title")
        point.body_en = fields.get("en")
        point.body_hu = fields.get("hu")
        point.concepts = parse_concepts(fields.get("concepts"))
        if "figure" in fields.fields:
            point.figure = parse_figure(fields.get("figure"), fields.line_of("figure", point.line), "summary", issues)
        point = None
        fields = None

    for lineno, line in body:
        if not line.strip():
            if fields:
                fields.blank()
            continue
        if fields and fields.continuation(line):
            continue
        if H1_RE.match(line):
            finish_point()
            expect_section_hu = False
            continue
        m = SECTION_RE.match(line)
        if m:
            finish_point()
            section = Section(key=m.group("key"), heading_en=m.group("title").strip(), line=lineno)
            doc.sections.append(section)
            expect_section_hu = True
            continue
        if expect_section_hu and (m := SECTION_HU_RE.match(line)):
            assert section is not None
            section.heading_hu = m.group("value").strip()
            expect_section_hu = False
            continue
        expect_section_hu = False
        m = POINT_RE.match(line)
        if m:
            finish_point()
            if section is None:
                issues.append(Issue(lineno, "bullet point before the first '## Section {#id}' heading", doc="summary"))
                section = Section(key="untitled", heading_en="Untitled", line=lineno)
                doc.sections.append(section)
            point = Point(key=m.group("key"), title_en=m.group("title").strip(), line=lineno)
            section.points.append(point)
            fields = _FieldCollector(indent=4)
            continue
        m = POINT_FIELD_RE.match(line)
        if m and fields is not None:
            fields.start(m.group("name"), m.group("value") or "", lineno)
            continue
        if fields:
            fields.stop()
        issues.append(Issue(lineno, f"unexpected line: {line.strip()[:80]!r}", doc="summary"))
    finish_point()
    return doc, issues


# -------------------------------------------------------------- flashcards


def _parse_entries(text: str, doc_name: str):
    """Shared walker for flashcards.md / quiz.md: yields entries with fields and options."""
    meta, body, issues = split_front_matter(text, doc_name)
    entries: list[dict] = []
    entry: dict | None = None
    for lineno, line in body:
        if not line.strip():
            if entry:
                entry["fields"].blank()
            continue
        if entry and entry["fields"].continuation(line):
            continue
        if line.startswith("# ") or line == "#":
            continue
        m = CARD_HEAD_RE.match(line)
        if m:
            n = int(m.group("n")) if m.group("n") else None
            entry = {
                "point_key": m.group("key"),
                "key": card_key(m.group("key"), n),
                "line": lineno,
                "fields": _FieldCollector(indent=2),
                "options": [],
            }
            entries.append(entry)
            continue
        if line.startswith("## "):
            issues.append(Issue(lineno, "entry heading must be '## <point-id>' or '## <point-id> (2)'", doc=doc_name))
            entry = None
            continue
        if entry is None:
            issues.append(Issue(lineno, f"unexpected line outside an entry: {line.strip()[:80]!r}", doc=doc_name))
            continue
        m = OPTION_RE.match(line)
        if m:
            entry["fields"].stop()
            entry["options"].append((lineno, m.group("mark").lower() == "x", m.group("text")))
            continue
        m = CARD_FIELD_RE.match(line)
        if m:
            entry["fields"].start(m.group("name"), m.group("value") or "", lineno)
            continue
        entry["fields"].stop()
        issues.append(Issue(lineno, f"unexpected line: {line.strip()[:80]!r}", doc=doc_name))
    return meta, entries, issues


def parse_flashcards(text: str) -> tuple[FlashcardDoc, list[Issue]]:
    meta, entries, issues = _parse_entries(text, "flashcards")
    doc = FlashcardDoc(meta=meta)
    for e in entries:
        f: _FieldCollector = e["fields"]
        for name in f.fields:
            if name not in CARD_FIELDS:
                issues.append(Issue(f.line_of(name, e["line"]), f"unknown flashcard field '{name}'", doc="flashcards"))
        for lineno, _, _ in e["options"]:
            issues.append(Issue(lineno, "answer options belong in quiz.md, not flashcards.md", doc="flashcards"))
        card = Flashcard(
            key=e["key"],
            point_key=e["point_key"],
            front_en=f.get("front-en"),
            front_hu=f.get("front-hu"),
            back_en=f.get("back-en"),
            back_hu=f.get("back-hu"),
            line=e["line"],
        )
        if "figure" in f.fields:
            card.figure = parse_figure(f.get("figure"), f.line_of("figure", e["line"]), "flashcards", issues)
        doc.cards.append(card)
    return doc, issues


def parse_quiz(text: str) -> tuple[QuizDoc, list[Issue]]:
    meta, entries, issues = _parse_entries(text, "quiz")
    doc = QuizDoc(meta=meta)
    for e in entries:
        f: _FieldCollector = e["fields"]
        for name in f.fields:
            if name not in QUIZ_FIELDS:
                issues.append(Issue(f.line_of(name, e["line"]), f"unknown quiz field '{name}'", doc="quiz"))
        q = QuizQuestion(
            key=e["key"],
            point_key=e["point_key"],
            question_en=f.get("q-en"),
            question_hu=f.get("q-hu"),
            why_en=f.get("why-en"),
            why_hu=f.get("why-hu"),
            line=e["line"],
        )
        for idx, (_lineno, correct, text_) in enumerate(e["options"]):
            en, hu = split_pair(text_)
            q.options.append(QuizOption(en=en, hu=hu))
            if correct:
                q.correct_index = idx if q.correct_index == -1 else -2  # -2 = more than one
        if "figure" in f.fields:
            q.figure = parse_figure(f.get("figure"), f.line_of("figure", e["line"]), "quiz", issues)
        doc.questions.append(q)
    return doc, issues


# -------------------------------------------------------------------- notes


def parse_note(text: str) -> tuple[NoteDoc, list[Issue]]:
    meta, body, issues = split_front_matter(text, "notes")
    return NoteDoc(meta=meta, body="\n".join(line for _, line in body).strip("\n")), issues
