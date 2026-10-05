"""Play Now and Add to Queue on a new-episode notice, on keys (ear.md R9).

A desktop toast is not reliably reachable with a screen reader, so the two
things a new-episode notice is for live on the notice itself, wherever it is
listed -- the Notifications place in the main window and the Notifications
window -- and on keys as well as in the row's menu:

* **Ctrl+Enter** plays the episode now;
* **Space** adds it to the Play Queue, as Space does on any episode row.

Shared by both lists so the two cannot drift.
"""

from __future__ import annotations

from typing import Any

__all__ = ["add_to_queue", "episode_for", "play_now"]


def episode_for(notice: Any) -> tuple[Any, Any] | None:
    """(show, newest unheard episode) for a new-episode notice, or None."""
    from quill.core.podcasts import notices as cast_notices
    from quill.ui.notification_open import resolve_show

    if notice is None or cast_notices.kind_of(notice) != cast_notices.NEW_EPISODE:
        return None
    show, _refusal = resolve_show(str(getattr(notice, "target", "") or ""))
    if show is None:
        return None
    from quill.core.podcasts.sorting import sort_episodes

    for episode in sort_episodes(list(show.episodes), "newest_first"):
        if not episode.played:
            return show, episode
    return None


def _live_pair(host: Any, pair: tuple[Any, Any]) -> tuple[Any, Any] | None:
    """The same show and episode from the host's own library (resolve_show
    reads the file fresh, and playing must use the objects Cast holds)."""
    library = host._podcast_library
    show = library.find_show(pair[0].id)
    episode = show.find_episode(pair[1].guid) if show is not None else None
    return (show, episode) if show is not None and episode is not None else None


def _mark_read(notice: Any) -> None:
    if not getattr(notice, "read", True):
        from quill.core.notifications import mark_read

        mark_read(notice.id)


def play_now(host: Any, notice: Any) -> bool:
    """Ctrl+Enter on a new-episode notice. True when something started."""
    pair = episode_for(notice)
    live = _live_pair(host, pair) if pair is not None else None
    if live is None:
        host._announce("Nothing to play for this one.")
        return False
    _mark_read(notice)
    host._play_episode_object(*live)
    return True


def add_to_queue(host: Any, notice: Any) -> bool:
    """Space on a new-episode notice. True when it was added."""
    from quill.core.podcasts import queue as queue_ops
    from quill.core.sound_events import SoundEvent
    from quill.ui.podcasts.outcome_feedback import say_outcome

    pair = episode_for(notice)
    live = _live_pair(host, pair) if pair is not None else None
    if live is None:
        host._announce("Nothing to queue for this one.")
        return False
    show, episode = live
    _mark_read(notice)
    if not queue_ops.add_to_queue(host._podcast_library, show.id, episode.guid):
        host._announce(f"{episode.title} is already in the Play Queue.")
        return False
    host._save_podcast_library()
    say_outcome(
        host, f"Added {episode.title} to the Play Queue.", sound=SoundEvent.CAST_QUEUE_ADDED
    )
    return True
