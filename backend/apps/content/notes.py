"""Material-level notes: one Markdown file per note in content/<slug>/notes/."""

from __future__ import annotations

import re

from django.http import Http404

from apps.core.csvstore import data_lock, utcnow
from apps.core.exceptions import Conflict
from apps.core.paths import notes_dir

from .mdformat import parse, render
from .mdformat.model import NoteDoc
from .ops import make_id
from .repository import _atomic_write, sha_of

NOTE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def _path(slug: str, note_id: str):
    if not NOTE_ID_RE.match(note_id):
        raise Http404("invalid note id")
    return notes_dir(slug) / f"{note_id}.md"


def _serialize(slug: str, note_id: str, text: str, with_body: bool = True) -> dict:
    doc, _ = parse.parse_note(text)
    out = {
        "id": note_id,
        "title": str(doc.meta.get("title") or note_id),
        "created": str(doc.meta.get("created") or ""),
        "updated": str(doc.meta.get("updated") or ""),
        "sha": sha_of(text),
    }
    if with_body:
        out["body"] = doc.body
    else:
        out["excerpt"] = doc.body[:160]
    return out


def list_notes(slug: str) -> list[dict]:
    folder = notes_dir(slug)
    if not folder.exists():
        return []
    notes = [_serialize(slug, p.stem, p.read_text(encoding="utf-8"), with_body=False) for p in folder.glob("*.md")]
    return sorted(notes, key=lambda n: n["updated"], reverse=True)


def get_note(slug: str, note_id: str) -> dict:
    path = _path(slug, note_id)
    if not path.exists():
        raise Http404("note not found")
    return _serialize(slug, note_id, path.read_text(encoding="utf-8"))


def create_note(slug: str, title: str, body: str = "") -> dict:
    with data_lock():
        folder = notes_dir(slug)
        taken = {p.stem for p in folder.glob("*.md")} if folder.exists() else set()
        note_id = make_id(title or "note", taken, "note")
        now = utcnow().isoformat(timespec="seconds")
        text = render.render_note(NoteDoc(meta={"title": title or "Untitled", "created": now, "updated": now}, body=body))
        _atomic_write(_path(slug, note_id), text)
    return get_note(slug, note_id)


def update_note(slug: str, note_id: str, title: str, body: str, base_sha: str) -> dict:
    with data_lock():
        path = _path(slug, note_id)
        if not path.exists():
            raise Http404("note not found")
        current = path.read_text(encoding="utf-8")
        if sha_of(current) != base_sha:
            raise Conflict()
        doc, _ = parse.parse_note(current)
        meta = dict(doc.meta)
        meta["title"] = title or meta.get("title") or "Untitled"
        meta["updated"] = utcnow().isoformat(timespec="seconds")
        _atomic_write(path, render.render_note(NoteDoc(meta=meta, body=body)))
    return get_note(slug, note_id)


def delete_note(slug: str, note_id: str) -> None:
    with data_lock():
        _path(slug, note_id).unlink(missing_ok=True)
