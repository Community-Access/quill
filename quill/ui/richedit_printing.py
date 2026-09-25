"""Printing a rich document as it looks: ``EM_FORMATRANGE`` on the shared surface.

Neither editor printed formatting. QUILL printed ``editor.GetValue()`` -- flat
text with no structural marker at all -- and QUILL Lite at least prefixed a
heading line with its level, which meant the *small* product was ahead on paper
(bad.md PR1, PR3). Both are fixed here, in one place, because a second
implementation of this is a second set of pagination bugs.

``EM_FORMATRANGE`` is how WordPad prints, and the only way to get a Rich Edit
control's own rendering onto a printer DC: the control is handed a device
context and a rectangle in **twips**, lays out as much text as fits, draws it,
and answers with the character offset it reached. Print a page, feed that offset
back as the next page's start, repeat until the whole document is consumed.

Three things about it bite, and all three are in the code below:

* **Twips, not pixels.** The rectangle is in 1/1440ths of an inch and the DC
  reports pixels, so every measurement is converted through the DC's own
  logical-pixels-per-inch. Getting this wrong does not raise; it silently prints
  one line per sheet, or the top-left ninth of the page.
* **Measure before you draw.** The same call does both, chosen by a flag, and a
  page count has to be known before the first page is drawn -- so the document
  is laid out once with drawing off to count the pages, then again to print.
* **It allocates, and you have to say when you are done.** ``EM_FORMATRANGE``
  with a null range frees the cache the control built; skipping it leaks for the
  life of the process.

Off Windows, or with no native surface, :func:`format_range_available` answers
``False`` and the caller keeps its existing text printout. That is not a
fallback so much as the honest answer: there is no Rich Edit to ask.
"""

from __future__ import annotations

import sys
from typing import Any

__all__ = ["format_range_available", "print_rich_document"]

# richedit.h
_EM_FORMATRANGE = 0x0400 + 57
#: A twip is 1/1440 inch. The rectangle EM_FORMATRANGE takes is in twips while
#: every DC measurement is in pixels, and the conversion needs the DC's own DPI.
_TWIPS_PER_INCH = 1440

_AVAILABLE = False

if sys.platform == "win32":  # pragma: no cover - Windows + a real HWND only
    try:
        import ctypes
        from ctypes import wintypes

        class _RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class _CHARRANGE(ctypes.Structure):
            _fields_ = [("cpMin", ctypes.c_long), ("cpMax", ctypes.c_long)]

        class _FORMATRANGE(ctypes.Structure):
            _fields_ = [
                ("hdc", wintypes.HDC),
                ("hdcTarget", wintypes.HDC),
                ("rc", _RECT),
                ("rcPage", _RECT),
                ("chrg", _CHARRANGE),
            ]

        _SendMessageW = ctypes.windll.user32.SendMessageW
        _SendMessageW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            ctypes.c_void_p,
        )
        _SendMessageW.restype = ctypes.c_ssize_t
        _AVAILABLE = True
    except Exception:  # noqa: BLE001 - any setup failure disables formatted print
        _AVAILABLE = False


def format_range_available(hwnd: int) -> bool:
    """Whether this control can print its own rendering.

    ``False`` off Windows, without ctypes, or with no window handle -- and a
    caller that gets ``False`` should print its text version rather than
    printing nothing.
    """
    return bool(_AVAILABLE and hwnd)


def print_rich_document(
    hwnd: int,
    dc: Any,
    *,
    margins_twips: tuple[int, int, int, int],
    draw: bool = True,
) -> list[int]:
    """Lay the document out on *dc* and return each page's starting offset.

    With ``draw=False`` nothing is painted and the return value is just the
    pagination -- which is how a page count is known before the first page is
    printed, and how an accessible preview can say "eleven pages" without
    sending anything to a printer.

    *margins_twips* is ``(left, top, right, bottom)``. Returns ``[0]`` for a
    document that cannot be laid out, so a caller always has at least one page
    and never divides by zero.
    """
    if not format_range_available(hwnd):
        return [0]
    try:
        return _paginate(hwnd, dc, margins_twips, draw)
    except Exception:  # noqa: BLE001 - a printing failure is a message, not a crash
        return [0]


def _paginate(  # pragma: no cover - needs a live HWND and a printer DC
    hwnd: int,
    dc: Any,
    margins: tuple[int, int, int, int],
    draw: bool,
) -> list[int]:
    hdc = int(dc.GetHandle())
    pixels_x = int(dc.GetPPI().width) or 96
    pixels_y = int(dc.GetPPI().height) or 96
    width_px, height_px = (int(value) for value in dc.GetSize())

    def x_twips(pixels: int) -> int:
        return int(pixels * _TWIPS_PER_INCH / pixels_x)

    def y_twips(pixels: int) -> int:
        return int(pixels * _TWIPS_PER_INCH / pixels_y)

    left, top, right, bottom = margins
    page = _RECT(0, 0, x_twips(width_px), y_twips(height_px))
    body = _RECT(left, top, page.right - right, page.bottom - bottom)

    fr = _FORMATRANGE()
    fr.hdc = hdc
    fr.hdcTarget = hdc
    fr.rc = body
    fr.rcPage = page
    fr.chrg.cpMin = 0
    fr.chrg.cpMax = -1  # to the end of the document

    starts: list[int] = [0]
    try:
        while True:
            next_offset = int(
                _SendMessageW(hwnd, _EM_FORMATRANGE, 1 if draw else 0, ctypes.byref(fr))
            )
            # The control answers with the offset it reached. Not advancing
            # means it cannot fit anything more -- a rectangle too small for one
            # line -- and looping on that is an infinite loop on somebody's
            # printer, so it stops.
            if next_offset <= fr.chrg.cpMin or next_offset < 0:
                break
            fr.chrg.cpMin = next_offset
            if fr.chrg.cpMax != -1 and next_offset >= fr.chrg.cpMax:
                break
            starts.append(next_offset)
            if len(starts) > 10_000:
                break  # a runaway backstop; no real document is 10,000 pages
    finally:
        # Free the layout cache the control built. Skipping this leaks for the
        # life of the process, and nothing complains.
        _SendMessageW(hwnd, _EM_FORMATRANGE, 0, None)
    return starts
