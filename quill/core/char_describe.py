"""Describe the character under the cursor for screen-reader inspection.

The modern descendant of the WordPerfect Editor "Reveal Codes" view, adapted
for a screen-reader editor: instead of a visual hex pane, it produces a spoken
and on-screen description of exactly which character sits at a given offset —
its glyph, Unicode name, code point (hex and decimal), general category, and
plain-language notes for the invisibles that bite writers (no-break space,
zero-width characters, smart quotes, tab, line endings).

Pure logic, no ``wx``; the UI layer renders :class:`CharacterDescription` into
an accessible dialog and a status-line summary.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

# Plain-language names for the Unicode general-category codes we are most likely
# to meet in prose and code. Anything not listed falls back to the raw code.
_CATEGORY_LABELS = {
    "Lu": "Uppercase letter",
    "Ll": "Lowercase letter",
    "Lt": "Titlecase letter",
    "Lm": "Modifier letter",
    "Lo": "Letter",
    "Mn": "Combining mark (non-spacing)",
    "Mc": "Combining mark (spacing)",
    "Me": "Enclosing mark",
    "Nd": "Decimal digit",
    "Nl": "Letter-like number",
    "No": "Other number",
    "Pc": "Connector punctuation",
    "Pd": "Dash punctuation",
    "Ps": "Open punctuation",
    "Pe": "Close punctuation",
    "Pi": "Initial quote",
    "Pf": "Final quote",
    "Po": "Punctuation",
    "Sm": "Math symbol",
    "Sc": "Currency symbol",
    "Sk": "Modifier symbol",
    "So": "Symbol",
    "Zs": "Space separator",
    "Zl": "Line separator",
    "Zp": "Paragraph separator",
    "Cc": "Control character",
    "Cf": "Format character (invisible)",
    "Cs": "Surrogate",
    "Co": "Private-use character",
    "Cn": "Unassigned code point",
}

# Friendly names + notes for characters whose Unicode name is unhelpful, missing
# (control characters), or whose presence is easy to miss while editing. Keyed by
# code point (built via ``chr``) so the invisibles are unambiguous in source and
# can never collapse into one another.
_SPECIAL = {
    chr(cp): value
    for cp, value in {
        0x0A: ("Line feed", "Ends a line (LF, new line)."),
        0x0D: ("Carriage return", "Part of a Windows CR LF line ending."),
        0x09: ("Tab", "A single tab character, not spaces."),
        0x20: ("Space", "An ordinary space."),
        0xA0: (
            "No-break space",
            "Looks like a space but never wraps. Often pasted from the web.",
        ),
        0x202F: ("Narrow no-break space", "A thin space that never wraps."),
        0x200B: ("Zero-width space", "Invisible. Can break searches and word counts."),
        0x200C: ("Zero-width non-joiner", "Invisible joining control."),
        0x200D: (
            "Zero-width joiner",
            "Invisible joining control; used in emoji sequences.",
        ),
        0xFEFF: (
            "Byte-order mark / zero-width no-break space",
            "Invisible; often a stray BOM.",
        ),
        0x2018: (
            "Left single quotation mark",
            "A curly opening quote, not a straight apostrophe.",
        ),
        0x2019: ("Right single quotation mark", "A curly apostrophe, not a straight one."),
        0x201C: ("Left double quotation mark", "A curly opening quote, not a straight quote."),
        0x201D: ("Right double quotation mark", "A curly closing quote, not a straight quote."),
        0x2013: ("En dash", "A short dash, wider than a hyphen."),
        0x2014: ("Em dash", "A long dash."),
        0x00AD: ("Soft hyphen", "Invisible unless the word breaks at the line end."),
    }.items()
}

# Categories whose members should never be printed literally in the UI.
_NON_PRINTING = {"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"}


@dataclass(frozen=True)
class CharacterDescription:
    """A one-line summary plus a multi-line detail block for a character."""

    summary: str
    detail: str


def _display_glyph(char: str) -> str:
    """A speakable stand-in for characters that should not be shown literally."""
    if char in _SPECIAL:
        return _SPECIAL[char][0]
    if unicodedata.category(char) in _NON_PRINTING:
        return f"U+{ord(char):04X}"
    return char


def describe_character(text: str, position: int) -> CharacterDescription:
    """Describe the character at *position* within *text*.

    A position at or past the end of the text reports "end of document" rather
    than raising, so the caller can bind this to a key without guarding bounds.
    """
    if position < 0:
        position = 0
    if not text or position >= len(text):
        return CharacterDescription(
            summary="End of document (no character at the cursor)",
            detail="There is no character at the cursor. The cursor is at the end of the document.",
        )

    char = text[position]
    codepoint = ord(char)
    special_name, special_note = _SPECIAL.get(char, ("", ""))
    unicode_name = unicodedata.name(char, "")
    name = special_name or unicode_name or "Unnamed character"
    category_code = unicodedata.category(char)
    category = _CATEGORY_LABELS.get(category_code, category_code)
    glyph = _display_glyph(char)

    summary = f"{glyph}  U+{codepoint:04X}  {name}"

    detail_lines = [
        f"Character: {glyph}",
        f"Name: {name}",
        f"Code point: U+{codepoint:04X} (decimal {codepoint})",
        f"Category: {category} ({category_code})",
    ]
    if unicode_name and special_name and unicode_name != special_name:
        detail_lines.append(f"Unicode name: {unicode_name}")
    if special_note:
        detail_lines.append("")
        detail_lines.append(f"Note: {special_note}")
    if codepoint > 127:
        detail_lines.append("")
        detail_lines.append("This is a non-ASCII character.")

    return CharacterDescription(summary=summary, detail="\n".join(detail_lines))
