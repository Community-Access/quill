"""The Now Playing window's "Now playing" field (plan Phase 2, 2026-11-27).

A read-only, multi-line field a listener reaches with Tab and reads with the
arrow keys: the episode, the chapter, the position with its percentage, the
speed and volume, what kind of episode it is, and where its chapters came
from. The lines come from :mod:`quill.core.media.now_playing_lines`, which Quill
Radio's player panel uses too.

It updates on the window's once-a-second tick **only while it does not have
focus**: a value rewritten under the caret is a value the screen reader reads
again from the top, every second. Leaving the field brings it up to date, and
so does Where Am I? for the moment in between.
"""

from __future__ import annotations

from typing import Any

from quill.core.media.now_playing_lines import NowPlayingFacts, now_playing_lines

__all__ = ["bind_info_field", "cast_facts", "cast_now_playing_text", "refresh_info_field"]


def _sleep_words(host: Any) -> str:
    timer = getattr(host, "_sleep_timer_controller", None)
    if timer is None or not getattr(timer, "is_active", False):
        return ""
    if getattr(timer, "is_end_of_episode", False):
        return "sleep at the end of this episode"
    minutes = max(1, round(int(getattr(timer, "remaining_seconds", 0) or 0) / 60))
    return f"sleep in {minutes} minute{'s' if minutes != 1 else ''}"


def cast_facts(host: Any) -> NowPlayingFacts:
    """What Cast knows about the episode playing now."""
    from quill.core.media.progress_words import trusted_length_ms
    from quill.core.podcasts.chapter_words import chapter_index_at, source_phrase
    from quill.ui.podcasts.player_controller import PodcastPlayerState

    controller = getattr(host, "_podcast_controller", None)
    state = getattr(controller, "state", None)
    if controller is None or not getattr(state, "episode_guid", ""):
        return NowPlayingFacts()
    library = getattr(host, "_podcast_library", None)
    show = library.find_show(state.show_id) if library is not None else None
    episode = show.find_episode(state.episode_guid) if show is not None else None
    downloaded = bool(str(getattr(episode, "downloaded_path", "") or ""))
    try:
        position = int(controller.position_ms())
        engine_length = int(controller.length_ms())
    except Exception:  # noqa: BLE001 - mid-load: no numbers yet
        position, engine_length = 0, 0
    feed_ms = int(getattr(episode, "duration_seconds", 0) or 0) * 1000
    facts = NowPlayingFacts(
        title=str(getattr(state, "title", "") or getattr(episode, "title", "")),
        collection=str(getattr(show, "title", "") or ""),
        paused=getattr(state, "state", None) is PodcastPlayerState.PAUSED,
        position_ms=position,
        length_ms=trusted_length_ms(engine_length, feed_ms, buffering=not downloaded),
        speed=float(getattr(controller, "rate", 1.0) or 1.0),
        volume_percent=getattr(controller, "volume_percent", None),
        muted=bool(getattr(controller, "muted", False)),
        sleep=_sleep_words(host),
        published=str(getattr(episode, "published", "") or "")[:10],
        season=int(getattr(episode, "season", 0) or 0),
        episode_number=int(getattr(episode, "episode_number", 0) or 0),
        where="file" if downloaded else "stream",
    )
    chapters = list(getattr(host, "_podcast_current_chapters", []) or [])
    index = chapter_index_at(chapters, position) if chapters else -1
    if index >= 0:
        chapter = chapters[index]
        facts.chapter_title = str(getattr(chapter, "title", "") or "")
        facts.chapter_start_ms = int(getattr(chapter, "start_ms", 0) or 0)
        facts.chapter_index = index
        facts.chapter_count = len(chapters)
        phrase = source_phrase(str(getattr(host, "_podcast_chapters_source", "") or ""))
        facts.chapter_source = f"Chapters {phrase}" if phrase else ""
    if str(getattr(episode, "transcript_url", "") or ""):
        facts.transcript = "transcript published"
    return facts


def cast_now_playing_text(host: Any) -> str:
    try:
        return "\n".join(now_playing_lines(cast_facts(host)))
    except Exception:  # noqa: BLE001 - a readout must never take the window with it
        return "Playing."


def refresh_info_field(window: Any, *, force: bool = False) -> None:
    """Rewrite the field when it has changed and does not have focus."""
    field = getattr(window, "_info", None)
    if field is None or (field.HasFocus() and not force):
        return
    text = cast_now_playing_text(window._host)
    if field.GetValue() != text:
        field.ChangeValue(text)  # ChangeValue: no text event, nothing to echo


def bind_info_field(window: Any) -> None:
    """Bring the field up to date as focus leaves it."""
    import wx

    def _on_blur(event: Any) -> None:
        refresh_info_field(window, force=True)
        event.Skip()

    window._info.Bind(wx.EVT_KILL_FOCUS, _on_blur)
