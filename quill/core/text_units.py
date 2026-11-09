"""Text lengths in the units a native Windows edit control counts.

A Python string counts code points; a Windows Edit or Rich Edit control (and
so every ``wx.TextCtrl`` on wxMSW) counts UTF-16 code units. They agree until
an astral character -- every emoji -- arrives: it is one code point and two
units. Arithmetic that adds ``len(text)`` to a position the control gave
lands one short per emoji, so the caret stops between the two halves of a
surrogate pair, and the next edit cuts the character in two.

:func:`native_length` is the length to add to a control position;
:func:`native_offset` and :func:`text_index` convert a whole offset each way,
for the seams where a position from the control meets a slice of its
``GetValue()`` (review 2026-11-09, QUILL 5 and QUILL Lite 7). Pure, wx-free.
"""

from __future__ import annotations

import re
import sys

__all__ = ["native_length", "native_offset", "text_index", "utf16_length"]

_ASTRAL = re.compile("[\U00010000-\U0010ffff]")


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


def native_offset(text: str, index: int, *, platform: str | None = None) -> int:
    """The control position of code-point *index* in *text* (clamped to it)."""
    index = max(0, min(index, len(text)))
    return native_length(text[:index], platform=platform)


def text_index(text: str, position: int, *, platform: str | None = None) -> int:
    """The code-point index in *text* of control *position*: the inverse.

    A position between the two halves of an astral character (which the control
    should never report) maps to the character after it.
    """
    position = max(0, position)
    if (platform or sys.platform) != "win32":
        return min(position, len(text))
    index = units = 0
    for match in _ASTRAL.finditer(text):
        # Everything before this astral character is one unit per code point.
        gap = match.start() - index
        if units + gap >= position:
            return index + (position - units)
        units += gap + 2
        index = match.start() + 1
        if units >= position:
            return index
    return min(index + (position - units), len(text))
