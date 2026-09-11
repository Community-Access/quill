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


# --------------------------------------------------------------------- #
# The library: the automatic tier under all of it
# --------------------------------------------------------------------- #


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
