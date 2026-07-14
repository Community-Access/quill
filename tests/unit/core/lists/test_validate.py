"""Unit tests for pre-commit list validation (PRD §26)."""

from __future__ import annotations

from quill.core.lists.model import DefinitionEntry, DefinitionList, FlatList, ListItem, ListType
from quill.core.lists.render import render_markdown
from quill.core.lists.validate import validate_before_commit


def _md(model: FlatList) -> str:
    return render_markdown(model)


def test_empty_source_is_rejected() -> None:
    model = FlatList(items=[ListItem("")])
    assert validate_before_commit(model, "   ", "markdown") == [
        "The list has no content to insert."
    ]


def test_clean_flat_list_validates() -> None:
    model = FlatList(items=[ListItem("apples"), ListItem("oranges")])
    assert validate_before_commit(model, _md(model), "markdown") == []


def test_clean_nested_checklist_validates() -> None:
    model = FlatList(
        list_type=ListType.CHECKLIST,
        items=[ListItem("top", checked=True), ListItem("child", level=1)],
    )
    assert validate_before_commit(model, _md(model), "markdown") == []


def test_multiline_item_still_round_trips() -> None:
    # A genuine multi-line item must NOT be flagged (continuation lines reparse
    # back into the same single item).
    model = FlatList(items=[ListItem("line one\nline two"), ListItem("second")])
    assert validate_before_commit(model, _md(model), "markdown") == []


def test_item_text_injecting_markup_is_flagged() -> None:
    # An item whose text contains a bullet line changes the structure on reparse.
    model = FlatList(items=[ListItem("intro\n- sneaky bullet")])
    issues = validate_before_commit(model, _md(model), "markdown")
    assert issues and "round-trip" in issues[0]


def test_html_format_skips_round_trip() -> None:
    # No HTML reparser, so the round-trip check is skipped (structural only).
    model = FlatList(items=[ListItem("intro\n- not a problem in html")])
    assert validate_before_commit(model, "<ul><li>x</li></ul>", "html") == []


def test_definition_entry_without_term_is_flagged() -> None:
    model = DefinitionList(
        entries=[
            DefinitionEntry(terms=["Good"], definitions=["d"]),
            DefinitionEntry(terms=[""], definitions=["orphan definition"]),
        ]
    )
    issues = validate_before_commit(model, "Good\n: d", "markdown")
    assert issues == ["Entry 2 has no term."]


def test_empty_definition_list_is_rejected() -> None:
    model = DefinitionList(entries=[DefinitionEntry()])
    assert validate_before_commit(model, "x", "markdown") == [
        "The definition list has no entries to insert."
    ]
