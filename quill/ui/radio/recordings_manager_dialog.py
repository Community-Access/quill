"""Internet Radio > Recordings... -- everything you've recorded, live.

One list for the whole recording life cycle, shared by embedded QUILL and
standalone Quill Radio: the recording being written right now (status
"Recording", size growing on the 2-second refresh), every finished file in
the recordings folder ("Recorded", newest first), and upcoming scheduled
recordings ("Scheduled", with their time). Play any finished recording
through the shared radio player (which also silences anything else
playing), stop the active recording, reveal a file in Explorer, or remove
it -- all keyboard-first and announced.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from typing import Any

from quill.core.radio.models import RadioStation
from quill.core.radio.recordings_index import (
    STATUS_RECORDED,
    STATUS_RECORDING,
    RecordingEntry,
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
    ) -> None:
        import wx

        self._wx = wx
        self._recorder = recorder
        self._settings = settings
        self._scheduler = scheduler
        self._controller = controller
        self._announce = announce_cb or (lambda _m: None)
        self._entries: list[RecordingEntry] = []

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
            "Recordings; the row's status column reads Recording, Recorded, or "
            "Scheduled. Enter plays a finished recording, Delete removes it"
        )
        self._list.InsertColumn(0, "Name", width=280)
        self._list.InsertColumn(1, "Status", width=100)
        self._list.InsertColumn(2, "Size", width=100)
        self._list.InsertColumn(3, "When", width=200)
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
            "Finish the recording being written right now",
        )
        self._open_btn = self._button(
            buttons, "&Open in Folder", self._on_open_in_folder, "Show this file in Explorer"
        )
        self._remove_btn = self._button(
            buttons, "&Remove...", self._on_remove, "Delete this recording file"
        )
        self._button(buttons, "Re&fresh", self._refresh, "Reload the recordings list now")
        buttons.AddStretchSpacer()
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close (recordings continue)")
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda _e: self._on_selection_changed())
        self._list.Bind(wx.EVT_LIST_ITEM_DESELECTED, lambda _e: self._on_selection_changed())
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self._on_play())
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_key)

        # Live status: sizes grow and Recording flips to Recorded without a
        # manual refresh -- the same auto-refresh cadence as the Status Page.
        self._timer = wx.Timer(self.dialog)
        self.dialog.Bind(wx.EVT_TIMER, lambda _e: self._refresh(keep_selection=True))
        self._timer.Start(_REFRESH_MS)
        # quill-radio #4: pause the auto-refresh while the list has focus, so it
        # never rebuilds out from under a screen reader mid-read. It resumes when
        # focus leaves the list (onto a button, or away from the dialog); the
        # Refresh button covers a manual update while reading.
        self._list.Bind(wx.EVT_SET_FOCUS, self._on_list_focus)
        self._list.Bind(wx.EVT_KILL_FOCUS, self._on_list_blur)
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

    def _on_list_focus(self, event: Any) -> None:
        """Pause the auto-refresh while the list is being read (#4)."""
        self._timer.Stop()
        event.Skip()

    def _on_list_blur(self, event: Any) -> None:
        """Resume the auto-refresh once focus leaves the list (#4)."""
        if self._timer is not None:
            self._timer.Start(_REFRESH_MS)
        event.Skip()

    def _on_close(self, event: Any) -> None:
        self._timer.Stop()
        event.Skip()

    # -- data -------------------------------------------------------------------

    def _refresh(self, keep_selection: bool = False) -> None:
        selected_name = None
        if keep_selection:
            index = self._list.GetFirstSelected()
            if 0 <= index < len(self._entries):
                selected_name = (self._entries[index].name, self._entries[index].status)
        self._entries = list_recordings(
            self._settings,
            active_path=getattr(self._recorder, "current_destination", None),
            scheduled=list(getattr(self._scheduler, "entries", []) or []),
        )
        self._list.DeleteAllItems()
        for row, entry in enumerate(self._entries):
            self._list.InsertItem(row, entry.name)
            self._list.SetItem(row, 1, entry.status)
            self._list.SetItem(row, 2, entry.size_display)
            when = entry.modified.strftime("%Y-%m-%d %H:%M") if entry.modified else entry.detail
            self._list.SetItem(row, 3, when)
        recorded = sum(1 for e in self._entries if e.status == STATUS_RECORDED)
        active = sum(1 for e in self._entries if e.status == STATUS_RECORDING)
        scheduled = len(self._entries) - recorded - active
        self._status.SetLabel(
            f"{recorded} recorded, {active} recording now, {scheduled} scheduled -- "
            f"in {recordings_dir(self._settings)}"
        )
        if self._entries:
            restore = 0
            if selected_name is not None:
                for row, entry in enumerate(self._entries):
                    if (entry.name, entry.status) == selected_name:
                        restore = row
                        break
            self._list.Select(restore)
            self._list.Focus(restore)
        self._on_selection_changed()

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
        playing = self._is_entry_playing(entry)
        self._play_btn.Enable(bool(is_done))
        self._play_btn.SetLabel("&Stop" if playing else "&Play")
        self._play_btn.SetName("Stop this recording" if playing else "Play this recording")
        self._open_btn.Enable(bool(is_file))
        self._remove_btn.Enable(bool(is_done))
        self._stop_btn.Enable(bool(getattr(self._recorder, "is_recording", False)))

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
        if not bool(getattr(self._recorder, "is_recording", False)):
            self._announce("Nothing is recording right now.")
            return
        self._recorder.stop()
        self._announce("Stopping recording; it will appear as Recorded in a moment.")
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
            wx.ICON_QUESTION | wx.YES_NO,
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
        self._refresh()

    def _on_key(self, event: Any) -> None:
        wx = self._wx
        if event.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self._on_remove()
            return
        event.Skip()
