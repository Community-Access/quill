"""Bytes arriving from the network for podcasts: downloads, and the playback cache.

Two transfers, one concern. A **download** is content -- the listener asked for
the file and it stays until a retention rule or the listener removes it. A
**playback cache** fill is not: it happens because a streamed episode started
playing, it is bounded and evicted, and losing all of it costs nothing but
bandwidth. They share this mixin because they share everything else -- the same
resumable fetch, the same auth header, the same "fires on a worker thread, so
marshal to wx" contract -- and keeping them apart in two places is how the two
drift into disagreeing about where an episode's bytes are.

The playback cache exists to remove a two-tier system: through 1.1.0, chapters,
exact bookmarks, dependable resume and audio analysis were all downloaded-only,
so a streamed episode was quietly a second-class one. See
``quill/core/podcasts/playback_cache.py`` for the policy; this module is the
host wiring:

* fill the cache for whatever is playing, on a queue of its own so a large
  download batch can never leave the episode you are listening to waiting;
* stop filling for an episode you have moved on from;
* keep the cache under its cap without ever evicting what is playing;
* turn a cached episode into a kept download by moving it (**Keep This
  Episode**), rather than downloading the same bytes a second time.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.podcasts import playback_cache, retention
from quill.core.podcasts.download_queue import DownloadItem, PodcastDownloadQueue
from quill.core.sound_events import SoundEvent
from quill.ui.companion_cues import post_cue


class PodcastTransfersMixin:
    """Download-queue callbacks plus the playback cache, for ``PodcastsMixin``."""

    # -- where downloads land ---------------------------------------------

    def _podcast_download_root(self) -> Path:
        override = self._podcast_library.settings.download_root
        return Path(override) if override else app_data_dir() / "podcasts"

    # -- download queue callbacks (fire on the download worker thread --
    # everything here must be wx.CallAfter-safe) ---------------------------

    def _on_podcast_download_status_changed(self, item: DownloadItem) -> None:
        self._wx.CallAfter(self._apply_podcast_download_status, item)

    def _on_podcast_download_completed(self, item: DownloadItem) -> None:
        self._wx.CallAfter(self._apply_podcast_download_completed, item)

    def _on_podcast_download_reconnect(
        self, item: DownloadItem, attempt: int, max_attempts: int
    ) -> None:
        self._wx.CallAfter(
            self._announce,
            f"Download connection dropped; reconnecting (attempt {attempt} of {max_attempts})...",
        )

    def _apply_podcast_download_status(self, item: DownloadItem) -> None:
        self._refresh_statusbar()
        self._podcast_cue_download_started(item)
        if item.status == "failed":
            self._record_podcast_download_problem(item)
        if self._podcast_manager_dialog is not None:
            self._podcast_manager_dialog.on_download_status_changed(item)

    def _record_podcast_download_problem(self, item: DownloadItem) -> None:
        """Write a failed download down (11.5), so an overnight batch that
        lost three episodes can still say which three, and why."""
        from quill.core import problem_log
        from quill.core.paths import app_data_dir

        subject = item.episode_guid
        show = self._podcast_library.find_show(item.show_id)
        if show is not None:
            episode = show.find_episode(item.episode_guid)
            title = getattr(episode, "title", "") if episode is not None else ""
            named = title or "an episode"
            subject = f"{named} -- {show.title}" if show.title else named
        problem_log.record_problem(
            app_data_dir(),
            problem_log.KIND_DOWNLOAD,
            subject,
            item.error_message or "the download failed",
            target=item.show_id + problem_log.TARGET_SEP + item.episode_guid,
        )

    def _podcast_cue_download_started(self, item: DownloadItem) -> None:
        """Earcon the moment downloading actually begins (#1302).

        This callback also carries every progress chunk of every item, so it
        must never cue per call. The queue going from idle to busy is the state
        worth hearing: a forty-episode batch says "downloading" once, and the
        cue is armed again only after the queue has drained.
        """
        queue = getattr(self, "_podcast_download_queue", None)
        active = int(queue.active_count()) if queue is not None else 0
        if active < 1:
            self._podcast_download_cued = False
            return
        if str(getattr(item, "status", "")) != "downloading":
            return
        if getattr(self, "_podcast_download_cued", False):
            return
        self._podcast_download_cued = True
        post_cue(SoundEvent.CAST_DOWNLOAD_STARTED)

    def _apply_podcast_download_completed(self, item: DownloadItem) -> None:
        # The queue calls this exactly once per finished download, so one
        # episode landing on disk makes exactly one sound (#1302).
        post_cue(SoundEvent.CAST_DOWNLOAD_COMPLETE)
        show = self._podcast_library.find_show(item.show_id)
        if show is not None:
            episode = show.find_episode(item.episode_guid)
            if episode is not None:
                episode.downloaded_path = str(item.destination)
                self._maybe_process_downloaded_audio(show, item)
                # The bytes are content now; a cache copy of the same episode
                # would just be a duplicate waiting to be evicted.
                playback_cache.forget(show.id, episode.guid, episode.audio_url)
            settings = self._podcast_library.effective_settings(show)
            retention.apply_keep_last_n(show, settings)
        self._save_podcast_library()
        self._refresh_statusbar()
        if self._podcast_manager_dialog is not None:
            self._podcast_manager_dialog.on_download_completed(item)
        self._maybe_notify_downloads_finished(item)

    def _maybe_notify_downloads_finished(self, item: DownloadItem) -> None:
        """One desktop notification when the queue goes quiet (list.md 2.5).

        Counted here rather than in the notice, because the tally is a fact
        about this run: a forty-episode batch is one event to a listener,
        however many rows it had, and forty toasts would be a fault with a
        friendly icon. The count resets as the queue drains, so the next batch
        starts from nothing.
        """
        from quill.core.podcasts import download_notice

        finished = int(getattr(self, "_podcast_downloads_finished", 0)) + 1
        self._podcast_downloads_finished = finished
        queue = getattr(self, "_podcast_download_queue", None)
        still = int(queue.active_count()) if queue is not None else 0
        # getattr, because a host can reach here with a library that has no
        # settings record yet -- and "no settings" must read as "not asked
        # for", which is what wants_notice answers for anything it does not
        # recognise.
        settings = getattr(self._podcast_library, "settings", None)
        if not download_notice.should_notify(settings, still_downloading=still, finished=finished):
            return
        self._podcast_downloads_finished = 0
        # Quiet hours, as the ``download`` kind. The download itself already
        # happened; what is held back is the interruption about it.
        from quill.core.quiet_hours import Kind
        from quill.ui.quiet_hours_ui import held_back

        if held_back(Kind.DOWNLOAD):
            return
        show = self._podcast_library.find_show(item.show_id)
        episode = show.find_episode(item.episode_guid) if show is not None else None
        from quill.ui.toast import show_toast

        show_toast(
            download_notice.TITLE,
            download_notice.notice(
                finished,
                str(getattr(episode, "title", "") or ""),
                str(getattr(show, "title", "") or ""),
            ),
            parent=self.frame,
        )

    # -- the playback cache -------------------------------------------------

    def _init_podcast_transfers(self) -> None:
        """Build both transfer queues. Called once, from ``_init_podcasts``."""
        settings = self._podcast_library.settings
        self._podcast_download_queue = PodcastDownloadQueue(
            on_status_changed=self._on_podcast_download_status_changed,
            on_completed=self._on_podcast_download_completed,
            on_reconnect=self._on_podcast_download_reconnect,
            reconnect_enabled=settings.reconnect_enabled,
            reconnect_max_attempts=settings.reconnect_max_attempts,
            reconnect_wait_seconds=settings.reconnect_wait_seconds,
        )
        # One at a time, and separate from the download queue on purpose: the
        # episode being listened to must never queue behind a forty-episode
        # download batch for the bytes that make it drop-proof. Silent by
        # construction -- no status callback, so a cache fill never earcons,
        # never touches the status bar, and never appears in Downloads.
        self._podcast_cache_queue = PodcastDownloadQueue(
            max_concurrent=1,
            on_completed=self._on_podcast_cache_completed,
            reconnect_enabled=settings.reconnect_enabled,
            reconnect_max_attempts=settings.reconnect_max_attempts,
            reconnect_wait_seconds=settings.reconnect_wait_seconds,
        )
        #: The cache item currently being filled, so starting a different
        #: episode can stop it.
        self._podcast_cache_item_id = ""
        self._podcast_cache_key: tuple[str, str] = ("", "")

    def _podcast_manage_playback_cache(self, state: object) -> None:
        """Keep the cache pointed at whatever is playing now.

        Rides the player's state-changed callback, which is the only event that
        knows an episode switched -- and it fires for every route into
        playback (Play, the Play Queue, auto-advance, resume on launch), so no
        call site can forget to do this.
        """
        show_id = str(getattr(state, "show_id", "") or "")
        episode_guid = str(getattr(state, "episode_guid", "") or "")
        key = (show_id, episode_guid)
        if key == self._podcast_cache_key:
            return
        self._podcast_cache_key = key
        self._stop_podcast_cache_fill()
        if not show_id or not episode_guid:
            return
        show = self._podcast_library.find_show(show_id)
        if show is None:
            return
        episode = show.find_episode(episode_guid)
        if episode is None:
            return
        if not self._podcast_library.effective_settings(show).playback_cache:
            return
        from quill.ui.podcasts.show_actions import start_playback_cache

        self._podcast_cache_item_id = start_playback_cache(self._podcast_cache_queue, show, episode)
        self._evict_podcast_cache()

    def _stop_podcast_cache_fill(self) -> None:
        """Stop filling the cache for the episode that is no longer playing.

        A partial ``.part`` file is left where it is: it costs one eviction
        candidate and, if the same episode is played again, the fetch resumes
        from it by Range rather than starting over.
        """
        item_id = getattr(self, "_podcast_cache_item_id", "")
        if not item_id:
            return
        self._podcast_cache_item_id = ""
        queue = getattr(self, "_podcast_cache_queue", None)
        if queue is not None:
            queue.cancel_item(item_id)

    def _podcast_local_fallback(self, position_ms: int) -> str:
        """A local file that already covers *position_ms*, or "".

        Asked by the player when a stream errors out. A complete cache entry is
        always good. A partial one is good only if the bytes on disk reach past
        where the listener is -- and that is answered from the fetch's own
        reported progress against the episode's duration, never guessed: a
        recovery that lands short would replace a dropped stream with an
        episode that ends early, which is worse than saying nothing.
        """
        show_id, episode_guid = getattr(self, "_podcast_cache_key", ("", ""))
        if not show_id or not episode_guid:
            return ""
        show = self._podcast_library.find_show(show_id)
        episode = show.find_episode(episode_guid) if show is not None else None
        if episode is None:
            return ""
        path, size, complete = playback_cache.cached_bytes(show_id, episode_guid, episode.audio_url)
        if path is None or size <= 0:
            return ""
        if complete:
            return str(path)
        item = self._podcast_cache_queue.get(f"cache:{show_id}:{episode_guid}")
        total = int(getattr(item, "total_bytes", 0) or 0)
        duration_ms = int(episode.duration_seconds or 0) * 1000
        if total <= 0 or duration_ms <= 0:
            return ""
        covered_ms = int(duration_ms * (size / total))
        # Five seconds of headroom: the bytes have to be genuinely ahead of the
        # listener, not level with them.
        return str(path) if covered_ms > position_ms + 5000 else ""

    def _shutdown_podcast_transfers(self) -> None:
        """Stop both transfer queues. The frame's close path calls this once."""
        for queue in (
            getattr(self, "_podcast_download_queue", None),
            getattr(self, "_podcast_cache_queue", None),
        ):
            if queue is None:
                continue
            try:
                queue.shutdown()
            except Exception:  # noqa: BLE001 - shutdown must never block exit
                continue

    def _podcast_cache_in_use(self) -> frozenset[Path]:
        """Cache files nothing may evict: what is playing, and what is filling."""
        show_id, episode_guid = self._podcast_cache_key
        if not show_id or not episode_guid:
            return frozenset()
        show = self._podcast_library.find_show(show_id)
        episode = show.find_episode(episode_guid) if show is not None else None
        url = str(getattr(episode, "audio_url", "") or "")
        return frozenset({
            playback_cache.playback_path(show_id, episode_guid, url),
            playback_cache.partial_path(show_id, episode_guid, url),
        })

    def _evict_podcast_cache(self) -> None:
        cap_mb = max(0, int(self._podcast_library.settings.playback_cache_cap_mb))
        if cap_mb <= 0:
            return
        playback_cache.evict_to_cap(cap_mb * 1024 * 1024, keep=self._podcast_cache_in_use())

    def _on_podcast_cache_completed(self, item: DownloadItem) -> None:
        self._wx.CallAfter(self._apply_podcast_cache_completed, item)

    def _apply_podcast_cache_completed(self, item: DownloadItem) -> None:
        """The episode is byte-backed now. Deliberately silent.

        Nothing is announced and no sound plays: the listener did not ask for a
        download, and the whole value of this is that they never had to think
        about it. What changes is what is now *possible* -- Find Chapters, Deep
        transcription and Keep This Episode all work from here on.
        """
        show = self._podcast_library.find_show(item.show_id)
        episode = show.find_episode(item.episode_guid) if show is not None else None
        url = str(getattr(episode, "audio_url", "") or "")
        playback_cache.finalize(item.show_id, item.episode_guid, url)
        if item.item_id == getattr(self, "_podcast_cache_item_id", ""):
            self._podcast_cache_item_id = ""
        self._evict_podcast_cache()

    def podcast_keep_episode(self) -> None:
        """Keep This Episode: turn what is playing into a kept download.

        When the bytes are already cached this is a move, not a transfer -- the
        usual "change your mind, download the whole episode again" is simply
        not necessary. When they are not (the fill has not finished, or caching
        is off for this show), it falls back to an ordinary download, which is
        exactly what the listener would otherwise have done.
        """
        state = self._podcast_controller.state
        show = self._podcast_library.find_show(str(state.show_id or ""))
        episode = show.find_episode(str(state.episode_guid or "")) if show is not None else None
        if show is None or episode is None:
            self._announce("Play an episode first.")
            return
        if episode.downloaded_path:
            self._announce(f"{episode.title} is already downloaded.")
            return
        from quill.ui.podcasts.manager_dialog import episode_destination
        from quill.ui.podcasts.show_actions import enqueue_episode_download

        destination = episode_destination(self._podcast_download_root(), show, episode)
        kept = playback_cache.promote(show.id, episode.guid, episode.audio_url, destination)
        if kept is None:
            enqueue_episode_download(
                self._podcast_download_queue, self._podcast_download_root(), show, episode
            )
            self._announce(f"Downloading {episode.title} to keep it.")
            return
        episode.downloaded_path = str(kept)
        self._save_podcast_library()
        self._announce(f"Keeping {episode.title}. It was already here, so nothing was downloaded.")
