"""Turn a PDF outline (``doc.get_toc()``) into chapters. Pure functions, no I/O.

TOC rows are ``[level, title, page]`` with 1-based pages. For the CompTIA book:

    [1, 'Lesson 1', 38]
    [2, 'Installing Motherboards and Connectors', 38]   <- lesson subtitle (no children)
    [2, 'Topic 1A', 40]                                 <- chapter (has children)
    [3, 'Explain Cable Types and Connectors', 40]       <- chapter title (merged)
    [3, 'Personal Computers', 41]                       <- section
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

CODE_RE = re.compile(
    r"^(topic|chapter|lesson|unit|part|module|section|week|day)\s+[\w.-]+$|^\d+[A-Za-z]?$",
    re.IGNORECASE,
)
KEY_FROM_CODE_RE = re.compile(r"(\d+(?:[.-]\d+)*[A-Za-z]?)\s*$")


@dataclass
class ChapterSpec:
    key: str
    order: int
    code: str
    title: str
    group_title: str
    group_subtitle: str
    start_page: int
    end_page: int
    sections: list[tuple[str, int]] = field(default_factory=list)  # (title, page)

    @property
    def pages(self) -> int:
        return self.end_page - self.start_page + 1


def _has_children(toc: list, i: int) -> bool:
    return i + 1 < len(toc) and toc[i + 1][0] > toc[i][0]


def _end_page(toc: list, i: int, page_count: int) -> int:
    level, _, start = toc[i]
    for j in range(i + 1, len(toc)):
        if toc[j][0] <= level and toc[j][2] > 0:
            return max(start, toc[j][2] - 1)
    return page_count


def _make_key(code: str, title: str, order: int, used: set[str]) -> str:
    m = KEY_FROM_CODE_RE.search(code) if code else None
    key = m.group(1).replace(".", "-") if m else f"c{order:02d}"
    key = re.sub(r"[^A-Za-z0-9_-]", "", key) or f"c{order:02d}"
    base, n = key, 2
    while key in used:
        key = f"{base}-{n}"
        n += 1
    used.add(key)
    return key


def build_chapters(toc: list, page_count: int, level: int) -> list[ChapterSpec]:
    """Chapters = outline entries at ``level`` that have sub-entries.

    If no entry at that level has children, every entry at that level is a chapter.
    """
    at_level = [i for i, row in enumerate(toc) if row[0] == level and row[2] > 0]
    with_children = [i for i in at_level if _has_children(toc, i)]
    chosen = with_children or at_level

    specs: list[ChapterSpec] = []
    used: set[str] = set()
    for order, i in enumerate(chosen, start=1):
        lvl, title, start = toc[i]
        title = title.strip()
        code = ""
        children: list[tuple[str, int]] = []
        j = i + 1
        while j < len(toc) and toc[j][0] > lvl:
            if toc[j][0] == lvl + 1:
                children.append((toc[j][1].strip(), toc[j][2]))
            j += 1
        if children and CODE_RE.match(title):
            code = title
            title = children[0][0]
            children = children[1:]

        # Group: nearest preceding entry one level up, plus its first childless child (subtitle).
        group_title = group_subtitle = ""
        for k in range(i - 1, -1, -1):
            if toc[k][0] < lvl:
                group_title = toc[k][1].strip()
                for m in range(k + 1, i):
                    if toc[m][0] == lvl and not _has_children(toc, m):
                        group_subtitle = toc[m][1].strip()
                        break
                break

        specs.append(
            ChapterSpec(
                key=_make_key(code, title, order, used),
                order=order,
                code=code,
                title=title,
                group_title=group_title,
                group_subtitle=group_subtitle,
                start_page=start,
                end_page=_end_page(toc, i, page_count),
                sections=children,
            )
        )
    return specs


def level_stats(toc: list, page_count: int) -> list[dict]:
    """For each outline level: how many chapters it would yield and their size."""
    out = []
    for level in sorted({row[0] for row in toc}):
        specs = build_chapters(toc, page_count, level)
        if not specs:
            continue
        pages = [s.pages for s in specs]
        out.append(
            {
                "level": level,
                "chapters": len(specs),
                "avg_pages": round(sum(pages) / len(pages), 1),
                "examples": [f"{s.code + ' · ' if s.code else ''}{s.title}" for s in specs[:3]],
            }
        )
    return out


def suggest_level(toc: list, page_count: int, target_pages: float = 20.0) -> int:
    """Pick the level whose chapters are closest to ``target_pages`` long (log scale)."""
    stats = [s for s in level_stats(toc, page_count) if s["chapters"] >= 2]
    if not stats:
        return 1
    return min(stats, key=lambda s: abs(math.log(max(s["avg_pages"], 0.5) / target_pages)))["level"]


def outline_tree(toc: list) -> list[dict]:
    """Nested outline for display: [{title, page, level, children: [...]}, ...]."""
    root: list[dict] = []
    stack: list[tuple[int, list]] = [(0, root)]
    for level, title, page in toc:
        node = {"title": title.strip(), "page": page, "level": level, "children": []}
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack[-1][1].append(node)
        stack.append((level, node["children"]))
    return root
