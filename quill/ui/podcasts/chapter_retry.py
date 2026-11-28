"""Look for a streamed episode's file chapters again once its first bytes arrive.

Cast works out an episode's chapters once, when it starts. For a streamed
episode that is before the playback cache holds a single byte, so chapters
written inside the file (ID3 CHAP frames, which sit at the very start of an
MP3) were never read, and the cascade fell through to the show notes or to
nothing. One of the candidates for Jeff's "Chapter 1, Chapter 2" (2026-11-27).

So when the answer did not come from the publisher or the file and the episode
is not downloaded, this asks once more, a little later, when the cache has the
head of the file. Once per episode: a second miss is the real answer.
"""

from __future__ import annotations

from typing import Any

__all__ = ["RETRY_AFTER_MS", "retry_when_cached", "should_retry"]

#: Long enough for the head of the file (where ID3 tags live) to be cached.
RETRY_AFTER_MS = 20_000

_STRONG_SOURCES = frozenset({"published", "file"})


def should_retry(host: Any, key: object, episode: Any, result: Any) -> bool:
    """Whether a second look could find chapters the first one could not."""
    if str(getattr(result, "source", "")) in _STRONG_SOURCES:
        return False
    if str(getattr(episode, "downloaded_path", "") or ""):
        return False  # the file was there the first time
    return getattr(host, "_podcast_chapters_retried", None) != key


def retry_when_cached(host: Any, key: object, state: Any, episode: Any, result: Any) -> None:
    """Schedule the one second look, if it is worth one."""
    if not should_retry(host, key, episode, result):
        return
    host._podcast_chapters_retried = key

    def _again() -> None:
        if getattr(host, "_podcast_chapters_key", None) != key:
            return  # another episode is playing now
        host._podcast_chapters_key = None  # let the reload run for the same episode
        host._maybe_reload_podcast_chapters(state)

    try:
        import wx

        wx.CallLater(RETRY_AFTER_MS, _again)
    except Exception:  # noqa: BLE001 - no event loop (tests, shutdown): no second look
        return
