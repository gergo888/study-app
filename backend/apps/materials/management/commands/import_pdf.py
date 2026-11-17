"""Create (or update) a material from a local PDF and build its chapters."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.core import tables
from apps.materials import outline, services


class Command(BaseCommand):
    help = "Import a PDF into a material (creates the material if needed) and build chapters from its outline."

    def add_arguments(self, parser):
        parser.add_argument("slug", help="material slug, e.g. comptia-a-plus")
        parser.add_argument("pdf", help="path to the PDF file")
        parser.add_argument("--title", help="material title (default: PDF title)")
        parser.add_argument("--description", default="")
        parser.add_argument("--level", type=int, help="outline level to use for chapters (default: auto)")

    def handle(self, *args, slug, pdf, title, description, level, **opts):
        path = Path(pdf).expanduser()
        if not path.is_file():
            raise CommandError(f"{path} does not exist")
        if tables.materials.first(slug=slug) is None:
            if not title:
                import pymupdf

                with pymupdf.open(path) as doc:
                    title = (doc.metadata or {}).get("title") or path.stem
            services.create_material(title, description, slug=slug)
            self.stdout.write(f"Created material {slug!r}: {title}")
        material = services.attach_pdf(slug, path, path.name, level=level)
        toc, pages = services.material_toc(material)
        for s in outline.level_stats(toc, pages):
            mark = "*" if s["level"] == material.chapter_level else " "
            self.stdout.write(f" {mark} level {s['level']}: {s['chapters']} chapters, avg {s['avg_pages']} pages")
        chapters = services.material_chapters(slug)
        self.stdout.write(
            self.style.SUCCESS(f"{material.page_count} pages, {len(chapters)} chapters at level {material.chapter_level}.")
        )
        for c in chapters[:5]:
            self.stdout.write(f"   {c.key:>5}  pp. {c.start_page}-{c.end_page}  {c.title}  [{c.group_title}]")
