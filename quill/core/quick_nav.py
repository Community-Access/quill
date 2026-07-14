"""Unified navigation index for Quick Nav (NAV-1) and Go to Anything (NAV-4).

Both features present the same underlying index of navigable landmarks in the
current document: headings, links, lists, list items, tables, block quotes,
bookmarks, and code blocks. This module is UI-agnostic and builds that index
from the browse navigation context (the same cache the QUILL key browse mode
uses), so the panel and the jumper always agree with what browse mode can reach.

Two *transient* nav types are also supported (#513) when the context supplies
their positions: ``Misspelling`` (the document's flagged words) and
``Search hit`` (matches of the active find query). The UI computes these on
demand for the Quick Nav panel rather than in the prewarmed browse cache, so
they appear in the live-count panel and the jumper alongside the landmarks.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

#: Flat element kinds and the browse-context key that holds their positions.
_FLAT_KINDS: tuple[tuple[str, str], ...] = (
    ("Link", "links"),
    ("List", "lists"),
    ("List item", "list_items"),
    ("Table", "tables"),
    ("Block quote", "block_quotes"),
    ("Bookmark", "bookmarks"),
    ("Code block", "code_blocks"),
    # Transient types (#513): present only when the UI augments the context.
    ("Misspelling", "misspellings"),
    ("Search hit", "search_hits"),
)


@dataclass(frozen=True)
class NavItem:
    """A single navigable landmark: its kind, a short preview, and position."""

    kind: str
    label: str
    position: int


def nav_category(kind: str) -> str:
    """Collapse ``Heading 1`` .. ``Heading 6`` into a single ``Heading`` category."""
    return "Heading" if kind.startswith("Heading") else kind


def _preview_at(text: str, position: int, *, limit: int = 80) -> str:
    """Return the trimmed line at ``position`` as a short preview string."""
    if position < 0 or position > len(text):
        return ""
    start = text.rfind("\n", 0, position) + 1
    end = text.find("\n", position)
    if end == -1:
        end = len(text)
    line = text[start:end].strip()
    if len(line) > limit:
        line = line[: limit - 1].rstrip() + "\u2026"
    return line


def build_nav_index(text: str, context: Mapping[str, object]) -> list[NavItem]:
    """Build the document's navigable-landmark index, ordered by position."""
    items: list[NavItem] = []
    headings_by_level = context.get("headings_by_level")
    if isinstance(headings_by_level, Mapping):
        for level in range(1, 7):
            positions = headings_by_level.get(level)
            if not isinstance(positions, Iterable):
                continue
            for pos in positions:
                if isinstance(pos, int):
                    preview = _preview_at(text, pos) or "(empty heading)"
                    items.append(NavItem(f"Heading {level}", preview, pos))
    for kind, key in _FLAT_KINDS:
        positions = context.get(key)
        if not isinstance(positions, Iterable):
            continue
        for pos in positions:
            if isinstance(pos, int):
                preview = _preview_at(text, pos) or kind
                items.append(NavItem(kind, preview, pos))
    items.sort(key=lambda item: (item.position, item.kind))
    return items


def nav_type_summary(items: Sequence[NavItem]) -> list[tuple[str, int]]:
    """Return ``(category, count)`` pairs in first-seen order for the panel."""
    counts: dict[str, int] = {}
    order: list[str] = []
    for item in items:
        category = nav_category(item.kind)
        if category not in counts:
            counts[category] = 0
            order.append(category)
        counts[category] += 1
    return [(category, counts[category]) for category in order]


def filter_nav_items(
    items: Sequence[NavItem],
    query: str = "",
    category: str | None = None,
) -> list[NavItem]:
    """Filter the index by a type-ahead ``query`` and/or a ``category``."""
    needle = query.strip().lower()
    result: list[NavItem] = []
    for item in items:
        if category and nav_category(item.kind) != category:
            continue
        if needle and needle not in item.label.lower() and needle not in item.kind.lower():
            continue
        result.append(item)
    return result


def nav_item_display(item: NavItem) -> str:
    """Return a one-line display string for an index entry."""
    return f"{item.kind}: {item.label}"


def include_nav_items(
    items: Sequence[NavItem],
    *,
    headings: bool = True,
    links: bool = True,
    lists: bool = True,
) -> list[NavItem]:
    """Drop element categories the user has switched off in Settings (SET-4).

    ``lists`` covers both ``List`` and ``List item`` entries. Categories without
    a dedicated toggle (tables, block quotes, bookmarks, code blocks) are always
    kept.
    """
    result: list[NavItem] = []
    for item in items:
        category = nav_category(item.kind)
        if not headings and category == "Heading":
            continue
        if not links and category == "Link":
            continue
        if not lists and category in {"List", "List item"}:
            continue
        result.append(item)
    return result
