"""Text lengths in the units a native Windows edit control counts.

A Python string counts code points; a Windows Edit or Rich Edit control (and
so every ``wx.TextCtrl`` on wxMSW) counts UTF-16 code units. They agree until
an astral character -- every emoji -- arrives: it is one code point and two
units. Arithmetic that adds ``len(text)`` to a position the control gave
lands one short per emoji, so the caret stops between the two halves of a
surrogate pair, and the next edit cuts the character in two.

:func:`native_length` is the length to add to a control position. Pure,
wx-free.
"""

from __future__ import annotations

import sys

__all__ = ["native_length", "utf16_length"]


def utf16_length(text: str) -> int:
    """How many UTF-16 code units *text* is: two for each astral character."""
    return len(text) + sum(1 for char in text if ord(char) > 0xFFFF)


def native_length(text: str, *, platform: str | None = None) -> int:
    """*text*'s length in the units a text control's positions count.

    UTF-16 units on Windows; code points elsewhere (wxGTK and wxOSX count
    characters). *platform* defaults to ``sys.platform``.
    """
    if (platform or sys.platform) == "win32":
        return utf16_length(text)
    return len(text)
