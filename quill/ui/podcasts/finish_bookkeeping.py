"""What finishing an episode writes down, however it was finished.

Two paths finish an episode: the player reaching the end by itself, and
leaving it inside its finish window (``PodcastSettings.finished_within_seconds``,
see :mod:`quill.core.podcasts.finish_window`). They share this bookkeeping and
differ only in what follows it -- the finish cue and auto-advance belong to the
player reaching the end, never to a listener who chose to stop.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import position_sync, retention


def record_finish(host: Any, show: Any, episode: Any) -> None:
    """Mark *episode* played and do everything a finish implies."""
    position_sync.mark_played(episode)
    # A finish is sticky across apps (11.11): Radio must not offer to
    # resume an episode Cast has just finished.
    host._podcast_share_place(show, episode, 0, finished=True)
    host._podcast_flush_stats(completed=True)
    retention.apply_delete_after_play(episode, host._podcast_library.effective_settings(show))


def on_left_finished(host: Any, show_id: str, episode_guid: str) -> None:
    """Left an episode inside its finish window: it is finished, silently."""
    show = host._podcast_library.find_show(show_id)
    episode = show.find_episode(episode_guid) if show is not None else None
    if episode is None:
        return
    record_finish(host, show, episode)
    from quill.ui.podcasts.save_snapshot import save_show

    save_show(host, show_id, episode_guid=episode_guid)
