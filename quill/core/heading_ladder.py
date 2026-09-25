"""The rich-text heading ladder: a point size and bold per level, and its inverse.

Rich-mode headings are presentational. A Windows edit control has no paragraph
styles, so QUILL and QUILL Lite say "this is a Heading 2" by making the paragraph
bold at 16 pt, and read it back by recognising that pair. The ladder is
therefore load-bearing in two directions at once, and both of them cross the
layer boundary:

* the **editor** applies it through the Text Object Model
  (:mod:`quill.ui.richedit_rtf_surface`) and reads it back for the headings
  list, heading navigation and the status bar;
* the **RTF writer** (:mod:`quill.io.rtf`) has to emit the same sizes, because a
  document saved with different ones would come back from disk with every
  heading a different level -- or not a heading at all.

That is why it lives in ``core`` rather than beside the control: ``quill/io`` may
not import ``quill/ui``, and a second copy of the numbers in the writer is a
silent round-trip bug waiting for the first time somebody tunes one of them.
:mod:`quill.ui.richedit_rtf_surface` re-exports these names, so every existing
call site is unchanged.
"""

from __future__ import annotations

__all__ = [
    "BODY_POINT_SIZE",
    "HEADING_POINT_SIZES",
    "HEADING_STYLE_NAMES",
    "heading_level_for_font",
]

#: Rich-mode heading presentation: point size + bold per level, chosen to track
#: Word's Heading 1-6 ladder closely enough that a saved RTF reads as headings
#: in Word while staying legible in the editor. Body text is 11 pt.
#:
#: **Every level has a size of its own.** Levels 5 and 6 were both 11 pt, which
#: is also the body size -- so the ladder could not tell a Heading 5 from an
#: ordinary paragraph, ``heading_level_for_font`` refused to report either, and
#: a document with them had headings that heading *navigation* could not find.
#: A level you can apply and cannot then move to is worse than a level that does
#: not exist, so the two were never offered in a menu. They are now 11.5 and
#: 10.5: half a point either side of body text, far enough apart for the 0.25
#: tolerance below to separate them, and Word's own ladder likewise runs its
#: last heading level below body size.
HEADING_POINT_SIZES: dict[int, float] = {1: 20.0, 2: 16.0, 3: 14.0, 4: 12.0, 5: 11.5, 6: 10.5}
BODY_POINT_SIZE = 11.0

#: The names Word gives its built-in heading styles in an RTF stylesheet. The
#: exact lower-case spelling matters: Word matches a style by this name, and
#: "Heading 1" is a *different*, user-defined style from "heading 1".
HEADING_STYLE_NAMES: dict[int, str] = {level: f"heading {level}" for level in HEADING_POINT_SIZES}


def heading_level_for_font(size: float, bold: bool) -> int | None:
    """The rich-mode heading level a paragraph's font implies, or ``None``.

    A heading is bold and matches one of the six heading point sizes. Body text
    is 11 pt and is not one of them, so bold body text is still body text --
    which is the one case this has to get right, because bolding a word is the
    commonest thing anybody does to a paragraph.
    """
    if not bold:
        return None
    for level, points in HEADING_POINT_SIZES.items():
        if abs(float(size) - points) < 0.25:
            return level
    return None
