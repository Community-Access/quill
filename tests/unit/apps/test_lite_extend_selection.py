"""F8 extend mode, driven the way the keyboard drives it.

This file exists because of a bug that every other kind of test passed over.
``cmd_start_selection`` was right, ``cmd_complete_selection`` was right, the keys
were right, the menu was right, and F8 followed by Shift+F8 answered **"No
selection in progress"** every single time -- reported by ear, 2026-09-10:
*"using f8 and then shift+f8 tells me that no selection was enabled and so this
feels wrong."*

The fault was between the two. F8's accelerator set the anchor; a moment later
F8's own *key-up* reached the control, ``_on_caret_moved`` handed the key code to
``extend_selection_after_move``, and the rule there was "anything that is not a
navigation key ends the mode" -- which F8 is not. So the mode ended on the
keystroke that started it, and nothing in the app said so.

Nothing that inspects the command table can see that, and nothing that calls one
command at a time can either. What catches it is calling **the command and the
hook, in the order the window fires them**, which is what every test below does
through ``on_caret_moved``. Read that as "the user let go of the key".
"""

from __future__ import annotations

import wx


def test_f8_then_shift_f8_reports_a_selection(lite_window) -> None:
    """The regression, in one test.

    Nobody presses F8 without releasing it, so a mode that could not survive the
    release was a mode that had never once worked.
    """
    win = lite_window("alpha bravo charlie", cursor=0)

    win.cmd_start_selection()
    win.on_caret_moved(wx.WXK_F8)  # the F8 key coming back up

    assert win.selection_extend_active(), (
        "F8's own key-up ended the mode it had just started -- the 2026-09-10 bug"
    )

    win.control.SetInsertionPoint(5)
    win.on_caret_moved(wx.WXK_RIGHT)
    win.cmd_complete_selection()

    assert win.control.GetSelection() == (0, 5)
    assert any("Selected" in message for message in win.announcements), win.announcements
    assert "No selection in progress" not in win.announcements


def test_every_function_key_leaves_the_mode_alone(lite_window) -> None:
    """Not just F8: a key nobody thought about must not end the mode.

    The old rule was an inverse -- everything except navigation cancelled -- so
    each of these was a second copy of the same bug waiting for somebody to press
    it while extending.
    """
    for key in (wx.WXK_F1, wx.WXK_F5, wx.WXK_F8, wx.WXK_F12, wx.WXK_ALT, wx.WXK_MENU):
        win = lite_window("alpha bravo", cursor=0)
        win.cmd_start_selection()
        win.on_caret_moved(key)
        assert win.selection_extend_active(), f"{key} ended extend mode"


def test_a_mouse_release_does_not_end_the_mode(lite_window) -> None:
    """``EVT_LEFT_UP`` shares the handler and carries no key code at all.

    It arrived as ``0``, which was not navigation, which cancelled -- so clicking
    anywhere while extending silently dropped the anchor.
    """
    win = lite_window("alpha bravo", cursor=0)
    win.cmd_start_selection()
    win.on_caret_moved(0)
    assert win.selection_extend_active()


def test_moving_after_the_marker_leaves_the_caret_alone(lite_window) -> None:
    """The 2026-09-15 report, in one test.

    F8 used to stretch a live selection to meet the caret on every navigation
    key-up. On wxMSW an arrow key pressed with text selected collapses the
    selection to its edge and stays there, so the next key-up re-selected the
    same span and the caret stopped advancing after one character -- "if I press
    F8 the cursor doesn't move at all after pressing it". Nothing may touch the
    selection between the marker and Shift+F8.
    """
    win = lite_window("alpha bravo charlie", cursor=6)
    win.cmd_start_selection()
    win.on_caret_moved(wx.WXK_F8)

    for position in (7, 8, 9, 10, 11):
        win.control.SetInsertionPoint(position)
        win.on_caret_moved(wx.WXK_RIGHT)
        assert win.control.GetSelection() == (position, position), (
            "the marker must not select anything until Shift+F8 asks it to"
        )
        assert win.control.GetInsertionPoint() == position, (
            "and it must never move the caret the user just moved"
        )

    win.cmd_complete_selection()
    assert win.control.GetSelection() == (6, 11)
    assert win.control.GetValue()[6:11] == "bravo"


def test_the_span_reaches_backwards_too(lite_window) -> None:
    """Marker after caret is the same question asked the other way round."""
    win = lite_window("alpha bravo charlie", cursor=11)
    win.cmd_start_selection()
    win.on_caret_moved(wx.WXK_F8)

    for position in (10, 9, 8, 7, 6):
        win.control.SetInsertionPoint(position)
        win.on_caret_moved(wx.WXK_LEFT)

    win.cmd_complete_selection()
    assert win.control.GetSelection() == (6, 11)


def test_a_find_between_the_two_keystrokes_is_not_the_answer(lite_window) -> None:
    """What the marker model buys, and live extension could never have done.

    Find leaves its own match selected. Honouring "whatever is selected" would
    hand back the match; the span is the marker and the caret, so it hands back
    the run the user actually marked.
    """
    win = lite_window("alpha bravo charlie delta", cursor=0)
    win.cmd_start_selection()
    # A Find lands on "charlie" and selects it, as Find does.
    win.control.SetSelection(12, 19)
    win.control.SetInsertionPoint(19)

    win.cmd_complete_selection()
    assert win.control.GetSelection() == (0, 19)
    assert win.control.GetValue()[0:19] == "alpha bravo charlie"


def test_a_standing_selection_is_left_to_the_control(lite_window) -> None:
    """Shift+arrow extends natively; re-deriving the span would fight it."""
    win = lite_window("alpha bravo charlie", cursor=0)
    win.cmd_start_selection()
    win.control.SetSelection(0, 11)
    win.on_caret_moved(wx.WXK_SHIFT)
    assert win.control.GetSelection() == (0, 11)


def test_typing_ends_the_mode(lite_window) -> None:
    """The documented intent, now tested through the hook that can see it.

    A letter replaces the selection, so there is nothing left to extend and the
    anchor points into text that has moved. The text changing is the signal, not
    the key code -- a paste and a menu command do it too.
    """
    win = lite_window("alpha bravo", cursor=0)
    win.cmd_start_selection()
    win.control.WriteText("x")
    win.on_text_changed()
    assert not win.selection_extend_active()


def test_loading_a_document_does_not_end_the_mode_by_accident(lite_window) -> None:
    """``ChangeValue`` is how a load writes text, and it raises no text event.

    The real window guards on ``_loading`` for exactly this reason; the guard is
    worth a test because removing it would look harmless.
    """
    win = lite_window("alpha bravo", cursor=0)
    win.cmd_start_selection()
    win.control.ChangeValue("something else entirely")
    assert win.selection_extend_active()


def test_dropping_the_marker_says_so(lite_window) -> None:
    """Silence and "dropped" are different answers, and only one is usable.

    The marker is invisible state, so every change to it is spoken. Escape no
    longer reaches it -- there is no mode for Escape to leave, and a key-up hook
    that touched the marker is exactly what this change removed.
    """
    win = lite_window("alpha bravo", cursor=0)
    win.cmd_start_selection()
    win.cancel_extend_selection()
    assert not win.selection_extend_active()
    assert win.announcements[-1] == "Selection marker dropped"


def test_dropping_a_marker_that_was_never_set_says_nothing(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.cancel_extend_selection()
    assert win.announcements == []


def test_escape_no_longer_touches_the_marker(lite_window) -> None:
    """Escape is the control's business now, not the selection's."""
    win = lite_window("alpha bravo", cursor=0)
    win.cmd_start_selection()
    win.on_caret_moved(wx.WXK_ESCAPE)
    assert win.selection_extend_active()


def test_complete_without_start_says_why(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.cmd_complete_selection()
    assert win.announcements == ["No selection marked. Press F8 where you want it to start."]


def test_complete_after_no_movement_says_nothing_was_taken(lite_window) -> None:
    """A refusal, not silence: the mode did end, and the user has to hear that."""
    win = lite_window("alpha bravo", cursor=3)
    win.cmd_start_selection()
    win.on_caret_moved(wx.WXK_F8)
    win.cmd_complete_selection()
    assert win.announcements[-1] == "Selection cancelled, nothing selected"
    assert not win.selection_extend_active()


def test_complete_falls_back_to_the_anchor_when_nothing_was_selected(lite_window) -> None:
    """The caret travelled and no selection was ever set: still report the span.

    This is the belt to the braces. If live extension misses -- an unbound key, a
    caret moved by something other than a navigation key -- the anchor is still a
    truthful answer, and it is a better one than "nothing selected" after the
    user has heard the caret move.
    """
    win = lite_window("alpha bravo charlie", cursor=0)
    win.cmd_start_selection()
    win.control.SetInsertionPoint(11)  # moved, but no hook ran
    win.cmd_complete_selection()
    assert win.control.GetSelection() == (0, 11)


def test_the_check_mark_follows_the_mode(lite_window) -> None:
    """The Extend Mode menu item mirrors the anchor, so every exit must sync it.

    A menu that says the mode is on when it is off is worse than no menu item:
    it is the only place a listener can go to find out.
    """
    win = lite_window("alpha bravo", cursor=0)
    before = win.checks_synced
    win.cmd_start_selection()
    assert win.checks_synced > before
    synced = win.checks_synced
    win.cancel_extend_selection()
    assert win.checks_synced > synced


def test_toggle_extend_mode_turns_it_both_ways(lite_window) -> None:
    win = lite_window("alpha bravo", cursor=0)
    win.cmd_toggle_extend_mode()
    assert win.selection_extend_active()
    win.cmd_toggle_extend_mode()
    assert not win.selection_extend_active()


def test_starting_a_selection_makes_a_sound_as_well_as_speaking(lite_window) -> None:
    """The sounds existed in the pack and QuillLite played neither of them.

    ``selection_started.wav`` and ``selection_completed.wav`` have shipped in the
    Ink pack all along; QUILL posted both and QuillLite posted neither.
    """
    from quill.core.sound_events import SoundEvent

    win = lite_window("alpha bravo charlie", cursor=0)
    win.cmd_start_selection()
    assert SoundEvent.SELECTION_STARTED in win.cues

    win.control.SetInsertionPoint(5)
    win.on_caret_moved(wx.WXK_RIGHT)
    win.cmd_complete_selection()
    assert SoundEvent.SELECTION_COMPLETED in win.cues


def test_completing_an_empty_selection_makes_no_completion_sound(lite_window) -> None:
    """A cue is for something that happened."""
    from quill.core.sound_events import SoundEvent

    win = lite_window("alpha", cursor=2)
    win.cmd_start_selection()
    win.cmd_complete_selection()
    assert SoundEvent.SELECTION_COMPLETED not in win.cues
