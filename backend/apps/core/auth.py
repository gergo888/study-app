"""Single-user password authentication.

There is no user table. The owner's password hash lives in settings
(``OWNER_PASSWORD_HASH``, written to backend/.env by ``manage.py set_password``).
A successful login stores ``owner=True`` plus a fingerprint of the current hash
in the signed-cookie session; changing the password changes the fingerprint and
therefore logs out every existing session.
"""

from __future__ import annotations

import hashlib

from django.conf import settings
from django.contrib.auth.hashers import check_password
from rest_framework.authentication import SessionAuthentication


class Owner:
    """The one and only user. Quacks enough like a Django user for DRF."""

    pk = 1
    id = 1
    username = "owner"
    is_authenticated = True
    is_anonymous = False
    is_active = True

    def __str__(self) -> str:  # pragma: no cover - debugging aid
        return "owner"


OWNER = Owner()


def password_fingerprint() -> str:
    raw = settings.OWNER_PASSWORD_HASH or ""
    return hashlib.sha256(f"{settings.SECRET_KEY}:{raw}".encode()).hexdigest()[:24]


def verify_password(password: str) -> bool:
    if not settings.OWNER_PASSWORD_HASH:
        return False
    return check_password(password, settings.OWNER_PASSWORD_HASH)


def login_session(request) -> None:
    session = request.session
    session.cycle_key()
    session["owner"] = True
    session["pwfp"] = password_fingerprint()


def logout_session(request) -> None:
    request.session.flush()


def is_logged_in(request) -> bool:
    session = getattr(request, "session", None)
    if session is None:
        return False
    return bool(session.get("owner")) and session.get("pwfp") == password_fingerprint() and bool(
        settings.OWNER_PASSWORD_HASH
    )


class OwnerSessionAuthentication(SessionAuthentication):
    """DRF authentication backed by the signed-cookie session (CSRF enforced)."""

    def authenticate(self, request):
        if not is_logged_in(request._request):
            return None
        self.enforce_csrf(request)
        return (OWNER, None)

    def authenticate_header(self, request) -> str:
        # Makes DRF answer 401 (not 403) for unauthenticated requests.
        return 'Session realm="study-app"'
