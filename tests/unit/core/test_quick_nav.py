"""Tests for the unified Quick Nav / Go to Anything index (NAV-1, NAV-4)."""

from __future__ import annotations

from quill.core.quick_nav import (
    NavItem,
    build_nav_index,
    filter_nav_items,
    include_nav_items,
    nav_category,
    nav_item_display,
    nav_type_summary,
)

_TEXT = "# Title\nSome intro text\n## Section\nA paragraph with detail\n### Sub\nmore\n"


def _context() -> dict[str, object]:
    # Positions are approximate offsets into _TEXT; exact values are not asserted.
    return {
        "headings_by_level": {1: [0], 2: [23], 3: [55]},
        "links": [10],
        "lists": [],
        "list_items": [],
        "tables": [],
        "block_quotes": [],
        "bookmarks": [40],
        "code_blocks": [],
    }


def test_build_nav_index_collects_landmarks_in_position_order() -> None:
    items = build_nav_index(_TEXT, _context())
    positions = [item.position for item in items]
    assert positions == sorted(positions)
    kinds = {item.kind for item in items}
    assert "Heading 1" in kinds
    assert "Heading 2" in kinds
    assert "Link" in kinds
    assert "Bookmark" in kinds


def test_build_nav_index_previews_use_line_text() -> None:
    items = build_nav_index(_TEXT, _context())
    heading = next(item for item in items if item.kind == "Heading 1")
    assert "Title" in heading.label


def test_build_nav_index_ignores_non_int_positions_and_missing_keys() -> None:
    context = {"headings_by_level": {1: ["bad", 0]}, "links": "nope"}
    items = build_nav_index(_TEXT, context)
    # Only the integer heading position survives.
    assert len(items) == 1
    assert items[0].kind == "Heading 1"


def test_nav_category_groups_heading_levels() -> None:
    assert nav_category("Heading 3") == "Heading"
    assert nav_category("Link") == "Link"


def test_nav_type_summary_counts_by_category_in_order() -> None:
    items = build_nav_index(_TEXT, _context())
    summary = dict(nav_type_summary(items))
    assert summary["Heading"] == 3
    assert summary["Link"] == 1
    assert summary["Bookmark"] == 1


def test_filter_by_query_matches_label_and_kind() -> None:
    items = [
        NavItem("Heading 1", "Introduction", 0),
        NavItem("Link", "Contact us", 10),
    ]
    assert filter_nav_items(items, "intro") == [items[0]]
    assert filter_nav_items(items, "link") == [items[1]]
    assert filter_nav_items(items, "") == items


def test_filter_by_category() -> None:
    items = build_nav_index(_TEXT, _context())
    only_headings = filter_nav_items(items, "", category="Heading")
    assert only_headings
    assert all(nav_category(item.kind) == "Heading" for item in only_headings)


def test_nav_item_display_is_kind_and_label() -> None:
    assert nav_item_display(NavItem("Link", "Home", 3)) == "Link: Home"


def _inclusion_items() -> list[NavItem]:
    return [
        NavItem("Heading 1", "Title", 0),
        NavItem("Link", "Home", 5),
        NavItem("List", "Items", 10),
        NavItem("List item", "First", 12),
        NavItem("Table", "Grid", 20),
        NavItem("Bookmark", "mark", 25),
    ]


def test_include_nav_items_keeps_everything_by_default() -> None:
    items = _inclusion_items()
    assert include_nav_items(items) == items


def test_include_nav_items_drops_headings_when_off() -> None:
    items = _inclusion_items()
    kept = include_nav_items(items, headings=False)
    assert all(nav_category(item.kind) != "Heading" for item in kept)
    assert len(kept) == len(items) - 1


def test_include_nav_items_drops_links_when_off() -> None:
    items = _inclusion_items()
    kept = include_nav_items(items, links=False)
    assert all(item.kind != "Link" for item in kept)


def test_include_nav_items_drops_lists_and_list_items_when_off() -> None:
    items = _inclusion_items()
    kept = include_nav_items(items, lists=False)
    kinds = {item.kind for item in kept}
    assert "List" not in kinds
    assert "List item" not in kinds
    # Tables and bookmarks have no toggle and are always kept.
    assert "Table" in kinds
    assert "Bookmark" in kinds


# --------------------------------------------------------------------------- #
# Transient nav types: misspellings and search hits (#513)
# --------------------------------------------------------------------------- #


def test_build_nav_index_includes_misspellings_and_search_hits() -> None:
    context = {
        "headings_by_level": {1: [0]},
        "misspellings": [9],  # "intro" position-ish
        "search_hits": [5, 30],
    }
    items = build_nav_index(_TEXT, context)
    kinds = [item.kind for item in items]
    assert "Misspelling" in kinds
    assert kinds.count("Search hit") == 2
    # Position-ordered with the rest of the index.
    assert [item.position for item in items] == sorted(item.position for item in items)


def test_transient_types_appear_in_count_panel_summary() -> None:
    context = {"misspellings": [1, 4], "search_hits": [2]}
    summary = dict(nav_type_summary(build_nav_index(_TEXT, context)))
    assert summary["Misspelling"] == 2
    assert summary["Search hit"] == 1


def test_transient_types_filterable_by_category() -> None:
    items = build_nav_index(_TEXT, {"misspellings": [3], "links": [10]})
    only = filter_nav_items(items, category="Misspelling")
    assert len(only) == 1 and only[0].kind == "Misspelling"


def test_include_nav_items_keeps_transient_types() -> None:
    # Misspellings/search hits have no settings toggle; they are always kept.
    items = build_nav_index(_TEXT, {"misspellings": [3], "search_hits": [6]})
    kept = include_nav_items(items, headings=False, links=False, lists=False)
    kinds = {item.kind for item in kept}
    assert {"Misspelling", "Search hit"} <= kinds
