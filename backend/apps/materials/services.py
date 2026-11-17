"""Material and chapter operations on top of the CSV tables."""

from __future__ import annotations

import dataclasses
import re
import shutil
import unicodedata
from pathlib import Path

from django.conf import settings
from django.http import Http404

from apps.core import tables
from apps.core.csvstore import data_lock, utcnow
from apps.core.files import check_key, check_slug
from apps.core.paths import material_media_dir

from . import outline, pdf

STATUSES = ("not_started", "reading", "read", "learned")


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:60] or "material"


def get_material(slug: str) -> tables.MaterialRow:
    row = tables.materials.first(slug=check_slug(slug))
    if row is None:
        raise Http404("material not found")
    return row


def get_chapter(slug: str, key: str) -> tables.ChapterRow:
    row = tables.chapters.first(material=check_slug(slug), key=check_key(key))
    if row is None:
        raise Http404("chapter not found")
    return row


def material_chapters(slug: str) -> list[tables.ChapterRow]:
    return sorted(tables.chapters.filter(material=slug), key=lambda c: c.order)


def create_material(title: str, description: str = "", slug: str | None = None) -> tables.MaterialRow:
    with data_lock():
        base = check_slug(slug or slugify(title))
        existing = {m.slug for m in tables.materials.all()}
        candidate, n = base, 2
        while candidate in existing:
            candidate = f"{base}-{n}"
            n += 1
        row = tables.MaterialRow(
            slug=candidate,
            title=title.strip(),
            description=description.strip(),
            pdf_path="",
            pdf_name="",
            page_count=0,
            chapter_level=0,
            plan_start=None,
            plan_target=None,
            study_weekdays="0,1,2,3,4,5,6",
            created_at=utcnow(),
        )
        tables.materials.update(lambda rows: rows + [row])
        return row


def update_material(slug: str, **changes) -> tables.MaterialRow:
    with data_lock():
        row = dataclasses.replace(get_material(slug), **changes)
        tables.materials.upsert(row, key=("slug",))
        return row


def delete_material(slug: str) -> None:
    """Removes CSV state and the stored PDF. Markdown in content/ is left on disk on purpose."""
    with data_lock():
        get_material(slug)
        for table in (tables.materials,):
            table.update(lambda rows: [r for r in rows if r.slug != slug])
        for table in (tables.chapters, tables.plan, tables.doc_index, tables.points, tables.cards):
            table.update(lambda rows: [r for r in rows if r.material != slug])
        shutil.rmtree(material_media_dir(slug), ignore_errors=True)


def attach_pdf(slug: str, source: Path, original_name: str, *, move: bool = False, level: int | None = None) -> tables.MaterialRow:
    """Store the PDF under media/<slug>/ and (re)build chapters from its outline."""
    material = get_material(slug)
    media_dir = material_media_dir(slug)
    media_dir.mkdir(parents=True, exist_ok=True)
    target = media_dir / "source.pdf"
    tmp = media_dir / ".source.pdf.tmp"
    if move:
        shutil.move(str(source), tmp)
    else:
        shutil.copyfile(source, tmp)
    tmp.replace(target)
    # Old slices/caches belong to the previous file.
    shutil.rmtree(media_dir / "slices", ignore_errors=True)
    (media_dir / "decorative_xrefs.json").unlink(missing_ok=True)

    toc, page_count = pdf.read_toc(target)
    material = update_material(
        slug,
        pdf_path=target.relative_to(Path(settings.MEDIA_ROOT)).as_posix(),
        pdf_name=original_name,
        page_count=page_count,
    )
    chosen = level or (outline.suggest_level(toc, page_count) if toc else 0)
    if chosen:
        build_chapters(slug, chosen)
    return get_material(slug)


def material_toc(material: tables.MaterialRow) -> tuple[list, int]:
    if not material.pdf_path:
        return [], 0
    return pdf.read_toc(pdf.pdf_path(material))


def build_chapters(slug: str, level: int) -> list[tables.ChapterRow]:
    """(Re)build chapters at an outline level, keeping progress of chapters whose key survives."""
    material = get_material(slug)
    toc, page_count = material_toc(material)
    specs = outline.build_chapters(toc, page_count, level)
    with data_lock():
        old = {c.key: c for c in tables.chapters.filter(material=slug)}
        new_rows = []
        for s in specs:
            prev = old.get(s.key)
            new_rows.append(
                tables.ChapterRow(
                    material=slug,
                    key=s.key,
                    order=s.order,
                    code=s.code,
                    title=s.title,
                    group_title=s.group_title,
                    group_subtitle=s.group_subtitle,
                    start_page=s.start_page,
                    end_page=s.end_page,
                    status=prev.status if prev else "not_started",
                    read_at=prev.read_at if prev else None,
                    learned_at=prev.learned_at if prev else None,
                    learned_via=prev.learned_via if prev else "",
                )
            )
        tables.chapters.update(lambda rows: [r for r in rows if r.material != slug] + new_rows)
        update_material(slug, chapter_level=level)
        keys = {r.key for r in new_rows}
        tables.plan.update(lambda rows: [r for r in rows if r.material != slug or r.chapter in keys])
    return new_rows


def chapter_sections(material: tables.MaterialRow, chapter: tables.ChapterRow) -> list[tuple[str, int]]:
    toc, page_count = material_toc(material)
    for spec in outline.build_chapters(toc, page_count, material.chapter_level):
        if spec.key == chapter.key:
            return spec.sections
    return []


def set_chapter_status(slug: str, key: str, status: str, *, via: str = "manual") -> tables.ChapterRow:
    if status not in STATUSES:
        raise ValueError(f"unknown status {status}")
    with data_lock():
        ch = get_chapter(slug, key)
        now = utcnow()
        changes: dict = {"status": status}
        if status in ("read", "learned") and not ch.read_at:
            changes["read_at"] = now
        if status == "learned":
            changes["learned_at"] = ch.learned_at if ch.status == "learned" else now
            changes["learned_via"] = ch.learned_via if ch.status == "learned" else via
        else:
            changes["learned_at"] = None
            changes["learned_via"] = ""
        if status == "not_started":
            changes["read_at"] = None
        row = dataclasses.replace(ch, **changes)
        tables.chapters.upsert(row, key=("material", "key"))
        return row
