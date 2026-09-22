r"""The Delete and Backspace keys make a sound, because the menu item always did.

Reported: "the delete key does not play a sound, or I do not hear one." It did
not, and the reason is in ``cmd_delete``'s own docstring -- "The Del key already
does this inside the control". The earcon lived in the command, the command is
the *menu item*, and the key nobody uses the menu for went straight past it.

The same shape as cut, copy and paste, which is why ``bind_clipboard_cues``
exists: a cue posted inside ``cmd_copy`` reports the copies that went through
``cmd_copy`` and no others.
"""

from __future__ import annotations

import wx

from quill.core.sound_events import SoundEvent


class _KeyEvent:
    """The two methods the handler asks of a key event, and the one it sets."""

    def __init__(self, code: int) -> None:
        self._code = code
        self.skipped = False

    def GetKeyCode(self) -> int:  # noqa: N802 - wx API shape
        return self._code

    def Skip(self) -> None:  # noqa: N802 - wx API shape
        self.skipped = True


def _press(window, code: int) -> None:
    window._on_key_down(_KeyEvent(code))


def test_the_delete_key_sounds(lite_window) -> None:
    window = lite_window("something to delete", cursor=0)
    _press(window, wx.WXK_DELETE)
    assert SoundEvent.TEXT_DELETED in window.cues


def test_the_backspace_key_sounds(lite_window) -> None:
    window = lite_window("something to delete", cursor=4)
    _press(window, wx.WXK_BACK)
    assert SoundEvent.TEXT_DELETED in window.cues


def test_a_selection_sounds_from_either_key(lite_window) -> None:
    window = lite_window("something to delete", cursor=0)
    window.control.SetSelection(0, 9)
    _press(window, wx.WXK_BACK)
    assert SoundEvent.TEXT_DELETED in window.cues


def test_delete_at_the_end_of_the_document_is_silent(lite_window) -> None:
    """A tone that says something went when nothing did is worse than none."""
    window = lite_window("all of it", cursor=9)
    _press(window, wx.WXK_DELETE)
    assert SoundEvent.TEXT_DELETED not in window.cues


def test_backspace_at_the_start_of_the_document_is_silent(lite_window) -> None:
    window = lite_window("all of it", cursor=0)
    _press(window, wx.WXK_BACK)
    assert SoundEvent.TEXT_DELETED not in window.cues


def test_the_key_is_never_swallowed(lite_window) -> None:
    """The control does the deleting; the cue only listens.

    A handler that stopped skipping would stop Delete working outright, which
    is a far worse bug than the silent one it was added to fix.
    """
    window = lite_window("something to delete", cursor=0)
    event = _KeyEvent(wx.WXK_DELETE)
    window._on_key_down(event)
    assert event.skipped is True


def test_nothing_is_spoken_for_a_keystroke(lite_window) -> None:
    """GATE-13: the reader already says the character that went.

    A sentence per press -- on a key that repeats while it is held -- is the
    over-announcement nobody files and everybody turns the app off over. It
    would take the status message with it, too, burying whatever the bar was
    actually reporting under one word.
    """
    window = lite_window("something to delete", cursor=0)
    _press(window, wx.WXK_DELETE)
    assert window.announcements == []
    assert window.status_messages == []
