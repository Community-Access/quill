"""Internet Radio > Recording Settings... -- format, quality, destination,
and filename pattern for every stream recording (Record Now and scheduled).
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.radio.recording import (
    RECORD_FORMAT_LABELS,
    RECORD_FORMATS,
    RecordingSettings,
    format_uses_bitrate,
)
from quill.ui.dialog_contract import apply_modal_ids

_BITRATE_CHOICES = (96, 128, 160, 192, 256, 320)


class RecordingSettingsDialog:
    """Returns the updated :class:`RecordingSettings`, or ``None`` on Cancel."""

    def __init__(
        self,
        parent: object,
        *,
        settings: RecordingSettings,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: RecordingSettings | None = None

        self.dialog = wx.Dialog(
            parent,
            title="Recording Settings",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((520, 420))
        root = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(self.dialog, label="&Format:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._format_choice = wx.Choice(
            self.dialog, choices=[RECORD_FORMAT_LABELS[f] for f in RECORD_FORMATS]
        )
        self._format_choice.SetName(
            "Audio format for recordings. Raw stream saves exactly what the "
            "station sends, with no re-encoding -- the most lossless capture, "
            "for your own editing"
        )
        if settings.format in RECORD_FORMATS:
            self._format_choice.SetSelection(RECORD_FORMATS.index(settings.format))
        # Bitrate only applies to the lossy re-encode formats; toggle its row's
        # visibility when the format changes so a Raw stream (or lossless) never
        # shows a meaningless, confusing bitrate control (#1155).
        self._format_choice.Bind(wx.EVT_CHOICE, self._on_format_changed)
        grid.Add(self._format_choice, 1, wx.EXPAND)

        self._bitrate_label = wx.StaticText(self.dialog, label="&Quality (bitrate):")
        grid.Add(self._bitrate_label, 0, wx.ALIGN_CENTER_VERTICAL)
        self._bitrate_choice = wx.Choice(
            self.dialog, choices=[f"{b} kbps" for b in _BITRATE_CHOICES]
        )
        self._bitrate_choice.SetName(
            "Bitrate for MP3/OGG recordings; ignored for lossless and raw stream formats"
        )
        closest = min(_BITRATE_CHOICES, key=lambda b: abs(b - settings.bitrate_kbps))
        self._bitrate_choice.SetSelection(_BITRATE_CHOICES.index(closest))
        grid.Add(self._bitrate_choice, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="&Destination folder:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        dest_row = wx.BoxSizer(wx.HORIZONTAL)
        self._destination_ctrl = wx.TextCtrl(self.dialog, value=settings.destination_root)
        self._destination_ctrl.SetName(
            "Where recordings are saved; blank uses the default recordings folder"
        )
        browse_btn = wx.Button(self.dialog, label="&Browse...")
        browse_btn.SetName("Choose a destination folder")
        dest_row.Add(self._destination_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        dest_row.Add(browse_btn, 0)
        grid.Add(dest_row, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="&Temporary folder (while recording):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        temp_row = wx.BoxSizer(wx.HORIZONTAL)
        self._temp_dir_ctrl = wx.TextCtrl(self.dialog, value=settings.temp_dir)
        self._temp_dir_ctrl.SetName(
            "Where a recording is written while in progress, then moved to the "
            "destination folder when it finishes; blank records straight to the "
            "destination folder"
        )
        temp_browse_btn = wx.Button(self.dialog, label="B&rowse...")
        temp_browse_btn.SetName("Choose a temporary folder")
        temp_row.Add(self._temp_dir_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        temp_row.Add(temp_browse_btn, 0)
        grid.Add(temp_row, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="Filename &pattern:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._pattern_ctrl = wx.TextCtrl(self.dialog, value=settings.filename_pattern)
        self._pattern_ctrl.SetName(
            "Filename pattern; use {station}, {date}, and {time} as placeholders"
        )
        grid.Add(self._pattern_ctrl, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="&Maximum recording length (minutes):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._max_duration_ctrl = wx.SpinCtrl(self.dialog, min=1, max=1440)
        self._max_duration_ctrl.SetValue(settings.max_duration_minutes)
        self._max_duration_ctrl.SetName(
            "Safety cap: every recording stops automatically after this many minutes"
        )
        grid.Add(self._max_duration_ctrl, 0)

        grid.Add(
            wx.StaticText(self.dialog, label="Maximum &simultaneous recordings:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._max_concurrent_ctrl = wx.SpinCtrl(self.dialog, min=0, max=99)
        self._max_concurrent_ctrl.SetValue(max(0, settings.max_concurrent_recordings))
        self._max_concurrent_ctrl.SetName(
            "How many recordings may run at the same time. Zero means unlimited "
            "-- every recording you or the schedule asks for starts. Set a number "
            "to cap it on a slower machine or a metered connection"
        )
        grid.Add(self._max_concurrent_ctrl, 0)

        root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        reconnect_box = wx.StaticBoxSizer(wx.VERTICAL, self.dialog, "If the connection drops")
        self._reconnect_check = wx.CheckBox(
            self.dialog, label="&Reconnect and keep recording automatically"
        )
        self._reconnect_check.SetName(
            "When the internet hiccups mid-recording, ride it out and resume "
            "into a continuation part file instead of losing the rest of the show"
        )
        self._reconnect_check.SetValue(settings.reconnect_enabled)
        reconnect_box.Add(self._reconnect_check, 0, wx.ALL, 6)
        reconnect_grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        reconnect_grid.Add(
            wx.StaticText(self.dialog, label="Reconnect &attempts:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._reconnect_attempts_ctrl = wx.SpinCtrl(self.dialog, min=1, max=99)
        self._reconnect_attempts_ctrl.SetValue(max(1, settings.reconnect_max_attempts))
        self._reconnect_attempts_ctrl.SetName(
            "How many times to try reconnecting before giving up on the recording"
        )
        reconnect_grid.Add(self._reconnect_attempts_ctrl, 0)
        reconnect_grid.Add(
            wx.StaticText(self.dialog, label="Seconds &between attempts:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._reconnect_wait_ctrl = wx.SpinCtrl(self.dialog, min=1, max=600)
        self._reconnect_wait_ctrl.SetValue(max(1, settings.reconnect_wait_seconds))
        self._reconnect_wait_ctrl.SetName(
            "How long to wait before each reconnect attempt; also how long "
            "ffmpeg itself rides out short gaps"
        )
        reconnect_grid.Add(self._reconnect_wait_ctrl, 0)
        reconnect_box.Add(reconnect_grid, 0, wx.LEFT | wx.BOTTOM, 6)
        root.Add(reconnect_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._apply_enhancements_check = wx.CheckBox(
            self.dialog, label="Apply Sound Enhancements to &recordings"
        )
        self._apply_enhancements_check.SetName(
            "Record the EQ preset and compressor from Playback > Sound Enhancements "
            "instead of an unfiltered archival copy"
        )
        self._apply_enhancements_check.SetValue(settings.apply_sound_enhancements)
        root.Add(self._apply_enhancements_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        hint = wx.StaticText(
            self.dialog,
            label=(
                "{station}, {date}, and {time} in the filename pattern are replaced "
                'automatically -- for example, "{station} - {date} {time}" becomes '
                '"WXYZ - 2026-07-14 08-00-00".'
            ),
        )
        hint.Wrap(480)
        root.Add(hint, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        save_btn = wx.Button(self.dialog, wx.ID_OK, "OK")
        save_btn.SetName("Save these recording settings")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetHelpText("Closes without changing how recordings are made.")
        btn_row.AddStretchSpacer()
        btn_row.Add(save_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        temp_browse_btn.Bind(wx.EVT_BUTTON, self._on_browse_temp)
        save_btn.Bind(wx.EVT_BUTTON, self._on_save)

        # Hide the bitrate row now if the initial format doesn't use it.
        self._sync_bitrate_visibility()

    def _current_format(self) -> str:
        index = self._format_choice.GetSelection()
        return RECORD_FORMATS[index] if index >= 0 else "mp3"

    def _sync_bitrate_visibility(self) -> None:
        """Show the bitrate row only for formats that re-encode to a lossy
        codec; hide the label and control for Raw stream and the lossless
        formats, where bitrate does nothing -- keeping it off the screen and
        out of the screen reader's tab order (#1155)."""
        show = format_uses_bitrate(self._current_format())
        self._bitrate_label.Show(show)
        self._bitrate_choice.Show(show)
        self.dialog.Layout()

    def _on_format_changed(self, _event: object) -> None:
        self._sync_bitrate_visibility()

    def show(self) -> RecordingSettings | None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="OK",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            answer = show_modal_dialog(self.dialog, "Recording Settings", announce=self._announce)
            return self._result if answer == self._wx.ID_OK else None
        finally:
            self.dialog.Destroy()

    def _on_browse(self, _event: object) -> None:
        wx = self._wx
        with wx.DirDialog(
            self.dialog, "Choose a destination folder"
        ) as dlg:  # dialog_button_contract: exempt
            if dlg.ShowModal() == wx.ID_OK:
                self._destination_ctrl.SetValue(dlg.GetPath())

    def _on_browse_temp(self, _event: object) -> None:
        wx = self._wx
        with wx.DirDialog(
            self.dialog, "Choose a temporary folder"
        ) as dlg:  # dialog_button_contract: exempt
            if dlg.ShowModal() == wx.ID_OK:
                self._temp_dir_ctrl.SetValue(dlg.GetPath())

    def _on_save(self, _event: object) -> None:
        format_index = self._format_choice.GetSelection()
        fmt = RECORD_FORMATS[format_index] if format_index >= 0 else "mp3"
        bitrate_index = self._bitrate_choice.GetSelection()
        bitrate = _BITRATE_CHOICES[bitrate_index] if bitrate_index >= 0 else 192
        pattern = self._pattern_ctrl.GetValue().strip() or "{station} - {date} {time}"
        self._result = RecordingSettings(
            format=fmt,
            bitrate_kbps=bitrate,
            destination_root=self._destination_ctrl.GetValue().strip(),
            temp_dir=self._temp_dir_ctrl.GetValue().strip(),
            filename_pattern=pattern,
            max_duration_minutes=self._max_duration_ctrl.GetValue(),
            reconnect_enabled=self._reconnect_check.GetValue(),
            reconnect_max_attempts=self._reconnect_attempts_ctrl.GetValue(),
            reconnect_wait_seconds=self._reconnect_wait_ctrl.GetValue(),
            apply_sound_enhancements=self._apply_enhancements_check.GetValue(),
            max_concurrent_recordings=self._max_concurrent_ctrl.GetValue(),
        )
        self.dialog.EndModal(self._wx.ID_OK)
