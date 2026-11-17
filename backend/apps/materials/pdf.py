"""PDF processing with PyMuPDF: outline, chapter slices, text and figure extraction."""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf
from django.conf import settings

from apps.core import tables
from apps.core.paths import material_media_dir, source_dir

# Images repeated on more pages than this are decorative (icons, logos).
DECORATIVE_MIN_PAGES = 20
# Minimum rendered size (PDF points) for an image to count as a figure.
MIN_FIG_W, MIN_FIG_H = 120, 80
FIGURE_DPI = 160
CAPTION_MAX_GAP = 60  # points below the image


@dataclass
class FigureCandidate:
    key: str
    page: int
    caption: str
    file: str  # path relative to the chapter dir, e.g. "_source/figures/p0047-x1015.jpg"
    width: int
    height: int
    bbox: list[float]


def pdf_path(material: tables.MaterialRow) -> Path:
    return Path(settings.MEDIA_ROOT) / material.pdf_path


def open_pdf(material: tables.MaterialRow) -> pymupdf.Document:
    return pymupdf.open(pdf_path(material))


def read_toc(path: Path) -> tuple[list, int]:
    with pymupdf.open(path) as doc:
        return doc.get_toc(simple=True), doc.page_count


def _atomic_save(doc: pymupdf.Document, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    doc.save(tmp, garbage=3, deflate=True)
    os.replace(tmp, target)


def chapter_slice(material: tables.MaterialRow, chapter: tables.ChapterRow) -> Path:
    """A cached PDF containing only the chapter's pages."""
    target = material_media_dir(material.slug) / "slices" / f"{chapter.key}-{chapter.start_page}-{chapter.end_page}.pdf"
    if target.exists():
        return target
    with open_pdf(material) as src, pymupdf.open() as out:
        out.insert_pdf(src, from_page=chapter.start_page - 1, to_page=chapter.end_page - 1)
        out.set_metadata({"title": f"{chapter.code} {chapter.title}".strip()})
        _atomic_save(out, target)
    return target


# ---------------------------------------------------------------- text


def chapter_text(material: tables.MaterialRow, chapter: tables.ChapterRow) -> str:
    """Plain text of the chapter with page markers, for Claude Code to read."""
    parts = [f"# {chapter.code} · {chapter.title}".strip(" ·"), ""]
    with open_pdf(material) as doc:
        for pno in range(chapter.start_page, chapter.end_page + 1):
            text = doc[pno - 1].get_text("text").strip()
            parts.append(f"<!-- page {pno} -->")
            parts.append(text)
            parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------- figures


def decorative_xrefs(material: tables.MaterialRow) -> set[int]:
    """xrefs used on many pages (icons). Cached per material in media/."""
    cache = material_media_dir(material.slug) / "decorative_xrefs.json"
    if cache.exists():
        return set(json.loads(cache.read_text()))
    counts: Counter[int] = Counter()
    with open_pdf(material) as doc:
        for page in doc:
            for xref in {img[0] for img in page.get_images(full=True)}:
                counts[xref] += 1
    result = sorted(x for x, n in counts.items() if n > DECORATIVE_MIN_PAGES)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result))
    return set(result)


def _caption_below(page: pymupdf.Page, rect: pymupdf.Rect) -> str:
    best: tuple[float, str] | None = None
    for x0, y0, x1, y1, text, *_ in page.get_text("blocks"):
        text = " ".join(text.split())
        if not text:
            continue
        gap = y0 - rect.y1
        overlaps = min(x1, rect.x1) - max(x0, rect.x0) > 0
        if -2 <= gap <= CAPTION_MAX_GAP and overlaps and (best is None or gap < best[0]):
            best = (gap, text)
    return best[1] if best else ""


def extract_figures(material: tables.MaterialRow, chapter: tables.ChapterRow) -> list[FigureCandidate]:
    """Render every real figure of the chapter into ``_source/figures`` and index it."""
    out_dir = source_dir(material.slug, chapter.key) / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    skip = decorative_xrefs(material)
    found: list[FigureCandidate] = []
    seen: set[int] = set()
    with open_pdf(material) as doc:
        for pno in range(chapter.start_page, chapter.end_page + 1):
            page = doc[pno - 1]
            for img in page.get_images(full=True):
                xref = img[0]
                if xref in skip or xref in seen:
                    continue
                for rect in page.get_image_rects(xref):
                    if rect.width < MIN_FIG_W or rect.height < MIN_FIG_H:
                        continue
                    seen.add(xref)
                    try:
                        ext = doc.extract_image(xref).get("ext", "png")
                    except Exception:  # pragma: no cover - broken image streams
                        ext = "png"
                    suffix = "jpg" if ext in ("jpeg", "jpg", "jpx") else "png"
                    key = f"p{pno:04d}-x{xref}"
                    pix = page.get_pixmap(clip=rect, dpi=FIGURE_DPI)
                    target = out_dir / f"{key}.{suffix}"
                    if suffix == "jpg":
                        pix.save(target, jpg_quality=85)
                    else:
                        pix.save(target)
                    found.append(
                        FigureCandidate(
                            key=key,
                            page=pno,
                            caption=_caption_below(page, rect),
                            file=f"_source/figures/{target.name}",
                            width=pix.width,
                            height=pix.height,
                            bbox=[round(v, 1) for v in rect],
                        )
                    )
                    break
    index = source_dir(material.slug, chapter.key) / "figures.json"
    index.write_text(json.dumps([asdict(f) for f in found], indent=2, ensure_ascii=False), encoding="utf-8")
    return found


def crop_figure(
    material: tables.MaterialRow, chapter: tables.ChapterRow, page_no: int, bbox: list[float], caption: str = ""
) -> FigureCandidate:
    """Render a page region (e.g. a vector diagram) as an extra candidate figure."""
    out_dir = source_dir(material.slug, chapter.key) / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open_pdf(material) as doc:
        page = doc[page_no - 1]
        rect = pymupdf.Rect(*bbox) if bbox else page.rect
        key = f"p{page_no:04d}-crop{int(rect.x0)}-{int(rect.y0)}"
        pix = page.get_pixmap(clip=rect, dpi=FIGURE_DPI)
        target = out_dir / f"{key}.png"
        pix.save(target)
        cand = FigureCandidate(
            key=key,
            page=page_no,
            caption=caption or _caption_below(page, rect),
            file=f"_source/figures/{target.name}",
            width=pix.width,
            height=pix.height,
            bbox=[round(v, 1) for v in rect],
        )
    index = source_dir(material.slug, chapter.key) / "figures.json"
    existing = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    existing = [e for e in existing if e["key"] != key] + [asdict(cand)]
    index.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    return cand


def load_candidates(slug: str, key: str) -> list[dict]:
    index = source_dir(slug, key) / "figures.json"
    if not index.exists():
        return []
    return json.loads(index.read_text(encoding="utf-8"))
