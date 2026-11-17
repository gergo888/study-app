"""Canonical Markdown rendering. ``parse(render(doc)) == doc`` for every valid doc."""

from __future__ import annotations

import yaml

from .model import Figure, FlashcardDoc, NoteDoc, QuizDoc, SummaryDoc, split_card_key


def _front_matter(meta: dict) -> str:
    if not meta:
        return ""
    dumped = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=1000).strip()
    return f"---\n{dumped}\n---\n\n"


def _value(value: str, indent: int) -> str:
    """First line inline, following lines indented (blank lines stay blank)."""
    lines = value.strip().split("\n")
    out = [lines[0]]
    for ln in lines[1:]:
        out.append((" " * indent + ln) if ln.strip() else "")
    return "\n".join(out)


def _escape(text: str) -> str:
    return text.replace(" | ", " \\| ")


def pair(en: str, hu: str) -> str:
    if en == hu or not hu:
        return _escape(en)
    return f"{_escape(en)} | {_escape(hu)}"


def figure_md(fig: Figure) -> str:
    return f"![{pair(fig.caption_en, fig.caption_hu)}]({fig.path})"


def concepts_md(groups: list[list[str]]) -> str:
    return " ; ".join(" | ".join(g) for g in groups)


def render_summary(doc: SummaryDoc) -> str:
    out = [_front_matter(doc.meta)]
    title = doc.meta.get("title")
    if title:
        out.append(f"# {title}\n\n")
    for section in doc.sections:
        out.append(f"## {section.heading_en} {{#{section.key}}}\n")
        if section.heading_hu:
            out.append(f"hu: {section.heading_hu}\n")
        out.append("\n")
        for p in section.points:
            out.append(f"- **{p.title_en}** {{#{p.key}}}\n")
            out.append(f"  - hu-title: {p.title_hu}\n")
            out.append(f"  - en: {_value(p.body_en, 4)}\n")
            out.append(f"  - hu: {_value(p.body_hu, 4)}\n")
            out.append(f"  - concepts: {concepts_md(p.concepts)}\n")
            if p.figure:
                out.append(f"  - figure: {figure_md(p.figure)}\n")
            out.append("\n")
    return "".join(out).rstrip("\n") + "\n"


def _heading(key: str) -> str:
    point, n = split_card_key(key)
    return f"## {point}" if n == 1 else f"## {point} ({n})"


def render_flashcards(doc: FlashcardDoc) -> str:
    out = [_front_matter(doc.meta)]
    for c in doc.cards:
        out.append(_heading(c.key) + "\n")
        out.append(f"- front-en: {_value(c.front_en, 2)}\n")
        out.append(f"- front-hu: {_value(c.front_hu, 2)}\n")
        out.append(f"- back-en: {_value(c.back_en, 2)}\n")
        out.append(f"- back-hu: {_value(c.back_hu, 2)}\n")
        if c.figure:
            out.append(f"- figure: {figure_md(c.figure)}\n")
        out.append("\n")
    return "".join(out).rstrip("\n") + "\n"


def render_quiz(doc: QuizDoc) -> str:
    out = [_front_matter(doc.meta)]
    for q in doc.questions:
        out.append(_heading(q.key) + "\n")
        out.append(f"- q-en: {_value(q.question_en, 2)}\n")
        out.append(f"- q-hu: {_value(q.question_hu, 2)}\n")
        for i, opt in enumerate(q.options):
            mark = "x" if i == q.correct_index else " "
            out.append(f"- [{mark}] {pair(opt.en, opt.hu)}\n")
        if q.why_en:
            out.append(f"- why-en: {_value(q.why_en, 2)}\n")
        if q.why_hu:
            out.append(f"- why-hu: {_value(q.why_hu, 2)}\n")
        if q.figure:
            out.append(f"- figure: {figure_md(q.figure)}\n")
        out.append("\n")
    return "".join(out).rstrip("\n") + "\n"


def render_note(doc: NoteDoc) -> str:
    return _front_matter(doc.meta) + doc.body.strip("\n") + "\n"
