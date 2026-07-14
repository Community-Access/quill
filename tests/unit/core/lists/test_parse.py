from __future__ import annotations

from quill.core.lists.model import ListType
from quill.core.lists.parse import (
    detect_definition_separator,
    interpret_definition_entries,
    interpret_selection,
    interpret_text_into_definition,
    interpret_text_into_flat,
    strip_marker,
)
from quill.core.lists.settings import StructuredListSettings


def test_interpret_text_into_flat_one_item_per_line() -> None:
    flat = interpret_text_into_flat("apples\noranges\npears")
    assert flat.list_type is ListType.BULLET
    assert [i.text for i in flat.items] == ["apples", "oranges", "pears"]


def test_interpret_text_into_flat_promotes_checklist() -> None:
    flat = interpret_text_into_flat("- [ ] todo\n- [x] done")
    assert flat.list_type is ListType.CHECKLIST
    assert [(i.text, i.checked) for i in flat.items] == [("todo", False), ("done", True)]


def test_interpret_text_into_flat_empty_yields_single_item() -> None:
    flat = interpret_text_into_flat("   ")
    assert len(flat.items) == 1
    assert flat.items[0].text == ""


def test_interpret_text_into_definition_uses_detected_separator() -> None:
    dl = interpret_text_into_definition("HTTP: A protocol\nDNS: Name resolution")
    assert dl.entries[0].primary_term == "HTTP"
    assert dl.entries[0].primary_definition == "A protocol"
    assert dl.entries[1].primary_term == "DNS"


def test_interpret_text_into_definition_falls_back_to_term_only() -> None:
    # No confident separator -> one term-only entry per line, no guessed split.
    dl = interpret_text_into_definition("apple\nbanana\ncherry")
    assert [e.primary_term for e in dl.entries] == ["apple", "banana", "cherry"]
    assert all(e.primary_definition == "" for e in dl.entries)


def test_interpret_text_into_definition_empty_yields_single_entry() -> None:
    dl = interpret_text_into_definition("")
    assert len(dl.entries) == 1
    assert dl.entries[0].is_blank()


def texts(items: list[tuple[str, str, bool]]) -> list[str]:
    return [content for content, _kind, _checked in items]


def test_strip_marker_detects_kinds() -> None:
    assert strip_marker("- apples") == ("apples", "bullet", False)
    assert strip_marker("3. third") == ("third", "ordered", False)
    assert strip_marker("- [x] done") == ("done", "task", True)
    assert strip_marker("- [ ] todo") == ("todo", "task", False)
    assert strip_marker("plain text") == ("plain text", "", False)


def test_auto_mode_lines_when_no_blank_separators() -> None:
    items = interpret_selection("apples\noranges\npears")
    assert texts(items) == ["apples", "oranges", "pears"]


def test_auto_mode_paragraphs_when_blank_separated() -> None:
    items = interpret_selection("first para\nstill first\n\nsecond para")
    # Two paragraphs; the first keeps its internal line break by default.
    assert len(items) == 2
    assert items[0][0] == "first para\nstill first"
    assert items[1][0] == "second para"


def test_blank_lines_do_not_create_blank_items() -> None:
    items = interpret_selection(
        "one\n\n\ntwo", StructuredListSettings(selection_mode="nonblank_line")
    )
    assert texts(items) == ["one", "two"]


def test_markers_are_stripped_on_import() -> None:
    items = interpret_selection("- apples\n- oranges")
    assert texts(items) == ["apples", "oranges"]


def test_trim_whitespace_default() -> None:
    items = interpret_selection("  spaced  \n\ttabbed\t")
    assert texts(items) == ["spaced", "tabbed"]


# -- definition separator detection ---------------------------------------- #


def test_detect_tab_separator() -> None:
    interp = detect_definition_separator("HTML\tmarkup language\nCSS\tstyle sheets")
    assert interp.separator == "tab"
    assert interp.entries[0] == ("HTML", "markup language")
    assert not interp.ambiguous


def test_detect_colon_separator() -> None:
    interp = detect_definition_separator("Screen reader: speaks text\nMagnifier: enlarges")
    assert interp.separator == "colon"
    assert interp.entries[0][0] == "Screen reader"


def test_ambiguous_when_two_separators_fit() -> None:
    # Both " - " (dash) and ":" appear consistently; flag ambiguity for preview.
    interp = detect_definition_separator("A - x: y\nB - p: q")
    assert interp.ambiguous
    assert len(interp.candidates) >= 2


def test_alternating_lines_detected() -> None:
    interp = detect_definition_separator("Term one\nDefinition one\nTerm two\nDefinition two")
    assert interp.separator == "alternating_lines"
    assert interp.entries == [("Term one", "Definition one"), ("Term two", "Definition two")]


def test_interpret_definition_entries_with_chosen_colon() -> None:
    dl = interpret_definition_entries("A: 1\nB: 2", separator="colon")
    assert dl.entries[0].primary_term == "A"
    assert dl.entries[0].primary_definition == "1"
    assert len(dl.entries) == 2


def test_interpret_alternating_paragraphs() -> None:
    text = "Term one\n\nThe first definition.\n\nTerm two\n\nThe second definition."
    dl = interpret_definition_entries(text, separator="alternating_paragraphs")
    assert dl.entries[0].primary_term == "Term one"
    assert dl.entries[1].primary_definition == "The second definition."
