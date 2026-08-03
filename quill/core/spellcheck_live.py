"""Suppression rules for the live spell-check-as-you-type alert.

Spell-check-as-you-type fires on every completed word, and three regions are
wall-to-wall false positives when read by ear: URLs and email addresses,
Markdown inline code spans, and fenced code blocks. A sighted user filters
these visually without noticing; for a screen-reader user every false alert
costs a spoken interruption, so the checker must filter them instead.

Only the ambient alert consults this module -- the F7 Spelling Review still
covers the whole document. Pure text logic; no wx, strict-typed.
"""

from __future__ import annotations

import re

_URL_OR_EMAIL = re.compile(
    r"(?:https?://|www\.)\S+|[\w.+-]+@[\w-]+\.[\w.-]+",
    re.IGNORECASE,
)
_CODE_SPAN = re.compile(r"`[^`\n]+`")
_FENCE = re.compile(r"^\s*(?:```|~~~)")


def live_alert_suppressed(text: str, start: int, end: int) -> bool:
    """True when a live spelling alert for ``text[start:end]`` should stay silent."""
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end]
    rel_start = start - line_start
    rel_end = end - line_start
    for match in _URL_OR_EMAIL.finditer(line):
        if match.start() < rel_end and rel_start < match.end():
            return True
    for match in _CODE_SPAN.finditer(line):
        if match.start() < rel_end and rel_start < match.end():
            return True
    if _FENCE.match(line):
        return True
    before = text[:line_start]
    if "```" not in before and "~~~" not in before:
        return False
    fences = sum(1 for prior in before.splitlines() if _FENCE.match(prior))
    return fences % 2 == 1
