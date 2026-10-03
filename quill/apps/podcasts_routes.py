"""Every door into a place leads to the one window (qc.md Phase 2).

The openers the shared podcast mixins defined for QUILL's dialogs -- the
Podcast Manager, the Play Queue window, the Downloads window, Continue
Listening -- still exist by name, because Go To, the status-bar cells, the
command palette and the tutorials all call them. In QUILL Cast each of them
is a place now, so this mixin answers those names with :meth:`show_place`.
It sits *before* ``PodcastsMixin`` in the frame's bases so its answers win.

Also here: the small verbs the one window gained that no shared mixin had --
Settings for This Podcast from the selection, Change Schedule, the queue
lineups as commands, the notices' Mark All and Clear, the launch digest, and
the feature-switch helpers the menus, the status bar and Go To consult.
"""

from __future__ import annotations

from typing import Any

__all__ = ["CastPlaceRoutesMixin"]

#: Status-bar cell -> the Customize Features area that owns it.
_CELL_AREAS: dict[str, str] = {
    "queue": "queue",
    "inbox": "inbox",
    "downloads": "downloads",
    "notifications": "notifications",
    "sleep_timer": "sleep_timer",
    "speed": "speed",
}


class CastPlaceRoutesMixin:
    """On ``PodcastsAppFrame``, first among the podcast mixins."""

    def say_now_playing(self) -> None:
        """Ctrl+T: the Now Playing line, said again (qc.md 4.1)."""
        text = str(self._podcast_status_text() or "")  # type: ignore[attr-defined]
        self._announce(text or "Nothing is playing.", force=True)  # type: ignore[attr-defined]

    def _append_episode_extras(self, episode_menu: Any) -> None:
        """Three Episode rows whose commands existed with nowhere to press them:
        Bookmark This Moment (Ctrl+Alt+A), Skip Silence (Ctrl+Shift+9) and Say
        Current Episode (Ctrl+T). Out of ``podcasts_menu.py`` under GATE-11.
        The first two carry no access letter: the Episode menu has none free.
        """
        import wx

        bookmark_id, silence_id, say_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        label = self._menu_label  # type: ignore[attr-defined]
        self._area_row(
            episode_menu, "notes", bookmark_id, label("Bookmark This Moment", "app.bookmark_moment")
        )
        self._area_row(
            episode_menu, "skipping", silence_id, label("Skip Silence", "podcasts.skip_silence")
        )
        episode_menu.Append(say_id, label("Say &Current Episode", "podcasts.say_now_playing"))
        frame = self.frame  # type: ignore[attr-defined]
        frame.Bind(wx.EVT_MENU, lambda _e: self.bookmark_this_moment(), id=bookmark_id)  # type: ignore[attr-defined]
        frame.Bind(wx.EVT_MENU, lambda _e: self.podcast_toggle_skip_silence(), id=silence_id)  # type: ignore[attr-defined]
        frame.Bind(wx.EVT_MENU, lambda _e: self.say_now_playing(), id=say_id)
        self._keep_menu_ids(bookmark_id, silence_id, say_id)  # type: ignore[attr-defined]

    # -- the old doors ---------------------------------------------------------- #

    def open_podcast_manager(self) -> None:
        """The Manager is gone from Cast; its name leads to the Podcasts place."""
        self.show_place("podcasts")  # type: ignore[attr-defined]

    def _open_play_queue(self) -> None:
        self.show_place("queue")  # type: ignore[attr-defined]

    def open_podcast_downloads(self) -> None:
        self.show_place("downloads")  # type: ignore[attr-defined]

    def open_continue_listening(self) -> None:
        self.show_place("continue_listening")  # type: ignore[attr-defined]

    def open_cast_new_episodes(self) -> None:
        self.show_place("new_episodes")  # type: ignore[attr-defined]

    def open_cast_favorites(self) -> None:
        self.show_place("favorites")  # type: ignore[attr-defined]

    def open_cast_recently_expired(self) -> None:
        self.show_place("recently_expired")  # type: ignore[attr-defined]

    def open_cast_playlists(self) -> None:
        self.show_place("playlists")  # type: ignore[attr-defined]

    def open_cast_notifications(self) -> None:
        """View > Notifications: the place. The window is Help > Notifications."""
        self.show_place("notifications")  # type: ignore[attr-defined]

    def open_notifications(self) -> None:
        """Help > Notifications and the status cell: Cast's own peer window."""
        from quill.ui.podcasts.notifications_window import open_notifications_window

        open_notifications_window(self)

    def mark_all_notices_read(self) -> None:
        from quill.core.notifications import load_notifications, mark_all_read

        try:
            unread = sum(1 for n in load_notifications() if not n.read)
            mark_all_read()
        except Exception:  # noqa: BLE001
            unread = 0
        self._refresh_place(keep=True)  # type: ignore[attr-defined]
        self._announce("Nothing was unread." if not unread else f"Marked {unread} as read.")  # type: ignore[attr-defined]

    def clear_all_notices(self) -> None:
        from quill.core.notifications import clear_notifications, load_notifications

        try:
            count = len(load_notifications())
            clear_notifications()
        except Exception:  # noqa: BLE001
            count = 0
        self._refresh_place(keep=False)  # type: ignore[attr-defined]
        self._announce(  # type: ignore[attr-defined]
            "The list is already empty."
            if not count
            else f"Cleared {count} notification{'s' if count != 1 else ''}."
        )

    def _mark_notice_read(self, notice_id: str) -> None:
        from quill.core.notifications import mark_read

        mark_read(notice_id)
        self._refresh_place(keep=True)  # type: ignore[attr-defined]
        self._announce("Marked as read.")  # type: ignore[attr-defined]

    # -- settings for the selection, and schedules ---------------------------------- #

    def open_show_settings_for_selection(self) -> None:
        """Podcasts > Settings for This Podcast... (Ctrl+Alt+,) on the selected podcast."""
        show = self._unfollow_target()  # type: ignore[attr-defined]
        if show is None:
            self._announce("Select a podcast or one of its episodes first.")  # type: ignore[attr-defined]
            return
        self._on_show_settings(show)  # type: ignore[attr-defined]

    def change_show_schedule(self, show: Any = None) -> None:
        """Change Schedule... on a podcast row, or for the selection."""
        from quill.ui.podcasts.schedule_dialog import change_schedule

        target = show if show is not None else self._unfollow_target()  # type: ignore[attr-defined]
        if target is None:
            self._announce("Select a podcast first; the shared schedule is in Preferences.")  # type: ignore[attr-defined]
            return
        if change_schedule(self, target):
            self._refresh_place(keep=True)  # type: ignore[attr-defined]

    def _on_refresh_feed(self, show: Any) -> None:
        """Check Now on a podcast: the shared refresh, said first."""
        self._announce(f"Checking {show.title}...")  # type: ignore[attr-defined]
        self.refresh_podcast_feed(show.id)  # type: ignore[attr-defined]

    def _download_item_id(self, episode: Any) -> str:
        return str(episode.guid)

    def _resolved_episode_actions(self) -> list[Any]:
        from quill.ui.podcasts.context_menus import resolved_episode_actions

        return resolved_episode_actions(self)

    def _on_download(self, _event: object = None) -> None:
        """Download the selected episode, from any place (the Manager needed a current show)."""
        pair = self._selected_episode()  # type: ignore[attr-defined]
        if pair is None:
            return
        show, episode = pair
        from quill.ui.podcasts.show_actions import enqueue_episode_download

        enqueue_episode_download(
            self._podcast_download_queue,  # type: ignore[attr-defined]
            self._podcast_download_root(),  # type: ignore[attr-defined]
            show,
            episode,
            item_id=self._download_item_id(episode),
        )
        self._announce(f"Downloading {episode.title}")  # type: ignore[attr-defined]
        self._refresh_selected_episode_row()  # type: ignore[attr-defined]

    # -- the queue's lineups, as commands ------------------------------------------------ #

    def podcast_save_queue_lineup(self) -> None:
        from quill.core.podcasts.queue_lineups import find_lineup, save_lineup
        from quill.ui.podcasts.folder_prompt import name_prompt

        library = self._podcast_library  # type: ignore[attr-defined]
        if not library.queue:
            self._announce("The queue is empty, so there is no order to save.")  # type: ignore[attr-defined]
            return
        name = name_prompt(
            self.frame, "Save Lineup", announce=self._announce, message="Lineup name:"
        )  # type: ignore[attr-defined]
        if name is None:
            return
        replacing = find_lineup(library, name) is not None
        saved = save_lineup(library, name)
        if saved is None:
            self._announce("That lineup could not be saved.")  # type: ignore[attr-defined]
            return
        self._save_podcast_library()  # type: ignore[attr-defined]
        verb = "Replaced" if replacing else "Saved"
        self._announce(f"{verb} lineup {name}: {len(saved.items)} episode(s), in this order.")  # type: ignore[attr-defined]

    def podcast_apply_queue_lineup(self) -> None:
        import wx

        from quill.core.podcasts.queue_lineups import apply_lineup, lineup_names

        library = self._podcast_library  # type: ignore[attr-defined]
        names = lineup_names(library)
        if not names:
            self._announce("No lineups have been saved yet. Use Save Lineup first.")  # type: ignore[attr-defined]
            return
        with wx.SingleChoiceDialog(  # dialog_button_contract: exempt
            self.frame,
            "Apply which lineup?",
            "Apply Lineup",
            names,  # type: ignore[attr-defined]
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            chosen = dialog.GetStringSelection()
        playlist = next((p for p in library.playlists if p.name == chosen), None)
        if playlist is None:
            return
        counted = apply_lineup(library, playlist)
        self._save_podcast_library()  # type: ignore[attr-defined]
        self._refresh_place(keep=False)  # type: ignore[attr-defined]
        self._announce(counted.sentence("Applied", chosen, noun="episode"))  # type: ignore[attr-defined]

    # -- feature switches ------------------------------------------------------------- #

    def _cell_enabled(self, key: str) -> bool:
        area = _CELL_AREAS.get(key, "")
        return not area or self._cast_area_enabled(area)  # type: ignore[attr-defined]

    def _area_row(self, menu: Any, area: str, item_id: object, label: str) -> bool:
        """Append *label* only when *area* is on in Customize Features (section 17).

        The Bind is left in place at every site, as ``_advanced_row`` does, so the
        id is harmless; what makes the feature *absent* is that the row, its key,
        its place and its cell are not built, and the palette says where it went.
        """
        if not self._cast_area_enabled(area):  # type: ignore[attr-defined]
            return False
        menu.Append(item_id, label)
        return True

    def _cast_command_unavailable_reason(self, command_id: str) -> str:
        """The palette's "(off in Customize Features)" (section 17), installed as
        the registry's probe in the frame's ``__init__`` (the shell's own answer
        comes first in the bases, so this cannot simply override it)."""
        from quill.core.podcasts.cast_features import area_for_command
        from quill.ui.app_availability import CommandAvailabilityMixin

        area = area_for_command(command_id)
        if area and not self._cast_area_enabled(area):  # type: ignore[attr-defined]
            return "off in Customize Features"
        return CommandAvailabilityMixin._command_unavailable_reason(self, command_id)  # type: ignore[arg-type]

    # -- the launch digest ---------------------------------------------------------------- #

    def _say_launch_digest(self) -> None:
        """One sentence about what arrived while Cast was closed (qc.md 5b)."""
        from datetime import UTC, datetime

        from quill.core.notifications import load_notifications
        from quill.core.podcasts import notices
        from quill.core.quiet_hours import Kind
        from quill.ui.quiet_hours_ui import held_back

        history = self._podcast_history  # type: ignore[attr-defined]
        if not getattr(history, "launch_digest", True) or not self._cast_area_enabled("digest"):  # type: ignore[attr-defined]
            return
        since_raw = str(getattr(history, "last_seen_at", "") or "")
        try:
            since = datetime.fromisoformat(since_raw) if since_raw else None
        except ValueError:
            since = None
        if since is None or held_back(Kind.NEW_EPISODE):
            return
        try:
            entries = load_notifications()
        except Exception:  # noqa: BLE001
            return
        said = notices.digest(
            entries,
            since=since,
            now=datetime.now(UTC),
            inbox_on=self._cast_area_enabled("inbox"),  # type: ignore[attr-defined]
        )
        if said:
            self._announce(said)  # type: ignore[attr-defined]

    def _check_at_launch(self) -> int:
        """Check when Cast opens, and catch up on a missed check (qc.md 5e).

        Per podcast: *Check when Cast opens* checks it now; *Catch up on a missed
        check* checks it when its own schedule fell due while Cast was closed.
        Safe Mode, a paused podcast and a podcast with no feed are never checked.
        Returns how many checks started.
        """
        from datetime import UTC, datetime

        from quill.core.podcasts import schedule_policy

        self._watch_power_resume()
        if getattr(self, "_safe_mode", False):
            return 0
        library = self._podcast_library  # type: ignore[attr-defined]
        now = datetime.now(UTC)
        started = 0
        for show in list(library.shows):
            if not show.feed_url or getattr(show, "paused", False):
                continue
            wanted = schedule_policy.switch(library, show, "check_on_launch")
            if not wanted and schedule_policy.switch(library, show, "check_burst_after_miss"):
                wanted = schedule_policy.is_due(library, show, now=now) and bool(
                    getattr(self._podcast_history, "podcast_check_enabled", False)  # type: ignore[attr-defined]
                )
            if wanted:
                self.refresh_podcast_feed(show.id)  # type: ignore[attr-defined]
                started += 1
        return started

    def _watch_power_resume(self) -> None:
        """Check when the computer wakes (qc.md 5e): once, on resume from sleep."""
        if getattr(self, "_power_resume_bound", False):
            return
        self._power_resume_bound = True
        try:
            import wx

            event = getattr(wx, "EVT_POWER_RESUME", None)
            if event is not None:
                self.frame.Bind(event, self._on_power_resume)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - a platform without the event checks at launch only
            pass

    def _on_power_resume(self, event: Any = None) -> int:
        """Each podcast whose *Check when the computer wakes* is on, checked once."""
        from quill.core.podcasts import schedule_policy

        if event is not None and hasattr(event, "Skip"):
            event.Skip()
        if getattr(self, "_safe_mode", False):
            return 0
        started = 0
        for show in list(self._podcast_library.shows):  # type: ignore[attr-defined]
            if not show.feed_url or getattr(show, "paused", False):
                continue
            if schedule_policy.switch(self._podcast_library, show, "check_on_resume"):  # type: ignore[attr-defined]
                self.refresh_podcast_feed(show.id)  # type: ignore[attr-defined]
                started += 1
        return started

    def _stamp_last_seen(self) -> None:
        from datetime import UTC, datetime

        self._podcast_history.last_seen_at = datetime.now(UTC).isoformat()  # type: ignore[attr-defined]
