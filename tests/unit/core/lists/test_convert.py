from __future__ import annotations

from quill.core.lists.convert import definition_to_flat, flat_to_definition
from quill.core.lists.model import (
    DefinitionEntry,
    DefinitionList,
    FlatList,
    ListItem,
    ListType,
)


def test_flat_to_definition_colon_split() -> None:
    flat = FlatList(
        list_type=ListType.BULLET,
        items=[ListItem("HTML: web markup"), ListItem("CSS: styles")],
    )
    dl, loss = flat_to_definition(flat, split="colon")
    assert dl.entries[0].primary_term == "HTML"
    assert dl.entries[0].primary_definition == "web markup"
    assert not loss.lossy


def test_flat_to_definition_term_only() -> None:
    flat = FlatList(items=[ListItem("Glossary entry")])
    dl, _loss = flat_to_definition(flat, split="term_only")
    assert dl.entries[0].primary_term == "Glossary entry"
    assert dl.entries[0].primary_definition == ""


def test_flat_to_definition_warns_on_checked_states() -> None:
    flat = FlatList(
        list_type=ListType.CHECKLIST,
        items=[ListItem("done", checked=True)],
    )
    _dl, loss = flat_to_definition(flat)
    assert loss.lossy
    assert any("Checked" in reason for reason in loss.reasons)


def test_flat_to_definition_warns_on_nesting() -> None:
    flat = FlatList(items=[ListItem("top"), ListItem("child", level=1)])
    _dl, loss = flat_to_definition(flat)
    assert any("Nesting" in reason for reason in loss.reasons)


def test_definition_to_flat_term_definition_style() -> None:
    dl = DefinitionList(entries=[DefinitionEntry(terms=["Term"], definitions=["A definition."])])
    flat, loss = definition_to_flat(dl)
    assert flat.items[0].text == "Term: A definition."
    assert not loss.lossy


def test_definition_to_flat_warns_on_multiple_definitions() -> None:
    dl = DefinitionList(entries=[DefinitionEntry(terms=["T"], definitions=["one", "two"])])
    _flat, loss = definition_to_flat(dl)
    assert any("Extra definitions" in reason for reason in loss.reasons)


def test_definition_to_checklist_type() -> None:
    dl = DefinitionList(entries=[DefinitionEntry(terms=["Task"], definitions=["do it"])])
    flat, _loss = definition_to_flat(dl, list_type=ListType.CHECKLIST)
    assert flat.list_type is ListType.CHECKLIST
