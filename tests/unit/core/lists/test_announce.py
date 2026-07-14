from __future__ import annotations

from quill.core.lists.announce import (
    checklist_toggle_announcement,
    definition_entry_announcement,
    flat_item_announcement,
    list_summary,
)
from quill.core.lists.model import (
    DefinitionEntry,
    DefinitionList,
    FlatList,
    ListItem,
    ListType,
)
from quill.core.lists.settings import StructuredListSettings


def test_flat_item_standard_includes_position() -> None:
    model = FlatList(items=[ListItem("apples"), ListItem("oranges")])
    out = flat_item_announcement(model, 0)
    assert "apples" in out
    assert "1 of 2" in out


def test_checklist_toggle_announcement_includes_total() -> None:
    model = FlatList(
        list_type=ListType.CHECKLIST,
        items=[ListItem("buy coffee", checked=True), ListItem("call", checked=False)],
    )
    out = checklist_toggle_announcement(model, 0)
    assert "Checked: buy coffee" in out
    assert "1 of 2 tasks complete" in out


def test_concise_checklist_toggle_is_short() -> None:
    model = FlatList(
        list_type=ListType.CHECKLIST,
        items=[ListItem("x", checked=True)],
    )
    out = checklist_toggle_announcement(model, 0, StructuredListSettings(verbosity="concise"))
    assert out == "Checked: x."


def test_definition_entry_single_definition() -> None:
    model = DefinitionList(
        entries=[DefinitionEntry(terms=["Screen reader"], definitions=["Speaks text."])]
    )
    out = definition_entry_announcement(model, 0)
    assert "Term: Screen reader" in out
    assert "Entry 1 of 1" in out
    assert "One definition" in out


def test_definition_entry_multiple_terms() -> None:
    model = DefinitionList(
        entries=[
            DefinitionEntry(terms=["HTML", "HyperText Markup Language"], definitions=["markup"])
        ]
    )
    out = definition_entry_announcement(model, 0)
    assert "Terms: HTML and HyperText Markup Language" in out
    assert "2 terms" in out


def test_list_summary_flat_and_definition() -> None:
    flat = FlatList(items=[ListItem("a"), ListItem("b")])
    assert list_summary(flat) == "Bulleted list, 2 items."

    dl = DefinitionList(
        entries=[
            DefinitionEntry(terms=["a"], definitions=["1"]),
            DefinitionEntry(terms=["b"], definitions=["2"]),
        ]
    )
    assert list_summary(dl) == "Definition list, 2 entries."


def test_detailed_definition_summary_counts() -> None:
    dl = DefinitionList(entries=[DefinitionEntry(terms=["a", "b"], definitions=["1", "2"])])
    out = list_summary(dl, StructuredListSettings(verbosity="detailed"))
    assert "2 terms" in out and "2 definitions" in out
