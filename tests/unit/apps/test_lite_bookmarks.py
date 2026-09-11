"""Numbered bookmarks, and reading the character under the caret.

A bookmark is not a mark. A mark is where you were standing ten seconds ago and
is used up when you go back to it (``test_lite_selection_commands.py``); a
bookmark is a place you *meant to keep*, it has a number, and the number is the
handle -- "bookmark 3" is something a person can hold in their head where "the
third one down a list" is not.

What matters in every announcement here is the **label**: a bookmark you cannot
identify is a bookmark you have to visit to identify, which for a listener costs
the whole journey. So each one is announced with the text it sits on, and a
listing that says only "3 bookmarks" would be a listing that has failed.
"""

from __future__ import annotations

DOC = "alpha bravo charlie\nsecond line here\n\nEcho FOXTROT delta\n"


def test_set_bookmark_takes_the_next_free_number_and_labels_it(lite_window) -> None:
    win = lite_window(DOC, cursor=2)
    win.cmd_set_bookmark()
    assert win.announcements[-1] == "Bookmark 1 set: alpha bravo charlie"


def test_setting_a_second_one_takes_the_next_number(lite_window) -> None:
    win = lite_window(DOC, cursor=2)
    win.cmd_set_bookmark()
    win.control.SetInsertionPoint(25)
    win.cmd_set_bookmark()
    assert win.announcements[-1] == "Bookmark 2 set: second line here"


def test_a_numbered_key_sets_that_number_whatever_is_free(lite_window) -> None:
    """Ctrl+Shift+3 means three. The point of a number is that it is chosen."""
    win = lite_window(DOC, cursor=2)
    win.cmd_set_bookmark_3()
    assert win.announcements[-1] == "Bookmark 3 set: alpha bravo charlie"


def test_pressing_the_same_number_again_moves_it_and_relabels_it(lite_window) -> None:
    """Set, not toggle -- and the new label proves which of the two happened.

    A number is a slot the user chose, so pressing it again means "put it here
    instead". Removing one is a deliberate act and lives in the list, where it
    can be confirmed; a key that sometimes set and sometimes deleted would be a
    key nobody could press with confidence.
    """
    win = lite_window(DOC, cursor=2)
    win.cmd_set_bookmark_3()
    win.control.SetInsertionPoint(25)
    win.cmd_set_bookmark_3()
    assert win.announcements[-1] == "Bookmark 3 set: second line here"

    win.control.SetInsertionPoint(0)
    win.cmd_next_bookmark()
    assert win.control.GetInsertionPoint() == 25


def test_next_bookmark_goes_to_the_one_after_the_caret(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.cmd_set_bookmark_1()
    win.control.SetInsertionPoint(25)
    win.cmd_set_bookmark_2()
    win.control.SetInsertionPoint(0)
    win.cmd_next_bookmark()
    assert win.control.GetInsertionPoint() == 25
    assert "second line here" in win.announcements[-1]


def test_previous_bookmark_goes_the_other_way(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.cmd_set_bookmark_1()
    win.control.SetInsertionPoint(25)
    win.cmd_set_bookmark_2()
    win.cmd_previous_bookmark()
    assert win.control.GetInsertionPoint() == 0


def test_next_with_none_set_says_so_rather_than_going_quiet(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.cmd_next_bookmark()
    assert win.announcements == ["No bookmarks in this document"]


def test_listing_nothing_says_how_to_make_one(lite_window) -> None:
    """An empty list is the moment somebody is most likely not to know the key."""
    win = lite_window(DOC, cursor=0)
    win.cmd_list_bookmarks()
    spoken = win.announcements[-1]
    assert "No bookmarks in this document" in spoken
    assert "Control Shift B" in spoken


def test_clear_all_reports_the_count_it_cleared(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.cmd_set_bookmark_1()
    win.control.SetInsertionPoint(25)
    win.cmd_set_bookmark_2()
    win.cmd_clear_bookmarks()
    assert "2" in win.announcements[-1]


def test_clear_all_with_none_set_says_so(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.cmd_clear_bookmarks()
    assert win.announcements == ["No bookmarks to clear"]


def test_a_bookmark_past_the_end_of_a_shrunken_document_still_lands_inside_it(
    lite_window,
) -> None:
    """Documents get shorter. A jump to a position that no longer exists must not
    put the caret past the end, where the next keystroke behaves unpredictably."""
    win = lite_window(DOC, cursor=40)
    win.cmd_set_bookmark_1()
    win.control.ChangeValue("tiny")
    win.control.SetInsertionPoint(0)
    win.cmd_next_bookmark()
    assert win.control.GetInsertionPoint() <= len("tiny")


# --------------------------------------------------------------------- #
# Reading the character under the caret
# --------------------------------------------------------------------- #


def test_describe_character_names_the_character_and_its_code_point(lite_window) -> None:
    """ "p" and "P" sound identical read aloud, and so do a hyphen and an en dash.

    The code point and the Unicode name are the only way to tell them apart
    without sight, which is the whole reason the command exists.
    """
    win = lite_window("alpha", cursor=2)
    win.cmd_describe_character()
    assert win.announcements == ["p  U+0070  LATIN SMALL LETTER P"]


def test_describe_character_at_the_end_of_the_document_says_so(lite_window) -> None:
    win = lite_window("alpha", cursor=5)
    win.cmd_describe_character()
    assert win.announcements != []
    assert "U+" not in win.announcements[-1]
