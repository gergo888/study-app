"""Every test runs against empty temporary DATA_ROOT / CONTENT_ROOT / MEDIA_ROOT."""

from datetime import datetime, timezone

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client

from apps.core import tables

PASSWORD = "correct horse battery"
_HASH = make_password(PASSWORD)


@pytest.fixture(autouse=True)
def isolated_storage(settings, tmp_path):
    settings.DATA_ROOT = tmp_path / "data"
    settings.CONTENT_ROOT = tmp_path / "content"
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.OWNER_PASSWORD_HASH = _HASH
    settings.ALLOWED_HOSTS = ["testserver"]
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {"login": "1000/min"}}
    return tmp_path


@pytest.fixture
def chapter():
    """A material with one chapter (no PDF), enough for content/study tests."""
    now = datetime.now(timezone.utc)
    tables.materials.update(
        lambda rows: rows
        + [tables.MaterialRow("demo", "Demo", "", "", "", 0, 2, None, None, "0,1,2,3,4,5,6", now)]
    )
    tables.chapters.update(
        lambda rows: rows
        + [tables.ChapterRow("demo", "1A", 1, "Topic 1A", "Cables", "Lesson 1", "Intro", 1, 10, "not_started", None, None, "")]
    )
    return ("demo", "1A")


@pytest.fixture
def client_logged_in():
    c = Client(enforce_csrf_checks=True)
    c.get("/api/auth/csrf/")
    token = c.cookies["csrftoken"].value
    r = c.post("/api/auth/login/", {"password": PASSWORD}, content_type="application/json", HTTP_X_CSRFTOKEN=token)
    assert r.status_code == 200
    c.csrf = c.cookies["csrftoken"].value
    return c


def post(c, url, data, method="post"):
    return getattr(c, method)(url, data, content_type="application/json", HTTP_X_CSRFTOKEN=c.csrf)


SUMMARY = """---
material: demo
chapter: 1A
title: Cables
---

# Cables

## USB {#usb}
hu: USB

- **USB 2.0 speed** {#usb-2}
  - hu-title: USB 2.0 sebesség
  - en: USB 2.0 HighSpeed runs at **480 Mbps** over up to 5 m.
  - hu: Az USB 2.0 HighSpeed **480 Mbps**, max. 5 m.
  - concepts: 480 Mbps | 480 Mb/s ; 5 m | 5 méter

- **Type B** {#type-b}
  - hu-title: Type B
  - en: Square connector used by printers.
  - hu: Négyzetes csatlakozó nyomtatókhoz.
  - concepts: square | négyzet ; printer | nyomtató
"""

FLASHCARDS = """---
material: demo
chapter: 1A
---

## usb-2
- front-en: USB 2.0 speed?
- front-hu: USB 2.0 sebesség?
- back-en: 480 Mbps
- back-hu: 480 Mbps

## type-b
- front-en: Printer connector?
- front-hu: Nyomtató csatlakozó?
- back-en: Type B
- back-hu: Type B
"""

QUIZ = """---
material: demo
chapter: 1A
---

## usb-2
- q-en: USB 2.0 speed?
- q-hu: USB 2.0 sebesség?
- [ ] 12 Mbps
- [x] 480 Mbps
- [ ] 5 Gbps
- [ ] 10 Gbps
- why-en: HighSpeed.
- why-hu: HighSpeed.

## type-b
- q-en: Printer connector?
- q-hu: Nyomtató csatlakozó?
- [x] Type B
- [ ] Type A
- [ ] Type C
- [ ] Micro-B
- why-en: Square.
- why-hu: Négyzetes.
"""


@pytest.fixture
def content(chapter, settings):
    folder = settings.CONTENT_ROOT / "demo" / "1A"
    folder.mkdir(parents=True)
    (folder / "summary.md").write_text(SUMMARY, encoding="utf-8")
    (folder / "flashcards.md").write_text(FLASHCARDS, encoding="utf-8")
    (folder / "quiz.md").write_text(QUIZ, encoding="utf-8")
    return folder
