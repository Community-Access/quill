"""Winamp classic-skin playback keys for the Quill Media Player (item 13).

The map itself lives in :mod:`quill.ui.radio.winamp_keys` and is deliberately
wx-free so a surface can adopt it without a second implementation. Quill Radio's
recordings list was the first, QUILL Cast the second
(:mod:`quill.ui.podcasts.winamp_mixin`), and the Media Player was the last
holdout -- which mattered, because it is the surface a Winamp user is *most*
likely to reach for: an audiobook player with a track list is a playlist
editor with a transport, which is exactly what the classic skin's main window
was.

The whole value of muscle memory is that it does not have to be relearned per
app, so the same ``Z X C V B``, the same arrow seeking, the same ``T`` /
``J`` / ``Ctrl+J`` / ``L`` answer here, with the same words spoken back.

Two meanings the Media Player gives the shared actions, both falling out of
what it plays rather than invented for it:

* **B / Z** step through the book's own track list (the chapter nodes that are
  separate files), because in an audiobook "next" means the next section.
  A book whose chapters are positions *inside one file* has no track list, so
  B and Z move by chapter instead -- the same intent against the other shape.
* **L (Open)** is Open File..., which is what Open means on a player whose
  content is files rather than a subscribed library.

Shift+V is stop-with-fade in Winamp; this engine has no fade, so it stops
cleanly rather than pretending, exactly as the other two surfaces do.

The letters are only claimed when no text field has focus -- the trap #1263
hit. The Media Player has no search box today, but the Bookmarks page can grow
one, and a letter binding that eats what is being typed is not a bug worth
discovering later.
"""

from __future__ import annotations

from typing import Any

from quill.ui.radio.winamp_keys import normalize_key_code, resolve_winamp_action

#: Arrow-key seek steps, matching the other two surfaces exactly.
_SEEK_SMALL_MS = 5_000
_SEEK_LARGE_MS = 30_000
_VOLUME_STEP = 5


class MediaWinampKeysMixin:
    """Winamp transport keys over the Media Player's track list."""

    # -- state the frame initialises -------------------------------------

    #: Whether T last chose "remaining" over "elapsed".
    _winamp_show_remaining: bool = False

    # -- dispatch ---------------------------------------------------------

    def _winamp_focus_is_text_entry(self) -> bool:
        """True when a text field has focus, so a letter must not be eaten."""
        import wx

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

    def _on_winamp_char_hook(self, event: Any) -> None:
        """The classic transport keys. Anything unmapped passes through."""
        import wx

        key = normalize_key_code(event.GetKeyCode(), wx)
        ctrl = bool(event.ControlDown())
        shift = bool(event.ShiftDown())
        alt = bool(event.AltDown())
        if not key or self._winamp_focus_is_text_entry():
            event.Skip()
            return
        # Ctrl+arrow volume predates the letter map and can never collide with
        # typing, so it is outside the opt-out.
        if ctrl and not shift and not alt and key in ("UP", "DOWN"):
            self._winamp_volume(up=key == "UP")
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
            wk.ACTION_BACK_5: lambda: self._winamp_seek(-_SEEK_SMALL_MS),
            wk.ACTION_FORWARD_5: lambda: self._winamp_seek(_SEEK_SMALL_MS),
            wk.ACTION_BACK_30: lambda: self._winamp_seek(-_SEEK_LARGE_MS),
            wk.ACTION_FORWARD_30: lambda: self._winamp_seek(_SEEK_LARGE_MS),
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
        """X: play, or resume what is paused."""
        if not self._player.has_media():
            self._announce("Open a file or a folder first.")
            return
        if self._player.is_playing():
            self._announce("Already playing")
            return
        self._player.play()
        self._announce("Playing")

    def _winamp_pause(self) -> None:
        """C: pause or unpause, and say which it was."""
        if not self._player.has_media():
            self._announce("Nothing is playing.")
            return
        was_playing = self._player.is_playing()
        self._player.toggle()
        self._announce("Paused" if was_playing else "Playing")

    def _winamp_stop(self) -> None:
        """V (and Shift+V): stop. No engine fade, so Shift+V stops cleanly."""
        if not self._player.has_media():
            self._announce("Nothing is playing.")
            return
        self._player.stop()
        self._announce("Stopped")

    def _winamp_open(self) -> None:
        """L: Open File... -- what Open means on a player of files."""
        self._on_open_file(None)

    def _winamp_step(self, direction: int) -> None:
        """B / Z: the next or previous track, or chapter for a single file.

        An audiobook that is one file per chapter has a real track list; one
        that is a single file with chapter marks has none, and stepping by
        chapter is the same intent against the other shape rather than a
        different feature.
        """
        tracks = list(self._playlist)
        if not tracks:
            self._winamp_step_chapter(direction)
            return
        target = self._playlist_index + direction
        if not (0 <= target < len(tracks)):
            self._announce(
                "Already at the last track." if direction > 0 else "Already at the first track."
            )
            return
        self._playlist_index = target
        title, payload = tracks[target]
        self._play_payload(payload, title, autoplay=True)
        self._announce(title)

    def _winamp_step_chapter(self, direction: int) -> None:
        if not self._chapters:
            self._announce("There is nothing to step through.")
            return
        if direction > 0:
            self._player.next_chapter()
        else:
            self._player.previous_chapter()

    def _winamp_seek(self, delta_ms: int) -> None:
        """Arrows: move along the timeline, and say where we landed."""
        if not self._player.has_media():
            self._announce("Nothing is playing.")
            return
        length = self._player.length_ms()
        target = max(0, self._player.playhead_ms() + delta_ms)
        if length > 0:
            target = min(length, target)
        self._player.seek_to(target)
        self._announce(self._winamp_position_text())

    def _winamp_volume(self, *, up: bool) -> None:
        step = _VOLUME_STEP if up else -_VOLUME_STEP
        self._announce(f"Volume {self._player.set_volume(self._player.volume() + step)}")

    # -- position ---------------------------------------------------------

    def _winamp_toggle_time(self) -> None:
        """T: flip between elapsed and remaining, and say the new reading."""
        self._winamp_show_remaining = not self._winamp_show_remaining
        self._announce(self._winamp_position_text())

    def _winamp_position_text(self) -> str:
        """Spoken as words, never as a clock face.

        ``1:05:00`` read aloud is a time of day; "1 hour 5 minutes" is a
        duration. Same rule as the chapter list and Cast's own announcements.
        """
        from quill.core.media import format_spoken

        if not self._player.has_media():
            return "Nothing is playing."
        position = self._player.playhead_ms()
        length = self._player.length_ms()
        if self._winamp_show_remaining and length > 0:
            return f"{format_spoken(max(0, length - position))} remaining"
        if length > 0:
            return f"{format_spoken(position)} of {format_spoken(length)}"
        return format_spoken(position)

    def _winamp_jump_to_time(self) -> None:
        """Ctrl+J: the shared Go to Position dialog.

        The Media Player already had this on Ctrl+G, built to the desktop
        accessibility checklist (labelled H/M/S spin controls plus a timecode
        field). Ctrl+J is the Winamp muscle memory for the same thing, so it
        opens the same dialog rather than a second, lesser prompt.
        """
        self._on_go_to_position(None)

    def _winamp_jump_to_file(self) -> None:
        """J: type part of a title and land on the first track that matches."""
        import wx

        from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

        tracks = list(self._playlist)
        if not tracks:
            self._announce("There are no tracks to jump to.")
            return
        with wx.TextEntryDialog(
            self.frame,
            "Jump to which track? Type any part of its title.",
            "Jump to File",
        ) as dialog:
            apply_modal_ids(dialog)
            if show_modal_dialog(dialog, "Jump to File", announce=self._announce) != wx.ID_OK:
                return
            needle = dialog.GetValue().strip().casefold()
        if not needle:
            return
        for index, (title, payload) in enumerate(tracks):
            if needle in title.casefold():
                self._playlist_index = index
                self._play_payload(payload, title, autoplay=True)
                self._announce(title)
                return
        self._announce(f"No track matches {needle}.")


__all__ = ["MediaWinampKeysMixin"]
