"""Internet Radio > Recordings... -- everything you've recorded, live.

One list for the whole recording life cycle, shared by embedded QUILL and
standalone Quill Radio: the recording being written right now (status
"Recording", size and elapsed growing on the refresh), every finished file
in the recordings folder ("Recorded", newest first), and upcoming scheduled
recordings ("Scheduled", with their time and timezone). Play any finished
recording through the shared radio player (which also silences anything else
playing), stop the active recording, reveal a file in Explorer, or remove
it -- all keyboard-first and announced.

R1/quill-radio #8: the list refreshes as an *in-place diff* keyed by stable
identity (the file path for recorded/recording rows, ``schedule:<id>`` for
scheduled ones). It never tears the list down and rebuilds it, so a screen
reader never loses its place or hears the whole list re-announced every two
seconds -- only the cells that actually changed (the active row's size and
elapsed, a status flip Recording -> Recorded) are touched, and selection,
focus, and scroll are preserved by identity. The timer always runs; the old
focus-pause workaround is gone because there is no teardown rebuild to pause.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from typing import Any

from quill.core.radio.models import RadioStation
from quill.core.radio.recordings_index import (
    STATUS_COMPLETED,
    STATUS_RECORDED,
    STATUS_RECORDING,
    STATUS_SCHEDULED,
    ActiveRecording,
    RecordingEntry,
    format_elapsed,
    list_recordings,
    recordings_dir,
)
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

_REFRESH_MS = 2000


class RecordingsManagerDialog:
    """List, play, stop, reveal, and remove radio recordings."""

    def __init__(
        self,
        parent: object,
        *,
        recorder: object,
        settings: object,
        scheduler: object,
        controller: object,
        announce_cb: Callable[[str], None] | None = None,
        history: object | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._recorder = recorder
        self._settings = settings
        self._scheduler = scheduler
        self._controller = controller
        self._history = history
        self._announce = announce_cb or (lambda _m: None)
        self._entries: list[RecordingEntry] = []
        #: #1344: whether T reads out time remaining rather than time elapsed.
        self._speak_remaining = False

        self.dialog = wx.Dialog(
            parent,
            title="Radio Recordings",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((760, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(self.dialog, label="&Recordings (made, in progress, and scheduled)"),
            0,
            wx.LEFT | wx.TOP,
            10,
        )
        self._list = wx.ListCtrl(self.dialog, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._list.SetName(
            "Recordings; the row's status column reads Recording, Recorded, "
            "Scheduled, or Completed. Enter plays a finished recording, Delete "
            "removes it. Winamp keys: X play, C pause, V stop, B next, Z "
            "previous, arrows seek, J jump to file"
        )
        self._list.InsertColumn(0, "Name", width=280)
        self._list.InsertColumn(1, "Status", width=100)
        self._list.InsertColumn(2, "Size", width=100)
        self._list.InsertColumn(3, "When", width=220)
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._play_btn = self._button(buttons, "&Play", self._on_play, "Play this recording")
        self._stop_btn = self._button(
            buttons,
            "&Stop Recording",
            self._on_stop_recording,
            "Finish the selected recording being written right now",
        )
        # Stop All is only shown/enabled when two or more recordings are running
        # at once (concurrent recording) -- it stays out of the way for the
        # common single-recording case.
        self._stop_all_btn = self._button(
            buttons,
            "Stop A&ll Recordings",
            self._on_stop_all_recordings,
            "Finish every recording being written right now",
        )
        self._open_btn = self._button(
            buttons, "&Open in Folder", self._on_open_in_folder, "Show this file in Explorer"
        )
        self._remove_btn = self._button(
            buttons, "&Remove...", self._on_remove, "Delete this recording file"
        )
        self._button(buttons, "Re&fresh", self._on_refresh_button, "Reload the recordings list now")
        buttons.AddStretchSpacer()
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close (recordings continue)")
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        # Stop All starts hidden; the first refresh reveals it only when two or
        # more recordings are running (concurrent recording).
        self._stop_all_btn.Show(False)

        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda _e: self._on_selection_changed())
        self._list.Bind(wx.EVT_LIST_ITEM_DESELECTED, lambda _e: self._on_selection_changed())
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self._on_play())
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_key)
        # Ctrl+Up/Down adjusts playback volume from anywhere in this modal dialog
        # -- a played recording runs through the same controller/engine as live
        # radio, so it can be turned down just like a live stream (the modal
        # otherwise hides the Playback menu's volume shortcuts).
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

        # Live status: the active row's size and elapsed grow and a Recording
        # flips to Recorded without a manual refresh. The in-place diff means
        # this never rebuilds the list out from under a screen reader -- only
        # the changed cells move -- so the timer always runs (R1).
        self._timer = wx.Timer(self.dialog)
        self.dialog.Bind(wx.EVT_TIMER, lambda _e: self._refresh())
        self._timer.Start(_REFRESH_MS)
        self.dialog.Bind(wx.EVT_CLOSE, self._on_close)

        self._refresh()

    def _button(self, sizer: Any, label: str, handler: Callable[[], None], name: str) -> Any:
        wx = self._wx
        button = wx.Button(self.dialog, label=label)
        button.SetName(name)
        button.Bind(wx.EVT_BUTTON, lambda _e: handler())
        sizer.Add(button, 0, wx.RIGHT, 6)
        return button

    def show(self) -> None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=wx.ID_CANCEL)
        try:
            show_modal_dialog(self.dialog, "Radio Recordings", announce=self._announce)
        finally:
            self._timer.Stop()
            self.dialog.Destroy()

    def _on_close(self, event: Any) -> None:
        self._timer.Stop()
        event.Skip()

    def _on_refresh_button(self) -> None:
        """Manual Refresh keeps the selection (R1/9 -- never jumps to top)."""
        self._refresh(keep_selection=True)

    # -- data -------------------------------------------------------------------

    def _active_recordings(self) -> list[ActiveRecording]:
        """Every recording being written right now, by identity (R1/10.3,
        concurrent recording), oldest first -- so each shows as its own
        "Recording" row even in a temp dir and its firing schedule is not also
        double-listed as "Scheduled".
        """
        rec = self._recorder
        jobs = getattr(rec, "active_jobs", None)
        if callable(jobs):
            return [
                ActiveRecording(
                    path=getattr(j, "destination", None),
                    station_name=getattr(j, "station_name", "") or "",
                    stream_url=getattr(j, "stream_url", "") or "",
                    started_at=getattr(j, "started_at", None),
                    job_id=getattr(j, "job_id", "") or "",
                )
                for j in jobs()
            ]
        # Back-compat with a recorder exposing only the old scalar getters.
        if not bool(getattr(rec, "is_recording", False)):
            return []
        return [
            ActiveRecording(
                path=getattr(rec, "current_destination", None),
                station_name=getattr(rec, "current_station_name", "") or "",
                stream_url=getattr(rec, "current_stream_url", "") or "",
                started_at=getattr(rec, "current_started_at", None),
            )
        ]

    def _cells(self, entry: RecordingEntry) -> tuple[str, str, str, str]:
        """The four column strings for *entry* (used by both the diff and the
        no-op fast path, so they always agree)."""
        if entry.status == STATUS_RECORDING and entry.started_at is not None:
            when = f"elapsed {format_elapsed(entry.started_at)}"
        elif entry.modified is not None:
            when = entry.modified.strftime("%Y-%m-%d %H:%M")
        else:
            when = entry.detail
        return (entry.name, entry.status, entry.size_display, when)

    def _set_row(self, row: int, entry: RecordingEntry) -> None:
        """Update row *row* in place to match *entry* (R1 -- no rebuild)."""
        name, status, size, when = self._cells(entry)
        self._list.SetItem(row, 0, name)
        self._list.SetItem(row, 1, status)
        self._list.SetItem(row, 2, size)
        self._list.SetItem(row, 3, when)

    def _snapshot_unchanged(self, snapshot: list[RecordingEntry]) -> bool:
        """True when *snapshot* is cell-for-cell identical to what is shown.

        The no-op fast path: when nothing changed (the common tick), the list
        is not touched at all -- no SetItem, no Select, no focus event -- so a
        screen reader reading a row never has it shift or re-announce.
        """
        if len(snapshot) != len(self._entries):
            return False
        for new, old in zip(snapshot, self._entries, strict=True):
            if new.id != old.id:
                return False
            if self._cells(new) != self._cells(old):
                return False
        return True

    def _refresh(self, keep_selection: bool = True) -> None:
        snapshot = list_recordings(
            self._settings,
            active=self._active_recordings(),
            scheduled=list(getattr(self._scheduler, "entries", []) or []),
        )
        # No-op fast path: identical content means zero list mutation, so the
        # cursor and the screen reader's place are never disturbed (R1/9).
        if self._snapshot_unchanged(snapshot):
            self._entries = snapshot
            return

        selected_id: str | None = None
        if keep_selection:
            index = self._list.GetFirstSelected()
            if 0 <= index < len(self._entries):
                selected_id = self._entries[index].id
        top = self._list.GetTopItem() if self._list.GetItemCount() else 0

        new_count = len(snapshot)
        old_count = len(self._entries)
        for row in range(min(new_count, old_count)):
            self._set_row(row, snapshot[row])
        if new_count > old_count:
            for row in range(old_count, new_count):
                self._list.InsertItem(row, snapshot[row].name)
                self._set_row(row, snapshot[row])
        elif new_count < old_count:
            for row in range(old_count - 1, new_count - 1, -1):
                self._list.DeleteItem(row)
        self._entries = snapshot

        self._update_status_label()

        # Restore selection by identity. A status flip Recording -> Recorded
        # keeps the same path identity, so the cursor stays on the same row
        # instead of yanking to the top (the original 9/10.1 symptom). When the
        # selected row is genuinely gone (file removed), nothing is forced.
        if selected_id is not None:
            for row, entry in enumerate(snapshot):
                if entry.id == selected_id:
                    self._list.Select(row)
                    self._list.Focus(row)
                    break
        # Best-effort scroll preservation.
        if snapshot and top:
            try:
                self._list.EnsureVisible(min(top, len(snapshot) - 1))
            except Exception:  # noqa: BLE001 - scroll preservation is best-effort
                pass
        self._on_selection_changed()

    def _update_status_label(self) -> None:
        recorded = sum(1 for e in self._entries if e.status == STATUS_RECORDED)
        active = sum(1 for e in self._entries if e.status == STATUS_RECORDING)
        scheduled = sum(1 for e in self._entries if e.status == STATUS_SCHEDULED)
        completed = sum(1 for e in self._entries if e.status == STATUS_COMPLETED)
        parts = [f"{recorded} recorded", f"{active} recording now", f"{scheduled} scheduled"]
        if completed:
            parts.append(f"{completed} completed")
        self._status.SetLabel(", ".join(parts) + f" -- in {recordings_dir(self._settings)}")

    def _selected(self) -> RecordingEntry | None:
        index = self._list.GetFirstSelected()
        if 0 <= index < len(self._entries):
            return self._entries[index]
        return None

    def _is_entry_playing(self, entry: RecordingEntry | None) -> bool:
        from quill.ui.radio.player_controller import RadioPlayerState

        if entry is None or entry.path is None:
            return False
        state = self._controller.state
        return (
            state.station is not None
            and state.station.stream_url == str(entry.path)
            and state.state in (RadioPlayerState.PLAYING, RadioPlayerState.CONNECTING)
        )

    def _on_selection_changed(self) -> None:
        entry = self._selected()
        is_file = entry is not None and entry.path is not None
        is_done = is_file and entry is not None and entry.status == STATUS_RECORDED
        is_active_row = entry is not None and entry.status == STATUS_RECORDING
        playing = self._is_entry_playing(entry)
        self._play_btn.Enable(bool(is_done))
        self._play_btn.SetLabel("&Stop" if playing else "&Play")
        self._play_btn.SetName("Stop this recording" if playing else "Play this recording")
        self._open_btn.Enable(bool(is_file))
        self._remove_btn.Enable(bool(is_done))
        # Stop targets the selected Recording row; Stop All appears only when two
        # or more recordings are running (concurrent recording).
        active = sum(1 for e in self._entries if e.status == STATUS_RECORDING)
        self._stop_btn.Enable(bool(is_active_row))
        self._stop_all_btn.Show(active >= 2)
        self._stop_all_btn.Enable(active >= 2)

    # -- Winamp classic-skin playback keys (#1344) --------------------------------

    def _winamp_keys_enabled(self) -> bool:
        """Whether the classic-skin letter keys are live (Preferences, default on).

        Everything the map binds is otherwise unused in this dialog, so on is
        the right default; the checkbox exists for anyone who wants the letters
        back for list typeahead.
        """
        return bool(getattr(getattr(self, "_history", None), "winamp_playback_keys", True))

    def _focus_is_text_entry(self) -> bool:
        """True when a text field has focus, so a letter key must not be eaten.

        The trap #1263 hit: a global letter binding that swallows what the user
        is typing. This dialog has no text field today, but a future one (or a
        child control that reports as an entry) must not be broken by a key map.
        """
        wx = self._wx
        try:
            focused = wx.Window.FindFocus()
        except Exception:  # noqa: BLE001 - no focus is not a text entry
            return False
        if focused is None:
            return False
        for name in ("TextCtrl", "ComboBox", "SearchCtrl", "SpinCtrl"):
            control = getattr(wx, name, None)
            if control is not None and isinstance(focused, control):
                return True
        return False

    def _on_char_hook(self, event: object) -> None:
        """The Winamp classic transport keys, plus Ctrl+Up/Ctrl+Down for volume.

        A played recording runs through the same controller/engine as live
        radio, so it can be driven -- and turned down -- like a live stream (the
        modal otherwise hides the Playback menu's shortcuts). Anything the map
        does not claim passes through untouched.
        """
        from quill.ui.radio.winamp_keys import normalize_key_code, resolve_winamp_action

        wx = self._wx
        code = event.GetKeyCode()
        ctrl = bool(event.ControlDown())
        shift = bool(event.ShiftDown())
        alt = bool(event.AltDown())
        key = normalize_key_code(code, wx)
        # Volume is not part of the opt-out: it predates #1344 and Ctrl+arrow can
        # never collide with typing.
        if ctrl and not shift and not alt and key in ("UP", "DOWN"):
            self._adjust_volume(up=key == "UP")
            return
        if not key or not self._winamp_keys_enabled() or self._focus_is_text_entry():
            event.Skip()
            return
        action = resolve_winamp_action(key, ctrl=ctrl, shift=shift, alt=alt)
        if action is None:
            event.Skip()
            return
        self._run_winamp_action(action)

    def _run_winamp_action(self, action: str) -> None:
        from quill.ui.radio import winamp_keys as wk

        handlers: dict[str, Callable[[], None]] = {
            wk.ACTION_PLAY: self._winamp_play,
            wk.ACTION_PAUSE: self._winamp_pause,
            wk.ACTION_STOP: lambda: self._winamp_stop("Stopped"),
            wk.ACTION_STOP_FADE: lambda: self._winamp_stop("Stopped"),
            wk.ACTION_NEXT: lambda: self._winamp_step(1),
            wk.ACTION_PREVIOUS: lambda: self._winamp_step(-1),
            wk.ACTION_BACK_5: lambda: self._winamp_seek(-5_000),
            wk.ACTION_FORWARD_5: lambda: self._winamp_seek(5_000),
            wk.ACTION_BACK_30: lambda: self._winamp_seek(-30_000),
            wk.ACTION_FORWARD_30: lambda: self._winamp_seek(30_000),
            wk.ACTION_TOGGLE_TIME: self._winamp_toggle_time,
            wk.ACTION_JUMP_TO_TIME: self._winamp_jump_to_time,
            wk.ACTION_JUMP_TO_FILE: self._winamp_jump_to_file,
            wk.ACTION_OPEN: self._on_play,
        }
        handler = handlers.get(action)
        if handler is not None:
            handler()

    def _playable_rows(self) -> list[int]:
        """Row indexes of finished recordings -- what B and Z move between."""
        return [
            row
            for row, entry in enumerate(self._entries)
            if entry.status == STATUS_RECORDED and entry.path is not None
        ]

    def _winamp_play(self) -> None:
        """X: play the selected recording, or resume a paused one."""
        from quill.ui.radio.player_controller import RadioPlayerState

        state = getattr(self._controller, "state", None)
        if state is not None and state.state is RadioPlayerState.PAUSED:
            self._controller.toggle_play_pause()
            self._announce("Playing")
            return
        entry = self._selected()
        if entry is None or entry.path is None or entry.status != STATUS_RECORDED:
            self._announce("Select a finished recording to play.")
            return
        if self._is_entry_playing(entry):
            self._announce(f"Already playing {entry.name}")
            return
        self._on_play()

    def _winamp_pause(self) -> None:
        """C: pause or unpause, and say which it was."""
        from quill.ui.radio.player_controller import RadioPlayerState

        state = getattr(self._controller, "state", None)
        if state is None or state.state not in (RadioPlayerState.PLAYING, RadioPlayerState.PAUSED):
            self._announce("Nothing is playing.")
            return
        was_playing = state.state is RadioPlayerState.PLAYING
        self._controller.toggle_play_pause()
        self._announce("Paused" if was_playing else "Playing")

    def _winamp_stop(self, message: str) -> None:
        """V (and Shift+V): stop playback. The engine has no fade, so Shift+V
        stops cleanly rather than pretending to fade."""
        self._controller.stop()
        self._announce(message)
        self._on_selection_changed()

    def _winamp_step(self, direction: int) -> None:
        """B / Z: move to the next or previous finished recording and play it."""
        rows = self._playable_rows()
        if not rows:
            self._announce("There are no finished recordings to play.")
            return
        current = self._list.GetFirstSelected()
        if current in rows:
            index = rows.index(current) + direction
        else:
            index = 0 if direction > 0 else len(rows) - 1
        if index < 0 or index >= len(rows):
            self._announce(
                "This is the last recording." if direction > 0 else "This is the first recording."
            )
            return
        row = rows[index]
        self._list.Select(row)
        self._list.Focus(row)
        entry = self._entries[row]
        station = RadioStation(name=entry.name, stream_url=str(entry.path))
        self._controller.play_station(station)
        self._announce(f"Playing recording {entry.name}")
        self._on_selection_changed()

    def _winamp_seek(self, delta_ms: int) -> None:
        """Arrows: move along the recording's timeline, and say where we landed."""
        from quill.ui.radio.bounded_playback_ui import spoken_duration

        if not self._controller.is_seekable():
            self._announce("There is nothing to seek through right now.")
            return
        self._controller.skip_by(delta_ms)
        self._announce(spoken_duration(self._controller.position_ms()))

    def _spoken_position(self) -> str:
        """Elapsed or remaining, whichever T last selected."""
        from quill.ui.radio.bounded_playback_ui import spoken_duration

        position = self._controller.position_ms()
        total = self._controller.duration_ms()
        if self._speak_remaining and total:
            return f"{spoken_duration(max(0, total - position))} remaining"
        return f"{spoken_duration(position)} elapsed"

    def _winamp_toggle_time(self) -> None:
        """T: elapsed <-> remaining.

        Winamp puts this on Ctrl+T, which Quill Radio already uses for What's
        Playing -- the more valuable meaning, so it keeps the key and the time
        toggle moves to plain T (documented in CONTROL_REFERENCE.md).
        """
        if not self._controller.is_seekable():
            self._announce("There is no timeline to read right now.")
            return
        self._speak_remaining = not self._speak_remaining
        self._announce(self._spoken_position())

    def _winamp_jump_to_time(self) -> None:
        """Ctrl+J: type a position (90, 1:30, or 1:02:03) and go there."""
        from quill.ui.radio.winamp_keys import parse_time_to_ms

        wx = self._wx
        if not self._controller.is_seekable():
            self._announce("There is nothing to seek through right now.")
            return
        with wx.TextEntryDialog(
            self.dialog,
            "Jump to which position? Type seconds, or minutes and seconds "
            "separated by a colon (for example 1:30).",
            "Jump to Time",
        ) as dialog:
            apply_modal_ids(dialog)
            if show_modal_dialog(dialog, "Jump to Time", announce=self._announce) != wx.ID_OK:
                return
            typed = dialog.GetValue()
        target = parse_time_to_ms(typed)
        if target is None:
            self._announce("That is not a time. Try 90, or 1:30.")
            return
        self._controller.seek_to(target)
        self._announce(self._spoken_position())

    def _winamp_jump_to_file(self) -> None:
        """J: type part of a name and land on the first recording that matches."""
        wx = self._wx
        if not self._entries:
            self._announce("There are no recordings to jump to.")
            return
        with wx.TextEntryDialog(
            self.dialog,
            "Jump to which recording? Type any part of its name.",
            "Jump to File",
        ) as dialog:
            apply_modal_ids(dialog)
            if show_modal_dialog(dialog, "Jump to File", announce=self._announce) != wx.ID_OK:
                return
            needle = dialog.GetValue().strip().lower()
        if not needle:
            return
        for row, entry in enumerate(self._entries):
            if needle in entry.name.lower():
                self._list.Select(row)
                self._list.Focus(row)
                self._list.EnsureVisible(row)
                self._announce(f"{entry.name}, {entry.status}")
                self._on_selection_changed()
                return
        self._announce(f"No recording matches {needle}.")

    def _adjust_volume(self, *, up: bool) -> None:
        """Step the shared radio volume (recording playback runs through the same
        controller/engine as live radio) and announce the new level."""
        if up:
            self._controller.volume_up()
        else:
            self._controller.volume_down()
        state = getattr(self._controller, "state", None)
        if state is not None:
            self._announce(f"Volume {state.volume_percent}")

    # -- actions ------------------------------------------------------------------

    def _on_play(self) -> None:
        entry = self._selected()
        if entry is None or entry.path is None:
            return
        if entry.status == STATUS_RECORDING:
            self._announce("Still recording; stop it first to play it.")
            return
        # One button, honest label: while this recording plays it reads Stop.
        if self._is_entry_playing(entry):
            self._controller.stop()
            self._announce("Playback stopped")
        else:
            station = RadioStation(name=entry.name, stream_url=str(entry.path))
            self._controller.play_station(station)
            self._announce(f"Playing recording {entry.name}")
        self._on_selection_changed()

    def _on_stop_recording(self) -> None:
        entry = self._selected()
        if entry is None or entry.status != STATUS_RECORDING:
            self._announce("Select a recording that is in progress to stop it.")
            return
        # Target this exact recording by its job id (concurrent recording); fall
        # back to the old stop-the-one behavior for a recorder without job ids.
        if entry.job_id:
            self._recorder.stop(entry.job_id)
        else:
            self._recorder.stop()
        self._announce(
            f"Stopping recording of {entry.name}; it will appear as Recorded in a moment."
        )
        self._refresh(keep_selection=True)

    def _on_stop_all_recordings(self) -> None:
        count = sum(1 for e in self._entries if e.status == STATUS_RECORDING)
        if count < 1:
            self._announce("Nothing is recording right now.")
            return
        stop_all = getattr(self._recorder, "stop_all", None)
        if callable(stop_all):
            stop_all()
        else:
            self._recorder.stop()
        self._announce(
            f"Stopping all {count} recordings; they will appear as Recorded in a moment."
        )
        self._refresh(keep_selection=True)

    def _on_open_in_folder(self) -> None:
        entry = self._selected()
        if entry is None or entry.path is None:
            return
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", "/select,", str(entry.path)])  # noqa: S603,S607
        else:
            subprocess.Popen(["open", "-R", str(entry.path)])  # noqa: S603,S607
        self._announce(f"Showing {entry.name} in the file manager")

    def _on_remove(self) -> None:
        wx = self._wx
        entry = self._selected()
        if entry is None or entry.path is None:
            return
        if entry.status == STATUS_RECORDING:
            self._announce("Still recording; stop it before removing it.")
            return
        answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation inside a managed dialog
            f"Delete the recording {entry.name}?\n\nThis removes the file "
            f"({entry.size_display}) from your recordings folder permanently.",
            "Remove Recording",
            wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
            self.dialog,
        )
        if answer != wx.YES:
            return
        try:
            entry.path.unlink()
        except OSError as error:
            self._announce(f"Could not delete the file: {error}")
            return
        self._announce(f"Removed recording {entry.name}")
        self._refresh(keep_selection=True)

    def _on_key(self, event: Any) -> None:
        wx = self._wx
        if event.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self._on_remove()
            return
        event.Skip()
