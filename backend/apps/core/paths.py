"""Where things live on disk. All paths are derived from settings roots."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings

from .files import check_key, check_slug


def material_media_dir(slug: str) -> Path:
    return Path(settings.MEDIA_ROOT) / check_slug(slug)


def material_content_dir(slug: str) -> Path:
    return Path(settings.CONTENT_ROOT) / check_slug(slug)


def chapter_dir(slug: str, key: str) -> Path:
    return material_content_dir(slug) / check_key(key)


def source_dir(slug: str, key: str) -> Path:
    """Gitignored scratch area with extracted text and candidate figures for Claude Code."""
    return chapter_dir(slug, key) / "_source"


def figures_dir(slug: str, key: str) -> Path:
    return chapter_dir(slug, key) / "figures"


def notes_dir(slug: str) -> Path:
    return material_content_dir(slug) / "notes"
