"""Internet Radio > Add Custom Station... -- type any stream link and save it.

RadioBrowser and ACB Media don't carry every station in existence; this is
the escape hatch for "a wide variety of links" -- any http(s) stream URL,
tested through the same shared player before it's saved. Can be pre-filled
(from the website link finder, or from "Edit" on an existing favorite).
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.radio.models import RadioStation
from quill.ui.dialog_contract import apply_modal_ids


class AddStationDialog:
    """Returns the new :class:`RadioStation`, or ``None`` on Cancel/Escape."""

    def __init__(
        self,
        parent: object,
        *,
        controller: object,
        prefill: RadioStation | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._controller = controller
        self._announce = announce_cb or (lambda _m: None)
        self._result: RadioStation | None = None

        self.dialog = wx.Dialog(
            parent, title="Add Custom Station", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((520, 340))
        root = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)

        def _field(label: str, *, accessible_name: str, value: str = "") -> wx.TextCtrl:
            grid.Add(wx.StaticText(self.dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = wx.TextCtrl(self.dialog, value=value)
            ctrl.SetName(accessible_name)
            grid.Add(ctrl, 1, wx.EXPAND)
            return ctrl

        prefill = prefill or RadioStation(name="", stream_url="")
        self._name_ctrl = _field(
            "Station &name:", accessible_name="Name for this station", value=prefill.name
        )
        self._url_ctrl = _field(
            "Stream &URL:",
            accessible_name="The direct stream link (http or https)",
            value=prefill.stream_url,
        )
        self._homepage_ctrl = _field(
            "&Homepage (optional):",
            accessible_name="The station's website, optional",
            value=prefill.homepage,
        )
        self._tags_ctrl = _field(
            "&Tags (optional, comma-separated):",
            accessible_name="Optional tags or genres, comma-separated",
            value=", ".join(prefill.tags),
        )
        root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        test_btn = wx.Button(self.dialog, label="&Test")
        test_btn.SetName("Play this stream link now, before saving, to check it works")
        save_btn = wx.Button(self.dialog, wx.ID_OK, "&Save")
        save_btn.SetName("Save this custom station")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetName("Cancel")
        btn_row.Add(test_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(save_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        test_btn.Bind(wx.EVT_BUTTON, self._on_test)
        save_btn.Bind(wx.EVT_BUTTON, self._on_save)

    def show(self) -> RadioStation | None:
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
            answer = show_modal_dialog(self.dialog, "Add Custom Station", announce=self._announce)
            return self._result if answer == self._wx.ID_OK else None
        finally:
            self.dialog.Destroy()

    def _build_station(self) -> RadioStation | None:
        name = self._name_ctrl.GetValue().strip()
        url = self._url_ctrl.GetValue().strip()
        if not name or not url:
            self._status.SetLabel("A station name and a stream URL are both required.")
            return None
        if not (url.startswith("http://") or url.startswith("https://")):
            self._status.SetLabel("The stream URL should start with http:// or https://")
            return None
        tags = tuple(t.strip() for t in self._tags_ctrl.GetValue().split(",") if t.strip())
        return RadioStation(
            name=name,
            stream_url=url,
            homepage=self._homepage_ctrl.GetValue().strip(),
            tags=tags,
        )

    def _on_test(self, _event: object) -> None:
        station = self._build_station()
        if station is None:
            return
        self._controller.play_station(station)
        self._status.SetLabel(f"Testing {station.name} -- listen for it to start playing.")
        self._announce(f"Testing {station.name}")

    def _on_save(self, _event: object) -> None:
        station = self._build_station()
        if station is None:
            return
        self._result = station
        self.dialog.EndModal(self._wx.ID_OK)
