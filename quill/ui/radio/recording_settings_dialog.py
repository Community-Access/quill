"""Internet Radio > Recording Settings... -- format, quality, destination,
and filename pattern for every stream recording (Record Now and scheduled).
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.radio.recording import RECORD_FORMATS, RecordingSettings
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
        self._format_choice = wx.Choice(self.dialog, choices=list(RECORD_FORMATS))
        self._format_choice.SetName("Audio format for recordings")
        if settings.format in RECORD_FORMATS:
            self._format_choice.SetSelection(RECORD_FORMATS.index(settings.format))
        grid.Add(self._format_choice, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="&Quality (bitrate):"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._bitrate_choice = wx.Choice(
            self.dialog, choices=[f"{b} kbps" for b in _BITRATE_CHOICES]
        )
        self._bitrate_choice.SetName(
            "Bitrate for MP3/OGG recordings; ignored for lossless FLAC/WAV"
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

        root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

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
        save_btn = wx.Button(self.dialog, wx.ID_OK, "&Save")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        btn_row.AddStretchSpacer()
        btn_row.Add(save_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        save_btn.Bind(wx.EVT_BUTTON, self._on_save)

    def show(self) -> RecordingSettings | None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Save",
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
            filename_pattern=pattern,
            max_duration_minutes=self._max_duration_ctrl.GetValue(),
        )
        self.dialog.EndModal(self._wx.ID_OK)
