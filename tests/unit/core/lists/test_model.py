"""Unit tests for structured-list model helpers."""

from __future__ import annotations

from quill.core.lists.model import DefinitionEntry


def test_terms_text_joins_one_per_line() -> None:
    entry = DefinitionEntry(terms=["alpha", "beta"])
    assert entry.terms_text() == "alpha\nbeta"


def test_set_terms_text_splits_non_blank_lines() -> None:
    entry = DefinitionEntry()
    entry.set_terms_text("alpha\n  beta  \n\ngamma\n")
    assert entry.terms == ["alpha", "beta", "gamma"]


def test_set_terms_text_all_blank_keeps_single_empty_term() -> None:
    entry = DefinitionEntry(terms=["alpha"])
    entry.set_terms_text("   \n\n")
    assert entry.terms == [""]  # never collapses to zero terms
    assert entry.primary_term == ""


def test_terms_text_round_trips_through_set() -> None:
    entry = DefinitionEntry(terms=["one", "two", "three"])
    clone = DefinitionEntry()
    clone.set_terms_text(entry.terms_text())
    assert clone.terms == entry.terms


def test_definitions_text_joins_blank_line_separated() -> None:
    entry = DefinitionEntry(definitions=["first", "second"])
    assert entry.definitions_text() == "first\n\nsecond"


def test_set_definitions_text_splits_on_blank_lines() -> None:
    entry = DefinitionEntry()
    entry.set_definitions_text("first def\n\nsecond def\n\n\nthird def\n")
    assert entry.definitions == ["first def", "second def", "third def"]


def test_set_definitions_text_preserves_multi_line_within_a_block() -> None:
    entry = DefinitionEntry()
    entry.set_definitions_text("line one\nline two\n\nsecond def")
    assert entry.definitions == ["line one\nline two", "second def"]


def test_set_definitions_text_all_blank_keeps_single_empty() -> None:
    entry = DefinitionEntry(definitions=["x"])
    entry.set_definitions_text("\n   \n")
    assert entry.definitions == [""]


def test_definitions_text_round_trips_through_set() -> None:
    entry = DefinitionEntry(definitions=["alpha", "beta\nstill beta", "gamma"])
    clone = DefinitionEntry()
    clone.set_definitions_text(entry.definitions_text())
    assert clone.definitions == entry.definitions
