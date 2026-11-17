"""Validate a chapter's Markdown, adopt referenced figures, reindex, report problems.

Exit code 1 if anything is wrong (errors, or warnings unless --allow-warnings),
so Claude Code can loop until it passes.
"""

import shutil

from django.core.management.base import BaseCommand, CommandError

from apps.content import repository, sync
from apps.content.mdformat import validate
from apps.core.paths import chapter_dir, figures_dir, source_dir
from apps.materials import services


def _figures_of(doc, kind):
    if doc is None:
        return []
    if kind == "summary":
        return [p.figure for _, p in doc.all_points() if p.figure]
    items = doc.cards if kind == "flashcards" else doc.questions
    return [i.figure for i in items if i.figure]


class Command(BaseCommand):
    help = "Validate content/<slug>/<key>/*.md, copy referenced figures from _source/, reindex and report."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("key")
        parser.add_argument("--allow-warnings", action="store_true")

    def handle(self, *args, slug, key, allow_warnings, **opts):
        services.get_chapter(slug, key)
        folder = chapter_dir(slug, key)

        # 1. Adopt figures referenced as figures/<name> that only exist in _source/figures/.
        copied = 0
        for kind in ("summary", "flashcards", "quiz"):
            path = repository.doc_path(slug, key, kind)
            if not path.exists():
                continue
            doc, _ = repository.PARSERS[kind](path.read_text(encoding="utf-8"))
            for fig in _figures_of(doc, kind):
                if not validate.FIGURE_PATH_RE.match(fig.path):
                    continue
                target = folder / fig.path
                candidate = source_dir(slug, key) / "figures" / target.name
                if not target.exists() and candidate.exists():
                    figures_dir(slug, key).mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(candidate, target)
                    copied += 1
        if copied:
            self.stdout.write(f"adopted {copied} figure(s) from _source/figures")

        # 2. Validate each document and the links between them.
        issues = []
        loaded = {}
        for kind in ("summary", "flashcards", "quiz"):
            ld = repository.load(slug, key, kind)
            loaded[kind] = ld
            if not ld.exists:
                issues.append(validate.Issue(0, "file is missing", doc=kind))
            issues += ld.issues
        issues += validate.validate_links(loaded["summary"].doc, loaded["flashcards"].doc, loaded["quiz"].doc)

        # 3. Reindex state and report health.
        sync.reindex(slug, key)
        health = sync.chapter_health(slug, key)
        doc = loaded["summary"].doc
        n_points = len(doc.all_points()) if doc else 0
        n_fc = len(loaded["flashcards"].doc.cards) if loaded["flashcards"].doc else 0
        n_qz = len(loaded["quiz"].doc.questions) if loaded["quiz"].doc else 0
        self.stdout.write(f"{n_points} points · {n_fc} flashcards · {n_qz} quiz questions")
        for s in health.stale:
            issues.append(validate.Issue(0, f"{s['kind']} '{s['card_key']}' is stale: point '{s['point_key']}' changed after it was written", severity="warning", doc="flashcards" if s["kind"] == "flashcard" else "quiz"))

        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        for i in issues:
            style = self.style.ERROR if i.severity == "error" else self.style.WARNING
            self.stdout.write(style(str(i)))
        if errors or (warnings and not allow_warnings):
            raise CommandError(f"{len(errors)} error(s), {len(warnings)} warning(s)")
        self.stdout.write(self.style.SUCCESS("OK"))
