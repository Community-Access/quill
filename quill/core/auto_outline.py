"""Accessible AutoOutline (#894): literal-text heading numbering.

Auto-numbers Markdown headings by nesting level -- 1 / 1.1 / 1.1.1
(numeric) or I / A / 1 (legal) -- inserting the number as literal text
into the heading line itself. Literal text (not a rendering overlay)
survives copy/paste and export without any extra machinery: what a
screen reader announces is exactly what's in the file.

Applying the outline is idempotent: an existing AutoOutline number at
the start of a heading is recognized and replaced, never stacked, so
running it again after adding/removing/reordering headings is a clean
refresh, not an accumulation.
"""

from __future__ import annotations

import re
from enum import StrEnum

from quill.core.markdown_sections import parse_heading_blocks

__all__ = ["OutlineStyle", "apply_auto_outline", "remove_outline_numbers", "strip_outline_number"]


class OutlineStyle(StrEnum):
    NUMERIC = "numeric"
    LEGAL = "legal"


_NUMERIC_PREFIX = re.compile(r"^\d+(\.\d+)*\.\s+")
_LEGAL_PREFIX = re.compile(r"^(?:[IVXLCDM]+|[A-Z]|\d+)(?:\.(?:[IVXLCDM]+|[A-Z]|\d+))*\.\s+")


def _to_roman(n: int) -> str:
    values = (
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
        (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    )
    parts = []
    for value, symbol in values:
        count, n = divmod(n, value)
        parts.append(symbol * count)
    return "".join(parts)


def _to_alpha(n: int) -> str:
    letters = []
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        letters.append(chr(ord("A") + remainder))
    return "".join(reversed(letters))


def strip_outline_number(title: str) -> str:
    """Remove a leading AutoOutline number (either style), if present."""
    for pattern in (_NUMERIC_PREFIX, _LEGAL_PREFIX):
        match = pattern.match(title)
        if match:
            return title[match.end() :]
    return title


def _label(counters: list[int], style: OutlineStyle) -> str:
    if style is OutlineStyle.NUMERIC:
        return ".".join(str(c) for c in counters)
    parts = []
    for depth, count in enumerate(counters):
        if depth == 0:
            parts.append(_to_roman(count))
        elif depth == 1:
            parts.append(_to_alpha(count))
        else:
            parts.append(str(count))
    return ".".join(parts)


def apply_auto_outline(text: str, style: OutlineStyle = OutlineStyle.NUMERIC) -> str:
    """Return *text* with every Markdown heading renumbered by nesting level.

    Numbering resets whenever a shallower or equal heading appears (a new
    top-level heading starts a fresh "1", clearing any "1.1", "1.2", ...
    that came before it).
    """
    blocks = parse_heading_blocks(text, "markdown")
    if not blocks:
        return text

    counters: list[int] = []
    edits: list[tuple[int, int, str]] = []
    for block in blocks:
        level = block.level
        if len(counters) < level:
            counters.extend([0] * (level - len(counters)))
        else:
            counters = counters[:level]
        counters[level - 1] += 1
        label = _label(counters, style)
        clean_title = strip_outline_number(block.title)
        attr_suffix = f" {block.attributes}" if block.attributes else ""
        new_line = f"{'#' * level} {label}. {clean_title}{attr_suffix}\n"
        edits.append((block.start, block.end, new_line))

    result = text
    for start, end, new_line in reversed(edits):
        result = result[:start] + new_line + result[end:]
    return result


def remove_outline_numbers(text: str) -> str:
    """Return *text* with any AutoOutline numbers stripped from headings."""
    blocks = parse_heading_blocks(text, "markdown")
    if not blocks:
        return text

    edits: list[tuple[int, int, str]] = []
    for block in blocks:
        clean_title = strip_outline_number(block.title)
        if clean_title == block.title:
            continue
        attr_suffix = f" {block.attributes}" if block.attributes else ""
        new_line = f"{'#' * block.level} {clean_title}{attr_suffix}\n"
        edits.append((block.start, block.end, new_line))

    result = text
    for start, end, new_line in reversed(edits):
        result = result[:start] + new_line + result[end:]
    return result
