"""How wide a status-bar cell is, and why it is never allowed to get narrower.

A status bar is read two ways and the second one is the one that breaks. A
sighted user glances at the cell they want. A screen-reader user presses JAWS's
Insert+Page Down, which does not read the controls at all -- it reads the
**bottom line of the window off the screen**, out of a model built from what was
drawn there.

That makes the row's geometry part of the interface. A cell whose width follows
its text shoves every cell after it sideways whenever the text changes:
"No selection" becoming "1 words, 8 characters selected" is ninety pixels, and
in QUILL Lite it moved nine of thirteen cells on every selection and every
deselection. Text drawn at one position and then redrawn ninety pixels along
leaves both in that model, so the bar came back as halves and doubles --
"Line 1, colu Line 1, c ... No selectio ... B ody text" -- on a *maximised*
window where every cell fit with room to spare. Nothing was being clipped.

The other failure is the opposite one and was QUILL's: a fixed width per cell.
Nothing moves, and "Line 1, column 1 of 50,000" is ellipsised into a hundred and
forty pixels, so the same screen read returns the half that was drawn.

So a width is a **high-water mark**. It may grow, because the alternative is a
clipped cell and a clipped cell is read clipped; it may not shrink, because the
row has to hold still. Arrowing between line 9 and line 10, typing past a
thousand words, selecting and deselecting -- each settles its cell at its widest
once and never moves the row again.

Pure and wx-free: both editors ask the same question and get the same answer.
"""

from __future__ import annotations

__all__ = ["ratchet_width"]


def ratchet_width(needed: int, held: int, floor: int = 0) -> int:
    """The width a cell should ask for: the widest of what it has ever needed.

    *needed* is what the current text measures, *held* is what the cell is
    already asking for, and *floor* is a configured minimum -- QUILL gives each
    cell one so that a cell reading "UTF-8" is not a button the width of the
    word. A cell with no configured minimum passes zero.
    """
    return max(int(needed), int(held), int(floor))
