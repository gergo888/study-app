"""Safe path handling and authenticated file responses."""

from __future__ import annotations

import mimetypes
import re
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")


def check_slug(slug: str) -> str:
    if not SLUG_RE.match(slug or ""):
        raise Http404("invalid material slug")
    return slug


def check_key(key: str) -> str:
    if not KEY_RE.match(key or ""):
        raise Http404("invalid chapter key")
    return key


def safe_join(root: Path, relative: str) -> Path:
    """Join ``relative`` under ``root`` and refuse anything that escapes it."""
    root = root.resolve()
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise Http404("path outside of root")
    return target


def serve_file(path: Path, *, download_name: str | None = None, inline: bool = True) -> HttpResponse:
    if not path.is_file():
        raise Http404("file not found")
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if settings.USE_X_ACCEL_REDIRECT:
        # nginx maps /protected/media/ -> MEDIA_ROOT and /protected/content/ -> CONTENT_ROOT (internal).
        for prefix, root in (("media", settings.MEDIA_ROOT), ("content", settings.CONTENT_ROOT)):
            root = Path(root).resolve()
            if root in path.resolve().parents:
                rel = path.resolve().relative_to(root).as_posix()
                resp = HttpResponse(content_type=content_type)
                resp["X-Accel-Redirect"] = f"/protected/{prefix}/{rel}"
                if download_name:
                    disp = "inline" if inline else "attachment"
                    resp["Content-Disposition"] = f'{disp}; filename="{download_name}"'
                return resp
    resp = FileResponse(open(path, "rb"), content_type=content_type, as_attachment=not inline, filename=download_name or path.name)
    resp["Cache-Control"] = "private, max-age=300"
    return resp
