"""The Edit menu: the clipboard, undo, redo, delete, and how each reports back.

Cut, copy, paste, delete, undo and redo change the document and change **nothing
a screen reader announces**. No focus moves, no control is named, no selection
changes -- so to a listener a working Ctrl+C and a dead one are the same event.
That is why they have earcons, and it is why the earcon is not a nicety to be
tested loosely: it is the entire feedback these six commands have.

Two things are checked that were both reported broken by ear on 2026-09-10.

**The cue has to fire whichever route was taken.** It used to be posted inside
``cmd_copy``, which covers the accelerator and the menu and misses the control's
own key handling and the context menu. It now hangs off ``wxEVT_TEXT_CUT`` /
``COPY`` / ``PASTE``, which the control raises from the Windows messages it acts
on -- one event per operation, all four routes. The harness raises those events
the way the real control does, so deleting the binding fails these tests.

**The user chooses the channel.** ``settings.action_feedback`` is sound (the
default and what QUILL has always done), speech, both, or neither, and the rule
is in :mod:`quill.core.action_feedback` so that both editors resolve it
identically. What is asserted below is that each mode reaches the channels it
promises -- and that a mode asking for a tone where the pack has none falls
through to words rather than to silence.
"""

from __future__ import annotations

import pytest

from quill.core.sound_events import SoundEvent

# --------------------------------------------------------------------- #
# The three the control does itself
# --------------------------------------------------------------------- #


def test_copy_puts_the_selection_on_the_clipboard_and_cues(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.cmd_copy()
    assert win.control.clipboard == "alpha"
    assert SoundEvent.TEXT_COPIED in win.cues


def test_cut_removes_the_selection_and_cues(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 6)
    win.cmd_cut()
    assert win.control.GetValue() == "bravo"
    assert win.control.clipboard == "alpha "
    assert SoundEvent.TEXT_CUT in win.cues


def test_paste_inserts_and_cues(lite_window) -> None:
    win = lite_window("alpha ", cursor=6, mode="rich")
    win.control.clipboard = "bravo"
    win.cmd_paste()
    assert win.control.GetValue() == "alpha bravo"
    assert SoundEvent.TEXT_PASTED in win.cues


def test_the_cue_rides_the_control_not_the_command(lite_window) -> None:
    """The regression this arrangement exists to prevent.

    A Ctrl+C the control handles itself never reaches ``cmd_copy``, so a cue
    posted there is a cue that fires for some copies and not others -- and
    "sometimes silent" is indistinguishable from "broken" when silence is the
    only other thing the moment can be.
    """
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 5)
    win.control.Copy()  # the control's own key handling, bypassing cmd_copy
    assert SoundEvent.TEXT_COPIED in win.cues


def test_the_cue_handler_skips_so_the_control_still_cuts(lite_window) -> None:
    """A handler that swallowed the event would stop Ctrl+X working outright.

    The event *is* how the control learns it has been asked to cut. This is the
    one place where getting the feedback wrong breaks the feature.
    """
    win = lite_window("alpha bravo", cursor=0)
    handler = win.control.clipboard_handlers["cut"]

    class _Event:
        skipped = False

        def Skip(self, skip: bool = True) -> None:  # noqa: N802 - wx API shape
            self.skipped = bool(skip)

    event = _Event()
    handler(event)
    assert event.skipped is True


def test_all_three_clipboard_events_are_bound(lite_window) -> None:
    win = lite_window("alpha", cursor=0)
    assert set(win.control.clipboard_handlers) == {"cut", "copy", "paste"}


def test_paste_in_a_plain_document_pastes_as_plain_text(lite_window) -> None:
    """ "Plain text document" has to mean the paste arrives plain.

    The control is a Rich Edit whatever the document is, so a straight Paste
    would bring formatting in and then drop it, silently, at the next save.
    """
    win = lite_window("alpha ", cursor=6, mode="plain")
    win.control.clipboard = "bravo"
    win.cmd_paste()
    assert win.control.GetValue() == "alpha bravo"
    assert any("as plain text" in message for message in win.announcements)


def test_paste_plain_reports_how_much_arrived(lite_window) -> None:
    """The count is the informative half and is spoken in every mode.

    A tone cannot carry "1,234 characters", and after a paste that is exactly the
    fact somebody needs.
    """
    win = lite_window("", cursor=0, mode="rich")
    win.control.clipboard = "x" * 1234
    win.cmd_paste_plain()
    assert win.announcements == ["Pasted 1,234 characters as plain text"]
    assert SoundEvent.TEXT_PASTED in win.cues


def test_paste_plain_with_an_empty_clipboard_says_so(lite_window) -> None:
    win = lite_window("alpha", cursor=0, mode="rich")
    win.control.clipboard = ""
    win.cmd_paste_plain()
    assert win.announcements == ["The clipboard has no text"]
    assert win.cues == []


# --------------------------------------------------------------------- #
# Delete
# --------------------------------------------------------------------- #


def test_delete_removes_the_selection(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.control.SetSelection(0, 6)
    win.cmd_delete()
    assert win.control.GetValue() == "bravo"
    assert SoundEvent.TEXT_DELETED in win.cues


def test_delete_with_no_selection_takes_the_next_character(lite_window) -> None:
    win = lite_window("alpha", cursor=0)
    win.cmd_delete()
    assert win.control.GetValue() == "lpha"


def test_delete_at_the_very_end_takes_nothing_and_does_not_reach_past_it(lite_window) -> None:
    win = lite_window("alpha", cursor=5)
    win.cmd_delete()
    assert win.control.GetValue() == "alpha"


# --------------------------------------------------------------------- #
# Undo and redo
# --------------------------------------------------------------------- #


def test_undo_puts_the_text_back_and_cues(lite_window) -> None:
    win = lite_window("alpha", cursor=5)
    win.control.WriteText(" bravo")
    win.cmd_undo()
    assert win.control.GetValue() == "alpha"
    assert SoundEvent.UNDO_PERFORMED in win.cues


def test_redo_reapplies_it(lite_window) -> None:
    win = lite_window("alpha", cursor=5)
    win.control.WriteText(" bravo")
    win.cmd_undo()
    win.cmd_redo()
    assert win.control.GetValue() == "alpha bravo"
    assert SoundEvent.REDO_PERFORMED in win.cues


def test_nothing_to_undo_says_it_as_well_as_sounding_it(lite_window) -> None:
    """The one of the six where something *failed*.

    A listener should not have to interpret a tone to find out that the keystroke
    did nothing -- and the tone for it deliberately does not move in pitch,
    because the undo stack did not move either.
    """
    win = lite_window("alpha", cursor=0)
    win.cmd_undo()
    assert win.announcements == ["Nothing to undo"]
    assert SoundEvent.NOTHING_TO_UNDO in win.cues
    assert SoundEvent.UNDO_PERFORMED not in win.cues


def test_nothing_to_redo_says_so(lite_window) -> None:
    win = lite_window("alpha", cursor=0)
    win.cmd_redo()
    assert win.announcements == ["Nothing to redo"]
    assert SoundEvent.NOTHING_TO_UNDO in win.cues


# --------------------------------------------------------------------- #
# Select All and Insert Date and Time
# --------------------------------------------------------------------- #


def test_select_all_selects_everything(lite_window) -> None:
    win = lite_window("alpha bravo\ncharlie\n", cursor=0)
    win.cmd_select_all()
    assert win.control.GetSelection() == (0, 20)


def test_select_all_says_nothing_because_the_reader_does(lite_window) -> None:
    """GATE-13: a selection change is the screen reader's to announce."""
    win = lite_window("alpha bravo", cursor=0)
    win.cmd_select_all()
    assert win.announcements == []


def test_select_all_still_tells_the_status_bar_to_recount(lite_window) -> None:
    """The bar carries a Selection cell, and Ctrl+A was the one way of selecting
    that never asked it to recount -- so it went on saying "No selection" over a
    fully selected document."""
    win = lite_window("alpha bravo", cursor=0)
    before = win.status_touches
    win.cmd_select_all()
    assert win.status_touches > before


def test_insert_datetime_reads_back_what_it_inserted(lite_window) -> None:
    """Text appeared that nobody typed, and the reader says nothing about it.

    Without the read-back, F5 was a keystroke after which finding out what had
    landed meant arrowing back over it a character at a time.
    """
    win = lite_window("at ", cursor=3)
    win.cmd_insert_datetime()
    inserted = win.control.GetValue()[3:]
    assert inserted
    assert win.announcements == [f"Inserted {inserted}"]
    assert win.modified is True


# --------------------------------------------------------------------- #
# action_feedback: which channel each mode reaches
# --------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("mode", "expect_sound", "expect_speech"),
    [
        ("sound", True, False),
        ("speech", False, True),
        ("both", True, True),
        ("silent", False, False),
    ],
)
def test_each_feedback_mode_reaches_the_channels_it_promises(
    lite_window, mode: str, expect_sound: bool, expect_speech: bool
) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.app.settings.action_feedback = mode
    win.control.SetSelection(0, 5)
    win.cmd_copy()
    assert (SoundEvent.TEXT_COPIED in win.cues) is expect_sound
    assert ("Copied" in win.app.voice.said) is expect_speech


def test_the_default_is_the_tone_alone(lite_settings) -> None:
    """A setting that changed behaviour for somebody who never opened it would be
    a regression wearing a feature's clothes."""
    assert lite_settings.action_feedback == "sound"


def test_sound_mode_speaks_when_the_pack_has_no_clip(lite_window) -> None:
    """The setting chooses between two kinds of feedback, never down to none."""
    win = lite_window("alpha bravo", cursor=0)
    win.app.settings.action_feedback = "sound"
    win.available_sounds = frozenset()
    win.control.SetSelection(0, 5)
    win.cmd_copy()
    assert win.cues == []
    assert "Copied" in win.app.voice.said


def test_silent_still_writes_the_status_bar(lite_window) -> None:
    """The bar is the record, not the feedback.

    Somebody who turned the audio off is exactly the person who then reads the bar
    back with their reader to find out what happened, so a mode about *audio* has
    no business emptying it.
    """
    win = lite_window("alpha bravo", cursor=0)
    win.app.settings.action_feedback = "silent"
    win.control.SetSelection(0, 5)
    win.cmd_copy()
    assert "Copied" in win.status_messages


def test_an_unreadable_mode_falls_back_to_the_default(lite_window) -> None:
    """Settings arrive from a file a person may have edited by hand."""
    win = lite_window("alpha bravo", cursor=0)
    win.app.settings.action_feedback = "loud noises"
    win.control.SetSelection(0, 5)
    win.cmd_copy()
    assert SoundEvent.TEXT_COPIED in win.cues
    assert "Copied" not in win.app.voice.said
