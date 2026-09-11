"""The Tools menu's text transforms: case, order, and tidying.

``test_lite_tools_batch.py`` covers the indent ladder and four of the transforms.
This is the rest, and the reason to have the rest is that these commands are the
most destructive things in the app that are not called Delete. Sort Lines
rearranges a whole document in one keystroke. Remove Duplicate Lines throws text
away. Neither moves focus, so a screen reader says nothing about either, and the
announcement is the only evidence a listener has of what just happened to work
they cannot see.

So the count in each announcement is load-bearing and is asserted exactly.
"Sorted 5 lines" is a fact you can check against what you thought was there;
"Sorted" is a word that means the key did not crash.

**Scope.** Every one of these applies to the selection when there is one and to
the whole document when there is not, and both are tested: a transform that
quietly took the whole document when the user had selected three lines would be
the worst bug in the menu, and it is invisible without sight.
"""

from __future__ import annotations

MIXED = "banana\nApple\ncherry\nApple\n\n  spaced   out  \n"


# --------------------------------------------------------------------- #
# Case
# --------------------------------------------------------------------- #


def test_upper_case_shouts_and_counts_the_letters_it_changed(lite_window) -> None:
    win = lite_window("Hello world", cursor=0)
    win.control.SelectAll()
    win.cmd_upper_case()
    assert win.control.GetValue() == "HELLO WORLD"
    assert win.announcements[-1] == "Changed 9 characters"
    assert win.modified is True


def test_lower_case_goes_the_other_way(lite_window) -> None:
    win = lite_window("Hello World", cursor=0)
    win.control.SelectAll()
    win.cmd_lower_case()
    assert win.control.GetValue() == "hello world"


def test_title_case_capitalises_each_word(lite_window) -> None:
    win = lite_window("hello wide world", cursor=0)
    win.control.SelectAll()
    win.cmd_title_case()
    assert win.control.GetValue() == "Hello Wide World"


def test_sentence_case_lowers_the_rest(lite_window) -> None:
    win = lite_window("HELLO WORLD", cursor=0)
    win.control.SelectAll()
    win.cmd_sentence_case()
    assert win.control.GetValue() == "Hello world"


def test_toggle_case_swaps_every_letter(lite_window) -> None:
    win = lite_window("Hello World", cursor=0)
    win.control.SelectAll()
    win.cmd_toggle_case()
    assert win.control.GetValue() == "hELLO wORLD"


def test_a_case_change_that_changes_nothing_says_so(lite_window) -> None:
    """Silence would be indistinguishable from a key that is not bound."""
    win = lite_window("HELLO", cursor=0)
    win.control.SelectAll()
    win.cmd_upper_case()
    assert win.announcements[-1] == "No character to change"


def test_case_applies_to_the_selection_and_leaves_the_rest_alone(lite_window) -> None:
    """The bug this guards against is invisible without sight: a transform that
    silently took the whole document when three lines were selected."""
    win = lite_window("alpha bravo charlie", cursor=0)
    win.control.SetSelection(6, 11)
    win.cmd_upper_case()
    assert win.control.GetValue() == "alpha BRAVO charlie"


def test_case_with_no_selection_takes_the_whole_document(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.cmd_upper_case()
    assert win.control.GetValue() == "ALPHA BRAVO"


# --------------------------------------------------------------------- #
# Order
# --------------------------------------------------------------------- #


def test_sort_lines_sorts_and_counts_them(lite_window) -> None:
    win = lite_window("cherry\nbanana\napple\n", cursor=0)
    win.control.SelectAll()
    win.cmd_sort_lines()
    assert win.control.GetValue().startswith("apple\nbanana\ncherry")
    assert win.announcements[-1] == "Sorted 3 lines"


def test_sort_descending_is_the_mirror(lite_window) -> None:
    win = lite_window("apple\nbanana\ncherry\n", cursor=0)
    win.control.SelectAll()
    win.cmd_sort_lines_descending()
    assert win.control.GetValue().startswith("cherry\nbanana\napple")


def test_reverse_lines_reverses_rather_than_sorts(lite_window) -> None:
    win = lite_window("one\ntwo\nthree\n", cursor=0)
    win.control.SelectAll()
    win.cmd_reverse_lines()
    assert win.control.GetValue().startswith("three\ntwo\none")


# --------------------------------------------------------------------- #
# Throwing text away
# --------------------------------------------------------------------- #


def test_remove_duplicate_lines_keeps_the_first_of_each(lite_window) -> None:
    win = lite_window("a\nb\na\nc\nb\n", cursor=0)
    win.control.SelectAll()
    win.cmd_remove_duplicate_lines()
    assert win.control.GetValue().startswith("a\nb\nc")
    assert win.announcements[-1] == "Removed 2 lines"


def test_remove_duplicates_with_none_to_remove_says_so(lite_window) -> None:
    """The one that most needs saying: the user cannot see that nothing went."""
    win = lite_window("a\nb\nc\n", cursor=0)
    win.control.SelectAll()
    win.cmd_remove_duplicate_lines()
    assert "no" in win.announcements[-1].lower() or "0" in win.announcements[-1]
    assert win.control.GetValue() == "a\nb\nc\n"


def test_remove_blank_lines_removes_the_ones_in_the_middle_too(lite_window) -> None:
    """The command is called Remove Blank Lines and was wired to *trim* them.

    ``trim_blank_lines`` takes only the leading and trailing ones, so on any
    document with blank lines through the middle -- which is every document -- the
    command removed nothing, ate the terminal newline, and announced "Removed 1
    line". The false count is the worse half: a listener cannot see that the text
    is unchanged and has no reason to doubt the sentence.
    """
    win = lite_window("a\n\nb\n\n\nc\n", cursor=0)
    win.control.SelectAll()
    win.cmd_remove_blank_lines()
    assert win.control.GetValue() == "a\nb\nc\n"
    assert win.announcements[-1] == "Removed 3 lines"


def test_remove_blank_lines_counts_a_whitespace_only_line_as_blank(lite_window) -> None:
    """Three spaces is blank to every reader of the document and to every tool
    that consumes it; leaving it would make the answer depend on the invisible."""
    win = lite_window("a\n   \nb\n", cursor=0)
    win.control.SelectAll()
    win.cmd_remove_blank_lines()
    assert win.control.GetValue() == "a\nb\n"


def test_remove_blank_lines_keeps_the_terminal_newline(lite_window) -> None:
    win = lite_window("a\n\nb\n", cursor=0)
    win.control.SelectAll()
    win.cmd_remove_blank_lines()
    assert win.control.GetValue().endswith("\n")


def test_a_sort_counts_the_lines_it_sorted_not_the_ones_that_moved(lite_window) -> None:
    """ "Sorted 2 lines" for three sorted lines sends the reader looking for the
    one it missed. Nothing was added or removed, so the honest number is how many
    lines the tool was handed."""
    win = lite_window("cherry\nbanana\napple\n", cursor=0)
    win.control.SelectAll()
    win.cmd_sort_lines()
    assert win.announcements[-1] == "Sorted 3 lines"


def test_trim_trailing_space_reports_the_lines_it_touched(lite_window) -> None:
    win = lite_window("a   \nb\nc  \n", cursor=0)
    win.control.SelectAll()
    win.cmd_trim_trailing_space()
    assert win.control.GetValue() == "a\nb\nc\n"
    assert win.announcements[-1] == "Trimmed 2 lines"


def test_normalize_whitespace_collapses_runs(lite_window) -> None:
    win = lite_window("  spaced    out  \n", cursor=0)
    win.control.SelectAll()
    win.cmd_normalize_whitespace()
    assert win.control.GetValue() == "spaced out\n"
    assert win.announcements[-1] == "Tidied 1 line"


def test_number_lines_numbers_the_non_blank_ones(lite_window) -> None:
    win = lite_window("one\ntwo\n\nthree\n", cursor=0)
    win.control.SelectAll()
    win.cmd_number_lines()
    assert win.control.GetValue() == "1. one\n2. two\n\n3. three\n"
    assert win.announcements[-1] == "Numbered 3 lines"


def test_every_transform_leaves_the_document_marked_modified(lite_window) -> None:
    """A transform that edited the text and left the title clean would let the
    work be closed without a prompt."""
    for command, text in (
        ("cmd_upper_case", "abc"),
        ("cmd_sort_lines", "b\na\n"),
        ("cmd_reverse_lines", "a\nb\n"),
        ("cmd_remove_duplicate_lines", "a\na\n"),
        ("cmd_remove_blank_lines", "a\n\nb\n"),
        ("cmd_trim_trailing_space", "a  \n"),
        ("cmd_normalize_whitespace", "a   b\n"),
        ("cmd_number_lines", "a\nb\n"),
    ):
        win = lite_window(text, cursor=0)
        win.control.SelectAll()
        getattr(win, command)()
        assert win.modified is True, command
