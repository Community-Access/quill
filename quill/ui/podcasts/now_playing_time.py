"""Time formatting and seek intervals for the Now Playing window."""

from __future__ import annotations

from typing import Any

SKIP_MS = 30_000
_NUDGE_MS = 5_000
_PAGE_MS = 30_000


def _ms_text(ms: int) -> str:
    from quill.core.media.timecode import format_timecode

    return format_timecode(max(0, int(ms)))


def _spoken(ms: int) -> str:
    from quill.core.media.timecode import format_spoken

    return format_spoken(max(0, int(ms)))


def slider_value_words(window: Any) -> str:
    """The Position slider's accessible value: "12 minutes 34 of 58 minutes".

    Read from the slider itself, which is what the reader is on, and the
    episode's length from the controller.
    """
    from quill.core.podcasts.chapter_words import position_value

    controller = getattr(window._host, "_podcast_controller", None)
    try:
        length = int(controller.length_ms()) if controller is not None else 0
    except Exception:  # noqa: BLE001 - nothing loaded
        length = 0
    return position_value(int(window._slider.GetValue()) * 1000, length)
