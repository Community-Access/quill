"""QUILL Cast 1.1.0: session controls, statistics, storage, and maintenance.

``main_frame_podcasts.py`` owns the player, the download queue, and the
subscribe/refresh path. This mixin sits underneath it (``PodcastsMixin``
inherits it, so QUILL and QUILL Cast both get every command here) and owns
the things 1.1.0 added around that core:

- **Session control.** Stop after this episode; the continue-after-queue /
  continue-after-group pair that decides whether anything follows at all;
  playback speed as a real 0.5x-5.0x continuum with Speed Up / Speed Down /
  Reset commands instead of a six-item dropdown.
- **Statistics.** A once-a-second accumulator on the player's existing poll,
  flushed only at the points a position is already being saved, so a
  listening log costs one JSON write per stopping point rather than one per
  second.
- **Storage.** Total usage, a per-show breakdown, an age limit, and a cap --
  plus the one rule that makes an automatic cap safe to ship: a queued or
  in-progress episode is never evicted.
- **Maintenance.** The scheduled pass that expires stale queue items, sweeps
  Recently Expired, trims the Inbox to its caps, and applies the storage
  rules -- announcing everything it did, because a queue that quietly
  shortened itself is precisely the unannounced state change A-4 forbids.

Every announcement here is coalesced into one sentence per pass. Twelve
episodes expiring must not be twelve interruptions.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.podcasts import expiration, quick_actions, retention, stats
from quill.core.podcasts.models import SPEED_MAX, SPEED_MIN, clamp_speed
from quill.core.podcasts.subscriptions import PodcastLibrary

#: Speed Up / Speed Down step. Matches Earshot, and is small enough that
#: holding the key is a usable way to find the speed you want.
SPEED_STEP = 0.1


class PodcastSessionMixin:
    """1.1.0 session, statistics, storage, and maintenance commands."""

    # -- setup ----------------------------------------------------------

    def _init_podcast_session(self) -> None:
        """Called from ``_init_podcasts`` once the library and player exist."""
        self._podcast_quick_actions = quick_actions.load_quick_actions(app_data_dir())
        #: "Stop after this episode": one-off, cleared the moment it fires and
        #: never persisted, so a restart is always a clean slate.
        self._podcast_stop_after_episode = False
        #: Statistics accumulator: (show, episode) -> seconds at the speed in
        #: force. Buffered in memory; see _podcast_flush_stats.
        self._podcast_stats_key: tuple[str, str] | None = None
        self._podcast_stats_seconds = 0.0
        self._podcast_stats_speed = 1.0
        #: Chapter auto-skip marks for the playing episode. In memory only --
        #: a chapter you skipped in yesterday's episode says nothing about
        #: today's, and it resets when the episode (or the app) changes.
        from quill.core.podcasts.chapter_skip import ChapterSkipState

        self._podcast_chapter_skip = ChapterSkipState()

    def _podcast_stats_retention_days(self) -> int:
        """How long the listening log is kept -- the listener's own choice.

        Was hardcoded to 90 days, which meant a stated privacy setting the app
        offered no way to change. ``0`` means keep forever and ``-1`` means keep
        nothing at all, which ``_podcast_flush_stats`` short-circuits on rather
        than writing and pruning.
        """
        settings = getattr(self._podcast_library, "settings", None)
        return int(getattr(settings, "history_retention_days", stats.DEFAULT_RETENTION_DAYS))

    def open_podcast_directory_credentials(self) -> None:
        """Podcast Index Credentials... -- see ui/podcasts/directory_credentials_dialog."""
        from quill.ui.podcasts.directory_credentials_dialog import open_directory_credentials

        open_directory_credentials(self)

    def podcast_choose_output_device(self) -> None:
        """Audio Output Device...: route this app's sound. See ui/media/output_device."""
        from quill.ui.media.output_device import choose_output_device

        choose_output_device(self)

    # -- statistics -----------------------------------------------------

    def _podcast_second_tick(self) -> None:
        """One second of the player's existing poll.

        Deliberately does no I/O: it adds to a float. The log is written at
        the pause/stop/switch/close points that already write a position.
        """
        from quill.ui.podcasts.player_controller import PodcastPlayerState

        controller = getattr(self, "_podcast_controller", None)
        if controller is None:
            return
        state = controller.state
        if state.state is not PodcastPlayerState.PLAYING:
            return
        if not state.show_id or not state.episode_guid:
            return
        key = (state.show_id, state.episode_guid)
        if key != self._podcast_stats_key:
            self._podcast_flush_stats()
            self._podcast_stats_key = key
            self._podcast_stats_seconds = 0.0
        self._podcast_stats_seconds += 1.0
        self._podcast_stats_speed = float(controller.rate or 1.0)
        self._podcast_apply_chapter_skip(state.show_id, state.episode_guid)

    def _podcast_apply_chapter_skip(self, show_id: str, episode_guid: str) -> None:
        """Jump past a chapter marked to be skipped, and say so.

        Costs a set-emptiness check when nothing is marked, which is almost
        always -- this rides the same once-a-second poll as the statistics
        accumulator and must not become work the player does for nothing.
        """
        state = self._podcast_chapter_skip
        state.retarget(show_id, episode_guid)
        if not state.skipped:
            return
        chapters = list(getattr(self, "_podcast_current_chapters", []) or [])
        if not chapters:
            return
        controller = self._podcast_controller
        decision = state.evaluate(chapters, controller.position_ms())
        if decision.kind == "seek":
            controller.seek(decision.target_start_ms)
            self._announce(f"Skipping chapter: {decision.skipped_title}")
        elif decision.kind == "end":
            # Everything from here on is skipped, so the episode is over.
            # Stopping would strand auto-advance and delete-after-play, so
            # this seeks to the very end and lets the natural finish path run.
            self._announce(f"Skipping chapter: {decision.skipped_title}")
            length = controller.length_ms()
            if length > 0:
                controller.seek(max(0, length - 1000))

    def podcast_chapter_skip_state(self):
        """The marking state for whatever is playing (for the Chapters dialog)."""
        controller = getattr(self, "_podcast_controller", None)
        if controller is None or controller.state.show_id is None:
            return None
        self._podcast_chapter_skip.retarget(
            controller.state.show_id, controller.state.episode_guid or ""
        )
        return self._podcast_chapter_skip

    def _podcast_flush_stats(self, *, completed: bool = False) -> None:
        """Write the buffered listening time out as one session.

        ``smart_speed_saved_seconds`` stays 0. The relay reports its own
        output time, not how much source silence it dropped, so there is no
        honest number to record -- and a fabricated "time saved" figure is
        worse than an absent one, which is why the report omits the line
        entirely rather than showing a confident zero.
        """
        key = self._podcast_stats_key
        seconds = self._podcast_stats_seconds
        self._podcast_stats_key = None
        self._podcast_stats_seconds = 0.0
        if key is None or seconds < 1.0:
            return
        # "Do not keep a history" is short-circuited here rather than pruned
        # afterwards: writing a session and deleting it a moment later would
        # still have put it on the disk, which is precisely what somebody who
        # chose that option asked not to happen.
        if self._podcast_stats_retention_days() < 0:
            return
        session = stats.ListeningSession(
            show_id=key[0],
            episode_guid=key[1],
            seconds=seconds,
            speed=self._podcast_stats_speed,
            completed=completed,
        )
        try:
            stats.append_session(
                app_data_dir(), session, retention_days=self._podcast_stats_retention_days()
            )
        except OSError:
            # A statistics write is never worth interrupting playback for.
            pass

    def open_podcast_statistics(self) -> None:
        """Episode > Statistics...: how much you listened, and to what."""
        from quill.ui.podcasts.stats_dialog import PodcastStatsDialog

        self._podcast_flush_stats()
        titles = {show.id: show.title for show in self._podcast_library.shows}
        dialog = PodcastStatsDialog(
            self.frame,
            sessions=stats.load_sessions(app_data_dir()),
            show_titles=titles,
            announce_cb=self._announce,
            on_clear=self._podcast_clear_statistics,
            streaks_enabled=bool(
                getattr(self._podcast_library.settings, "stats_streaks_enabled", False)
            ),
        )
        dialog.show()

    def _podcast_clear_statistics(self) -> int:
        cleared = stats.clear_sessions(app_data_dir())
        self._announce(f"Cleared {cleared} listening session(s)")
        return cleared

    # -- session control ------------------------------------------------

    def podcast_toggle_stop_after_episode(self) -> None:
        """One-off: stop instead of auto-advancing when this episode ends."""
        controller = getattr(self, "_podcast_controller", None)
        if controller is None or controller.state.show_id is None:
            self._announce("Nothing is playing to stop after.")
            return
        self._podcast_stop_after_episode = not self._podcast_stop_after_episode
        self._announce(
            "Will stop after this episode."
            if self._podcast_stop_after_episode
            else "Will keep playing after this episode."
        )

    @property
    def podcast_stop_after_episode(self) -> bool:
        return bool(getattr(self, "_podcast_stop_after_episode", False))

    def _podcast_speed_context(self):
        """``(show, effective settings)`` the speed commands act on: the
        playing show's own override if something is playing, otherwise the
        shared default -- the same resolution Sound Enhancements uses."""
        controller = getattr(self, "_podcast_controller", None)
        show_id = controller.state.show_id if controller is not None else None
        show = self._podcast_library.find_show(show_id) if show_id else None
        settings = (
            self._podcast_library.effective_settings(show)
            if show is not None
            else self._podcast_library.settings
        )
        return show, settings

    def _podcast_apply_speed(self, speed: float) -> None:
        show, _settings = self._podcast_speed_context()
        resolved = clamp_speed(speed)
        if show is not None:
            self._podcast_library.apply_show_override(show, speed=resolved)
            target = show.title
        else:
            self._podcast_library.settings.speed = resolved
            target = "every podcast"
        self._save_podcast_library()
        controller = getattr(self, "_podcast_controller", None)
        if controller is not None and controller.state.show_id is not None:
            controller.set_rate(resolved)
        self._announce(f"Speed {resolved:g}x for {target}")

    def podcast_speed_up(self) -> None:
        _show, settings = self._podcast_speed_context()
        if settings.speed >= SPEED_MAX:
            self._announce(f"Already at the fastest speed, {SPEED_MAX:g}x")
            return
        self._podcast_apply_speed(settings.speed + SPEED_STEP)

    def podcast_speed_down(self) -> None:
        _show, settings = self._podcast_speed_context()
        if settings.speed <= SPEED_MIN:
            self._announce(f"Already at the slowest speed, {SPEED_MIN:g}x")
            return
        self._podcast_apply_speed(settings.speed - SPEED_STEP)

    def podcast_speed_reset(self) -> None:
        self._podcast_apply_speed(1.0)

    def podcast_current_show_unheard(self) -> int:
        """Unplayed count of the playing show; in-memory (EVT_UPDATE_UI-safe)."""
        controller = getattr(self, "_podcast_controller", None)
        show = self._podcast_library.find_show(controller.state.show_id) if controller else None
        return sum(1 for e in show.episodes if not e.played) if show is not None else 0

    def podcast_mark_all_played(self, show: object | None = None) -> None:
        """Mark every episode of one show played, confirmed by name and count
        until Don't ask me again is checked. Dismisses them from the Inbox as
        a side effect, because the Inbox is unplayed episodes and these are
        no longer that."""
        if show is None:
            controller = getattr(self, "_podcast_controller", None)
            show_id = controller.state.show_id if controller is not None else None
            show = self._podcast_library.find_show(show_id) if show_id else None
        if show is None:
            self._announce("Select a podcast first.")
            return
        unplayed = [e for e in show.episodes if not e.played]
        if not unplayed:
            self._announce(f"Every episode of {show.title} is already played.")
            return
        from quill.ui.podcasts.mark_played_confirm_dialog import confirm_mark_all_played

        if not confirm_mark_all_played(
            self.frame,
            message=(
                f"Mark all {len(unplayed)} unplayed episode(s) of {show.title} as played? "
                "They stay in your library; downloaded files are not deleted."
            ),
            announce=self._announce,
        ):
            return
        for episode in unplayed:
            from quill.core.podcasts.position_sync import mark_played

            mark_played(episode)
        self._save_podcast_library()
        manager = getattr(self, "_podcast_manager_dialog", None)
        if manager is not None:
            manager.refresh_tree()
        self._announce(f"Marked {len(unplayed)} episode(s) of {show.title} as played")

    # -- quick actions --------------------------------------------------

    def open_podcast_quick_actions(self) -> None:
        """Subscriptions > Quick Actions...: reorder the menus themselves."""
        from quill.ui.podcasts.quick_actions_dialog import QuickActionsDialog

        dialog = QuickActionsDialog(
            self.frame, orders=self._podcast_quick_actions, announce_cb=self._announce
        )
        updated = dialog.show()
        if updated is None:
            return
        self._podcast_quick_actions = updated
        quick_actions.save_quick_actions(app_data_dir(), updated)
        self._announce("Quick Actions saved")

    def podcast_quick_actions(self) -> quick_actions.QuickActionOrders:
        """The live order, for the dialogs that build menus from it."""
        orders = getattr(self, "_podcast_quick_actions", None)
        if orders is None:
            orders = quick_actions.QuickActionOrders()
            self._podcast_quick_actions = orders
        return orders

    # -- storage --------------------------------------------------------

    def open_podcast_downloads(self) -> None:
        """Downloads > Downloads...: what is on disk, and how to free it."""
        from quill.ui.podcasts.downloads_dialog import DownloadsDialog

        dialog = DownloadsDialog(
            self.frame,
            library=self._podcast_library,
            announce_cb=self._announce,
            on_library_changed=self._save_podcast_library,
            on_free_space=self.podcast_free_up_space,
        )
        dialog.show()

    def podcast_free_up_space(self) -> int:
        """Apply the age limit and the storage cap now, on request.

        Returns the bytes reclaimed. The same rules the maintenance pass
        applies -- this is the manual button for them, for the moment you
        actually need the disk back.
        """
        aged = retention.apply_age_limit(self._podcast_library)
        capped = retention.enforce_storage_cap(self._podcast_library)
        reclaimed = sum(size for _s, _e, size in [*aged, *capped])
        if not aged and not capped:
            self._announce("Nothing to free up: no download is past its age limit or over the cap.")
            return 0
        self._save_podcast_library()
        self._announce(
            f"Freed {retention.format_bytes(reclaimed)} from "
            f"{len(aged) + len(capped)} downloaded episode(s)"
        )
        return reclaimed

    # -- maintenance ----------------------------------------------------

    def podcast_run_maintenance(self, *, announce: bool = True) -> str:
        """Expire, sweep, trim, and enforce -- one pass, one sentence.

        Runs once at startup and again after every feed refresh. Everything
        it does is reported: an expired queue item, a trimmed Inbox episode
        and an evicted download are all state the listener did not ask for
        in that moment, and A-4 says none of them happen in silence.
        """
        library: PodcastLibrary = self._podcast_library
        changed = False
        parts: list[str] = []

        if expiration.stamp_missing_added_at(library):
            changed = True  # migration only; nothing to announce

        expired = expiration.expire_stale_queue_items(library)
        if expired:
            changed = True
            parts.append(
                f"{len(expired)} episode(s) expired from the queue -- "
                "find them under Recently Expired"
            )
        dropped, deleted_files = expiration.sweep_recently_expired(library)
        if dropped:
            changed = True
            if deleted_files:
                parts.append(
                    f"{len(dropped)} expired episode(s) passed the "
                    f"{expiration.RECENTLY_EXPIRED_HOLD_DAYS}-day hold; "
                    f"{deleted_files} downloaded file(s) removed"
                )
            else:
                parts.append(f"{len(dropped)} expired episode(s) passed the hold window")

        from quill.core.podcasts.inbox import trim_inbox

        trimmed = trim_inbox(library)
        if trimmed:
            changed = True
            parts.append(
                f"{len(trimmed)} episode(s) left the Inbox at its limit "
                "(still unplayed in their shows)"
            )

        aged = retention.apply_age_limit(library)
        capped = retention.enforce_storage_cap(library)
        if aged or capped:
            changed = True
            reclaimed = sum(size for _s, _e, size in [*aged, *capped])
            parts.append(
                f"{len(aged) + len(capped)} old download(s) removed, "
                f"{retention.format_bytes(reclaimed)} freed"
            )

        if changed:
            self._save_podcast_library()
        summary = "; ".join(parts)
        if summary and announce:
            self._announce(f"Podcast housekeeping: {summary}.")
        return summary

    # -- data export / reset (Cast's answer to "it is my data") ----------

    def podcast_export_data(self) -> None:
        """Export subscriptions, queue, playlists, notes, and stats as JSON.

        OPML covers subscriptions and nothing else. This is everything the
        app knows about your listening, in one readable file, because
        "export my data" should not mean "export the part that fits a 2005
        interchange format".
        """
        wx = self._wx
        with wx.FileDialog(  # dialog_button_contract: exempt
            self.frame,
            "Export Podcast Data",
            defaultFile="quill-cast-data.json",
            wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            target = Path(dialog.GetPath())
        import json

        from quill.core.podcasts.episode_notes import load_episode_notes

        library = self._podcast_library
        try:
            notes = load_episode_notes()
        except Exception:  # noqa: BLE001 - a missing notes file exports as none
            notes = {}
        payload = {
            "app": "QUILL Cast",
            "exported_at": stats.now_iso(),
            "shows": [show.to_dict() for show in library.shows],
            "folders": [
                {"id": f.id, "name": f.name, "parent_folder_id": f.parent_folder_id}
                for f in library.folders
            ],
            "settings": library.settings.to_dict(),
            "queue": [item.to_dict() for item in library.queue],
            "playlists": [p.to_dict() for p in library.playlists],
            "recently_expired": [e.to_dict() for e in library.recently_expired],
            "episode_notes": notes if isinstance(notes, dict) else {},
            "listening_sessions": [s.to_dict() for s in stats.load_sessions(app_data_dir())],
            "history": [e.to_dict() for e in self._podcast_history.episodes],
        }
        try:
            target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except (OSError, TypeError, ValueError) as error:
            self._announce(f"Could not export your data: {error}")
            return
        self._announce(f"Exported your podcast data to {target.name}")

    def podcast_delete_all_data(self) -> None:
        """Unsubscribe from everything and clear every local record.

        Confirmed twice, and the second confirmation names exactly what goes.
        Downloaded files are a separate question, asked separately, because
        "start over" and "reclaim the disk" are not the same wish.
        """
        wx = self._wx
        from quill.ui.dialog_contract import show_message_box

        library = self._podcast_library
        show_count = len(library.shows)
        if not show_count and not library.playlists:
            self._announce("There is nothing to delete: your library is already empty.")
            return
        first = show_message_box(
            f"Delete everything? This unsubscribes from all {show_count} podcast(s) and "
            "clears your queue, playlists, Inbox filing, listening statistics, and "
            "recently played list.",
            "Delete All Podcast Data",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            self.frame,
            announce=self._announce,
        )
        if first != wx.YES:
            return
        downloaded = [
            episode
            for show in library.shows
            for episode in show.episodes
            if episode.downloaded_path
        ]
        delete_files = False
        if downloaded:
            delete_files = (
                show_message_box(
                    f"Also delete the {len(downloaded)} downloaded episode file(s) from disk?",
                    "Delete Downloaded Files",
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                    self.frame,
                    announce=self._announce,
                )
                == wx.YES
            )
        confirm = show_message_box(
            "Last chance: this cannot be undone. Delete all podcast data now?",
            "Delete All Podcast Data",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            self.frame,
            announce=self._announce,
        )
        if confirm != wx.YES:
            self._announce("Nothing was deleted.")
            return
        controller = getattr(self, "_podcast_controller", None)
        if controller is not None:
            controller.stop()
        if delete_files:
            for episode in downloaded:
                try:
                    Path(episode.downloaded_path).unlink(missing_ok=True)
                except OSError:
                    continue
        from quill.core.podcasts import feed_auth

        for show in library.shows:
            feed_auth.delete_feed_password(show.id)
        library.shows = []
        library.folders = []
        library.queue = []
        library.playlists = []
        library.inbox_folders = []
        library.inbox_assignments = {}
        library.recently_expired = []
        self._podcast_history.episodes = []
        stats.clear_sessions(app_data_dir())
        self._save_podcast_library()
        from quill.core.podcasts import history as podcast_history

        podcast_history.save_history(app_data_dir(), self._podcast_history)
        manager = getattr(self, "_podcast_manager_dialog", None)
        if manager is not None:
            manager.refresh_tree()
        self._announce(
            "All podcast data deleted" + (" and downloaded files removed" if delete_files else "")
        )

    # -- command registration -------------------------------------------

    def _register_podcast_session_commands(self) -> None:
        """Palette wiring lives in quill/ui/podcasts/palette_commands.py (GATE-11)."""
        from quill.ui.podcasts.palette_commands import register_podcast_commands

        register_podcast_commands(self)
