"""What happens to a brand-new episode (QUILL Cast 1.1.0).

A feed refresh used to end at "N new episodes for X". This mixin owns
everything that now happens next -- the acquisition layer QUILL Cast did not
have:

- **Auto-Queue**: a show marked for it sends its new episodes straight into
  the Play Queue, skipping the Inbox.
- **Per-show announcement**: a show marked for it has its new episodes named
  out loud, in braille, and in a tray balloon.
- **Auto-download**: the newest N episodes (plus anything queued or in the
  Inbox, per the toggles) are fetched without being asked.

Split out of ``main_frame_podcasts.py`` rather than appended to it: that
module owns the player, the download queue, and the refresh call itself, and
this is a distinct decision -- *what should exist on disk and in the queue* --
that is worth reading on its own.

Every path here is gated: Safe Mode fetches nothing, a paused show is left
alone, and everything it does is announced (A-4).
"""

from __future__ import annotations

from quill.core.podcasts.models import PodcastEpisode, PodcastShow


class PodcastAcquisitionMixin:
    """Auto-Queue, per-show notification, and auto-download on refresh."""

    def _podcast_route_new_episodes(self, show: PodcastShow, fresh: list[PodcastEpisode]) -> int:
        """Auto-Queue: a show marked auto_queue sends its new episodes
        straight to the Play Queue, skipping the Inbox. Returns how many."""
        from quill.core.podcasts.acquisition import route_new_episodes

        return route_new_episodes(self._podcast_library, show, fresh)

    def _podcast_new_episode_message(self, show: PodcastShow, new_count: int, queued: int) -> str:
        """One sentence covering what arrived and where it went, rather than
        a count now and a separate "and they were queued" later."""
        message = f"{new_count} new episode(s) for {show.title}"
        if queued:
            message += f"; {queued} added to the Play Queue"
        return message

    def _podcast_notify_new_episodes(self, show: PodcastShow, fresh: list[PodcastEpisode]) -> None:
        """Per-show notification: name the episodes for a show that asked.

        The desktop answer to a push notification is a spoken/braille
        announcement plus a tray balloon -- and it is per show on purpose.
        Being told about every feed is being told about nothing, so this is
        off until a show is marked Announce New Episodes.
        """
        if not show.notify_new_episodes or not fresh:
            return
        titles = ", ".join(episode.title for episode in fresh[:3])
        if len(fresh) > 3:
            titles += f", and {len(fresh) - 3} more"
        message = f"{show.title}: {titles}"
        self._announce(message, force=True)
        tray_icon = getattr(self, "_tray_icon", None)
        if tray_icon is None:
            return
        try:
            tray_icon.ShowBalloon("New episode", message, 8000, self._wx.ICON_INFORMATION)
        except Exception:  # noqa: BLE001 - a balloon must never break a refresh
            pass

    def _podcast_apply_auto_download(self, show: PodcastShow) -> None:
        """Fetch what the acquisition policy says should be on disk.

        Gated with the rest of the network paths: Safe Mode downloads
        nothing, and neither does a paused show.
        """
        if self._safe_mode or show.paused:
            return
        from quill.core.podcasts.acquisition import episodes_to_auto_download
        from quill.core.podcasts.inbox import inbox_pairs
        from quill.ui.podcasts.show_actions import enqueue_episode_download

        queued_guids = frozenset(
            item.episode_guid for item in self._podcast_library.queue if item.show_id == show.id
        )
        inbox_guids = frozenset(
            episode.guid
            for inbox_show, episode in inbox_pairs(self._podcast_library)
            if inbox_show.id == show.id
        )
        wanted = episodes_to_auto_download(
            self._podcast_library, show, queued_guids=queued_guids, inbox_guids=inbox_guids
        )
        started = 0
        for episode in wanted:
            item_id = f"{show.id}:{episode.guid}"
            if self._podcast_download_queue.get(item_id) is not None:
                continue
            enqueue_episode_download(
                self._podcast_download_queue,
                self._podcast_download_root(),
                show,
                episode,
                item_id=item_id,
            )
            started += 1
        if started:
            self._announce(f"Downloading {started} episode(s) of {show.title} automatically")
