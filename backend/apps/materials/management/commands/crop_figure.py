"""Render a region of a PDF page as an extra candidate figure (for vector diagrams)."""

from django.core.management.base import BaseCommand, CommandError

from apps.materials import pdf, services


class Command(BaseCommand):
    help = "Render a page region (x0,y0,x1,y1 in PDF points; omit for the whole page) into _source/figures."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("key")
        parser.add_argument("page", type=int, help="1-based page number in the full PDF")
        parser.add_argument("bbox", nargs="?", default="", help="x0,y0,x1,y1")
        parser.add_argument("--caption", default="")

    def handle(self, *args, slug, key, page, bbox, caption, **opts):
        material = services.get_material(slug)
        chapter = services.get_chapter(slug, key)
        if not chapter.start_page <= page <= chapter.end_page:
            raise CommandError(f"page {page} is outside the chapter ({chapter.start_page}-{chapter.end_page})")
        box = [float(v) for v in bbox.split(",")] if bbox else []
        if box and len(box) != 4:
            raise CommandError("bbox must be x0,y0,x1,y1")
        cand = pdf.crop_figure(material, chapter, page, box, caption)
        self.stdout.write(self.style.SUCCESS(f"{cand.key} -> {cand.file} ({cand.width}x{cand.height})"))
