"""Prepare a chapter for content generation by Claude Code.

Writes into content/<slug>/<key>/_source/ (gitignored):
  text.md        chapter text with <!-- page N --> markers and the section list
  figures/       candidate figures rendered from the PDF
  figures.json   key, page, caption, file, size, bbox for every candidate
and makes sure the reader slice exists.
"""

from django.core.management.base import BaseCommand

from apps.core.paths import chapter_dir, source_dir
from apps.materials import pdf, services


class Command(BaseCommand):
    help = "Extract text and candidate figures of a chapter into its _source/ folder for Claude Code."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("key")
        parser.add_argument("--skip-figures", action="store_true")

    def handle(self, *args, slug, key, skip_figures, **opts):
        material = services.get_material(slug)
        chapter = services.get_chapter(slug, key)
        src = source_dir(slug, key)
        src.mkdir(parents=True, exist_ok=True)

        pdf.chapter_slice(material, chapter)
        sections = services.chapter_sections(material, chapter)
        header = [
            f"<!-- material: {slug} · chapter: {key} · {chapter.code} · pages {chapter.start_page}-{chapter.end_page} -->",
            f"<!-- group: {chapter.group_title} · {chapter.group_subtitle} -->",
            "<!-- sections (title · start page): -->",
            *[f"<!--   {t} · p.{p} -->" for t, p in sections],
            "",
        ]
        (src / "text.md").write_text("\n".join(header) + pdf.chapter_text(material, chapter), encoding="utf-8")
        self.stdout.write(f"text      -> {src / 'text.md'}")

        if not skip_figures:
            figs = pdf.extract_figures(material, chapter)
            self.stdout.write(f"figures   -> {src / 'figures'} ({len(figs)} candidates, index: figures.json)")
            for f in figs:
                self.stdout.write(f"   {f.key:<22} p.{f.page:<5} {f.width}x{f.height}  {f.caption[:70]}")
        self.stdout.write(self.style.SUCCESS(f"Chapter folder: {chapter_dir(slug, key)}"))
