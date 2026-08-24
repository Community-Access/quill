"""Internet Radio > Wake-Up Timer... -- the sleep timer's twin.

Pick a favorite, a time, once or every day -- and the station starts
playing by itself. Honest about its one requirement: QUILL or Quill Radio
must be running (the tray counts) for the wake-up to fire.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.core.radio.wake_timer import WakeUpSetting, parse_time_of_day
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog


class WakeUpTimerDialog:
    """Returns the updated :class:`WakeUpSetting`, or ``None`` on Cancel."""

    def __init__(
        self,
        parent: object,
        *,
        setting: WakeUpSetting,
        favorites: RadioFavoritesStore,
        now_playing: RadioStation | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: WakeUpSetting | None = None

        # Station choices: every favorite (user's own names), plus whatever
        # is playing right now if it isn't already among them.
        self._stations: list[RadioStation] = [f.station for f in favorites.favorites]
        labels = [f.display_label for f in favorites.favorites]
        if now_playing is not None and all(
            s.stream_url != now_playing.stream_url for s in self._stations
        ):
            self._stations.insert(0, now_playing)
            labels.insert(0, f"{now_playing.display_name} (now playing)")

        self.dialog = wx.Dialog(parent, title="Wake-Up Timer")
        root = wx.BoxSizer(wx.VERTICAL)

        summary = wx.StaticText(self.dialog, label=setting.spoken_summary())
        summary.SetName("Current wake-up timer")
        root.Add(summary, 0, wx.EXPAND | wx.ALL, 10)

        self._enable_check = wx.CheckBox(self.dialog, label="&Wake up with the radio")
        self._enable_check.SetName(
            "Turn the wake-up timer on; Quill Radio or QUILL must be running "
            "(the tray counts) for it to fire"
        )
        self._enable_check.SetValue(setting.enabled)
        root.Add(self._enable_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self.dialog, label="&Station:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._station_choice = wx.Choice(self.dialog, choices=labels or ["(no favorites yet)"])
        self._station_choice.SetName("The station that starts playing at wake-up time")
        selected = 0
        if setting.station is not None:
            for index, station in enumerate(self._stations):
                if station.stream_url == setting.station.stream_url:
                    selected = index
                    break
        if labels:
            self._station_choice.SetSelection(selected)
        grid.Add(self._station_choice, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="&Time:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._time_ctrl = wx.TextCtrl(self.dialog, value=setting.time_of_day or "07:00")
        self._time_ctrl.SetName('Wake-up time, like "07:00" or "7:30 AM"')
        grid.Add(self._time_ctrl, 1, wx.EXPAND)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._daily_check = wx.CheckBox(self.dialog, label="Every &day (not just once)")
        self._daily_check.SetName(
            "Repeat every day; unchecked wakes you once and then turns itself off"
        )
        self._daily_check.SetValue(setting.recurrence == "daily")
        root.Add(self._daily_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        save_btn = wx.Button(self.dialog, wx.ID_OK, "OK")
        save_btn.SetName("Save this wake-up timer")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetHelpText("Closes without changing the wake-up timer.")
        buttons.Add(save_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizerAndFit(root)

        save_btn.Bind(wx.EVT_BUTTON, self._on_save)

    def show(self) -> WakeUpSetting | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="OK",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )
        try:
            answer = show_modal_dialog(self.dialog, "Wake-Up Timer", announce=self._announce)
            return self._result if answer == wx.ID_OK else None
        finally:
            self.dialog.Destroy()

    def _on_save(self, _event: object) -> None:
        enabled = self._enable_check.GetValue()
        time_of_day = parse_time_of_day(self._time_ctrl.GetValue())
        index = self._station_choice.GetSelection()
        station = self._stations[index] if 0 <= index < len(self._stations) else None
        if enabled and not time_of_day:
            self._status.SetLabel('That time was not understood; try "07:00" or "7:30 AM".')
            self._announce(self._status.GetLabel())
            return
        if enabled and station is None:
            self._status.SetLabel("Pick a station first (add favorites from Browse Stations).")
            self._announce(self._status.GetLabel())
            return
        self._result = WakeUpSetting(
            enabled=enabled,
            time_of_day=time_of_day,
            recurrence="daily" if self._daily_check.GetValue() else "once",
            station=station,
        )
        self.dialog.EndModal(self._wx.ID_OK)
