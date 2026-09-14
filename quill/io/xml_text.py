"""Make text safe to put in an XML document, because .docx is XML (#1500).

Word files are zipped XML, and XML 1.0 cannot represent most control
characters at all -- not escaped, not encoded, not at any cost. `lxml` enforces
that at the point of assignment, so a single stray NUL or 0x01 anywhere in a
document turned Save into::

    ValueError: All strings must be XML compatible: Unicode or ASCII,
    no NULL bytes or control characters

which reached the user as a crash *while saving*, the one moment an editor must
never fail. They arrive by the routes nobody inspects: a paste out of a terminal
or a PDF, a dictation or AI bridge that returned a framing byte, a file recovered
from a damaged disk.

The rule is Unicode's, not ours: a character that cannot be written is dropped,
because there is no third option -- the alternative to dropping it is not
keeping it, it is failing to save the file. What can be done honestly is to
**say how many went**, which :func:`strip_xml_incompatible` reports so a caller
can tell the user rather than quietly changing their document.

Tab, newline and carriage return are the three control characters XML does
allow, and they are the three that carry meaning in prose, so they stay.
"""

from __future__ import annotations

__all__ = ["count_xml_incompatible", "is_xml_compatible", "strip_xml_incompatible"]


def _allowed(char: str) -> bool:
    """Whether *char* is a character XML 1.0 can represent.

    The production is ``#x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] |
    [#x10000-#x10FFFF]`` -- so: the three useful control characters, then
    everything from space up, minus the surrogate block and the two permanently
    unassigned code points at the end of the BMP.
    """
    point = ord(char)
    if point in (0x09, 0x0A, 0x0D):
        return True
    if point < 0x20:
        return False
    if 0xD800 <= point <= 0xDFFF:  # unpaired surrogate
        return False
    if point in (0xFFFE, 0xFFFF):
        return False
    return point <= 0x10FFFF


def is_xml_compatible(text: str) -> bool:
    """Whether *text* can be written into an XML document unchanged."""
    return all(_allowed(char) for char in text)


def count_xml_incompatible(text: str) -> int:
    """How many characters of *text* XML cannot represent."""
    return sum(1 for char in text if not _allowed(char))


def strip_xml_incompatible(text: str) -> tuple[str, int]:
    """``(text without the characters XML cannot hold, how many were removed)``.

    The count is the point. Dropping a NUL is invisible on the page and in the
    ear -- it has no glyph and the reader says nothing for it -- so a save that
    silently rewrote somebody's document would be indistinguishable from one
    that did not. The caller says the number.
    """
    if is_xml_compatible(text):
        return text, 0
    kept = [char for char in text if _allowed(char)]
    return "".join(kept), len(text) - len(kept)
