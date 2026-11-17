"""What finishing an episode writes down, however it was finished.

Three paths finish an episode: the player reaching the end by itself, leaving
it inside its finish window (``PodcastSettings.finished_within_seconds``, see
:mod:`quill.core.podcasts.finish_window`), and Mark as Played and Next. They
share this bookkeeping and differ only in what follows it -- the finish cue and
auto-advance belong to the player reaching the end, never to a listener who
chose to stop.

Mark as Played and Next used to set ``played`` by hand, which skipped the sync
timestamp, the Quill Radio share, the statistics and delete-after-play, and
then let the next episode's start write a position back onto the episode it had
just finished (earshot.md F1).

**Delete-after-play waits for the player to let go.** On the two paths where the
listener is leaving an episode that is still open (a stop or switch inside the
finish window, and Mark as Played and Next), the file is deleted on the next
turn of the event loop, after the engine has closed it: Windows refuses to
delete an open file, and the download would quietly survive.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.podcasts import position_sync, retention


def record_finish(host: Any, show: Any, episode: Any, *, file_still_open: bool = False) -> None:
    """Mark *episode* played and do everything a finish implies."""
    position_sync.mark_played(episode)
    # A finish is sticky across apps (11.11): Radio must not offer to
    # resume an episode Cast has just finished.
    host._podcast_share_place(show, episode, 0, finished=True)
    host._podcast_flush_stats(completed=True)
    settings = host._podcast_library.effective_settings(show)
    if not file_still_open:
        retention.apply_delete_after_play(episode, settings)
        return
    if not (retention.wants_delete_after_play(settings) and episode.downloaded_path):
        return

    def _delete_now_it_is_closed() -> None:
        if retention.apply_delete_after_play(episode, settings):
            host._save_podcast_library()

    wx.CallAfter(_delete_now_it_is_closed)


def on_left_finished(host: Any, show_id: str, episode_guid: str) -> None:
    """Left an episode inside its finish window: it is finished, silently."""
    show = host._podcast_library.find_show(show_id)
    episode = show.find_episode(episode_guid) if show is not None else None
    if episode is None:
        return
    record_finish(host, show, episode, file_still_open=True)
    from quill.ui.podcasts.save_snapshot import save_show

    save_show(host, show_id, episode_guid=episode_guid)
