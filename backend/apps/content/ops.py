"""Structured edits of the Markdown documents (used by the editor UI).

Every operation: load (deep copy) -> check base_sha -> modify -> render -> atomic
write -> reindex. Deleting a point also removes its flashcards and quiz
questions so no orphans are left behind.
"""

from __future__ import annotations

import copy
import re
import unicodedata

from apps.core.csvstore import data_lock
from apps.core.exceptions import Conflict
from apps.materials import services as material_services

from . import repository
from .mdformat import parse
from .mdformat.model import (
    Figure,
    Flashcard,
    FlashcardDoc,
    Point,
    QuizDoc,
    QuizOption,
    QuizQuestion,
    Section,
    SummaryDoc,
    card_key,
    split_card_key,
)


class OpError(ValueError):
    pass


# ----------------------------------------------------------------- helpers


def make_id(text: str, taken: set[str], prefix: str = "p") -> str:
    base = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:40].strip("-") or prefix
    if not base[0].isalnum():
        base = f"{prefix}-{base}"
    candidate, n = base, 2
    while candidate in taken:
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def _figure(data) -> Figure | None:
    if not data or not data.get("path"):
        return None
    en = (data.get("caption_en") or "").strip()
    hu = (data.get("caption_hu") or "").strip() or en
    return Figure(path=data["path"].strip(), caption_en=en, caption_hu=hu)


def _concepts(value) -> list[list[str]]:
    if isinstance(value, str):
        return parse.parse_concepts(value)
    groups = []
    for g in value or []:
        variants = [str(v).strip() for v in (g if isinstance(g, list) else [g]) if str(v).strip()]
        if variants:
            groups.append(variants)
    return groups


def _text(data: dict, name: str) -> str:
    return (data.get(name) or "").strip()


def _load(slug: str, key: str, kind: str, base_sha: str | None):
    loaded = repository.load(slug, key, kind)
    if loaded.exists:
        if base_sha != loaded.sha:
            raise Conflict()
        if loaded.doc is None:
            raise OpError(f"{kind}.md cannot be parsed; fix it in the Markdown editor first")
        return copy.deepcopy(loaded.doc)
    if base_sha:
        raise Conflict("The document was deleted in the meantime.")
    chapter = material_services.get_chapter(slug, key)
    meta = repository.default_meta(slug, key, chapter.title if kind == "summary" else "")
    return {"summary": SummaryDoc, "flashcards": FlashcardDoc, "quiz": QuizDoc}[kind](meta=meta)


def _point_order(slug: str, key: str) -> dict[str, int]:
    loaded = repository.load(slug, key, "summary")
    if not loaded.doc:
        return {}
    return {p.key: i for i, (_, p) in enumerate(loaded.doc.all_points())}


def _remove_cards_for_points(slug: str, key: str, point_keys: set[str]) -> None:
    for kind in ("flashcards", "quiz"):
        loaded = repository.load(slug, key, kind)
        if not loaded.exists or loaded.doc is None:
            continue
        doc = copy.deepcopy(loaded.doc)
        items = doc.cards if kind == "flashcards" else doc.questions
        kept = [i for i in items if i.point_key not in point_keys]
        if len(kept) != len(items):
            if kind == "flashcards":
                doc.cards = kept
            else:
                doc.questions = kept
            repository.write_doc(slug, key, kind, doc, loaded.sha, reindex=False)


# ----------------------------------------------------------------- summary


def point_from_payload(data: dict, key: str) -> Point:
    title_en = _text(data, "title_en")
    if not title_en:
        raise OpError("title_en is required")
    body_en = _text(data, "body_en")
    if not body_en:
        raise OpError("body_en is required")
    title_hu = _text(data, "title_hu") or title_en
    concepts = _concepts(data.get("concepts")) or [sorted({title_en, title_hu})]
    return Point(
        key=key,
        title_en=title_en,
        title_hu=title_hu,
        body_en=body_en,
        body_hu=_text(data, "body_hu") or body_en,
        concepts=concepts,
        figure=_figure(data.get("figure")),
    )


def summary_op(slug: str, key: str, op: str, payload: dict, base_sha: str | None) -> dict:
    with data_lock():
        doc: SummaryDoc = _load(slug, key, "summary", base_sha)
        taken = {s.key for s in doc.sections} | {p.key for _, p in doc.all_points()}
        removed_points: set[str] = set()
        result: dict = {}

        def section_or_fail(skey: str) -> Section:
            s = doc.find_section(skey)
            if s is None:
                raise OpError(f"unknown section {skey}")
            return s

        def point_or_fail(pkey: str) -> tuple[Section, Point]:
            found = doc.find_point(pkey)
            if found is None:
                raise OpError(f"unknown point {pkey}")
            return found

        if op == "add_section":
            heading_en = _text(payload, "heading_en")
            if not heading_en:
                raise OpError("heading_en is required")
            section = Section(key=make_id(heading_en, taken, "s"), heading_en=heading_en, heading_hu=_text(payload, "heading_hu"))
            after = payload.get("after")
            idx = next((i + 1 for i, s in enumerate(doc.sections) if s.key == after), len(doc.sections))
            doc.sections.insert(idx, section)
            result["key"] = section.key
        elif op == "update_section":
            s = section_or_fail(payload.get("section_key", ""))
            s.heading_en = _text(payload, "heading_en") or s.heading_en
            s.heading_hu = _text(payload, "heading_hu")
        elif op == "delete_section":
            s = section_or_fail(payload.get("section_key", ""))
            removed_points |= {p.key for p in s.points}
            doc.sections.remove(s)
        elif op == "move_section":
            s = section_or_fail(payload.get("section_key", ""))
            i = doc.sections.index(s)
            j = i - 1 if payload.get("direction") == "up" else i + 1
            if 0 <= j < len(doc.sections):
                doc.sections[i], doc.sections[j] = doc.sections[j], doc.sections[i]
        elif op == "add_point":
            s = section_or_fail(payload.get("section_key", ""))
            data = payload.get("point") or {}
            point = point_from_payload(data, make_id(_text(data, "title_en"), taken))
            after = payload.get("after")
            idx = next((i + 1 for i, p in enumerate(s.points) if p.key == after), len(s.points))
            s.points.insert(idx, point)
            result["key"] = point.key
        elif op == "update_point":
            s, p = point_or_fail(payload.get("point_key", ""))
            new = point_from_payload(payload.get("point") or {}, p.key)
            s.points[s.points.index(p)] = new
        elif op == "delete_point":
            s, p = point_or_fail(payload.get("point_key", ""))
            s.points.remove(p)
            removed_points.add(p.key)
        elif op == "move_point":
            s, p = point_or_fail(payload.get("point_key", ""))
            i = s.points.index(p)
            up = payload.get("direction") == "up"
            j = i - 1 if up else i + 1
            if 0 <= j < len(s.points):
                s.points[i], s.points[j] = s.points[j], s.points[i]
            else:
                si = doc.sections.index(s)
                sj = si - 1 if up else si + 1
                if 0 <= sj < len(doc.sections):
                    s.points.remove(p)
                    target = doc.sections[sj]
                    target.points.insert(len(target.points) if up else 0, p)
        else:
            raise OpError(f"unknown operation {op}")

        sha = repository.write_doc(slug, key, "summary", doc, base_sha, reindex=False)
        if removed_points:
            _remove_cards_for_points(slug, key, removed_points)
        from . import sync

        sync.reindex(slug, key)
        result["sha"] = sha
        return result


# ------------------------------------------------------------- flashcards/quiz


def flashcard_from_payload(data: dict, key: str, point_key: str) -> Flashcard:
    card = Flashcard(
        key=key,
        point_key=point_key,
        front_en=_text(data, "front_en"),
        front_hu=_text(data, "front_hu"),
        back_en=_text(data, "back_en"),
        back_hu=_text(data, "back_hu"),
        figure=_figure(data.get("figure")),
    )
    if not card.front_en or not card.back_en:
        raise OpError("front_en and back_en are required")
    card.front_hu = card.front_hu or card.front_en
    card.back_hu = card.back_hu or card.back_en
    return card


def question_from_payload(data: dict, key: str, point_key: str) -> QuizQuestion:
    options = []
    for o in data.get("options") or []:
        en = (o.get("en") or "").strip()
        hu = (o.get("hu") or "").strip() or en
        options.append(QuizOption(en=en, hu=hu))
    if len(options) != 4 or any(not o.en for o in options):
        raise OpError("exactly 4 non-empty options are required")
    correct = data.get("correct_index")
    if correct not in (0, 1, 2, 3):
        raise OpError("correct_index must be 0..3")
    q = QuizQuestion(
        key=key,
        point_key=point_key,
        question_en=_text(data, "question_en"),
        question_hu=_text(data, "question_hu"),
        options=options,
        correct_index=correct,
        why_en=_text(data, "why_en"),
        why_hu=_text(data, "why_hu"),
        figure=_figure(data.get("figure")),
    )
    if not q.question_en:
        raise OpError("question_en is required")
    q.question_hu = q.question_hu or q.question_en
    return q


def card_op(slug: str, key: str, kind: str, op: str, payload: dict, base_sha: str | None) -> dict:
    """kind: 'flashcards' | 'quiz'; op: 'upsert' | 'delete'."""
    if kind not in ("flashcards", "quiz"):
        raise OpError("kind must be flashcards or quiz")
    with data_lock():
        doc = _load(slug, key, kind, base_sha)
        items: list = doc.cards if kind == "flashcards" else doc.questions
        result: dict = {}
        if op == "upsert":
            data = payload.get("item") or {}
            item_key = data.get("key") or ""
            existing = next((i for i in items if i.key == item_key), None) if item_key else None
            if existing:
                point_key = existing.point_key
            else:
                point_key = data.get("point_key") or ""
                if point_key not in _point_order(slug, key):
                    raise OpError(f"unknown point {point_key}")
                used = {split_card_key(i.key)[1] for i in items if i.point_key == point_key}
                n = 1
                while n in used:
                    n += 1
                item_key = card_key(point_key, n)
            build = flashcard_from_payload if kind == "flashcards" else question_from_payload
            new_item = build(data, item_key, point_key)
            if existing:
                items[items.index(existing)] = new_item
            else:
                items.append(new_item)
                order = _point_order(slug, key)
                items.sort(key=lambda i: (order.get(i.point_key, 10**6), split_card_key(i.key)[1]))
            result["key"] = item_key
        elif op == "delete":
            target = next((i for i in items if i.key == payload.get("key")), None)
            if target is None:
                raise OpError("unknown item")
            items.remove(target)
        else:
            raise OpError(f"unknown operation {op}")
        result["sha"] = repository.write_doc(slug, key, kind, doc, base_sha)
        return result
