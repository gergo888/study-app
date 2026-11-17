import pytest

from apps.content import ops, repository, sync
from apps.core import tables
from apps.core.exceptions import Conflict, InvalidDocument


def test_index_created_from_markdown(content):
    sync.ensure_indexed("demo", "1A")
    assert {p.point_key for p in tables.points.all()} == {"usb-2", "type-b"}
    assert {(c.kind, c.card_key) for c in tables.cards.all()} == {
        ("flashcard", "usb-2"), ("flashcard", "type-b"), ("quiz", "usb-2"), ("quiz", "type-b"),
    }
    assert sync.chapter_health("demo", "1A").stale == []


def _point_payload(**over):
    base = {"title_en": "USB 2.0 speed", "title_hu": "USB 2.0 sebesség", "body_en": "480 Mbps, max 5 m.", "body_hu": "480 Mbps, max 5 m.", "concepts": "480 Mbps ; 5 m"}
    return {**base, **over}


def test_editing_point_marks_cards_stale_and_card_edit_clears_it(content):
    sync.ensure_indexed("demo", "1A")
    sha = repository.load("demo", "1A", "summary").sha
    ops.summary_op("demo", "1A", "update_point", {"point_key": "usb-2", "point": _point_payload()}, sha)
    stale = {(s["kind"], s["card_key"]) for s in sync.chapter_health("demo", "1A").stale}
    assert stale == {("flashcard", "usb-2"), ("quiz", "usb-2")}

    # Editing the flashcard (as Claude Code would) makes it fresh again.
    path = repository.doc_path("demo", "1A", "flashcards")
    path.write_text(path.read_text().replace("- back-en: 480 Mbps\n", "- back-en: 480 Mbps, up to 5 m\n", 1))
    sync.ensure_indexed("demo", "1A")
    stale = {(s["kind"], s["card_key"]) for s in sync.chapter_health("demo", "1A").stale}
    assert stale == {("quiz", "usb-2")}

    sync.confirm_card("demo", "1A", "quiz", "usb-2")
    assert sync.chapter_health("demo", "1A").stale == []


def test_update_point_rewrites_only_that_entry(content):
    before = repository.load("demo", "1A", "summary")
    ops.summary_op("demo", "1A", "update_point", {"point_key": "type-b", "point": {"title_en": "Type B", "body_en": "Square, beveled top; printers.", "title_hu": "Type B", "body_hu": "Négyzetes.", "concepts": "square ; printer"}}, before.sha)
    after = repository.load("demo", "1A", "summary")
    assert after.doc.find_point("usb-2")[1] == before.doc.find_point("usb-2")[1]
    assert after.doc.find_point("type-b")[1].body_en == "Square, beveled top; printers."


def test_stale_base_sha_conflicts(content):
    with pytest.raises(Conflict):
        ops.summary_op("demo", "1A", "delete_point", {"point_key": "usb-2"}, "not-the-current-sha")


def test_invalid_raw_document_is_rejected(content):
    sha = repository.load("demo", "1A", "quiz").sha
    bad = repository.load("demo", "1A", "quiz").text.replace("- [ ] 12 Mbps\n", "", 1)
    with pytest.raises(InvalidDocument):
        repository.write_text("demo", "1A", "quiz", bad, sha)


def test_deleting_point_cascades_and_archives_state(content):
    sync.ensure_indexed("demo", "1A")
    sha = repository.load("demo", "1A", "summary").sha
    ops.summary_op("demo", "1A", "delete_point", {"point_key": "type-b"}, sha)
    assert [c.key for c in repository.load("demo", "1A", "flashcards").doc.cards] == ["usb-2"]
    archived = {(c.kind, c.card_key) for c in tables.cards.all() if c.archived}
    assert archived == {("flashcard", "type-b"), ("quiz", "type-b")}
    assert tables.points.first(point_key="type-b").archived


def test_adding_point_reports_missing_cards(content):
    sha = repository.load("demo", "1A", "summary").sha
    res = ops.summary_op("demo", "1A", "add_point", {"section_key": "usb", "point": {"title_en": "USB-C", "body_en": "Reversible."}}, sha)
    assert res["key"] == "usb-c"
    assert sync.chapter_health("demo", "1A").missing == {"usb-c": ["flashcard", "quiz"]}
    # Hungarian falls back to English, concepts to the title.
    point = repository.load("demo", "1A", "summary").doc.find_point("usb-c")[1]
    assert point.body_hu == "Reversible." and point.concepts == [["USB-C"]]


def test_card_upsert_adds_numbered_extra_card(content):
    sha = repository.load("demo", "1A", "flashcards").sha
    res = ops.card_op("demo", "1A", "flashcards", "upsert", {"item": {"point_key": "usb-2", "front_en": "Max length?", "back_en": "5 m"}}, sha)
    assert res["key"] == "usb-2.2"
    text = repository.load("demo", "1A", "flashcards").text
    assert "## usb-2 (2)" in text
