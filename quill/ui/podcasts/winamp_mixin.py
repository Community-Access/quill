"""Winamp classic-skin playback keys for QUILL Cast (#1344, extended).

The map itself lives in :mod:`quill.ui.radio.winamp_keys` and is deliberately
wx-free so a second surface can adopt it without a second implementation.
This is that second surface: the same ``Z X C V B`` bottom row, the same
arrow seeking, the same ``J`` / ``Ctrl+J`` / ``T``, dispatched against a
podcast episode list instead of a recordings list.

Keeping one map matters more here than it looks. Somebody who came through
Winamp has these in their fingers, and the whole value of muscle memory is
that it does not have to be relearned per app -- so Quill Radio's recordings
player, QUILL Cast, and anything that adopts this next all answer to the same
letters, with the same words spoken back.

Two Cast-specific meanings, both natural rather than invented:

* **B / Z** step through the episode list you are looking at, and fall back
  to the Play Queue when nothing is selected -- "next" in a podcast app means
  the next episode, and the queue is the app's own opinion about which that is.
* **L (Open)** plays the selected episode, which is what Open means when the
  thing selected is already in your library.

Shift+V is stop-with-fade in Winamp; neither engine here has a fade, so it
stops cleanly rather than pretending, exactly as the recordings player does.

The host supplies four small hooks (:meth:`_winamp_rows` and friends) so this
works over a ``wx.ListCtrl`` of episodes and over the standalone app's tree
without either one leaking into the other.
"""

from __future__ import annotations

from quill.ui.radio.winamp_keys import normalize_key_code, resolve_winamp_action


class CastWinampKeysMixin:
    """Winamp transport keys over a podcast episode list."""

    # -- hooks the host provides -----------------------------------------

    def _winamp_rows(self) -> list[tuple[object, object]]:
        """``(show, episode)`` for the list currently on screen."""
        return []

    def _winamp_selected_index(self) -> int:
        return -1

    def _winamp_select_index(self, index: int) -> None:
        return None

    def _winamp_play_pair(self, show: object, episode: object) -> None:
        return None

    def _winamp_controller(self) -> object | None:
        return getattr(self, "_controller", None)

    def _winamp_parent_window(self) -> object:
        return getattr(self, "dialog", None) or getattr(self, "frame", None)

    def _winamp_keys_enabled(self) -> bool:
        """Whether the letter keys are live (Preferences, default on).

        Every letter the map binds is otherwise unused on these surfaces, so
        on is the right default; the checkbox exists for anyone who would
        rather have the letters back for list typeahead.
        """
        return True

    def _winamp_wx(self):
        """The wx module. Dialogs here keep it on ``self._wx``; the app frame
        does not, and a key handler is not the place to require one -- so this
        falls back to a plain import rather than raising on a keystroke."""
        wx = getattr(self, "_wx", None)
        if wx is not None:
            return wx
        import wx as wx_module

        return wx_module

    # -- dispatch ---------------------------------------------------------

    def _winamp_focus_is_text_entry(self) -> bool:
        """True when a text field has focus, so a letter must not be eaten.

        The trap #1263 hit: a letter binding that swallows what is being
        typed. Cast's surfaces do have text fields (search, URL entry), so
        this is not theoretical here the way it was for the recordings list.
        """
        wx = self._winamp_wx()
        try:
            focused = wx.Window.FindFocus()
        except Exception:  # noqa: BLE001 - no focus is not a text entry
            return False
        if focused is None:
            return False
        for name in ("TextCtrl", "ComboBox", "SearchCtrl", "SpinCtrl", "Choice"):
            control = getattr(wx, name, None)
            if control is not None and isinstance(focused, control):
                return True
        return False

    def _on_winamp_char_hook(self, event: object) -> None:
        """The classic transport keys. Anything unmapped passes through."""
        wx = self._winamp_wx()
        code = event.GetKeyCode()
        ctrl = bool(event.ControlDown())
        shift = bool(event.ShiftDown())
        alt = bool(event.AltDown())
        key = normalize_key_code(code, wx)
        if not key or self._winamp_focus_is_text_entry():
            event.Skip()
            return
        # Ctrl+arrow volume is not part of the opt-out: it predates the letter
        # map and can never collide with typing.
        if ctrl and not shift and not alt and key in ("UP", "DOWN"):
            self._winamp_volume(up=key == "UP")
            return
        if not self._winamp_keys_enabled():
            event.Skip()
            return
        action = resolve_winamp_action(key, ctrl=ctrl, shift=shift, alt=alt)
        if action is None:
            event.Skip()
            return
        self._run_winamp_action(action)

    def _run_winamp_action(self, action: str) -> None:
        from quill.ui.radio import winamp_keys as wk

        handlers = {
            wk.ACTION_PLAY: self._winamp_play,
            wk.ACTION_PAUSE: self._winamp_pause,
            wk.ACTION_STOP: self._winamp_stop,
            wk.ACTION_STOP_FADE: self._winamp_stop,
            wk.ACTION_NEXT: lambda: self._winamp_step(1),
            wk.ACTION_PREVIOUS: lambda: self._winamp_step(-1),
            wk.ACTION_BACK_5: lambda: self._winamp_seek(-5_000),
            wk.ACTION_FORWARD_5: lambda: self._winamp_seek(5_000),
            wk.ACTION_BACK_30: lambda: self._winamp_seek(-30_000),
            wk.ACTION_FORWARD_30: lambda: self._winamp_seek(30_000),
            wk.ACTION_TOGGLE_TIME: self._winamp_toggle_time,
            wk.ACTION_JUMP_TO_TIME: self._winamp_jump_to_time,
            wk.ACTION_JUMP_TO_FILE: self._winamp_jump_to_file,
            wk.ACTION_OPEN: self._winamp_open,
        }
        handler = handlers.get(action)
        if handler is not None:
            handler()

    # -- transport --------------------------------------------------------

    def _winamp_play(self) -> None:
        """X: resume what is paused, or start what is selected."""
        from quill.ui.podcasts.player_controller import PodcastPlayerState

        controller = self._winamp_controller()
        if controller is None:
            return
        if controller.state.state is PodcastPlayerState.PAUSED:
            controller.toggle_play_pause()
            self._announce("Playing")
            return
        if controller.state.state is PodcastPlayerState.PLAYING:
            self._announce("Already playing")
            return
        self._winamp_open()

    def _winamp_pause(self) -> None:
        from quill.ui.podcasts.player_controller import PodcastPlayerState

        controller = self._winamp_controller()
        if controller is None or controller.state.state not in (
            PodcastPlayerState.PLAYING,
            PodcastPlayerState.PAUSED,
        ):
            self._announce("Nothing is playing.")
            return
        controller.toggle_play_pause()
        self._announce(
            "Paused" if controller.state.state is PodcastPlayerState.PAUSED else "Playing"
        )

    def _winamp_stop(self) -> None:
        """V (and Shift+V): stop. Neither engine has a fade, so Shift+V stops
        cleanly rather than pretending to fade out."""
        controller = self._winamp_controller()
        if controller is None:
            return
        controller.stop()
        self._announce("Stopped")

    def _winamp_open(self) -> None:
        """L: play whatever is selected."""
        rows = self._winamp_rows()
        index = self._winamp_selected_index()
        if not (0 <= index < len(rows)):
            self._announce("Select an episode first.")
            return
        show, episode = rows[index]
        self._winamp_play_pair(show, episode)

    def _winamp_step(self, direction: int) -> None:
        """B / Z: the next or previous episode in the list you are looking at.

        With nothing selected, B falls through to the Play Queue -- in a
        podcast app the queue is the app's own answer to "what is next", and
        ignoring it would make the key mean less than it should.
        """
        rows = self._winamp_rows()
        index = self._winamp_selected_index()
        if not rows or index < 0:
            if direction > 0:
                self._winamp_play_from_queue()
            else:
                self._announce("There is no previous episode here.")
            return
        target = index + direction
        if not (0 <= target < len(rows)):
            self._announce(
                "Already at the last episode." if direction > 0 else "Already at the first episode."
            )
            return
        self._winamp_select_index(target)
        show, episode = rows[target]
        self._winamp_play_pair(show, episode)

    def _winamp_play_from_queue(self) -> None:
        from quill.core.podcasts.queue import pop_next_playable

        library = getattr(self, "_library", None) or getattr(self, "_podcast_library", None)
        if library is None:
            self._announce("There is nothing queued.")
            return
        resolved = pop_next_playable(library)
        if resolved is None:
            self._announce("The Play Queue is empty.")
            return
        show, episode = resolved
        self._winamp_play_pair(show, episode)

    def _winamp_seek(self, delta_ms: int) -> None:
        controller = self._winamp_controller()
        if controller is None or controller.state.show_id is None:
            self._announce("Nothing is playing.")
            return
        length = controller.length_ms()
        target = max(0, controller.position_ms() + delta_ms)
        if length > 0:
            target = min(length, target)
        controller.seek(target)
        self._announce(self._winamp_position_text())

    def _winamp_volume(self, *, up: bool) -> None:
        controller = self._winamp_controller()
        if controller is None:
            return
        controller.set_volume(controller.volume_percent + (5 if up else -5))
        self._announce(f"Volume {controller.volume_percent}")

    # -- position ---------------------------------------------------------

    def _winamp_toggle_time(self) -> None:
        """T: flip between elapsed and remaining, and say the new reading."""
        self._winamp_show_remaining = not getattr(self, "_winamp_show_remaining", False)
        self._announce(self._winamp_position_text())

    def _winamp_position_text(self) -> str:
        controller = self._winamp_controller()
        if controller is None or controller.state.show_id is None:
            return "Nothing is playing."
        position = controller.position_ms()
        length = controller.length_ms()
        if getattr(self, "_winamp_show_remaining", False) and length > 0:
            return f"minus {_clock(max(0, length - position))}"
        return _clock(position) if length <= 0 else f"{_clock(position)} of {_clock(length)}"

    def _winamp_jump_to_time(self) -> None:
        """Ctrl+J: type 90, 1:30, or 1:02:03 and land there."""
        from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
        from quill.ui.radio.winamp_keys import parse_time_to_ms

        wx = self._winamp_wx()
        controller = self._winamp_controller()
        if controller is None or controller.state.show_id is None:
            self._announce("Nothing is playing to jump within.")
            return
        with wx.TextEntryDialog(
            self._winamp_parent_window(),
            "Jump to which time? Type seconds, or minutes and seconds like 1:30.",
            "Jump to Time",
        ) as dialog:
            apply_modal_ids(dialog)
            if show_modal_dialog(dialog, "Jump to Time", announce=self._announce) != wx.ID_OK:
                return
            raw = dialog.GetValue()
        target = parse_time_to_ms(raw)
        if target is None:
            self._announce(f"{raw!r} is not a time.")
            return
        length = controller.length_ms()
        if length > 0 and target > length:
            self._announce("That is past the end of this episode.")
            return
        controller.seek(target)
        self._announce(self._winamp_position_text())

    def _winamp_jump_to_file(self) -> None:
        """J: type part of a title and land on the first episode that matches."""
        from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

        wx = self._winamp_wx()
        rows = self._winamp_rows()
        if not rows:
            self._announce("There are no episodes to jump to.")
            return
        with wx.TextEntryDialog(
            self._winamp_parent_window(),
            "Jump to which episode? Type any part of its title.",
            "Jump to Episode",
        ) as dialog:
            apply_modal_ids(dialog)
            if show_modal_dialog(dialog, "Jump to Episode", announce=self._announce) != wx.ID_OK:
                return
            needle = dialog.GetValue().strip().casefold()
        if not needle:
            return
        for index, (show, episode) in enumerate(rows):
            haystack = f"{episode.title} {show.title}".casefold()
            if needle in haystack:
                self._winamp_select_index(index)
                self._announce(f"{episode.title}, {show.title}")
                return
        self._announce(f"No episode matches {needle}.")


def _clock(ms: int) -> str:
    total = max(0, int(ms)) // 1000
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"
