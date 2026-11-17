"""Keep the CSV index (points.csv, cards.csv, doc_index.csv) in step with the Markdown.

The Markdown files are the source of truth for *content*; the CSV holds *state*
keyed by stable ids. ``ensure_indexed`` is cheap (hashes three small files) and
is called before every chapter read, so edits made by Claude Code are picked up
without any import step.

Stale detection: ``cards.basis_hash`` is the point's ``content_hash`` at the
time the card text last changed (or was confirmed "still valid"). When the
point changes but the card text does not, the card is stale.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from apps.core import tables
from apps.core.csvstore import data_lock, utcnow

from . import repository
from .mdformat import validate

INDEXED_KINDS = ("summary", "flashcards", "quiz")


def _index_rows(slug: str, key: str) -> dict[str, tables.DocIndexRow]:
    return {r.kind: r for r in tables.doc_index.filter(material=slug, chapter=key)}


def ensure_indexed(slug: str, key: str) -> None:
    rows = _index_rows(slug, key)
    for kind in INDEXED_KINDS:
        sha = repository.current_sha(slug, key, kind) or ""
        row = rows.get(kind)
        if (row.sha256 if row else "") != sha:
            reindex(slug, key)
            return


def reindex(slug: str, key: str) -> None:
    with data_lock():
        loaded = {k: repository.load(slug, key, k) for k in INDEXED_KINDS}
        now = utcnow()

        def parsed(kind: str):
            ld = loaded[kind]
            return ld.doc if ld.exists and not validate.has_errors(ld.issues) else None

        summary, flashcards, quiz = parsed("summary"), parsed("flashcards"), parsed("quiz")

        # points.csv
        point_hash: dict[str, str] = {}
        if summary is not None or not loaded["summary"].exists:
            new_points: dict[str, tables.PointRow] = {}
            if summary is not None:
                order = 0
                for section, p in summary.all_points():
                    order += 1
                    point_hash[p.key] = p.content_hash
                    new_points[p.key] = tables.PointRow(slug, key, p.key, section.key, order, p.content_hash, False)

            def apply_points(rows: list[tables.PointRow]) -> list[tables.PointRow]:
                out = []
                for r in rows:
                    if r.material == slug and r.chapter == key:
                        if r.point_key in new_points:
                            out.append(new_points.pop(r.point_key))
                        elif not r.archived:
                            out.append(dataclasses.replace(r, archived=True))
                        else:
                            out.append(r)
                    else:
                        out.append(r)
                return out + list(new_points.values())

            tables.points.update(apply_points)
        else:
            point_hash = {r.point_key: r.content_hash for r in tables.points.filter(material=slug, chapter=key) if not r.archived}

        # cards.csv
        def card_items(kind: str):
            if kind == "flashcard":
                doc, exists = flashcards, loaded["flashcards"].exists
                items = doc.cards if doc else []
            else:
                doc, exists = quiz, loaded["quiz"].exists
                items = doc.questions if doc else []
            return doc, exists, items

        for kind in ("flashcard", "quiz"):
            doc, exists, items = card_items(kind)
            if doc is None and exists:
                continue  # unparsable file: keep the previous state untouched
            fresh = {i.key: i for i in items}

            def apply_cards(rows: list[tables.CardRow], kind=kind, fresh=fresh) -> list[tables.CardRow]:
                out = []
                pending = dict(fresh)
                for r in rows:
                    if r.material != slug or r.chapter != key or r.kind != kind:
                        out.append(r)
                        continue
                    item = pending.pop(r.card_key, None)
                    if item is None:
                        out.append(r if r.archived else dataclasses.replace(r, archived=True))
                        continue
                    changes: dict = {"archived": False, "point_key": item.point_key}
                    if item.text_hash != r.text_hash:
                        changes["text_hash"] = item.text_hash
                        changes["basis_hash"] = point_hash.get(item.point_key, "")
                    out.append(dataclasses.replace(r, **changes))
                for item in pending.values():
                    out.append(
                        tables.CardRow(
                            material=slug,
                            chapter=key,
                            kind=kind,
                            card_key=item.key,
                            point_key=item.point_key,
                            text_hash=item.text_hash,
                            basis_hash=point_hash.get(item.point_key, ""),
                            archived=False,
                            fsrs_card_id=None,
                            fsrs_state=None,
                            step=None,
                            stability=None,
                            difficulty=None,
                            due=None,
                            last_review=None,
                            reps=0,
                            lapses=0,
                        )
                    )
                return out

            tables.cards.update(apply_cards)

        # doc_index.csv
        new_index = [
            tables.DocIndexRow(slug, key, kind, loaded[kind].sha or "", loaded[kind].ok if loaded[kind].exists else False, now)
            for kind in INDEXED_KINDS
        ]
        tables.doc_index.update(
            lambda rows: [r for r in rows if not (r.material == slug and r.chapter == key)] + new_index
        )


@dataclass
class ChapterHealth:
    stale: list[dict] = field(default_factory=list)  # {kind, card_key, point_key}
    missing: dict[str, list[str]] = field(default_factory=dict)  # point_key -> ["flashcard", "quiz"]
    orphans: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"stale": self.stale, "missing": self.missing, "orphans": self.orphans}

    @property
    def stale_points(self) -> set[str]:
        return {s["point_key"] for s in self.stale}


def chapter_health(slug: str, key: str) -> ChapterHealth:
    points = {r.point_key: r for r in tables.points.filter(material=slug, chapter=key) if not r.archived}
    cards = [r for r in tables.cards.filter(material=slug, chapter=key) if not r.archived]
    health = ChapterHealth()
    covered: dict[str, set[str]] = {p: set() for p in points}
    for c in cards:
        p = points.get(c.point_key)
        if p is None:
            health.orphans.append({"kind": c.kind, "card_key": c.card_key, "point_key": c.point_key})
            continue
        covered[c.point_key].add(c.kind)
        if c.basis_hash != p.content_hash:
            health.stale.append({"kind": c.kind, "card_key": c.card_key, "point_key": c.point_key})
    for pk, kinds in covered.items():
        missing = [k for k in ("flashcard", "quiz") if k not in kinds]
        if missing:
            health.missing[pk] = missing
    return health


def confirm_card(slug: str, key: str, kind: str, card_key: str) -> None:
    """Mark a card as still valid for the current version of its point."""
    with data_lock():
        point_hash = {r.point_key: r.content_hash for r in tables.points.filter(material=slug, chapter=key)}

        def apply(rows):
            for i, r in enumerate(rows):
                if r.material == slug and r.chapter == key and r.kind == kind and r.card_key == card_key:
                    rows[i] = dataclasses.replace(r, basis_hash=point_hash.get(r.point_key, r.basis_hash))
            return rows

        tables.cards.update(apply)
