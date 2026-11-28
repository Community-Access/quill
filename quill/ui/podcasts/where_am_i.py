"""Where am I? -- the one key that says where you are in an episode.

Jeff, 2026-11-27: there was no key that said where he was. Quill Radio has had
Where Am I? on Ctrl+Shift+W since its bounded player; QUILL Cast now answers the
same chord with the same verb (family rule 2), chapter first:

    "Listener mail, 4 minutes 10 into the chapter, 2 minutes 20 left.
     18 minutes 30 of 58 minutes, 39 minutes 30 left."

Pressed twice within half a second, it copies that sentence instead of saying it
again -- the family's double-press window (``hosted_ai_choose_commands``).

Also here: the longer line Say Current Episode (Ctrl+T) speaks, which now
carries the position and the chapter as well as the title.
"""

from __future__ import annotations

import time
from typing import Any

from quill.ui.hosted_ai_choose_commands import DOUBLE_PRESS_WINDOW

__all__ = ["now_playing_sentence", "say_where_am_i", "where_am_i_sentence"]


def _playing(host: Any) -> tuple[Any, int, int] | None:
    controller = getattr(host, "_podcast_controller", None)
    state = getattr(controller, "state", None)
    if controller is None or not getattr(state, "episode_guid", ""):
        return None
    try:
        return controller, int(controller.position_ms()), int(controller.length_ms())
    except Exception:  # noqa: BLE001 - nothing loaded yet
        return None


def _chapters(host: Any) -> list[Any]:
    return list(getattr(host, "_podcast_current_chapters", []) or [])


def where_am_i_sentence(host: Any) -> str:
    """The sentence, or "Nothing is playing."."""
    from quill.core.podcasts.chapter_words import where_am_i

    playing = _playing(host)
    if playing is None:
        return "Nothing is playing."
    _controller, position, length = playing
    return where_am_i(position, length, _chapters(host))


def say_where_am_i(host: Any) -> None:
    """Say where playback is; pressed twice quickly, copy it."""
    now = time.monotonic()
    last = getattr(host, "_cast_where_pressed_at", None)
    host._cast_where_pressed_at = now
    sentence = where_am_i_sentence(host)
    if last is not None and now - last <= DOUBLE_PRESS_WINDOW:
        host._cast_where_pressed_at = None  # a third press speaks again
        from quill.ui.say_commands import set_clipboard_text

        if set_clipboard_text(sentence):
            host._announce("Copied where you are.", force=True)
        else:
            host._announce("Could not copy; the clipboard is in use.", force=True)
        return
    host._announce(sentence, force=True)


def now_playing_sentence(host: Any, status: str) -> str:
    """Say Current Episode's line: the status, then the chapter and the time."""
    from quill.core.podcasts.chapter_words import chapter_index_at, chapter_title
    from quill.core.podcasts.listening_words import clock

    playing = _playing(host)
    if not status or playing is None:
        return status or "Nothing is playing."
    _controller, position, length = playing
    parts = [status.rstrip(".")]
    chapters = _chapters(host)
    index = chapter_index_at(chapters, position)
    if index >= 0:
        parts.append(f"in {chapter_title(chapters[index])}")
    parts.append(f"{clock(position)} of {clock(length)}" if length > 0 else clock(position))
    return ", ".join(parts) + "."
