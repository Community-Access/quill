"""Tools > Media > Sleep Timer... -- set or cancel the shared Radio/Podcasts
sleep timer."""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids

_PRESET_MINUTES = (15, 30, 45, 60, 90)


class SleepTimerDialog:
    """Returns the chosen number of minutes, ``0`` to cancel an active timer,
    or ``None`` if the dialog was dismissed without a choice."""

    def __init__(
        self,
        parent: object,
        *,
        is_active: bool,
        remaining_seconds: float,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: int | None = None

        self.dialog = wx.Dialog(
            parent, title="Sleep Timer", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((420, 260))
        root = wx.BoxSizer(wx.VERTICAL)

        if is_active:
            minutes_left = max(0, int(remaining_seconds // 60))
            seconds_left = max(0, int(remaining_seconds % 60))
            status = wx.StaticText(
                self.dialog,
                label=f"Sleep timer active: {minutes_left}:{seconds_left:02d} remaining.",
            )
            root.Add(status, 0, wx.EXPAND | wx.ALL, 10)

        root.Add(
            wx.StaticText(self.dialog, label="Stop Radio and Podcasts playback after:"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            10,
        )
        self._preset_choice = wx.Choice(
            self.dialog, choices=[f"{m} minutes" for m in _PRESET_MINUTES] + ["Custom..."]
        )
        self._preset_choice.SetName("Sleep timer duration")
        self._preset_choice.SetSelection(0)
        root.Add(self._preset_choice, 0, wx.EXPAND | wx.ALL, 10)

        self._custom_ctrl = wx.SpinCtrl(self.dialog, min=1, max=600)
        self._custom_ctrl.SetValue(30)
        self._custom_ctrl.SetName("Custom sleep timer duration, in minutes")
        self._custom_ctrl.Enable(False)
        root.Add(self._custom_ctrl, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        start_btn = wx.Button(self.dialog, wx.ID_OK, "&Start")
        if is_active:
            cancel_timer_btn = wx.Button(self.dialog, label="&Cancel Sleep Timer")
            cancel_timer_btn.Bind(wx.EVT_BUTTON, self._on_cancel_timer)
            btn_row.Add(cancel_timer_btn, 0, wx.RIGHT, 6)
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        btn_row.Add(start_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._preset_choice.Bind(wx.EVT_CHOICE, self._on_preset_choice)
        start_btn.Bind(wx.EVT_BUTTON, self._on_start)

    def show(self) -> int | None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Start",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            answer = show_modal_dialog(self.dialog, "Sleep Timer", announce=self._announce)
            return self._result if answer == self._wx.ID_OK else None
        finally:
            self.dialog.Destroy()

    def _on_preset_choice(self, _event: object) -> None:
        is_custom = self._preset_choice.GetSelection() == len(_PRESET_MINUTES)
        self._custom_ctrl.Enable(is_custom)

    def _on_cancel_timer(self, _event: object) -> None:
        self._result = 0
        self.dialog.EndModal(self._wx.ID_OK)

    def _on_start(self, _event: object) -> None:
        index = self._preset_choice.GetSelection()
        if index < len(_PRESET_MINUTES):
            self._result = _PRESET_MINUTES[index]
        else:
            self._result = self._custom_ctrl.GetValue()
        self.dialog.EndModal(self._wx.ID_OK)
