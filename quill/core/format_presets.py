"""The fixed choices the Format menu offers: fonts, sizes, colours, spacing.

Extracted from ``quill/ui/main_frame_format_codes.py`` on 2026-09-10, when that
module crossed its size cap and the honest split turned out to be the obvious
one: these are **data**, not menu code. They describe what a person may pick,
which is a product decision; the wx that turns each row into a menu item is a
rendering detail that happens to live next to it.

Two things follow from the move, and both were reasons to make it rather than to
raise a budget:

* **They are testable without a display.** "No two colours share a name", "every
  point size is a size" and "the spacing presets come in before/after pairs" are
  all assertions about a tuple, and none of them needed a menu bar.
* **QuillLite can have the same ladder.** The two products already share the
  heading ladder and the metrics; a font list that differs between them would be
  a difference with no reason behind it, and CLAUDE.md's rule is that a shared
  capability lives in the shared package.

wx-free and dependency-free. The labels are deliberately **not** translated here:
a font family is a proper noun, a point size is a number, and a colour name is
looked up by the same string the renderer writes -- translating any of the three
would break the thing it names.
"""

from __future__ import annotations

__all__ = [
    "COLOR_PRESETS",
    "FONT_PRESETS",
    "HIGHLIGHT_PRESETS",
    "INDENT_PRESETS",
    "NAMED_STYLE_PRESETS",
    "SIZE_PRESETS",
    "SPACING_PRESETS",
]

#: Font families offered directly in the menu. Six, not sixty: the full list is
#: one More Font Options... away, and a submenu nobody can arrow to the end of is
#: a submenu that costs more than it saves.
FONT_PRESETS: tuple[str, ...] = (
    "Arial",
    "Calibri",
    "Times New Roman",
    "Courier New",
    "Verdana",
    "Georgia",
)

#: Point sizes, in the order a size list is conventionally shown.
SIZE_PRESETS: tuple[int, ...] = (8, 9, 10, 11, 12, 14, 16, 18, 24, 36, 48, 72)

#: ``(name, hex)``. The name is what is announced and what a person recognises;
#: the hex is what the renderer writes.
COLOR_PRESETS: tuple[tuple[str, str], ...] = (
    ("Black", "#000000"),
    ("Red", "#C00000"),
    ("Green", "#008000"),
    ("Blue", "#0000FF"),
    ("Orange", "#FF8C00"),
    ("Purple", "#800080"),
)

#: ``(name, value)``. Highlight values are named colours rather than hex,
#: because that is what the Word and RTF highlight attributes take.
HIGHLIGHT_PRESETS: tuple[tuple[str, str], ...] = (
    ("Yellow", "yellow"),
    ("Green", "green"),
    ("Turquoise", "turquoise"),
    ("Pink", "pink"),
    ("Gray", "gray"),
)

#: ``(label, value)`` for the named paragraph styles.
NAMED_STYLE_PRESETS: tuple[tuple[str, str], ...] = (
    ("Quote", "quote"),
    ("Title", "title"),
    ("Subtitle", "subtitle"),
    ("Caption", "caption"),
)

#: ``(label, kind, points)`` for the flattened Paragraph Spacing submenu. Flat
#: rather than a "space before" submenu and a "space after" submenu: eight rows
#: read faster than two menus of four.
SPACING_PRESETS: tuple[tuple[str, str, int], ...] = (
    ("Space before: 6 points", "before", 6),
    ("Space before: 12 points", "before", 12),
    ("Space after: 6 points", "after", 6),
    ("Space after: 12 points", "after", 12),
)

#: ``(label, kind, points)`` for the flattened Paragraph Indent submenu.
INDENT_PRESETS: tuple[tuple[str, str, int], ...] = (
    ("Left indent: 18 points", "indent", 18),
    ("Left indent: 36 points", "indent", 36),
    ("Left indent: 54 points", "indent", 54),
    ("First-line indent: 18 points", "first", 18),
    ("First-line indent: 36 points", "first", 36),
)
