"""The face and size the editor draws in -- one rule, both editors.

For an audience that includes low-vision users, "you cannot make the text
bigger" is not a missing preference, it is a product that does not work. QUILL
had no ``SetFont`` on any editor control, no font setting and no zoom command at
all until 2026-09-16 -- every call site in ``quill/ui`` was a dialog heading or a
print DC -- while QUILL Lite had Editor Font, Font for Selection and Notepad's
three text-size keys from its first release (bad.md 4.3, P0.6a).

Two things live here rather than in either shell.

**The range.** Six points to seventy-two, the same in both, so a settings file
carried between them cannot mean two different sizes.

**The rich/plain split** (bad.md 5.5), which is the part that is easy to get
wrong: in a plain, Markdown or HTML document the size *is* the font, and
changing it changes the font. In a **rich** document the run point sizes *are*
the heading ladder, so growing the font would silently re-level every heading in
the document -- a Heading 2 becoming the size of a Heading 1 and the headings
list following it. There the same keys change the **view zoom** instead, which
scales what is drawn and writes nothing.

wx-free, and directly tested.
"""

from __future__ import annotations

from quill.core.heading_ladder import BODY_POINT_SIZE

__all__ = [
    "DEFAULT_FONT_POINTS",
    "MAX_FONT_POINTS",
    "MIN_FONT_POINTS",
    "clamp_font_points",
    "editor_points_for",
    "sets_font",
    "zoom_for",
]

#: Below six points the text is a smudge; above seventy-two one word fills the
#: window. Both editors clamp rather than refuse, because a hand-edited settings
#: file with a size of 400 should give somebody a readable editor rather than an
#: editor that will not start.
MIN_FONT_POINTS = 6
MAX_FONT_POINTS = 72

#: What Reset Text Size goes back to, and what a fresh profile starts at.
DEFAULT_FONT_POINTS = 12


def sets_font(*, rich: bool, empty: bool = False) -> bool:
    """Whether the shell may call ``SetFont`` on this editor at all.

    False in a rich document that **has something in it**, and that half is the
    whole of bad.md R5. ``SetFont`` on wxMSW applies to **the entire control**,
    existing runs included -- so calling it on a populated rich document
    flattens every heading to one size no matter which size is passed, the body
    size included. Heading navigation and the headings list read that ladder, so
    the document also stops being navigable. Both editors had this call; both
    now skip it and change only the zoom, which scales what is drawn and writes
    nothing.

    A rich document's face is its own, carried in its runs. That is the right
    answer as well as the safe one: the face in a `.docx` is part of the
    document, not a reading preference, and overwriting it on every theme
    change would be an edit nobody asked for.

    True for an **empty** rich control, though, and that half is a bug report:
    "if I bold and underline a line it gets announced as heading level 4, and I
    did not use a heading command". A rich heading *is* its point size plus bold
    (:func:`~quill.core.heading_ladder.heading_level_for_font`), and Heading 4 is
    twelve point -- which is also ``DEFAULT_FONT_POINTS``, the size a plain
    document is drawn at. The control is the same control in both modes, so a
    document that had been plain was still carrying ``SetFont(12)`` when it
    became rich, every character typed into it was twelve point, and bolding a
    line made it indistinguishable from a Heading 4. A rich control with nothing
    in it has no runs to flatten, so it can be -- must be -- put back on the
    ladder's body size before anything is typed into it.
    """
    return (not rich) or empty


def clamp_font_points(points: object, fallback: int = DEFAULT_FONT_POINTS) -> int:
    """*points* forced into the readable range. Nonsense gives the default."""
    if isinstance(points, bool) or not isinstance(points, int | float | str):
        return fallback
    try:
        number = int(points)
    except (TypeError, ValueError):
        return fallback
    return max(MIN_FONT_POINTS, min(MAX_FONT_POINTS, number))


def editor_points_for(points: int, *, rich: bool) -> float:
    """The point size to hand ``SetFont``, given the user's chosen size.

    Only meaningful where :func:`sets_font` is true. In a rich document nothing
    should call ``SetFont`` at all, and the ladder's body size is returned only
    so a caller that ignores that rule does the least damage it can.
    """
    return BODY_POINT_SIZE if rich else float(clamp_font_points(points))


def zoom_for(points: int, *, rich: bool) -> tuple[int, int]:
    """``(numerator, denominator)`` for ``EM_SETZOOM``; ``(0, 0)`` means none.

    A zoom of "the size you asked for, over the ladder's body size" makes 22
    point text in a rich document look like 22 point text while every heading
    keeps its proportion. Plain documents get no zoom at all -- there the font
    itself changed, and zooming as well would double the effect.
    """
    if not rich:
        return (0, 0)
    return (clamp_font_points(points), int(BODY_POINT_SIZE))
