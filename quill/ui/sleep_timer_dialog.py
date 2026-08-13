"""Tools > Media > Sleep Timer... -- set, extend, or cancel the shared
Radio/Podcasts sleep timer."""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids

_PRESET_MINUTES = (15, 30, 45, 60, 90)
#: Returned instead of a number of minutes when "End of this episode" is
#: chosen. Negative so it can never be mistaken for a duration, and named so
#: no caller has to remember what -1 meant.
END_OF_EPISODE = -1
#: What the Extend button adds. One value, one button, no submenu: the point
#: of Extend is that it takes a single keypress while half asleep.
EXTEND_MINUTES = 5


class SleepTimerDialog:
    """Returns the chosen number of minutes, :data:`END_OF_EPISODE`, ``0`` to
    cancel an active timer, or ``None`` if the dialog was dismissed without a
    choice. Extend is applied through *on_extend* while the dialog is open,
    since extending is not a thing you finish the dialog to do."""

    def __init__(
        self,
        parent: object,
        *,
        is_active: bool,
        remaining_seconds: float,
        announce_cb: Callable[[str], None] | None = None,
        allow_end_of_episode: bool = False,
        on_extend: Callable[[int], bool] | None = None,
        is_end_of_episode: bool = False,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: int | None = None
        self._on_extend = on_extend
        #: "End of this episode" is podcast-only: a live radio stream has no
        #: end, so the choice is simply absent rather than present and broken.
        self._allow_end_of_episode = allow_end_of_episode

        self.dialog = wx.Dialog(
            parent, title="Sleep Timer", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((440, 300))
        root = wx.BoxSizer(wx.VERTICAL)

        self._status = None
        if is_active:
            self._status = wx.StaticText(
                self.dialog, label=self._status_text(remaining_seconds, is_end_of_episode)
            )
            self._status.SetName("Sleep timer status")
            root.Add(self._status, 0, wx.EXPAND | wx.ALL, 10)

        root.Add(
            wx.StaticText(self.dialog, label="Stop Radio and Podcasts playback after:"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            10,
        )
        self._choices = [f"{m} minutes" for m in _PRESET_MINUTES]
        if allow_end_of_episode:
            self._choices.append("End of this episode")
        self._choices.append("Custom...")
        self._preset_choice = wx.Choice(self.dialog, choices=self._choices)
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
            extend_btn = wx.Button(self.dialog, label=f"&Extend {EXTEND_MINUTES} Minutes")
            extend_btn.SetName(
                f"Add {EXTEND_MINUTES} minutes to the running timer and undo any fade"
            )
            extend_btn.Bind(wx.EVT_BUTTON, self._on_extend_click)
            btn_row.Add(extend_btn, 0, wx.RIGHT, 6)
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

    @staticmethod
    def _status_text(remaining_seconds: float, is_end_of_episode: bool) -> str:
        minutes_left = max(0, int(remaining_seconds // 60))
        seconds_left = max(0, int(remaining_seconds % 60))
        suffix = " (end of this episode)" if is_end_of_episode else ""
        return f"Sleep timer active: {minutes_left}:{seconds_left:02d} remaining{suffix}."

    def _on_preset_choice(self, _event: object) -> None:
        self._custom_ctrl.Enable(self._preset_choice.GetSelection() == len(self._choices) - 1)

    def _on_extend_click(self, _event: object) -> None:
        if self._on_extend is None or not self._on_extend(EXTEND_MINUTES):
            self._announce("No sleep timer is running.")
            return
        self._announce(f"Sleep timer extended by {EXTEND_MINUTES} minutes")

    def _on_cancel_timer(self, _event: object) -> None:
        self._result = 0
        self.dialog.EndModal(self._wx.ID_OK)

    def _on_start(self, _event: object) -> None:
        index = self._preset_choice.GetSelection()
        if 0 <= index < len(_PRESET_MINUTES):
            self._result = _PRESET_MINUTES[index]
        elif self._allow_end_of_episode and index == len(_PRESET_MINUTES):
            self._result = END_OF_EPISODE
        else:
            self._result = self._custom_ctrl.GetValue()
        self.dialog.EndModal(self._wx.ID_OK)
