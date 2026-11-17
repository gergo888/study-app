from pathlib import Path

import pytest

from apps.materials import outline

TOC = [
    [1, "Preface", 2],
    [2, "About", 2],
    [1, "Lesson 1", 5],
    [2, "Installing Things", 5],
    [2, "Topic 1A", 6],
    [3, "Explain Cables", 6],
    [3, "USB", 8],
    [2, "Topic 1B", 15],
    [3, "Install Boards", 15],
    [2, "Summary", 30],
    [1, "Lesson 2", 32],
    [2, "Topic 2A", 33],
    [3, "Power", 33],
    [1, "Glossary", 50],
]


def test_topics_become_chapters_with_merged_titles_and_groups():
    specs = outline.build_chapters(TOC, 60, 2)
    assert [(s.key, s.code, s.title, s.start_page, s.end_page) for s in specs] == [
        ("1A", "Topic 1A", "Explain Cables", 6, 14),
        ("1B", "Topic 1B", "Install Boards", 15, 29),
        ("2A", "Topic 2A", "Power", 33, 49),
    ]
    assert specs[0].group_title == "Lesson 1" and specs[0].group_subtitle == "Installing Things"
    assert specs[0].sections == [("USB", 8)]


def test_suggest_level_prefers_reasonable_chapter_size():
    # level 1 averages ~16 pages per chapter, level 2 ~14
    assert outline.suggest_level(TOC, 60, target_pages=12) == 2
    assert outline.suggest_level(TOC, 60, target_pages=40) == 1


REAL_PDF = Path("/home/gergo/Downloads/comptia.pdf")


@pytest.mark.skipif(not REAL_PDF.exists(), reason="CompTIA PDF not available")
def test_real_comptia_outline():
    from apps.materials.pdf import read_toc

    toc, pages = read_toc(REAL_PDF)
    specs = outline.build_chapters(toc, pages, 2)
    assert len(specs) == 64
    assert len({s.group_title for s in specs}) == 20
    first = specs[0]
    assert (first.key, first.title, first.start_page, first.end_page) == ("1A", "Explain Cable Types and Connectors", 40, 70)
    assert outline.suggest_level(toc, pages) == 2
