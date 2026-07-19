"""Add a weather location by searching (PRD 6.1, 7.3).

Type a ZIP, city, county, or address and press Search; the free Nominatim
(OpenStreetMap) US search returns the matching places -- so same-named towns
("Springfield") are disambiguated -- and you pick one from the list before it
is saved. A bare ``lat,lon`` resolves to that exact point with no request.
Searching runs off the UI thread.
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
        self._results: list[geocoding.GeocodeResult] = []

        self.dialog = wx.Dialog(
            parent, title="Add Weather Location", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((520, 420))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(
                self.dialog,
                label="&Search a ZIP code, city, county, or address, then pick a match:",
            ),
            0,
            wx.ALL,
            10,
        )
        search_row = wx.BoxSizer(wx.HORIZONTAL)
        self._query = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(self._query, "Search: ZIP, city, county, or address")
        search_row.Add(self._query, 1, wx.EXPAND | wx.RIGHT, 6)
        self._search_btn = wx.Button(self.dialog, label="&Search")
        search_row.Add(self._search_btn, 0)
        root.Add(search_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        results_label = wx.StaticText(self.dialog, label="&Results (choose one):")
        root.Add(results_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._results_list = wx.ListBox(self.dialog)
        set_accessible_name(self._results_list, "Search results, choose a place to add")
        root.Add(self._results_list, 1, wx.EXPAND | wx.ALL, 10)

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
        root.Add(name_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._status = wx.StaticText(self.dialog, label="")
        set_accessible_name(self._status, "Search status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._add_btn = wx.Button(self.dialog, wx.ID_OK, "&Add Selected")
        self._add_btn.Enable(False)
        btn_row.AddStretchSpacer()
        btn_row.Add(self._add_btn, 0, wx.RIGHT, 6)
        btn_row.Add(wx.Button(self.dialog, wx.ID_CANCEL, "Cancel"))
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizer(root)

        self._query.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._search())
        self._search_btn.Bind(wx.EVT_BUTTON, lambda _e: self._search())
        self._results_list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_result_selected())
        self._results_list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._add_selected())
        self._add_btn.Bind(wx.EVT_BUTTON, lambda _e: self._add_selected())

    def show(self) -> bool:
        """Modal; returns True if a location was added."""
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Add Selected",
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

    # -- search -----------------------------------------------------------------

    def _search(self) -> None:
        query = self._query.GetValue().strip()
        if not query:
            self._announce("Type a ZIP code, city, county, or address to search.")
            self._query.SetFocus()
            return
        self._search_btn.Enable(False)
        self._status.SetLabel(f"Searching for {query}...")
        self._announce(f"Searching for {query}.")

        def _work(**_kwargs: Any) -> object:
            try:
                return geocoding.search(query, safe_mode=self._safe_mode)
            except geocoding.WeatherGeocodeError as exc:
                return exc

        def _ok(_op: str, result: object) -> None:
            self._wx.CallAfter(self._searched, query, result)

        self._task_manager.submit("weather-search", _work, on_success=_ok, on_failure=None)

    def _searched(self, query: str, result: object) -> None:
        self._search_btn.Enable(True)
        if isinstance(result, geocoding.WeatherGeocodeError):
            self._results = []
            self._results_list.Set([])
            self._add_btn.Enable(False)
            self._status.SetLabel(str(result))
            self._announce(str(result))
            return
        results = result if isinstance(result, list) else []
        self._results = results
        self._results_list.Set([r.display_name for r in results])
        self._add_btn.Enable(bool(results))
        if not results:
            self._status.SetLabel(f"No places found for '{query}'.")
            self._announce(f"No places found for {query}.")
            return
        self._results_list.SetSelection(0)
        self._status.SetLabel(
            f"{len(results)} result{'' if len(results) == 1 else 's'}. Choose one."
        )
        self._announce(
            f"{len(results)} result{'' if len(results) == 1 else 's'}. "
            "Arrow to a place and press Add Selected."
        )
        self._results_list.SetFocus()

    def _on_result_selected(self) -> None:
        self._add_btn.Enable(self._results_list.GetSelection() >= 0)

    # -- add --------------------------------------------------------------------

    def _add_selected(self) -> None:
        index = self._results_list.GetSelection()
        if not (0 <= index < len(self._results)):
            self._announce("Choose a place from the results first.")
            return
        result = self._results[index]
        name = self._name.GetValue().strip() or result.display_name
        location = WeatherLocation(
            display_name=name,
            latitude=result.latitude,
            longitude=result.longitude,
            resolved_name=result.display_name,
            state=result.state,
            query=result.query,
        )
        if self._store.contains_point(result.latitude, result.longitude):
            self._announce(f"{result.display_name} is already saved; adding again.")
        self._store.add(location)
        loc_store.save_locations(self._data_dir, self._store)
        self._added = True
        self._announce(f"Added {name}.")
        if self.dialog.IsModal():
            self.dialog.EndModal(self._wx.ID_OK)
