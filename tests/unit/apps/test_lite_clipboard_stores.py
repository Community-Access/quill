"""The three clipboards above the system one: the tray, the collector, the library.

The system clipboard holds one thing, which is one fewer than people need. All
three of these exist because "hold on, let me go back and copy that other bit"
costs a listener a whole trip through a document they cannot glance at.

They are tested here through the commands rather than through their cores
(``quill/core/copy_tray.py`` and friends have their own tests) because the
commands are where the wiring can be wrong in a way the core cannot see: a slot
chosen by the wrong rule, a preview that does not identify what is in the slot, a
refusal that goes quiet instead of saying what to do first.

The real stores are used, in a temporary directory. A stand-in would be a second
implementation of numbered slots to keep in step with the first, and these
commands are mostly *about* the store.
"""

from __future__ import annotations


def test_copy_to_tray_takes_the_first_free_slot_and_previews_it(lite_window) -> None:
    """The preview is the identification. "Copied to tray slot 1" alone would
    leave twelve indistinguishable slots and a memory test."""
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_copy_to_tray()
    assert win.announcements == ["Copied to tray slot 1: alpha"]
    assert win.app.copy_tray.slot(1).text == "alpha"


def test_a_second_copy_goes_to_the_next_free_slot(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_copy_to_tray()
    win.control.SetSelection(6, 11)
    win.cmd_copy_to_tray()
    assert win.announcements[-1] == "Copied to tray slot 2: bravo"


def test_copy_to_tray_with_nothing_selected_says_what_to_do_first(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.cmd_copy_to_tray()
    assert win.announcements == ["Select something to copy first"]
    assert win.app.copy_tray.slot(1).is_empty()


def test_clearing_the_tray_reports_how_many_slots_went(lite_window) -> None:
    """ "Copy tray cleared" was the same sentence for twelve slots and for none.

    Those are the two outcomes most worth telling apart: one of them is the moment
    to reach for undo and the other is nothing at all.
    """
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_copy_to_tray()
    win.control.SetSelection(6, 11)
    win.cmd_copy_to_tray()
    win.cmd_clear_copy_tray()
    assert win.announcements[-1] == "Cleared 2 tray slots"
    assert win.app.copy_tray.slot(1).is_empty()


def test_clearing_one_slot_uses_the_singular(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_copy_to_tray()
    win.cmd_clear_copy_tray()
    assert win.announcements[-1] == "Cleared 1 tray slot"


def test_clearing_an_empty_tray_says_it_was_already_empty(lite_window) -> None:
    win = lite_window("alpha", cursor=0)
    win.cmd_clear_copy_tray()
    assert win.announcements[-1] == "The copy tray is already empty"


# --------------------------------------------------------------------- #
# The collector: gathering into one growing buffer
# --------------------------------------------------------------------- #


def test_collecting_counts_the_pieces_in_words_that_read_aloud(lite_window) -> None:
    """ "1 piece" and "2 pieces", never "1 pieces"."""
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_collect_selection()
    assert win.announcements[-1] == "Collected 1 piece"
    win.control.SetSelection(6, 11)
    win.cmd_collect_selection()
    assert win.announcements[-1] == "Collected 2 pieces"


def test_pasting_the_collection_puts_the_whole_buffer_in(lite_window) -> None:
    win = lite_window("alpha bravo\n", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_collect_selection()
    win.control.SetSelection(6, 11)
    win.cmd_collect_selection()

    win.control.SetInsertionPoint(win.control.GetLastPosition())
    win.cmd_paste_collected()
    pasted = win.control.GetValue()
    assert "alpha" in pasted[12:] and "bravo" in pasted[12:]
    assert win.modified is True


def test_pasting_an_empty_collection_says_so(lite_window) -> None:
    win = lite_window("alpha", cursor=0)
    win.cmd_paste_collected()
    assert "nothing" in win.announcements[-1].lower()


def test_clearing_the_collection_says_so(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_collect_selection()
    win.cmd_clear_collected()
    assert win.app.collected == ""
    win.cmd_paste_collected()
    assert "nothing" in win.announcements[-1].lower()


def test_clearing_the_collection_says_how_much_went(lite_window) -> None:
    """Discarding two gathered quotes and doing nothing are not one sentence."""
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_collect_selection()
    win.control.SetSelection(6, 11)
    win.cmd_collect_selection()
    win.cmd_clear_collected()
    assert win.announcements[-1] == "Collector cleared, 2 pieces discarded"


def test_clearing_an_empty_collector_says_it_was_already_empty(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.cmd_clear_collected()
    assert win.announcements[-1] == "The collector is already empty"


def test_a_piece_containing_the_divider_does_not_inflate_the_count(lite_window) -> None:
    """The count used to be the number of dividers in the buffer plus one.

    A line of dashes is most log files and half of everybody's notes, so the
    count was wrong for exactly the documents this feature is for (bad.md C7).
    """
    text = "one\n\n----\n\ntwo"
    win = lite_window(text, cursor=0)
    win.control.SetSelection(0, len(text))
    win.cmd_collect_selection()
    assert win.announcements[-1] == "Collected 1 piece"


# --------------------------------------------------------------------- #
# The library: the automatic tier under all of it
# --------------------------------------------------------------------- #


def test_the_empty_tray_names_the_key_that_is_actually_bound(lite_window) -> None:
    """It named Control Shift 0, which is QUILL's paste-slot-10 and has not been
    Copy to Tray here since before 1.0 -- and is rebindable besides (bad.md C7)."""
    win = lite_window("alpha", cursor=0)
    win.cmd_paste_from_tray()
    assert win.announcements[-1] == ("The copy tray is empty. Control Alt Y copies into it.")


def test_the_empty_tray_follows_a_rebinding(lite_window) -> None:
    win = lite_window("alpha", cursor=0)
    win.app.keymap = {"cmd_copy_to_tray": "Ctrl+Shift+F9"}
    win.cmd_paste_from_tray()
    assert "Control Shift F9" in win.announcements[-1]


# --------------------------------------------------------------------- #
# Copy to Tray Slot: the number is the point, so it has to be choosable
# --------------------------------------------------------------------- #


def test_the_slot_chooser_offers_every_slot_and_says_what_is_in_it(
    lite_window, lite_dialogs
) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_copy_to_tray()

    win.control.SetSelection(6, 11)
    lite_dialogs.answer("choose_from_rows_clipboard", 7)
    win.cmd_copy_to_tray_slot()

    rows = dict(lite_dialogs.kwargs_for("choose_from_rows_clipboard")["rows"])
    assert rows[1] == "Slot 1: alpha"
    assert rows[2] == "Slot 2: empty"
    assert win.app.copy_tray.slot(7).text == "bravo"
    assert win.announcements[-1] == "Copied to tray slot 7: bravo"


def test_choosing_an_occupied_slot_says_it_replaced_something(lite_window, lite_dialogs) -> None:
    """Overwriting a slot you filled on purpose is the one mistake this can make."""
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_copy_to_tray()

    win.control.SetSelection(6, 11)
    lite_dialogs.answer("choose_from_rows_clipboard", 1)
    win.cmd_copy_to_tray_slot()
    assert win.announcements[-1] == "Replaced tray slot 1: bravo"


def test_cancelling_the_slot_chooser_changes_nothing(lite_window, lite_dialogs) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_copy_to_tray_slot()
    assert win.app.copy_tray.slot(1).is_empty()


def test_the_slot_chooser_with_nothing_selected_says_what_to_do_first(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.cmd_copy_to_tray_slot()
    assert win.announcements[-1] == "Select something to copy first"


# --------------------------------------------------------------------- #
# Copy All
# --------------------------------------------------------------------- #


def test_copy_all_copies_without_selecting(lite_window) -> None:
    """Select All then Copy leaves the document selected, and the next character
    typed replaces all of it. This is the whole reason the command exists."""
    win = lite_window("alpha bravo", cursor=3)
    win.cmd_copy_all()
    assert win.control.clipboard == "alpha bravo"
    assert win.control.GetSelection() == (3, 3)
    assert win.announcements[-1] == "Copied the whole document, 11 characters"


def test_copy_all_on_an_empty_document_says_so(lite_window) -> None:
    win = lite_window("", cursor=0)
    win.cmd_copy_all()
    assert win.announcements[-1] == "The document is empty"
    assert win.control.clipboard == ""


def test_remembering_a_clip_keeps_it(lite_window) -> None:
    """You do not have to have decided in advance that a copy mattered."""
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_remember_clip()
    assert win.announcements[-1] == "Kept in the clip library"


def test_remembering_with_nothing_selected_says_what_to_do_first(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.cmd_remember_clip()
    assert "select" in win.announcements[-1].lower()


# --------------------------------------------------------------------- #
# The automatic tier, which was a promise and a method nobody called
# --------------------------------------------------------------------- #
#
# ``_remember_copy`` was defined, documented in three places -- the module
# docstring, the Recent Clips help text and the Customize Features blurb, all
# promising "a rolling history of the last two hundred things copied" -- and
# called from nowhere at all (bad.md C1). It is wired to wx's own cut and copy
# events now, which is the seam that sees every route into a copy, and it is off
# until somebody asks for it.


def test_a_copy_is_not_remembered_until_asked(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.control.Copy()
    assert win.app.clip_library.all_entries() == []


def test_a_copy_is_remembered_once_the_setting_is_on(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.app.settings.clip_library_autocapture = True
    win.control.SetSelection(0, 5)
    win.control.Copy()
    entries = win.app.clip_library.all_entries()
    assert [entry.fragment.markup for _index, entry in entries] == ["alpha"]


def test_a_cut_is_remembered_too(lite_window) -> None:
    """QUILL's own capture never saw a cut, which is the copy most worth keeping:
    the text is no longer in the document to go back for (bad.md C1)."""
    win = lite_window("alpha bravo", cursor=0)
    win.app.settings.clip_library_autocapture = True
    win.control.SetSelection(0, 5)
    win.control.Cut()
    entries = win.app.clip_library.all_entries()
    assert [entry.fragment.markup for _index, entry in entries] == ["alpha"]


def test_copy_all_fills_the_library_when_asked(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.app.settings.clip_library_autocapture = True
    win.cmd_copy_all()
    entries = win.app.clip_library.all_entries()
    assert [entry.fragment.markup for _index, entry in entries] == ["alpha bravo"]
