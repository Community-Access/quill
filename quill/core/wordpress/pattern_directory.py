"""WordPress.org's Pattern Directory, and pattern categories (wordpress.md 9.15).

**The directory** is searched through the site's own route
(``wp/v2/pattern-directory/patterns``): the site asks WordPress.org, so QUILL
reaches no new host. Each pattern is described in words before it goes in --
what it is for, the blocks it holds in order, and how many pictures it brings
with no alternative text -- because a pattern is a whole layout, and inserting
one unseen is the thing a screen-reader user cannot undo by looking.

**Pattern categories** (``wp_pattern_category``) group and filter Synced
Patterns.

Wx-free; every request goes through
:class:`~quill.core.wordpress.api.WordPressApi`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import plain_text, raw_text, rendered

DIRECTORY_ROUTE = r"^/wp/v2/pattern-directory/patterns$"
CATEGORY_ROUTE = r"^/wp/v2/wp_pattern_category$"

_OPENER = re.compile(r"<!--\s+wp:([a-z0-9-]+/)?([a-z0-9-]+)")
_IMG = re.compile(r"<img\b[^>]*>", re.I)
_ALT = re.compile(r"\balt\s*=\s*(\"([^\"]*)\"|'([^']*)')", re.I)


@dataclass(frozen=True)
class DirectoryPattern:
    id: int
    title: str
    description: str
    content: str
    categories: tuple[str, ...] = ()

    def row(self) -> str:
        about = self.description or "no description"
        return f"{self.title}: {about}"


def search(api: WordPressApi, words: str, *, per_page: int = 30) -> list[DirectoryPattern]:
    raw = api.get("wp/v2/pattern-directory/patterns", search=words.strip(), per_page=per_page)
    found: list[DirectoryPattern] = []
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict):
            continue
        content = raw_text(entry.get("content"))
        if not content.strip():
            continue
        found.append(
            DirectoryPattern(
                id=int(entry.get("id", 0) or 0),
                title=rendered(entry.get("title")) or "Untitled pattern",
                description=plain_text(rendered(entry.get("description"))),
                content=content,
                categories=tuple(str(c) for c in entry.get("categories", []) or []),
            )
        )
    return found


def block_list(content: str) -> list[str]:
    """The blocks in order, a run of the same one counted: ["Cover", "Paragraph (3)"]."""
    names = [_block_word(m.group(2)) for m in _OPENER.finditer(content)]
    out: list[str] = []
    count = 0
    for i, name in enumerate(names):
        count += 1
        if i + 1 == len(names) or names[i + 1] != name:
            out.append(f"{name} ({count})" if count > 1 else name)
            count = 0
    return out


def _block_word(slug: str) -> str:
    return slug.replace("-", " ").capitalize()


def pictures_without_alt(content: str) -> tuple[int, int]:
    """``(pictures, without alternative text)`` in *content*."""
    images = _IMG.findall(content)
    missing = 0
    for tag in images:
        match = _ALT.search(tag)
        text = (match.group(2) or match.group(3) or "") if match else ""
        if not text.strip():
            missing += 1
    return len(images), missing


def describe(pattern: DirectoryPattern) -> str:
    """What the pattern is, in words, for the question before it goes in."""
    parts = [f"{pattern.title}, from WordPress.org's Pattern Directory."]
    if pattern.description:
        parts.append(pattern.description.rstrip(".") + ".")
    blocks = block_list(pattern.content)
    if blocks:
        parts.append("Blocks, in order: " + ", ".join(blocks) + ".")
    pictures, missing = pictures_without_alt(pattern.content)
    if pictures:
        noun = "picture" if pictures == 1 else "pictures"
        if missing:
            parts.append(
                f"It brings {pictures} {noun}, {missing} with no alternative text. Describe "
                "each one or replace it before you publish."
            )
        else:
            parts.append(f"It brings {pictures} {noun}, each with alternative text.")
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# Pattern categories, for Synced Patterns


@dataclass(frozen=True)
class PatternCategories:
    #: (id, name) in the site's order.
    names: tuple[tuple[int, str], ...]
    #: pattern id -> the category ids it is in.
    membership: dict[int, tuple[int, ...]]

    def choices(self, pattern_ids: list[int]) -> list[tuple[str, list[int]]]:
        """``(row, pattern ids)``: All first, then each category in use, then None."""
        rows: list[tuple[str, list[int]]] = [
            (_counted("All patterns", len(pattern_ids)), list(pattern_ids))
        ]
        for cat_id, name in self.names:
            ids = [p for p in pattern_ids if cat_id in self.membership.get(p, ())]
            if ids:
                rows.append((_counted(name, len(ids)), ids))
        loose = [p for p in pattern_ids if not self.membership.get(p)]
        if loose and len(rows) > 1:
            rows.append((_counted("No category", len(loose)), loose))
        return rows


def _counted(name: str, count: int) -> str:
    return f"{name}, {count} {'pattern' if count == 1 else 'patterns'}"


def load_categories(api: WordPressApi) -> PatternCategories:
    """The site's pattern categories and which synced patterns are in each.

    A site or role without them gets empty categories, never a failure:
    Synced Patterns then opens as it always did.
    """
    try:
        terms = list(api.iter_collection("wp/v2/wp_pattern_category", {"_fields": "id,name"}))
        blocks = list(
            api.iter_collection(
                "wp/v2/blocks", {"context": "edit", "_fields": "id,wp_pattern_category"}
            )
        )
    except WordPressApiError:
        return PatternCategories((), {})
    names = tuple(
        (int(t.get("id", 0) or 0), rendered(t.get("name")) or str(t.get("id"))) for t in terms
    )
    membership: dict[int, tuple[int, ...]] = {}
    for block in blocks:
        cats: Any = block.get("wp_pattern_category") or []
        if isinstance(cats, list):
            membership[int(block.get("id", 0) or 0)] = tuple(int(c) for c in cats)
    return PatternCategories(names, membership)
