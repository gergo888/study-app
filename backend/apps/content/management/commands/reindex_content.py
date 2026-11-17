"""Rebuild points.csv / cards.csv / doc_index.csv from the Markdown files."""

from django.core.management.base import BaseCommand, CommandError

from apps.content import sync
from apps.core import tables


class Command(BaseCommand):
    help = "Reindex one chapter (slug key) or every chapter (--all)."

    def add_arguments(self, parser):
        parser.add_argument("slug", nargs="?")
        parser.add_argument("key", nargs="?")
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, slug, key, all, **opts):
        if all:
            targets = [(c.material, c.key) for c in tables.chapters.all()]
        elif slug and key:
            targets = [(slug, key)]
        else:
            raise CommandError("give <slug> <key> or --all")
        for s, k in targets:
            sync.reindex(s, k)
        self.stdout.write(self.style.SUCCESS(f"reindexed {len(targets)} chapter(s)"))
