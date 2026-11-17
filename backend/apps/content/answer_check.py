"""Offline check of a written-out bullet point against its key concepts.

Each concept is a group of acceptable variants (English and Hungarian), e.g.
``[["480 Mbps", "480 Mb/s"], ["Hi-Speed"]]``. A group counts as covered when
any variant appears (fuzzily) in the answer. The verdict is a suggestion; the
user confirms or overrides it in the UI.
"""

from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

MATCH_THRESHOLD = 85
CORRECT_AT = 0.75
PARTIAL_AT = 0.4


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^\w\s./+-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


NUMBER_UNIT_RE = re.compile(r"^(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>[a-z]{1,4})$")


def variant_matches(variant: str, answer_norm: str) -> bool:
    v = normalize(variant)
    if not v:
        return False
    m = NUMBER_UNIT_RE.match(v)
    if m:
        # "5 m" matches "5 m", "5m", "5 meters", "5 méter"; "480 mbps" matches "480mbps".
        num = "[.,]".join(re.escape(part) for part in re.split(r"[.,]", m.group("num")))
        unit = re.escape(m.group("unit"))
        return re.search(rf"(?<![\d.,]){num}\s*{unit}\w*", answer_norm) is not None
    if len(v.replace(" ", "")) <= 3:
        # Very short variants ("5 m", "IDE"): require a whole-word match.
        pattern = r"(?<!\w)" + r"\s*".join(re.escape(part) for part in v.split(" ")) + r"(?!\w)"
        return re.search(pattern, answer_norm) is not None
    if v in answer_norm or v.replace(" ", "") in answer_norm.replace(" ", ""):
        return True
    return fuzz.partial_ratio(v, answer_norm) >= MATCH_THRESHOLD


def check_answer(answer: str, concepts: list[list[str]]) -> dict:
    answer_norm = normalize(answer)
    matched, missed = [], []
    for group in concepts:
        (matched if any(variant_matches(v, answer_norm) for v in group) else missed).append(group)
    total = len(concepts)
    score = (len(matched) / total) if total else 0.0
    if not answer_norm:
        verdict = "wrong"
    elif score >= CORRECT_AT:
        verdict = "correct"
    elif score >= PARTIAL_AT:
        verdict = "partial"
    else:
        verdict = "wrong"
    return {"score": round(score, 2), "verdict": verdict, "matched": matched, "missed": missed}
