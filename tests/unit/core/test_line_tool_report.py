"""A line tool says what it did, with a number (bad.md N2, P1.16).

"Sorted lines ascending" tells a listener that a key was pressed, which they
knew, and not what happened to the document, which they cannot see -- and it
said the same sentence when nothing had changed at all, so Remove Duplicate
Lines on a file with none was indistinguishable from one that had twelve.
"""

from __future__ import annotations

from quill.core.line_tool_report import (
    changed_size,
    count_for,
    describe_result,
    is_reordering,
    nothing_changed,
    scope_size,
)

NL = chr(10)


def test_a_terminal_newline_is_not_a_line() -> None:
    """A file that ends the way files end has three lines, not four."""
    assert scope_size("a" + NL + "b" + NL + "c" + NL) == 3
    assert scope_size("a" + NL + "b" + NL + "c") == 3


def test_a_sort_is_counted_by_what_it_was_given() -> None:
    """Nothing was added or removed, so "moved 38" understates a sort of 40."""
    before = "c" + NL + "a" + NL + "b"
    after = "a" + NL + "b" + NL + "c"
    assert is_reordering(before, after) is True
    assert count_for(before, after) == 3


def test_a_removal_is_counted_by_what_it_removed() -> None:
    before = "a" + NL + "a" + NL + "b"
    after = "a" + NL + "b"
    assert is_reordering(before, after) is False
    assert count_for(before, after) == 1


def test_a_rewrite_counts_the_lines_that_differ() -> None:
    before = "one" + NL + "two"
    after = "ONE" + NL + "two"
    assert changed_size(before, after) == 1


def test_characters_are_counted_when_the_tool_works_on_characters() -> None:
    assert changed_size("abc", "abd", unit="character") == 1
    assert scope_size("abc", unit="character") == 3


def test_an_unchanged_document_is_not_a_reordering() -> None:
    """Identical text means the tool did nothing, which has its own sentence."""
    assert is_reordering("a" + NL + "b", "a" + NL + "b") is False


def test_the_no_op_sentence_names_the_unit() -> None:
    assert nothing_changed() == "No lines to change"
    assert nothing_changed("character") == "No characters to change"


def test_the_result_reads_as_one_sentence() -> None:
    assert describe_result("Sorted lines ascending", 12) == "Sorted lines ascending, 12 lines"
    assert describe_result("Removed duplicate lines", 1) == "Removed duplicate lines, 1 line"


def test_both_editors_read_this_module() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    lite = (root / "quill" / "apps" / "lite_window_tools.py").read_text(encoding="utf-8")
    quill = (root / "quill" / "ui" / "main_frame_power_tools.py").read_text(encoding="utf-8")
    assert "from quill.core.line_tool_report import" in lite
    assert "from quill.core.line_tool_report import" in quill
