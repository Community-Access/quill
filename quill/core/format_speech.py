"""Spoken vocabulary for inline text formatting (rtf.md "a spoken formatting model").

QUILL's native rich surface announces formatting the way it already announces
actions, so a screen-reader user *hears* bold, italic, headings and links instead
of only seeing them. This module is wx-free and takes primitive formatting flags
(not any ``quill.io`` rich type) so ``core`` stays at the bottom of the layer
stack: the UI reads the caret context and passes flags here for a phrase.
"""

from __future__ import annotations

__all__ = ["describe_inline_format", "describe_format_transition"]


_ALIGN_PHRASES = {
    "left": "left aligned",
    "right": "right aligned",
    "center": "centered",
    "justify": "justified",
}

_LINE_SPACING_PHRASES = {
    "1": "single spaced",
    "1.5": "1.5 line spacing",
    "2": "double spaced",
}


def describe_inline_format(
    *,
    bold: bool = False,
    italic: bool = False,
    href: str | None = None,
    heading_level: int = 0,
    bullet: bool = False,
    underline: bool = False,
    strike: bool = False,
    superscript: bool = False,
    subscript: bool = False,
    font_family: str | None = None,
    font_size_pt: int | None = None,
    color: str | None = None,
    highlight: str | None = None,
    align: str | None = None,
    named_style: str | None = None,
    line_spacing: str | None = None,
    space_before: int | None = None,
    space_after: int | None = None,
    indent: int | None = None,
    first_line_indent: int | None = None,
) -> str:
    """Return a spoken description of the formatting in effect, or ``""``.

    Examples: ``"bold"``, ``"bold italic"``, ``"link"``, ``"heading level 2"``,
    ``"bullet, bold"``, ``"Arial, 14 point, bold, centered, red"``. An empty
    string means plain body text with no formatting, which the announcer should
    leave silent. The most defining attributes (paragraph style, typeface, size)
    are spoken first, then weight/decoration, then layout (alignment, spacing,
    indent), then color.
    """
    parts: list[str] = []
    if heading_level:
        parts.append(f"heading level {heading_level}")
    elif bullet:
        parts.append("bullet")
    if named_style:
        parts.append(f"{named_style} style")
    if font_family:
        parts.append(font_family)
    if font_size_pt is not None and font_size_pt > 0:
        parts.append(f"{font_size_pt} point")
    inline: list[str] = []
    if bold:
        inline.append("bold")
    if italic:
        inline.append("italic")
    if underline:
        inline.append("underline")
    if strike:
        inline.append("strikethrough")
    if superscript:
        inline.append("superscript")
    if subscript:
        inline.append("subscript")
    if href:
        inline.append("link")
    if inline:
        parts.append(" ".join(inline))
    if align in _ALIGN_PHRASES:
        parts.append(_ALIGN_PHRASES[align])
    if line_spacing in _LINE_SPACING_PHRASES:
        parts.append(_LINE_SPACING_PHRASES[line_spacing])
    if space_before:
        parts.append("space before")
    if space_after:
        parts.append("space after")
    if indent:
        parts.append("indented")
    if first_line_indent:
        parts.append("first line indent")
    if color:
        parts.append(color)
    if highlight:
        parts.append(f"{highlight} highlight")
    return ", ".join(parts)


def describe_format_transition(previous: str, current: str) -> str:
    """Describe a change in formatting as the caret moves, or ``""``.

    Speaks only the delta so navigation stays terse: entering bold says ``"bold"``,
    leaving it says ``"plain"``. Identical contexts say nothing.
    """
    if previous == current:
        return ""
    if not current:
        return "plain"
    return current
