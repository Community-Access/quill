"""Time formatting and seek intervals for the Now Playing window."""

from __future__ import annotations

SKIP_MS = 30_000
_NUDGE_MS = 5_000
_PAGE_MS = 30_000


def _ms_text(ms: int) -> str:
    from quill.core.media.timecode import format_timecode

    return format_timecode(max(0, int(ms)))


def _spoken(ms: int) -> str:
    from quill.core.media.timecode import format_spoken

    return format_spoken(max(0, int(ms)))
