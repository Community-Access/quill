"""QuillLite's Insert Special Character: what the command does with an answer.

The picker itself is tested where it lives -- the catalogue and its search in
``tests/unit/core/test_special_characters.py``, the dialog by the contract gates
-- so what is left here is the command, which is one state change behind a
modal. The dialog recorder answers it, the default answer is cancel, and these
assert what reached the document and what was said.

The read-back is the thing being defended. Most of the catalogue is invisible on
the page, and a screen reader says nothing when an app writes text on its own
behalf, so without the announcement this command is a keystroke after which the
document may or may not have gained something nobody can see or hear.
"""

from __future__ import annotations

import pytest

from quill.core.special_characters import inserted_message

pytest.importorskip("wx")


EM_DASH = "—"
# Written as escapes, not as the characters themselves: a stray whitespace
# tidy would silently turn a no-break space into a space and the test would
# then assert the wrong character while still passing its own name.
NBSP = " "
E_ACUTE = "é"


def test_the_chosen_character_lands_at_the_cursor(lite_window, lite_dialogs) -> None:
    win = lite_window("dash", cursor=4)
    lite_dialogs.answer("choose_special_character", EM_DASH)
    win.cmd_insert_special_character()
    assert win.control.GetValue() == "dash" + EM_DASH
    assert win.modified is True


def test_it_says_what_it_inserted(lite_window, lite_dialogs) -> None:
    win = lite_window("", cursor=0)
    lite_dialogs.answer("choose_special_character", EM_DASH)
    win.cmd_insert_special_character()
    assert win.announcements == [inserted_message(EM_DASH)]


def test_the_read_back_names_an_invisible_character(lite_window, lite_dialogs) -> None:
    """ "Inserted" and then a no-break space is "Inserted" and then silence."""
    win = lite_window("", cursor=0)
    lite_dialogs.answer("choose_special_character", NBSP)
    win.cmd_insert_special_character()
    said = win.announcements[-1]
    assert "U+00A0" in said
    assert "No-break space" in said


def test_an_accented_letter_goes_in_as_the_letter_itself(lite_window, lite_dialogs) -> None:
    """The gap this expansion closed: no picker in either editor could type one,
    and Windows' own routes to them are all bad by ear."""
    win = lite_window("resum", cursor=5)
    lite_dialogs.answer("choose_special_character", E_ACUTE)
    win.cmd_insert_special_character()
    assert win.control.GetValue() == "resum" + E_ACUTE


def test_it_replaces_a_selection_the_way_typing_would(lite_window, lite_dialogs) -> None:
    win = lite_window("a-b", cursor=0)
    win.control.SetSelection(1, 2)
    lite_dialogs.answer("choose_special_character", EM_DASH)
    win.cmd_insert_special_character()
    assert win.control.GetValue() == "a" + EM_DASH + "b"


def test_cancelling_changes_nothing_and_says_nothing(lite_window, lite_dialogs) -> None:
    """Escape is not news, and a command that acts on a cancelled dialog is the
    bug the recorder's cancel-by-default exists to catch."""
    win = lite_window("intact", cursor=6)
    win.cmd_insert_special_character()
    assert win.control.GetValue() == "intact"
    assert win.modified is False
    assert win.announcements == []


def test_the_cursor_goes_back_to_the_document_either_way(lite_window, lite_dialogs) -> None:
    """A modal that closes leaving focus nowhere is a document you have to Tab
    back into."""
    win = lite_window("", cursor=0)
    win.cmd_insert_special_character()
    assert win.control.focused is True
    win.control.focused = False
    lite_dialogs.answer("choose_special_character", EM_DASH)
    win.cmd_insert_special_character()
    assert win.control.focused is True


def test_the_status_bar_is_told_to_recount(lite_window, lite_dialogs) -> None:
    """The bar carries a character count, and text arrived without a keystroke."""
    win = lite_window("", cursor=0)
    before = win.status_touches
    lite_dialogs.answer("choose_special_character", EM_DASH)
    win.cmd_insert_special_character()
    assert win.status_touches > before


# --------------------------------------------------------------------- #
# Insert Line Break (#1488)


def test_a_line_break_ends_the_line_without_starting_a_paragraph(lite_window) -> None:
    """The distinction the whole feature rests on. A blank line would make two
    paragraphs; this makes two lines of one."""
    win = lite_window("Illinois,", cursor=9)
    win.cmd_insert_line_break()
    assert win.control.GetValue() == "Illinois," + chr(92) + chr(10)
    assert win.modified is True


def test_the_break_style_setting_is_honoured(lite_window) -> None:
    win = lite_window("Illinois,", cursor=9)
    win.app.settings.markdown_hard_break_style = "spaces"
    win.cmd_insert_line_break()
    assert win.control.GetValue() == "Illinois,  " + chr(10)


def test_it_says_which_spelling_went_in(lite_window) -> None:
    """The one thing you cannot check for yourself: two trailing spaces are
    silent and invisible, and a backslash is neither."""
    win = lite_window("", cursor=0)
    win.cmd_insert_line_break()
    assert "backslash" in win.announcements[-1]
    win.app.settings.markdown_hard_break_style = "spaces"
    win.cmd_insert_line_break()
    assert "two spaces" in win.announcements[-1]


def test_a_nonsense_setting_still_inserts_a_break(lite_window) -> None:
    """A hand-edited settings file must not stop the editor writing a line."""
    win = lite_window("", cursor=0)
    win.app.settings.markdown_hard_break_style = "nonsense"
    win.cmd_insert_line_break()
    assert win.control.GetValue() == chr(92) + chr(10)
