"""Is a key held down right now, in whichever program has the keyboard?

QUILL Transcribe's hold-to-talk (D-9) follows its start and stop key, which is
registered with ``RegisterHotKey``: Windows reports the press and never the
release. Rather than a low-level keyboard hook -- which would see every key
the person types in every program -- the host asks ``GetAsyncKeyState`` about
that one key, every few hundredths of a second, and only while a press is
being followed. Nothing else is read, kept or logged.

``GetAsyncKeyState`` answers for the whole desktop, unlike ``GetKeyState``
(and so ``wx.GetKeyState``), which follows the calling thread's own input and
does not change while another program is in front.

Windows-only in effect; anywhere else, or on any failure, the key is "up".
"""

from __future__ import annotations

import sys

__all__ = ["key_is_down"]

_DOWN = 0x8000


def key_is_down(virtual_key: int) -> bool:
    """Whether the key with Windows virtual-key code *virtual_key* is down now."""
    if not virtual_key or not sys.platform.startswith("win"):
        return False
    try:
        import ctypes

        return bool(int(ctypes.windll.user32.GetAsyncKeyState(int(virtual_key))) & _DOWN)
    except Exception:  # noqa: BLE001 - cannot ask: treat as let go
        return False
