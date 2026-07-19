"""Add a weather location by ZIP, city/state, or coordinates (PRD 6.1, 7.3).

Resolution runs off the UI thread through the free geocoder; the resolved place
name is shown for confirmation before it is saved, so an ambiguous or wrong
entry is caught before it becomes a location.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.weather import geocoding
from quill.core.weather import locations as loc_store
from quill.core.weather.models import WeatherLocation
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name


class AddLocationDialog:
    def __init__(
        self,
        parent: object,
        *,
        store: loc_store.WeatherLocationStore,
        data_dir: Path,
        task_manager: object,
        safe_mode: bool,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._store = store
        self._data_dir = data_dir
        self._task_manager = task_manager
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._added = False

        self.dialog = wx.Dialog(parent, title="Add Weather Location")
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label="Enter a 5-digit ZIP code, a city and state (Tucson, AZ),\n"
                "or coordinates (32.2, -110.9):",
            ),
            0,
            wx.ALL,
            10,
        )
        self._query = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(self._query, "Location to add: ZIP, city and state, or coordinates")
        root.Add(self._query, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        name_row = wx.BoxSizer(wx.HORIZONTAL)
        name_row.Add(
            wx.StaticText(self.dialog, label="Friendly &name (optional):"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._name = wx.TextCtrl(self.dialog)
        set_accessible_name(self._name, "Friendly name for this location, for example Home")
        name_row.Add(self._name, 1, wx.EXPAND)
        root.Add(name_row, 0, wx.EXPAND | wx.ALL, 10)

        self._status = wx.StaticText(self.dialog, label="")
        set_accessible_name(self._status, "Resolution status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._add_btn = wx.Button(self.dialog, wx.ID_OK, "&Add")
        btn_row.AddStretchSpacer()
        btn_row.Add(self._add_btn, 0, wx.RIGHT, 6)
        btn_row.Add(wx.Button(self.dialog, wx.ID_CANCEL, "Cancel"))
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizer(root)
        root.Fit(self.dialog)

        self._query.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._resolve_and_add())
        self._add_btn.Bind(wx.EVT_BUTTON, lambda _e: self._resolve_and_add())

    def show(self) -> bool:
        """Modal; returns True if a location was added."""
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Add",
            cancel_id=self._wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        from quill.ui.dialog_contract import show_modal_dialog

        self._query.SetFocus()
        try:
            show_modal_dialog(self.dialog, "Add Weather Location", announce=self._announce)
        finally:
            self.dialog.Destroy()
        return self._added

    def _resolve_and_add(self) -> None:
        query = self._query.GetValue().strip()
        if not query:
            self._announce("Enter a ZIP code, a city and state, or coordinates.")
            self._query.SetFocus()
            return
        self._add_btn.Enable(False)
        self._status.SetLabel(f"Looking up {query}...")
        self._announce(f"Looking up {query}.")

        def _work(**_kwargs: Any) -> object:
            try:
                return geocoding.geocode(query, safe_mode=self._safe_mode)
            except geocoding.WeatherGeocodeError as exc:
                return exc

        def _ok(_op: str, result: object) -> None:
            self._wx.CallAfter(self._resolved, query, result)

        self._task_manager.submit("weather-geocode", _work, on_success=_ok, on_failure=None)

    def _resolved(self, query: str, result: object) -> None:
        self._add_btn.Enable(True)
        if isinstance(result, geocoding.WeatherGeocodeError):
            self._status.SetLabel(str(result))
            self._announce(str(result))
            self._query.SetFocus()
            return
        if not isinstance(result, geocoding.GeocodeResult):
            return
        name = self._name.GetValue().strip() or result.display_name
        location = WeatherLocation(
            display_name=name,
            latitude=result.latitude,
            longitude=result.longitude,
            resolved_name=result.display_name,
            state=result.state,
            query=query,
        )
        if self._store.contains_point(result.latitude, result.longitude):
            self._announce(f"{result.display_name} is already saved.")
        self._store.add(location)
        loc_store.save_locations(self._data_dir, self._store)
        self._added = True
        self._announce(f"Added {name}.")
        if self.dialog.IsModal():
            self.dialog.EndModal(self._wx.ID_OK)
