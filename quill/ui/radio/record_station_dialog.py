"""Internet Radio > Record Station... -- record without listening.

The recorder is its own ffmpeg process, so it never needed the player:
pick any favorite (or the station playing now), choose how long, and the
recording runs in the background while you listen to something else --
or to nothing at all.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog


class RecordStationDialog:
    """Returns ``(station, duration_minutes)``, or ``None`` on Cancel."""

    def __init__(
        self,
        parent: object,
        *,
        favorites: RadioFavoritesStore,
        now_playing: RadioStation | None = None,
        default_duration_minutes: int = 60,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: tuple[RadioStation, int] | None = None

        self._stations: list[RadioStation] = [f.station for f in favorites.favorites]
        labels = [f.display_label for f in favorites.favorites]
        if now_playing is not None and all(
            s.stream_url != now_playing.stream_url for s in self._stations
        ):
            self._stations.insert(0, now_playing)
            labels.insert(0, f"{now_playing.display_name} (now playing)")

        self.dialog = wx.Dialog(parent, title="Record Station")
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                "Recording runs on its own -- you can keep listening to a "
                "different station, or to nothing at all."
            ),
        )
        intro.Wrap(420)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self.dialog, label="S&tation:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._station_choice = wx.Choice(self.dialog, choices=labels or ["(no favorites yet)"])
        self._station_choice.SetName("The station to record")
        if labels:
            self._station_choice.SetSelection(0)
        grid.Add(self._station_choice, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="&Duration (minutes):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._duration_ctrl = wx.SpinCtrl(self.dialog, min=1, max=1440)
        self._duration_ctrl.SetValue(max(1, default_duration_minutes))
        self._duration_ctrl.SetName("How long to record before stopping automatically")
        grid.Add(self._duration_ctrl, 0)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        start_btn = wx.Button(self.dialog, wx.ID_OK, "&Start Recording")
        start_btn.SetHelpText(
            "Begins capturing now, in the background. The Recordings window "
            "and the status bar both show the progress."
        )
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetHelpText("Closes without recording anything.")
        buttons.Add(start_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizerAndFit(root)

        start_btn.Bind(wx.EVT_BUTTON, self._on_start)

    def show(self) -> tuple[RadioStation, int] | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Start Recording",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )
        try:
            answer = show_modal_dialog(self.dialog, "Record Station", announce=self._announce)
            return self._result if answer == wx.ID_OK else None
        finally:
            self.dialog.Destroy()

    def _on_start(self, _event: object) -> None:
        index = self._station_choice.GetSelection()
        station = self._stations[index] if 0 <= index < len(self._stations) else None
        if station is None:
            self._status.SetLabel("Pick a station first (add favorites from Browse Stations).")
            self._announce(self._status.GetLabel())
            return
        self._result = (station, self._duration_ctrl.GetValue())
        self.dialog.EndModal(self._wx.ID_OK)
