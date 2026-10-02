"""Now Playing: a console a listener can live in for an evening (qc.md section 5).

Window 2 of QUILL Cast. Opened from Window > Now Playing, Ctrl+2, the Episode
menu or the status bar's Play cell menu, and -- with the Preferences checkbox
on -- brought to the front when playback starts. It absorbs Player
Information (its lines are the Playing-from line and About This Episode), Go
to Position (the slider), the Speed chooser, Volume, and the Sleep Timer
dialog's readout; the Set... button keeps the dialog for typing a number.

Every control is a real control: the position is a ``wx.Slider`` a screen
reader reads as one (Left/Right five seconds, Page keys thirty, Home/End the
ends, and the readout beside it says minutes and seconds); the chapters are a
report list whose playing row carries "playing" in its Status column and
follows playback without moving the cursor; the show notes are the Notes
reader (:mod:`quill.ui.notes_reader`); Your note is a field saved on blur.

Announcements: the window announces nothing on open beyond its title (the
reader does that, GATE-13). Chapter changes say the chapter title, as the
keys do; the sleep timer says its last minute from the shared controller.
The once-a-second refresh never writes the slider while it has focus, because
a value written under a focused slider is a value the reader repeats.

The frame is made once and hidden on close rather than destroyed, so it keeps
its number in the Window menu and Ctrl+2 always reaches it; the refresh timer
runs only while it is shown and stops when the app closes.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.podcasts.now_playing_layout import SPEEDS, TITLE, build_controls

__all__ = ["SKIP_MS", "SPEEDS", "TITLE", "NowPlayingWindow", "open_now_playing"]

SKIP_MS = 30_000
_NUDGE_MS = 5_000
_PAGE_MS = 30_000


def _ms_text(ms: int) -> str:
    from quill.core.media.timecode import format_timecode

    return format_timecode(max(0, int(ms)))


def _spoken(ms: int) -> str:
    from quill.core.media.timecode import format_spoken

    return format_spoken(max(0, int(ms)))


class NowPlayingWindow:
    """The peer window over the host's controller, library and timer."""

    def __init__(self, host: Any) -> None:
        self._host = host
        self._loaded_key: tuple[str, str] | None = None
        self._last_chapter: int = -1
        self._slider_dragging = False
        self._note_key: tuple[str, str] | None = None

        build_controls(self, host)
        self._bind()
        self._tick = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, lambda _e: self.refresh(), self._tick)
        self.frame.Bind(wx.EVT_CLOSE, self._on_close)
        self.refresh(full=True)

    def _bind(self) -> None:
        host = self._host
        self._slider.Bind(wx.EVT_SCROLL_THUMBTRACK, lambda _e: self._dragging(True))
        self._slider.Bind(wx.EVT_SCROLL_THUMBRELEASE, lambda _e: self._dragging(False))
        self._slider.Bind(wx.EVT_SCROLL_CHANGED, lambda _e: self._on_slider())
        self._slider.Bind(wx.EVT_CHAR_HOOK, self._on_slider_key)
        self._play.Bind(wx.EVT_BUTTON, lambda _e: self._call("podcast_toggle_play_pause"))
        self._stop.Bind(wx.EVT_BUTTON, lambda _e: self._call("podcast_stop"))
        self._back.Bind(wx.EVT_BUTTON, lambda _e: self._skip(-SKIP_MS))
        self._forward.Bind(wx.EVT_BUTTON, lambda _e: self._skip(SKIP_MS))
        self._prev_chapter.Bind(wx.EVT_BUTTON, lambda _e: self._call("podcast_previous_chapter"))
        self._next_chapter.Bind(wx.EVT_BUTTON, lambda _e: self._call("podcast_next_chapter"))
        self._speed.Bind(wx.EVT_CHOICE, lambda _e: self._on_speed())
        self._volume.Bind(wx.EVT_SCROLL_CHANGED, lambda _e: self._on_volume())
        self._volume.Bind(wx.EVT_SCROLL_THUMBRELEASE, lambda _e: self._on_volume())
        self._mute.Bind(wx.EVT_BUTTON, lambda _e: self._call("podcast_mute_toggle"))
        self._sleep_set.Bind(wx.EVT_BUTTON, lambda _e: self._call("open_sleep_timer_dialog"))
        self._sleep_end.Bind(wx.EVT_BUTTON, lambda _e: self._call("sleep_timer_end_of_episode"))
        self._sleep_extend.Bind(wx.EVT_BUTTON, lambda _e: self._call("extend_sleep_timer_command"))
        self._chapters.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self._jump_to_chapter())
        self._note.Bind(wx.EVT_KILL_FOCUS, self._on_note_blur)
        self._favorite.Bind(wx.EVT_BUTTON, lambda _e: self._on_favorite())
        self._played.Bind(wx.EVT_BUTTON, lambda _e: self._on_mark_played())
        self._share.Bind(wx.EVT_BUTTON, lambda _e: self._on_share())
        self._about.Bind(wx.EVT_BUTTON, lambda _e: self._call("open_podcast_episode_extras"))
        del host

    # -- the host ----------------------------------------------------------------

    def _call(self, name: str) -> None:
        method = getattr(self._host, name, None)
        if callable(method):
            method()
            wx.CallAfter(self.refresh)

    def _controller(self) -> Any:
        return getattr(self._host, "_podcast_controller", None)

    def _playing(self) -> tuple[Any, Any]:
        controller = self._controller()
        state = getattr(controller, "state", None)
        show_id = getattr(state, "show_id", None)
        guid = getattr(state, "episode_guid", None)
        if not show_id or not guid:
            return None, None
        show = self._host._podcast_library.find_show(show_id)
        episode = show.find_episode(guid) if show is not None else None
        return show, episode

    # -- refresh ------------------------------------------------------------------

    def refresh(self, *, full: bool = False) -> None:
        """Bring every readout up to date. Cheap: static text and a column."""
        if not self.frame or not self.frame.IsShown() and not full:
            return
        controller = self._controller()
        state = getattr(controller, "state", None)
        show, episode = self._playing()
        key = (
            (str(state.show_id), str(state.episode_guid))
            if state is not None and state.show_id and state.episode_guid
            else None
        )
        if key != self._loaded_key or full:
            self._loaded_key = key
            self._load_episode(show, episode, state)
        self._refresh_transport(controller, state)
        self._refresh_position(controller)
        self._refresh_chapter_status(controller)
        self._refresh_sleep()

    def _load_episode(self, show: Any, episode: Any, state: Any) -> None:
        if episode is None:
            self._podcast.SetLabel("Nothing is playing.")
            self._episode.SetLabel("")
            self._source.SetLabel("")
            self.notes.set_notes("", title="", podcast="")
            self._chapters.DeleteAllItems()
            self._chapters_caption.SetLabel("&Chapters:")
            self._note.SetValue("")
            self._note_key = None
            self._favorite.SetLabel("Add to F&avorites")
            for button in (self._favorite, self._played, self._share, self._about):
                button.Enable(False)
            return
        self._podcast.SetLabel(str(getattr(show, "title", "")))
        self._episode.SetLabel(str(getattr(episode, "title", "")))
        self._source.SetLabel(self._playing_from(show, state))
        self.notes.set_notes(
            str(getattr(episode, "description", "") or ""),
            title=str(getattr(episode, "title", "")),
            podcast=str(getattr(show, "title", "")),
        )
        self._fill_chapters()
        self._note_key = (str(state.show_id), str(state.episode_guid))
        self._note.SetValue(self._episode_note_text())
        self._refresh_favorite(show)
        for button in (self._played, self._share, self._about):
            button.Enable(True)
        self._refresh_speed()
        self._refresh_volume()

    def _playing_from(self, show: Any, state: Any) -> str:
        try:
            from quill.core.podcasts.playing_from import playing_from

            library = self._host._podcast_library
            in_queue = any(
                item.show_id == state.show_id and item.episode_guid == state.episode_guid
                for item in getattr(library, "queue", [])
            )
            source = playing_from(library, show, from_queue=in_queue)
        except Exception:  # noqa: BLE001 - the line is a courtesy
            source = ""
        return f"Playing from: {source}" if source else ""

    def _refresh_transport(self, controller: Any, state: Any) -> None:
        from quill.ui.podcasts.player_controller import PodcastPlayerState

        kind = getattr(state, "state", None)
        loaded = kind not in (None, PodcastPlayerState.STOPPED, PodcastPlayerState.ERROR)
        label = "Res&ume" if kind is PodcastPlayerState.PAUSED else "Pa&use"
        if self._play.GetLabel() != label:
            self._play.SetLabel(label)
        for button in (self._play, self._stop, self._back, self._forward, self._slider):
            button.Enable(loaded)
        has_chapters = bool(getattr(self._host, "_podcast_current_chapters", []))
        self._prev_chapter.Enable(loaded and has_chapters)
        self._next_chapter.Enable(loaded and has_chapters)
        mute_label = "Un&mute" if getattr(controller, "muted", False) else "&Mute"
        if self._mute.GetLabel() != mute_label:
            self._mute.SetLabel(mute_label)

    def _refresh_position(self, controller: Any) -> None:
        if controller is None:
            return
        try:
            position = int(controller.position_ms())
            length = int(controller.length_ms())
        except Exception:  # noqa: BLE001 - a controller mid-load has no numbers yet
            return
        self._time.SetLabel(f"{_ms_text(position)} of {_ms_text(length)}")
        if length > 0 and not self._slider_dragging and not self._slider.HasFocus():
            self._slider.SetRange(0, max(1, length // 1000))
            self._slider.SetValue(position // 1000)

    def _refresh_speed(self) -> None:
        try:
            from quill.ui.podcasts.speed import current_speed

            speed = float(current_speed(self._host))
        except Exception:  # noqa: BLE001
            return
        nearest = min(range(len(self._speeds)), key=lambda i: abs(self._speeds[i] - speed))
        if self._speed.GetSelection() != nearest:
            self._speed.SetSelection(nearest)

    def _refresh_volume(self) -> None:
        controller = self._controller()
        percent = int(getattr(controller, "volume_percent", 100) or 0)
        if not self._volume.HasFocus() and self._volume.GetValue() != percent:
            self._volume.SetValue(percent)

    def _refresh_favorite(self, show: Any) -> None:
        self._favorite.Enable(show is not None)
        label = (
            "Remove from F&avorites"
            if show is not None and getattr(show, "is_favorite", False)
            else "Add to F&avorites"
        )
        if self._favorite.GetLabel() != label:
            self._favorite.SetLabel(label)

    def _refresh_sleep(self) -> None:
        timer = getattr(self._host, "_sleep_timer_controller", None)
        if timer is None:
            return
        if getattr(timer, "is_end_of_episode", False):
            text = "Sleep timer: at the end of this episode"
        elif getattr(timer, "is_active", False):
            remaining = int(getattr(timer, "remaining_seconds", 0) or 0)
            minutes, seconds = divmod(max(0, remaining), 60)
            text = f"Sleep timer: {minutes}:{seconds:02d} left"
        else:
            text = "Sleep timer: off"
        if self._sleep.GetLabel() != text:
            self._sleep.SetLabel(text)
        self._sleep_extend.Enable(bool(getattr(timer, "is_active", False)))

    # -- chapters -------------------------------------------------------------------

    def _chapter_list(self) -> list[Any]:
        return list(getattr(self._host, "_podcast_current_chapters", []) or [])

    def _fill_chapters(self) -> None:
        chapters = self._chapter_list()
        self._chapters.DeleteAllItems()
        self._last_chapter = -1
        for index, chapter in enumerate(chapters):
            row = self._chapters.InsertItem(index, str(index + 1))
            self._chapters.SetItem(row, 1, str(getattr(chapter, "title", "")))
            self._chapters.SetItem(row, 2, _ms_text(int(getattr(chapter, "start_ms", 0))))
            self._chapters.SetItem(row, 3, "")
        self._chapters_caption.SetLabel(
            f"&Chapters ({len(chapters)}):" if chapters else "&Chapters:"
        )
        self._chapters.Enable(bool(chapters))

    def _refresh_chapter_status(self, controller: Any) -> None:
        chapters = self._chapter_list()
        if not chapters or controller is None:
            return
        if self._chapters.GetItemCount() != len(chapters):
            self._fill_chapters()
        try:
            position = int(controller.position_ms())
        except Exception:  # noqa: BLE001
            return
        current = -1
        for index, chapter in enumerate(chapters):
            if int(getattr(chapter, "start_ms", 0)) <= position:
                current = index
        if current == self._last_chapter:
            return
        if 0 <= self._last_chapter < self._chapters.GetItemCount():
            self._chapters.SetItem(self._last_chapter, 3, "")
        if 0 <= current < self._chapters.GetItemCount():
            self._chapters.SetItem(current, 3, "playing")
        self._last_chapter = current

    def _jump_to_chapter(self) -> None:
        index = self._chapters.GetFirstSelected()
        chapters = self._chapter_list()
        controller = self._controller()
        if index < 0 or index >= len(chapters) or controller is None:
            return
        chapter = chapters[index]
        controller.seek(int(getattr(chapter, "start_ms", 0)))
        self._host._announce(f"Chapter: {getattr(chapter, 'title', '')}")
        wx.CallAfter(self.refresh)

    # -- position --------------------------------------------------------------------

    def _dragging(self, on: bool) -> None:
        self._slider_dragging = on
        if not on:
            self._on_slider()

    def _on_slider(self) -> None:
        controller = self._controller()
        if controller is None or self._slider_dragging:
            return
        target = int(self._slider.GetValue()) * 1000
        try:
            if abs(target - int(controller.position_ms())) < 1500:
                return
            controller.seek(target)
        except Exception:  # noqa: BLE001 - nothing loaded
            return
        self._time.SetLabel(f"{_ms_text(target)} of {_ms_text(int(controller.length_ms()))}")

    def _on_slider_key(self, event: Any) -> None:
        """Left/Right five seconds, Page keys thirty, Home/End the ends, said in time."""
        key = event.GetKeyCode()
        steps = {
            wx.WXK_LEFT: -_NUDGE_MS,
            wx.WXK_RIGHT: _NUDGE_MS,
            wx.WXK_DOWN: -_NUDGE_MS,
            wx.WXK_UP: _NUDGE_MS,
            wx.WXK_PAGEDOWN: -_PAGE_MS,
            wx.WXK_PAGEUP: _PAGE_MS,
        }
        controller = self._controller()
        if controller is None:
            event.Skip()
            return
        try:
            length = int(controller.length_ms())
            position = int(controller.position_ms())
        except Exception:  # noqa: BLE001
            event.Skip()
            return
        if key in steps:
            target = max(0, min(length, position + steps[key]))
        elif key == wx.WXK_HOME:
            target = 0
        elif key == wx.WXK_END:
            target = max(0, length - 1000)
        else:
            event.Skip()
            return
        controller.seek(target)
        self._slider.SetValue(target // 1000)
        self._time.SetLabel(f"{_ms_text(target)} of {_ms_text(length)}")
        self._host._announce(_spoken(target))

    def _skip(self, delta_ms: int) -> None:
        controller = self._controller()
        if controller is None:
            return
        try:
            length = int(controller.length_ms())
            target = max(0, min(length, int(controller.position_ms()) + delta_ms))
        except Exception:  # noqa: BLE001
            return
        controller.seek(target)
        self._host._announce(_spoken(target))
        self.refresh()

    def _seek_from_notes(self, ms: int) -> None:
        controller = self._controller()
        show, episode = self._playing()
        if controller is None or episode is None:
            self._host._announce("Nothing is playing to move within.")
            return
        controller.seek(int(ms))
        self._host._announce(f"At {_spoken(ms)}.")

    # -- speed and volume ---------------------------------------------------------------

    def _on_speed(self) -> None:
        index = self._speed.GetSelection()
        if index == len(self._speeds):
            self._custom_speed()
            return
        if index < 0 or index >= len(self._speeds):
            return
        try:
            from quill.ui.podcasts.speed import apply_speed

            apply_speed(self._host, self._speeds[index])
        except Exception:  # noqa: BLE001 - said by apply_speed when it can
            return

    def _custom_speed(self) -> None:
        from quill.core.podcasts.models_settings import SPEED_MAX, SPEED_MIN

        dialog = wx.TextEntryDialog(
            self.frame,
            f"Speed, from {SPEED_MIN:g} to {SPEED_MAX:g} (1 is normal):",
            "Custom Speed",
            value=f"{self._speeds[max(0, self._speed.GetSelection() - 1)]:g}",
        )
        try:
            shower = getattr(self._host, "_show_modal_dialog", None)
            if shower is not None:
                answer = shower(dialog, "Custom Speed")
            else:
                from quill.ui.dialog_contract import show_modal_dialog

                answer = show_modal_dialog(dialog, "Custom Speed", announce=self._host._announce)
            raw = dialog.GetValue().strip().rstrip("xX")
        finally:
            dialog.Destroy()
        if answer != wx.ID_OK:
            self._refresh_speed()
            return
        try:
            value = float(raw)
        except ValueError:
            self._host._announce("That is not a speed.")
            self._refresh_speed()
            return
        from quill.ui.podcasts.speed import apply_speed

        apply_speed(self._host, value)
        self._refresh_speed()

    def _on_volume(self) -> None:
        controller = self._controller()
        if controller is None:
            return
        try:
            controller.set_volume(int(self._volume.GetValue()))
        except Exception:  # noqa: BLE001
            return
        self._host._announce(f"Volume {int(self._volume.GetValue())}")
        refresh = getattr(self._host, "_refresh_statusbar", None)
        if callable(refresh):
            refresh()

    # -- your note ----------------------------------------------------------------------

    def _episode_note_text(self) -> str:
        if self._note_key is None:
            return ""
        from quill.core.podcasts.episode_notes import episode_level_note, load_episode_notes

        note = episode_level_note(load_episode_notes(), *self._note_key)
        return note.text if note is not None else ""

    def _on_note_blur(self, event: Any) -> None:
        event.Skip()
        if self._note_key is None:
            return
        from quill.core.podcasts.episode_notes import set_episode_level_note

        text = self._note.GetValue().strip()
        try:
            changed = set_episode_level_note(self._note_key[0], self._note_key[1], text)
        except Exception:  # noqa: BLE001 - a note that cannot be written is said, not raised
            self._host._announce("Your note could not be saved.")
            return
        if changed:
            self._host._announce("Note saved." if text else "Note removed.")

    def _remember_copy_format(self, fmt: str) -> None:
        history = getattr(self._host, "_podcast_history", None)
        if history is None:
            return
        history.notes_copy_format = fmt
        saver = getattr(self._host, "_save_podcast_history", None)
        if callable(saver):
            saver()

    # -- the bottom row -----------------------------------------------------------------

    def _on_favorite(self) -> None:
        self._call("_on_favorite_toggle")
        show, _episode = self._playing()
        self._refresh_favorite(show)

    def _on_mark_played(self) -> None:
        self._call("podcast_mark_played_and_next")

    def _on_share(self) -> None:
        show, episode = self._playing()
        controller = self._controller()
        from quill.ui.podcasts.share_moment import share_moment

        position = int(controller.position_ms()) if controller is not None else 0
        share_moment(self._host, show, episode, position)

    # -- lifetime ---------------------------------------------------------------------------

    def show(self, *, focus: bool = True) -> None:
        self.refresh(full=True)
        if not self._tick.IsRunning():
            self._tick.Start(1000)
        if focus:
            self.frame.Show()
            self.frame.Raise()
            first = self._slider if self._slider.IsEnabled() else self._play
            wx.CallAfter(first.SetFocus)
        else:
            self.frame.Show()

    def hide(self) -> None:
        self._tick.Stop()
        self.frame.Hide()

    def _on_close(self, event: Any) -> None:
        """Hide rather than destroy, so the window keeps its number; the app's
        exit destroys the frame with everything else."""
        if getattr(self._host, "_exiting", False) or event.CanVeto() is False:
            self._tick.Stop()
            event.Skip()
            return
        event.Veto()
        self.hide()
        host = self._host
        windows = getattr(host, "_windows", None)
        if windows is not None:
            previous = windows.previous_key(self.frame)
            if previous:
                wx.CallAfter(windows.activate, previous)

    def destroy(self) -> None:
        self._tick.Stop()
        try:
            self.frame.Destroy()
        except Exception:  # noqa: BLE001 - already gone
            pass


def open_now_playing(host: Any, *, focus: bool = True) -> NowPlayingWindow:
    """Open, or raise, the host's Now Playing window (made once, hidden on close)."""
    window = getattr(host, "_now_playing_window", None)
    if window is None:
        window = NowPlayingWindow(host)
        host._now_playing_window = window
        _install_peer(host, window)
    window.show(focus=focus)
    return window


def _install_peer(host: Any, window: NowPlayingWindow) -> None:
    """Menu bar (its own Close, the shared Window menu), and the window list."""
    windows = getattr(host, "_windows", None)
    frame = window.frame
    menu_bar = wx.MenuBar()
    own = wx.Menu()
    close_id = wx.NewIdRef()
    own.Append(close_id, "&Close\tCtrl+W")
    frame.Bind(wx.EVT_MENU, lambda _e: frame.Close(), id=close_id)
    menu_bar.Append(own, "Now &Playing")
    if windows is not None:
        windows.install(frame, menu_bar)
    frame.SetMenuBar(menu_bar)
    keep = getattr(host, "_keep_menu_ids", None)
    if callable(keep):
        keep(close_id)
    if windows is not None:
        windows.register(frame, TITLE, focus=lambda: window._slider.SetFocus())
