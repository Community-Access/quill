"""Whether another application has already claimed a chord system-wide.

Reported while testing: "Ctrl+Alt+G interferes with Google Drive." It does, and
nothing QUILL binds can win that fight. ``RegisterHotKey`` is a **system-wide**
claim: Windows delivers the key to its owner before a focused application sees
it, so an in-app accelerator on the same chord is not merely outranked, it is
never consulted. The command had a label, a menu row, a handler and a key, and
the key did nothing, and nothing said why.

Moving the one chord was the fix for that one app. This is the fix for the next
one. The Keyboard Manager in both editors already answers "what is this key
already doing?" -- it just could not see outside QUILL. Now it can: a chord is
probed by trying to claim it and immediately letting it go, which is the only
thing Windows will actually answer. A refusal with
``ERROR_HOTKEY_ALREADY_REGISTERED`` means somebody else has it.

Three things this deliberately does not do.

It does not say **who**. Windows does not offer the owner, and guessing from a
list of known applications would be a lie the moment somebody installed
something not on it.

It does not probe anything but a **global** claim, because that is the only kind
that can take a key away from a focused window. Another editor's in-app
accelerator for Ctrl+B is not a conflict and never was.

And it never leaves the hotkey registered. The probe claims the chord for the
length of one call and releases it in a ``finally`` -- taking a chord away from
the user while telling them it is free would be a remarkable way to answer the
question.
"""

from __future__ import annotations

import sys
from enum import Enum

__all__ = ["ChordOwner", "chord_owner"]

#: ``winerror.h``. Returned by GetLastError when the chord is somebody else's.
_ERROR_HOTKEY_ALREADY_REGISTERED = 1409

#: An id no other code in this process uses. RegisterHotKey ids are per-thread,
#: and the probe releases the chord before returning, so nothing collides.
_PROBE_ID = 0x5155  # "QU"


class ChordOwner(Enum):
    """Who holds a chord system-wide, as far as Windows will say."""

    #: Nothing holds it: an accelerator on this chord will be delivered.
    FREE = "free"
    #: Another application holds it; this chord cannot reach a focused window.
    ANOTHER_APPLICATION = "another_application"
    #: Not answerable here -- not Windows, or the chord could not be parsed.
    UNKNOWN = "unknown"


def chord_owner(modifiers: int, key_code: int) -> ChordOwner:
    """Whether *modifiers* + *key_code* is claimed system-wide by someone else.

    Takes the Win32 modifier flags and virtual-key code rather than a chord
    string: the editors already parse chords (``_parse_keybinding``), and a
    second parser would be a second thing to get wrong.

    Never raises. Every failure that is not an outright refusal answers
    ``UNKNOWN``, because "I could not tell" and "nobody owns it" are different
    answers and only one of them is safe to show somebody.
    """
    if sys.platform != "win32":
        return ChordOwner.UNKNOWN
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:  # noqa: BLE001 - no ctypes is an answer of "cannot tell"
        return ChordOwner.UNKNOWN
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        register = user32.RegisterHotKey
        register.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        register.restype = wintypes.BOOL
        unregister = user32.UnregisterHotKey
        unregister.argtypes = [wintypes.HWND, ctypes.c_int]
        unregister.restype = wintypes.BOOL
    except Exception:  # noqa: BLE001
        return ChordOwner.UNKNOWN

    took = False
    try:
        took = bool(register(None, _PROBE_ID, int(modifiers), int(key_code)))
        if took:
            return ChordOwner.FREE
        if ctypes.get_last_error() == _ERROR_HOTKEY_ALREADY_REGISTERED:
            return ChordOwner.ANOTHER_APPLICATION
        return ChordOwner.UNKNOWN
    except Exception:  # noqa: BLE001 - a probe must never break a dialog
        return ChordOwner.UNKNOWN
    finally:
        if took:
            try:
                unregister(None, _PROBE_ID)
            except Exception:  # noqa: BLE001 - nothing left to do about it
                pass
