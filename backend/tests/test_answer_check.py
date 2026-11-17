from apps.content.answer_check import check_answer

CONCEPTS = [["480 Mbps", "480 Mb/s", "480 megabits"], ["5 m", "5 méter", "5 meters"], ["half-duplex", "félduplex"]]


def test_english_answer_correct():
    r = check_answer("USB 2 HighSpeed gives 480Mbps, cable up to 5 meters, and it is half duplex", CONCEPTS)
    assert r["verdict"] == "correct" and r["missed"] == []


def test_hungarian_answer_without_accents_matches():
    r = check_answer("480 mb/s sebesseg, max 5 meter kabel, felduplex", CONCEPTS)
    assert r["verdict"] == "correct"


def test_partial_and_wrong():
    assert check_answer("it is 480 megabits per second and 5m", CONCEPTS)["verdict"] == "partial"
    assert check_answer("no idea", CONCEPTS)["verdict"] == "wrong"
    assert check_answer("", CONCEPTS)["verdict"] == "wrong"


def test_number_unit_does_not_match_other_numbers():
    r = check_answer("15 mbps over 50 meters", [["5 m"]])
    assert r["matched"] == []
