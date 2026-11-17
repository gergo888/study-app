"""List flashcards/quiz questions that must be refreshed after summary edits."""

from django.core.management.base import BaseCommand

from apps.content import repository, sync
from apps.materials import services


class Command(BaseCommand):
    help = "Show stale cards and points without cards for a chapter (what Claude Code should regenerate)."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("key")

    def handle(self, *args, slug, key, **opts):
        services.get_chapter(slug, key)
        sync.ensure_indexed(slug, key)
        health = sync.chapter_health(slug, key)
        summary = repository.load(slug, key, "summary").doc
        titles = {p.key: p.title_en for _, p in summary.all_points()} if summary else {}
        if not health.stale and not health.missing and not health.orphans:
            self.stdout.write(self.style.SUCCESS("Nothing to refresh."))
            return
        for s in health.stale:
            self.stdout.write(f"STALE    {s['kind']:<9} {s['card_key']:<28} point: {s['point_key']} ({titles.get(s['point_key'], '?')})")
        for pk, kinds in health.missing.items():
            self.stdout.write(f"MISSING  {','.join(kinds):<9} {'':<28} point: {pk} ({titles.get(pk, '?')})")
        for o in health.orphans:
            self.stdout.write(f"ORPHAN   {o['kind']:<9} {o['card_key']:<28} point {o['point_key']} no longer exists")
