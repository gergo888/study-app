from django.test import Client

from apps.core import tables

from .conftest import post


def test_endpoints_require_login(chapter):
    c = Client()
    for url in ["/api/materials/", "/api/chapters/demo/1A/", "/api/chapters/demo/1A/summary/", "/api/stats/dashboard/", "/api/practice/session/?due=1"]:
        assert c.get(url).status_code == 401, url


def test_wrong_password_and_csrf(chapter):
    c = Client(enforce_csrf_checks=True)
    assert c.post("/api/auth/login/", {"password": "x"}, content_type="application/json").status_code == 403  # no CSRF token
    c.get("/api/auth/csrf/")
    r = c.post("/api/auth/login/", {"password": "wrong"}, content_type="application/json", HTTP_X_CSRFTOKEN=c.cookies["csrftoken"].value)
    assert r.status_code == 400


def test_password_change_logs_out_sessions(client_logged_in, chapter, settings):
    assert client_logged_in.get("/api/materials/").status_code == 200
    settings.OWNER_PASSWORD_HASH = "pbkdf2_sha256$1$x$changed"
    assert client_logged_in.get("/api/materials/").status_code == 401


def test_writes_need_csrf(client_logged_in, content):
    r = client_logged_in.post("/api/chapters/demo/1A/summary/", {"op": "add_section", "heading_en": "X"}, content_type="application/json")
    assert r.status_code == 403


def test_summary_conflict_and_invalid_raw(client_logged_in, content):
    r = post(client_logged_in, "/api/chapters/demo/1A/summary/", {"op": "delete_point", "point_key": "usb-2", "base_sha": "stale"})
    assert r.status_code == 409
    raw = client_logged_in.get("/api/chapters/demo/1A/documents/quiz/").json()
    r = post(client_logged_in, "/api/chapters/demo/1A/documents/quiz/", {"text": raw["text"].replace("- [x] 480 Mbps", "- [ ] 480 Mbps"), "base_sha": raw["sha"]}, method="put")
    assert r.status_code == 422
    assert any("no correct option" in i["message"] for i in r.json()["issues"])


def test_quiz_answers_give_xp_and_learn_chapter(client_logged_in, content):
    session = client_logged_in.get("/api/practice/session/?mode=quiz&material=demo&chapter=1A").json()
    assert [i["key"] for i in session["items"]] == ["usb-2", "type-b"]

    r = post(client_logged_in, "/api/practice/answer/", {"material": "demo", "chapter": "1A", "kind": "quiz", "card_key": "usb-2", "selected_index": 0})
    assert r.json()["correct"] is False and r.json()["xp_awarded"] == 0
    r = post(client_logged_in, "/api/practice/answer/", {"material": "demo", "chapter": "1A", "kind": "quiz", "card_key": "type-b", "selected_index": 0})
    body = r.json()
    assert body["correct"] is True and body["xp_awarded"] == 10
    assert body["chapter_learned"] == "quiz"  # every point has now been through the quiz

    ch = tables.chapters.first(material="demo", key="1A")
    assert ch.status == "learned" and ch.learned_via == "quiz"
    card = tables.cards.first(kind="quiz", card_key="type-b")
    assert card.reps == 1 and card.due is not None
    assert sum(x.amount for x in tables.xp.all()) == 10
    assert len(tables.review_log.all()) == 2


def test_flashcard_ratings_and_reveal_rule(client_logged_in, content):
    r = post(client_logged_in, "/api/practice/answer/", {"material": "demo", "chapter": "1A", "kind": "flashcard", "card_key": "usb-2", "rating": 1})
    assert r.json()["xp_awarded"] == 0
    r = post(client_logged_in, "/api/practice/answer/", {"material": "demo", "chapter": "1A", "kind": "flashcard", "card_key": "usb-2", "rating": 3})
    assert r.json()["xp_awarded"] == 10

    # Memorize mode: revealing every point also counts as learned.
    for key in ("usb-2", "type-b"):
        r = post(client_logged_in, f"/api/chapters/demo/1A/points/{key}/activity/", {"kind": "reveal", "result": "seen"})
    assert r.json()["chapter_learned"] == "reveal"
    progress = client_logged_in.get("/api/chapters/demo/1A/summary/").json()["sections"][0]["points"][0]["progress"]
    assert progress["flashcard"]["result"] == "correct" and progress["reveal"]["result"] == "seen"


def test_check_answer_endpoint(client_logged_in, content):
    r = post(client_logged_in, "/api/chapters/demo/1A/points/usb-2/check-answer/", {"text": "480 mb/s és 5 méter", "lang": "hu"})
    assert r.json()["verdict"] == "correct"
    assert r.json()["original"].startswith("Az USB 2.0")


def test_manual_status_and_plan(client_logged_in, chapter):
    r = post(client_logged_in, "/api/chapters/demo/1A/", {"status": "learned"}, method="patch")
    assert r.json()["learned_via"] == "manual"
    r = post(client_logged_in, "/api/materials/demo/plan/", {"weekdays": [0, 1, 2, 3, 4]})
    assert r.status_code == 200 and r.json()["learned"] == 1
    assert tables.plan.first(material="demo", chapter="1A") is not None


def test_figure_files_are_path_safe(client_logged_in, content):
    (content / "figures").mkdir()
    (content / "figures" / "a.png").write_bytes(b"\x89PNG")
    assert client_logged_in.get("/api/chapters/demo/1A/files/figures/a.png").status_code == 200
    assert client_logged_in.get("/api/chapters/demo/1A/files/summary.md").status_code == 404
    assert client_logged_in.get("/api/chapters/demo/1A/files/figures/../../../../etc/passwd").status_code == 404


def test_chapter_planned_for_today_is_not_behind(client_logged_in, chapter):
    r = post(client_logged_in, "/api/materials/demo/plan/", {"weekdays": [0, 1, 2, 3, 4, 5, 6]})
    body = r.json()
    assert body["scheduled_by_today"] == 1 and body["behind"] == 0 and body["on_track"] is True
