"""The QUILL tools a listener feels immediately, now in QUILL Lite.

Tier 2 of bad.md 4.2: small, shared, and each one removing a specific cost. A
read-only copy of the selection so reading it back cannot destroy it. A list of
every misspelling instead of pressing Ctrl+F7 until it wraps. Quote marks, a
width to wrap to, a pattern to delete by -- the things a person opens a
plain-text editor to do.
"""

from __future__ import annotations

DOC = "alpha beta\ngamma delta\nepsilon\n"


# --------------------------------------------------------------------------- #
# Review Buffer
# --------------------------------------------------------------------------- #


def test_the_review_buffer_shows_the_selection_read_only(lite_window, lite_dialogs) -> None:
    win = lite_window(DOC, cursor=0)
    win.control.SetSelection(0, 10)
    win.cmd_open_review_buffer()
    assert lite_dialogs.args_for("show_text_window")[1:] == ("Review Buffer", "alpha beta")
    assert win.announcements[-1] == "Reviewed 2 words, 10 characters"


def test_the_review_buffer_leaves_the_document_alone(lite_window, lite_dialogs) -> None:
    """Which is the entire point: arrowing through a live selection in your own
    document means the next character you type replaces it."""
    win = lite_window(DOC, cursor=0)
    win.control.SetSelection(0, 10)
    win.cmd_open_review_buffer()
    assert win.control.GetValue() == DOC
    assert win.modified is False


def test_the_review_buffer_with_nothing_selected_says_what_to_do(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.cmd_open_review_buffer()
    assert win.announcements[-1] == "Select something to review first"


# --------------------------------------------------------------------------- #
# The Misspelling List
# --------------------------------------------------------------------------- #


def test_the_misspelling_list_offers_every_one_with_its_line(lite_window, lite_dialogs) -> None:
    win = lite_window("the quick brxwn fox\nand a zzqua here\n", cursor=0)
    lite_dialogs.answer("choose_from_rows", 1)
    win.cmd_misspelling_list()
    rows = dict(lite_dialogs.kwargs_for("choose_from_rows")["rows"])
    assert rows[0] == "brxwn -- line 1"
    assert rows[1] == "zzqua -- line 2"


def test_choosing_from_the_list_goes_there_and_selects_the_word(lite_window, lite_dialogs) -> None:
    text = "the quick brxwn fox\nand a zzqua here\n"
    win = lite_window(text, cursor=0)
    lite_dialogs.answer("choose_from_rows", 1)
    win.cmd_misspelling_list()
    start = text.index("zzqua")
    assert win.control.GetSelection() == (start, start + 5)
    assert win.announcements[-1] == "Misspelling: zzqua"


def test_a_clean_document_says_there_are_none(lite_window, lite_dialogs) -> None:
    win = lite_window("the quick brown fox\n", cursor=0)
    win.cmd_misspelling_list()
    assert win.announcements[-1] == "No misspellings found"
    assert lite_dialogs.names() == []


def test_a_word_you_chose_to_ignore_is_not_offered_again(lite_window, lite_dialogs) -> None:
    """A list that offers the word you just skipped is a list you re-skip on
    every visit."""
    text = "the quick brxwn fox\nand a zzqua here\n"
    win = lite_window(text, cursor=0)
    win.spell_ignores.ignore_word("brxwn")
    win.cmd_misspelling_list()
    rows = dict(lite_dialogs.kwargs_for("choose_from_rows")["rows"])
    assert list(rows.values()) == ["zzqua -- line 2"]


# --------------------------------------------------------------------------- #
# Quote and unquote
# --------------------------------------------------------------------------- #


def test_quoting_marks_the_lines_you_chose(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.control.SetSelection(0, 22)
    win.cmd_quote_lines()
    assert win.control.GetValue() == "> alpha beta\n> gamma delta\nepsilon\n"
    assert win.announcements[-1] == "Quoted 2 lines"


def test_unquoting_takes_the_marks_off(lite_window) -> None:
    win = lite_window("> alpha beta\n> gamma delta\n", cursor=0)
    win.control.SetSelection(0, 27)
    win.cmd_unquote_lines()
    assert win.control.GetValue() == "alpha beta\ngamma delta\n"


def test_with_nothing_selected_quoting_takes_the_whole_document(lite_window) -> None:
    win = lite_window("alpha\nbeta\n", cursor=0)
    win.cmd_quote_lines()
    assert win.control.GetValue() == "> alpha\n> beta\n"


# --------------------------------------------------------------------------- #
# Indentation
# --------------------------------------------------------------------------- #


def test_tabs_become_spaces(lite_window) -> None:
    win = lite_window("\tone\n\t\ttwo\n", cursor=0)
    win.cmd_indentation_to_spaces()
    assert win.control.GetValue() == "    one\n        two\n"


def test_spaces_become_tabs(lite_window) -> None:
    win = lite_window("    one\n        two\n", cursor=0)
    win.cmd_indentation_to_tabs()
    assert win.control.GetValue() == "\tone\n\t\ttwo\n"


# --------------------------------------------------------------------------- #
# Delete Lines Containing
# --------------------------------------------------------------------------- #


def test_deleting_lines_by_what_they_contain(lite_window, lite_dialogs) -> None:
    win = lite_window("keep this\nDEBUG noise\nkeep that\nDEBUG more\n", cursor=0)
    lite_dialogs.answer("ask_text", "DEBUG")
    win.cmd_delete_lines_containing()
    assert win.control.GetValue() == "keep this\nkeep that\n"
    assert win.announcements[-1] == "Deleted 2 lines"


def test_the_pattern_is_taken_literally(lite_window, lite_dialogs) -> None:
    """A "." that silently matched every character would be a poor surprise in
    a tool that deletes."""
    win = lite_window("version 1.2\nversion 1x2\n", cursor=0)
    lite_dialogs.answer("ask_text", "1.2")
    win.cmd_delete_lines_containing()
    assert win.control.GetValue() == "version 1x2\n"


def test_cancelling_deletes_nothing(lite_window, lite_dialogs) -> None:
    win = lite_window("keep this\nDEBUG noise\n", cursor=0)
    win.cmd_delete_lines_containing()
    assert win.control.GetValue() == "keep this\nDEBUG noise\n"


def test_an_empty_pattern_deletes_nothing_and_says_so(lite_window, lite_dialogs) -> None:
    win = lite_window("keep this\nDEBUG noise\n", cursor=0)
    lite_dialogs.answer("ask_text", "")
    win.cmd_delete_lines_containing()
    assert win.control.GetValue() == "keep this\nDEBUG noise\n"
    assert "no lines were deleted" in win.announcements[-1]


# --------------------------------------------------------------------------- #
# Hard Wrap
# --------------------------------------------------------------------------- #


def test_hard_wrapping_reflows_to_the_width_you_give(lite_window, lite_dialogs) -> None:
    text = "one two three four five six seven eight nine ten eleven twelve\n"
    win = lite_window(text, cursor=0)
    lite_dialogs.answer("ask_text", "20")
    win.cmd_hard_wrap()
    assert max(len(line) for line in win.control.GetValue().split("\n")) <= 20
    assert win.control.GetValue().split() == text.split(), "no word may be lost"


def test_a_width_that_is_not_a_number_says_so(lite_window, lite_dialogs) -> None:
    win = lite_window("one two three\n", cursor=0)
    lite_dialogs.answer("ask_text", "wide")
    win.cmd_hard_wrap()
    assert win.control.GetValue() == "one two three\n"
    assert "not a number" in win.announcements[-1]


def test_an_absurdly_narrow_width_is_refused(lite_window, lite_dialogs) -> None:
    """Below twenty characters a wrap width is not a width, it is a column of
    single letters."""
    win = lite_window("one two three\n", cursor=0)
    lite_dialogs.answer("ask_text", "3")
    win.cmd_hard_wrap()
    assert win.control.GetValue() == "one two three\n"
    assert "at least" in win.announcements[-1]


# --------------------------------------------------------------------------- #
# Line Statistics
# --------------------------------------------------------------------------- #


def test_line_statistics_say_how_wide_the_document_is(lite_window) -> None:
    win = lite_window("short\na much longer line here\nmid\n", cursor=0)
    win.cmd_line_statistics()
    said = win.announcements[-1]
    assert "Longest 23 characters, on line 2" in said
    assert said.startswith("4 lines.")


def test_line_statistics_on_an_empty_document_say_so(lite_window) -> None:
    win = lite_window("", cursor=0)
    win.cmd_line_statistics()
    assert win.announcements[-1] == "The document is empty"
