"""Heading-derived manuscript structure (wx-free).

A manuscript file uses ordinary Markdown ATX headings (``#`` .. ``######``) for
its parts, chapters, and scenes. The binder reflects that structure rather than
storing a parallel copy, so the two never drift: edit a heading and the binder
follows. ``iter_headings`` returns each heading's level, title, and character
offset (so a UI can open the file at that point).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["Heading", "iter_headings"]

# ATX heading: up to three leading spaces, 1-6 hashes, at least one space, then
# a non-space. Mirrors quill.core.navigation._heading_starts so manuscript
# structure matches the editor's heading navigation.
_HEADING_RE = re.compile(r"^[ \t]{0,3}(#{1,6})[ \t]+(\S.*?)[ \t]*#*[ \t]*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class Heading:
    """One manuscript heading: its depth, text, and character offset."""

    level: int
    title: str
    offset: int


def iter_headings(text: str) -> list[Heading]:
    """Return every Markdown ATX heading in ``text``, in document order."""
    headings: list[Heading] = []
    for match in _HEADING_RE.finditer(text):
        headings.append(
            Heading(level=len(match.group(1)), title=match.group(2).strip(), offset=match.start())
        )
    return headings
