from apps.content.mdformat import parse, render, validate

from .conftest import FLASHCARDS, QUIZ, SUMMARY


def test_summary_roundtrip():
    doc, issues = parse.parse_summary(SUMMARY)
    assert issues == []
    assert [p.key for _, p in doc.all_points()] == ["usb-2", "type-b"]
    point = doc.find_point("usb-2")[1]
    assert point.title_hu == "USB 2.0 sebesség"
    assert point.concepts == [["480 Mbps", "480 Mb/s"], ["5 m", "5 méter"]]
    again, issues2 = parse.parse_summary(render.render_summary(doc))
    assert issues2 == [] and again == doc


def test_multiline_body_with_nested_list_roundtrips():
    text = SUMMARY.replace(
        "  - en: Square connector used by printers.",
        "  - en: Square connector used by:\n    - printers\n\n    - scanners",
    )
    doc, issues = parse.parse_summary(text)
    assert issues == []
    assert doc.find_point("type-b")[1].body_en == "Square connector used by:\n- printers\n\n- scanners"
    assert parse.parse_summary(render.render_summary(doc))[0] == doc


def test_cards_and_quiz_roundtrip():
    fc, i1 = parse.parse_flashcards(FLASHCARDS)
    qz, i2 = parse.parse_quiz(QUIZ)
    assert i1 == [] and i2 == []
    assert qz.questions[0].correct_index == 1
    assert parse.parse_flashcards(render.render_flashcards(fc))[0] == fc
    assert parse.parse_quiz(render.render_quiz(qz))[0] == qz


def test_option_pairs_and_escaping():
    q = "## p\n- q-en: Q\n- q-hu: K\n- [x] Yes | Igen\n- [ ] A \\| B\n- [ ] C\n- [ ] D\n"
    doc, issues = parse.parse_quiz(q)
    assert issues == []
    assert (doc.questions[0].options[0].en, doc.questions[0].options[0].hu) == ("Yes", "Igen")
    assert doc.questions[0].options[1].en == "A | B"


def test_errors_have_line_numbers():
    bad = SUMMARY.replace("  - concepts: square | négyzet ; printer | nyomtató", "  - colour: red")
    doc, issues = parse.parse_summary(bad)
    issues += validate.validate_summary(doc)
    messages = {i.message for i in issues}
    assert "unknown point field 'colour'" in messages
    assert "point 'type-b' has no concepts" in messages
    unknown = next(i for i in issues if "colour" in i.message)
    assert bad.splitlines()[unknown.line - 1].strip() == "- colour: red"


def test_quiz_rules():
    q = "## p\n- q-en: Q\n- q-hu: K\n- [x] A\n- [x] B\n- [ ] C\n"
    doc, issues = parse.parse_quiz(q)
    msgs = [i.message for i in issues + validate.validate_quiz(doc)]
    assert any("exactly 4 options" in m for m in msgs)
    assert any("more than one correct" in m for m in msgs)


def test_link_warnings():
    summary, _ = parse.parse_summary(SUMMARY)
    fc, _ = parse.parse_flashcards(FLASHCARDS.split("## type-b")[0])
    qz, _ = parse.parse_quiz(QUIZ + "\n## ghost\n- q-en: x\n- q-hu: y\n- [x] a\n- [ ] b\n- [ ] c\n- [ ] d\n")
    msgs = [i.message for i in validate.validate_links(summary, fc, qz)]
    assert "point 'type-b' has no flashcard" in msgs
    assert "quiz question 'ghost' refers to unknown point 'ghost'" in msgs
