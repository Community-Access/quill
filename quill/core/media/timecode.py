"""Timecode parsing and formatting for the "Go to Position" command (Section 9.8).

Pure, dependency-free, unit-tested helpers converting between a position in
milliseconds and the human forms the player accepts and speaks:

* ``parse_timecode`` accepts ``"1:23:45"`` (h:mm:ss), ``"83:45"`` (mm:ss),
  ``"5025"`` (whole seconds), and ``"1h23m45s"`` (unit form), returning integer
  milliseconds -- raising :class:`InvalidTimecodeError` on anything else.
* ``format_timecode`` renders ``H:MM:SS`` (or ``M:SS`` under an hour).
* ``format_spoken`` renders "1 hour 23 minutes 45 seconds" for announcements.
"""

from __future__ import annotations

import re

from quill.core.media.errors import InvalidTimecodeError

_UNIT_RE = re.compile(r"^\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*s)?\s*$", re.IGNORECASE)


def parse_timecode(text: str) -> int:
    """Parse a timecode string into absolute milliseconds (non-negative)."""
    if not isinstance(text, str):
        raise InvalidTimecodeError("timecode must be a string")
    raw = text.strip()
    if not raw:
        raise InvalidTimecodeError("timecode is empty")

    if ":" in raw:
        return _parse_colon_form(raw)
    if raw.isdigit():
        return int(raw) * 1000
    return _parse_unit_form(raw)


def _parse_colon_form(raw: str) -> int:
    parts = raw.split(":")
    if len(parts) > 3:
        raise InvalidTimecodeError(f"too many ':' segments in {raw!r}")
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        raise InvalidTimecodeError(f"non-numeric segment in {raw!r}") from None
    if any(n < 0 for n in numbers):
        raise InvalidTimecodeError(f"negative segment in {raw!r}")
    # The minutes/seconds segments (everything after the first) must be 0-59.
    if any(n >= 60 for n in numbers[1:]):
        raise InvalidTimecodeError(f"minutes/seconds must be 0-59 in {raw!r}")
    hours, minutes, seconds = ([0] * (3 - len(numbers))) + numbers
    return ((hours * 3600) + (minutes * 60) + seconds) * 1000


def _parse_unit_form(raw: str) -> int:
    match = _UNIT_RE.match(raw)
    if not match or not any(match.groups()):
        raise InvalidTimecodeError(f"could not parse timecode {raw!r}")
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return ((hours * 3600) + (minutes * 60) + seconds) * 1000


def format_timecode(ms: int, *, always_hours: bool = False) -> str:
    """Render ``ms`` as ``H:MM:SS`` (or ``M:SS`` when under an hour)."""
    total_seconds = max(0, int(ms)) // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours or always_hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_spoken(ms: int) -> str:
    """Render ``ms`` as a spoken phrase, e.g. "1 hour 23 minutes 45 seconds"."""
    total_seconds = max(0, int(ms)) // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return " ".join(parts)


__all__ = ["format_spoken", "format_timecode", "parse_timecode"]
