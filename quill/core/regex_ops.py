"""Regular-expression count and extract commands (EDS-13).

Count Regex Matches counts matches of a pattern and Extract Regex Matches
extracts all matches into a new buffer. UI-framework agnostic so it can be
unit-tested without ``wx``. Invalid patterns raise :class:`RegexError`.
"""

from __future__ import annotations

import re

from quill.core.error_codes import CodedError

__all__ = ["RegexError", "count_matches", "extract_matches"]


class RegexError(CodedError):
    """Raised when a regular expression cannot be compiled."""

    code = "QUILL-REGEX-INVALID"


def _compile(pattern: str, flags: int) -> re.Pattern[str]:
    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise RegexError(f"Invalid regular expression: {exc}") from exc


def count_matches(text: str, pattern: str, *, flags: int = 0) -> int:
    """Return the number of non-overlapping matches of ``pattern`` in ``text``."""
    return sum(1 for _ in _compile(pattern, flags).finditer(text))


def extract_matches(text: str, pattern: str, *, divider: str = "\n", flags: int = 0) -> str:
    """Return all whole matches of ``pattern`` joined by ``divider``.

    Whole matches (group 0) are extracted even when the pattern contains capture
    groups.
    """
    matches = [match.group(0) for match in _compile(pattern, flags).finditer(text)]
    return divider.join(matches)
