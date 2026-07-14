"""Shared Markdown fence detection.

Centralises the CommonMark fence pattern so that any module which needs to
walk Markdown source line-by-line while skipping fenced code blocks
(:mod:`quill.core.markdown_extensions.apply_nl2br`,
:mod:`quill.core.heading_organizer`, the section-move primitives in
:mod:`quill.core.markdown_sections`, and so on) agrees on what counts as
a fence.

The pattern matches an opening or closing fence line:

* up to three leading spaces of indent
* three or more backticks or tildes
* optional info string (language tag, etc.) for opening fences

CommonMark rules followed:

* the closing fence must use the same character as the opening fence
* the closing fence must be at least as long as the opening fence
* the closing fence must not have an info string

Callers that only need a boolean ("is this line a fence?") use
:func:`is_fence_line`.  Callers that need to track open/close state across
lines use :func:`fence_open_char` to read the opening character and compare
it on subsequent fence lines.
"""

from __future__ import annotations

import re

# Matches a fence line: up to 3 spaces of indent, then 3+ backticks or
# tildes, then an optional info string (only meaningful for opening fences).
_FENCE_PATTERN = re.compile(r"^(?P<indent>[ ]{0,3})(?P<fence>`{3,}|~{3,})[ \t]*(?P<info>.*)$")


def is_fence_line(line: str) -> bool:
    """Return True if ``line`` is a Markdown fence opener or closer.

    Strips only the single trailing newline / carriage return that
    ``str.splitlines`` leaves behind; the CommonMark indent rule (up to
    three spaces) is the only indent recognised.
    """
    return _FENCE_PATTERN.match(line.rstrip("\r\n")) is not None


def fence_open_char(line: str) -> str | None:
    """Return the opening fence character (``"```"`` or ``"~"``) if ``line`` is a fence.

    Returns None for non-fence lines.  Use the character to enforce the
    CommonMark rule that a closing fence must use the same character as
    the opener.
    """
    match = _FENCE_PATTERN.match(line.rstrip("\r\n"))
    if match is None:
        return None
    fence = match.group("fence")
    return "`" if fence[0] == "`" else "~"


__all__ = ["_FENCE_PATTERN", "is_fence_line", "fence_open_char"]
