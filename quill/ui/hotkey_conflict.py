"""Saying that another application has taken a chord, in both Keyboard Managers.

Both editors ship a conflict-aware keymap editor that answers "what is this key
already doing?" -- and both could only see inside QUILL. Reported while testing:
"Ctrl+Alt+G interferes with Google Drive." It does, and nothing in either editor
could have said so.

The fact underneath is not negotiable. ``RegisterHotKey`` is a system-wide
claim, and Windows hands the key to its owner *before* a focused application
sees it, so an in-app accelerator on the same chord is never consulted. The key
does nothing, the command looks broken, and the Keyboard Manager -- the one
place a person goes to find out about keys -- says the chord is free.

Sweeping the shipped defaults on one developer machine found **five** claimed
chords, not one: Preferences, New Plain Text Document, Unquote Lines, the
Keyboard Manager itself, and the collector that prompted the report. That is
the argument against chasing them one at a time. The set depends entirely on
what somebody has installed, so no list of defaults can dodge it; what an editor
can do is stop being silent about it.

This sits in ``quill/ui`` rather than ``quill/core`` on purpose: it asks the
live operating system a question, which is not something a pure domain module
should do, and it needs the binding parser the UI layer already owns.
"""

from __future__ import annotations

from typing import Any

from quill.ui.keybinding_parse import KeybindingParseMixin

__all__ = ["claimed_by_another_application", "claim_sentence"]


class _Parser(KeybindingParseMixin):
    """The shared binding parser, given the wx module it reads chords with."""

    def __init__(self, wx_module: Any) -> None:
        self._wx = wx_module


def claimed_by_another_application(chord: str, wx_module: Any) -> bool:
    """Whether *chord* is held system-wide by some other application.

    False for a chord nothing holds, for one this platform cannot be asked
    about, and for one that will not parse -- "I could not tell" must never be
    shown to somebody as "another application has it".
    """
    from quill.platform.windows.hotkey_owner import ChordOwner, chord_owner

    parsed = _Parser(wx_module)._parse_keybinding(chord)
    if parsed is None:
        return False
    return chord_owner(*parsed) is ChordOwner.ANOTHER_APPLICATION


def claim_sentence(chord: str, wx_module: Any) -> str:
    """What to tell somebody about *chord*, or ``""`` when there is nothing to say.

    It does not name the application. Windows does not offer the owner, and
    guessing from a list of the usual suspects would be a lie the first time
    somebody installed something that is not on it. What it does say is the part
    a person can act on: the key will not reach this window, and the way out is
    a different key.
    """
    if not claimed_by_another_application(chord, wx_module):
        return ""
    return (
        f"{chord} is already claimed by another application running on this "
        "computer, so Windows sends it there and this window never sees it. "
        "Choose a different key."
    )
