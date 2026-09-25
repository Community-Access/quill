"""What an RTF document declares in its header: fonts, colours and styles.

Split out of :mod:`quill.io.rtf` under GATE-11, and a real seam rather than a
line-count dodge: ``rtf.py`` turns markup into runs and paragraphs, while
everything here is about the tables those runs point *at* -- the font table, the
colour table, and the stylesheet that makes a heading a heading rather than
large bold text. The escaping lives here too, because the table entries need it
before any body text does.
"""

from __future__ import annotations

from quill.core.heading_ladder import (
    BODY_POINT_SIZE,
    HEADING_POINT_SIZES,
    HEADING_STYLE_NAMES,
)

__all__ = [
    "DEFAULT_HALF_POINTS",
    "escape_rtf_text",
    "heading_stylesheet",
    "parse_color",
    "RtfTables",
]


_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
}


def parse_color(value: str) -> tuple[int, int, int] | None:
    text = value.strip()
    if text.startswith("#"):
        digits = text[1:]
        if len(digits) == 3:
            digits = "".join(char * 2 for char in digits)
        if len(digits) == 6:
            try:
                return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))
            except ValueError:
                return None
        return None
    return _NAMED_COLORS.get(text.lower())


def escape_rtf_text(text: str) -> str:
    out: list[str] = []
    for char in text:
        code = ord(char)
        if char in "\\{}":
            out.append("\\" + char)
        elif code < 128:
            out.append(char)
        else:
            out.append(f"\\u{code}?")
    return "".join(out)


class RtfTables:
    """Font and color tables built in a pre-pass and referenced by the writer.

    Index 0 is reserved in both tables (``\\f0`` Calibri default; color index 0 is
    the RTF "auto" slot), so user fonts/colors start at index 1.
    """

    def __init__(self) -> None:
        self.fonts: dict[str, int] = {}
        self.colors: dict[tuple[int, int, int], int] = {}

    def font_index(self, family: str) -> int:
        key = family.strip()
        if not key:
            return 0
        if key not in self.fonts:
            self.fonts[key] = len(self.fonts) + 1
        return self.fonts[key]

    def color_index(self, value: str) -> int:
        rgb = parse_color(value)
        if rgb is None:
            return 0
        if rgb not in self.colors:
            self.colors[rgb] = len(self.colors) + 1
        return self.colors[rgb]

    def font_table(self) -> str:
        entries = ["{\\f0 Calibri;}"]
        for family, index in sorted(self.fonts.items(), key=lambda item: item[1]):
            entries.append(f"{{\\f{index} {escape_rtf_text(family)};}}")
        return "{\\fonttbl" + "".join(entries) + "}"

    def color_table(self) -> str:
        if not self.colors:
            return ""
        # Color indices are assigned in insertion order (1..N); sorting by index
        # restores that order for the table body.
        ordered = sorted(self.colors.items(), key=lambda item: item[1])
        body = "".join(f"\\red{rgb[0]}\\green{rgb[1]}\\blue{rgb[2]};" for rgb, _index in ordered)
        # Leading ';' produces the empty auto entry at index 0.
        return "{\\colortbl;" + body + "}"


#: Body text, in half-points -- :data:`~quill.core.heading_ladder.BODY_POINT_SIZE`
#: and not RTF's own default, which is where this started and what it had to
#: stop being. A heading returns the font to this after its own size, because
#: ``\pard`` resets the paragraph and not the font; the writer also states it
#: once in the preamble, so every paragraph that never says a size is this size
#: rather than whatever the reader's default happens to be.
#:
#: It was 24 -- twelve points -- and that was a reported bug: twelve points is
#: :data:`~quill.core.heading_ladder.HEADING_POINT_SIZES`\ ``[4]``, so body text
#: in every file QUILL wrote was exactly the size of a Heading 4. Bold a line of
#: it and ``heading_level_for_font`` had no way left to tell the two apart, and
#: both editors announced "Heading 4" to somebody who had pressed Ctrl+B.
#: Eleven points is what the ladder has always called body text, and it is also
#: Word's own default body size, so the file opens elsewhere looking right.
DEFAULT_HALF_POINTS = int(round(BODY_POINT_SIZE * 2))


#: The named paragraph styles, as ``token -> (style index, Word's own name,
#: RTF character/paragraph controls)``.
#:
#: The **names matter more than the controls**. Word matches a stylesheet entry
#: to its own built-in style by name, so an entry called ``Quote`` lands in the
#: style box as Quote -- it can be restyled, it appears in the style gallery,
#: and a downstream tool reading structure sees a quotation. Spelled anything
#: else it would be a new user-defined style that merely looks similar, which is
#: the difference between a document Word understands and one it merely renders.
#:
#: Indices start at 10 to leave ``\\s1``-``\\s6`` to the headings; ``\\s0`` is
#: Normal. The controls are a readable approximation of Word's own defaults --
#: Word overrides them with the real style definition on open, and they are what
#: every *other* RTF reader will show.
NAMED_PARAGRAPH_STYLES: dict[str, tuple[int, str, str]] = {
    "quote": (10, "Quote", "\\ql\\li720\\ri720\\i"),
    "title": (11, "Title", "\\ql\\b\\f0\\fs56\\outlinelevel0"),
    "subtitle": (12, "Subtitle", "\\ql\\i\\f0\\fs28"),
    "caption": (13, "Caption", "\\ql\\b\\f0\\fs18"),
}

#: ``style index -> token``, for the reader putting a ``\\sN`` back.
NAMED_STYLE_BY_INDEX: dict[int, str] = {
    index: token for token, (index, _name, _controls) in NAMED_PARAGRAPH_STYLES.items()
}


def heading_stylesheet() -> str:
    """The RTF ``{\\stylesheet}`` group declaring Heading 1-6.

    Without it a heading in a saved file is merely bold text that happens to be
    large: Word shows "Normal" in its style box, its navigation pane lists
    nothing, and every downstream tool that reads structure -- a converter, an
    accessibility checker, another word processor -- sees a paragraph. The
    editor could still find its own headings, because it recognises the
    point-size ladder, which is exactly why this went unnoticed.

    Three things make a style real to Word, and all three matter:

    * ``\\sN`` on the paragraph, pointing at an entry here;
    * the entry's **name**, spelled ``heading 1`` in lower case, which is how
      Word recognises its own built-in style rather than defining a new one;
    * ``\\outlinelevelN``, which is what puts the heading in the navigation
      pane and in a generated table of contents.

    The point sizes come from :mod:`quill.core.heading_ladder`, the same table
    the editor applies through the Text Object Model. They have to: a file
    written with different sizes would reopen with every heading at the wrong
    level, or at no level at all.
    """
    entries = []
    for level, points in sorted(HEADING_POINT_SIZES.items()):
        half_points = int(round(points * 2))
        name = HEADING_STYLE_NAMES[level]
        entries.append(
            "{"
            + f"\\s{level}\\ql\\keepn\\b\\f0\\fs{half_points}"
            + f"\\outlinelevel{level - 1}\\sbasedon0\\snext0 {name};"
            + "}"
        )
    for _token, (index, name, controls) in sorted(NAMED_PARAGRAPH_STYLES.items()):
        entries.append("{" + f"\\s{index}{controls}\\sbasedon0\\snext0 {name};" + "}")
    return "{\\stylesheet{\\s0\\ql Normal;}" + "".join(entries) + "}"
