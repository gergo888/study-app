"""Shared API errors and the DRF exception handler."""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler


class Conflict(APIException):
    """The document changed on disk since the client loaded it (stale base_sha)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The document was changed in the meantime. Reload and try again."
    default_code = "conflict"


class InvalidDocument(APIException):
    """A Markdown document failed validation; ``detail`` carries the issues."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "invalid_document"

    def __init__(self, issues: list[dict], message: str = "The document is not valid."):
        super().__init__({"detail": message, "issues": issues})


def exception_handler(exc, context):
    return drf_exception_handler(exc, context)
