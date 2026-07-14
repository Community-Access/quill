"""Internet Radio > Browse Stations... -- search, browse, play, and favorite.

Same shape as the emoji picker (``main_frame_emoji_picker.py``): a category
list for instant browsing (Favorites, ACB Media -- both local, no network)
plus a search row for RadioBrowser (network, so it is an explicit Search
action, not live-filter-as-you-type like the emoji picker's local data).
Controls are parented directly on the dialog, not an intermediate panel (the
NVDA-virtual-buffer rule documented in ``dialog_button_contract.py``).

This dialog does not own playback -- it drives the single shared
``RadioPlayerController`` passed in, so closing it never stops the stream.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio import acb_media, radio_browser
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.ui.dialog_contract import apply_modal_ids

_FAVORITES = "Favorites"
_ACB_MEDIA = acb_media.CATEGORY_LABEL
_SEARCH_RESULTS = "Search Results"
_CATEGORIES = (_FAVORITES, _ACB_MEDIA, _SEARCH_RESULTS)


class StationBrowserDialog:
    """Browse/search/play/favorite internet radio stations."""

    def __init__(
        self,
        parent: object,
        *,
        controller: object,
        favorites_store: RadioFavoritesStore,
        task_manager: object,
        safe_mode: bool,
        announce_cb: Callable[[str], None] | None = None,
        on_favorites_changed: Callable[[], None] | None = None,
        on_open_add_custom: Callable[[RadioStation | None], None] | None = None,
        on_open_link_finder: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._controller = controller
        self._favorites = favorites_store
        self._task_manager = task_manager
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._on_favorites_changed = on_favorites_changed or (lambda: None)
        self._on_open_add_custom = on_open_add_custom
        self._on_open_link_finder = on_open_link_finder

        self._current_results: list[RadioStation] = []
        self._search_results: list[RadioStation] = []

        self.dialog = wx.Dialog(
            parent, title="Internet Radio", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((700, 520))
        self.dialog.SetSize((820, 600))
        root = wx.BoxSizer(wx.VERTICAL)

        search_box = wx.StaticBoxSizer(wx.HORIZONTAL, self.dialog, "Search RadioBrowser")
        search_grid = wx.FlexGridSizer(cols=2, gap=(6, 4))
        search_grid.AddGrowableCol(1, 1)

        def _labeled_field(label: str, *, accessible_name: str) -> wx.TextCtrl:
            search_grid.Add(wx.StaticText(self.dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
            ctrl.SetName(accessible_name)
            search_grid.Add(ctrl, 1, wx.EXPAND)
            return ctrl

        self._name_ctrl = _labeled_field(
            "Station &name:", accessible_name="Station name to search for on RadioBrowser"
        )
        self._tag_ctrl = _labeled_field(
            "&Tag/genre (optional):",
            accessible_name="Optional tag or genre to narrow the search, e.g. jazz",
        )
        self._country_ctrl = _labeled_field(
            "&Country (optional):",
            accessible_name="Optional country to narrow the search, e.g. Canada",
        )
        search_box.Add(search_grid, 1, wx.EXPAND | wx.ALL, 6)
        search_col = wx.BoxSizer(wx.VERTICAL)
        self._search_btn = wx.Button(self.dialog, label="&Search")
        self._search_btn.SetName("Search RadioBrowser for stations matching these fields")
        search_col.Add(self._search_btn, 0, wx.ALIGN_CENTER_VERTICAL)
        search_box.Add(search_col, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)
        root.Add(search_box, 0, wx.EXPAND | wx.ALL, 10)

        body = wx.BoxSizer(wx.HORIZONTAL)
        cat_col = wx.BoxSizer(wx.VERTICAL)
        cat_col.Add(wx.StaticText(self.dialog, label="&Category"), 0, wx.BOTTOM, 4)
        self._category_list = wx.ListBox(self.dialog, choices=list(_CATEGORIES))
        self._category_list.SetName(
            "Station category; Favorites and ACB Media are always available, "
            "Search Results appears after a search"
        )
        self._category_list.SetSelection(0)
        cat_col.Add(self._category_list, 1, wx.EXPAND)
        body.Add(cat_col, 1, wx.EXPAND | wx.RIGHT, 10)

        results_col = wx.BoxSizer(wx.VERTICAL)
        results_col.Add(wx.StaticText(self.dialog, label="&Stations"), 0, wx.BOTTOM, 4)
        self._results = wx.ListCtrl(self.dialog, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._results.SetName("Station results; arrow through to hear details of each")
        self._results.InsertColumn(0, "Name", width=260)
        self._results.InsertColumn(1, "Country", width=140)
        self._results.InsertColumn(2, "Format", width=140)
        results_col.Add(self._results, 1, wx.EXPAND)
        body.Add(results_col, 2, wx.EXPAND)
        root.Add(body, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        root.Add(wx.StaticText(self.dialog, label="Station details"), 0, wx.LEFT | wx.TOP, 10)
        self._details = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self._details.SetName("Read-only details of the selected station")
        root.Add(self._details, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        volume_row = wx.BoxSizer(wx.HORIZONTAL)
        volume_row.Add(
            wx.StaticText(self.dialog, label="Radio &volume:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._volume_slider = wx.Slider(self.dialog, value=100, minValue=0, maxValue=100)
        self._volume_slider.SetName(
            "Internet Radio's own volume, separate from your system volume and screen reader"
        )
        volume_row.Add(self._volume_slider, 1, wx.EXPAND | wx.RIGHT, 6)
        self._mute_btn = wx.ToggleButton(self.dialog, label="&Mute")
        self._mute_btn.SetName("Mute or unmute Internet Radio")
        volume_row.Add(self._mute_btn, 0)
        root.Add(volume_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._play_btn = wx.Button(self.dialog, label="&Play")
        self._play_btn.SetName("Play the selected station")
        self._play_btn.Enable(False)
        self._favorite_btn = wx.Button(self.dialog, label="Add to &Favorites")
        self._favorite_btn.SetName("Add or remove the selected station from Favorites")
        self._favorite_btn.Enable(False)
        add_custom_btn = wx.Button(self.dialog, label="Add &Custom Station...")
        add_custom_btn.SetName("Add a station by typing its own stream link")
        link_finder_btn = wx.Button(self.dialog, label="Find Streams from a &Website...")
        link_finder_btn.SetName("Scan a website you type in for stream links")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close (playback continues)")
        btn_row.Add(self._play_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._favorite_btn, 0, wx.RIGHT, 6)
        btn_row.Add(add_custom_btn, 0, wx.RIGHT, 6)
        btn_row.Add(link_finder_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._name_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        self._tag_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        self._country_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        self._search_btn.Bind(wx.EVT_BUTTON, self._on_search)
        self._category_list.Bind(wx.EVT_LISTBOX, self._on_category_selected)
        self._results.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_result_selected)
        self._results.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_activate)
        self._play_btn.Bind(wx.EVT_BUTTON, self._on_play)
        self._favorite_btn.Bind(wx.EVT_BUTTON, self._on_toggle_favorite)
        add_custom_btn.Bind(wx.EVT_BUTTON, self._on_add_custom)
        link_finder_btn.Bind(wx.EVT_BUTTON, self._on_link_finder)
        self._volume_slider.Bind(wx.EVT_SLIDER, self._on_volume_slider)
        self._mute_btn.Bind(wx.EVT_TOGGLEBUTTON, self._on_mute_toggle)

        state = getattr(self._controller, "state", None)
        if state is not None:
            self._volume_slider.SetValue(state.volume_percent)
            self._mute_btn.SetValue(state.muted)

        self._show_category(_FAVORITES)

    # ------------------------------------------------------------------

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Internet Radio", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def refresh_favorites_view(self) -> None:
        if self._category_list.GetSelection() == _CATEGORIES.index(_FAVORITES):
            self._show_category(_FAVORITES)

    # ------------------------------------------------------------------
    # Population

    def _fill_results(self, stations: list[RadioStation], *, status: str) -> None:
        self._current_results = stations
        self._results.DeleteAllItems()
        for row, station in enumerate(stations):
            self._results.InsertItem(row, station.display_name)
            self._results.SetItem(row, 1, station.country)
            bitrate = f"{station.bitrate_kbps}k" if station.bitrate_kbps else ""
            fmt = " ".join(part for part in (station.codec, bitrate) if part)
            self._results.SetItem(row, 2, fmt)
        self._status.SetLabel(status)
        self._play_btn.Enable(False)
        self._favorite_btn.Enable(False)
        self._details.SetValue("")
        if stations:
            self._results.Select(0)
            self._results.Focus(0)

    def _show_category(self, category: str) -> None:
        index = _CATEGORIES.index(category)
        if self._category_list.GetSelection() != index:
            self._category_list.SetSelection(index)
        if category == _FAVORITES:
            stations = [f.station for f in self._favorites.favorites]
            status = (
                f"{len(stations)} favorite station(s)."
                if stations
                else "No favorite stations yet. Select a station and press Add to Favorites."
            )
            self._fill_results(stations, status=status)
        elif category == _ACB_MEDIA:
            stations = acb_media.acb_media_stations()
            status = f"{len(stations)} ACB Media stations from the American Council of the Blind."
            self._fill_results(stations, status=status)
        else:
            status = (
                f"{len(self._search_results)} search result(s)."
                if self._search_results
                else "Search above to see results here."
            )
            self._fill_results(self._search_results, status=status)

    # ------------------------------------------------------------------
    # Events

    def _on_category_selected(self, _event: object) -> None:
        selection = self._category_list.GetSelection()
        if selection != self._wx.NOT_FOUND:
            self._show_category(_CATEGORIES[selection])

    def _on_search(self, _event: object) -> None:
        name = self._name_ctrl.GetValue().strip()
        tag = self._tag_ctrl.GetValue().strip()
        country = self._country_ctrl.GetValue().strip()
        if not (name or tag or country):
            self._status.SetLabel("Type a station name, tag, or country to search.")
            return
        if self._safe_mode:
            self._status.SetLabel("Internet Radio search is disabled in Safe Mode.")
            return
        self._status.SetLabel("Searching RadioBrowser...")
        self._search_btn.Enable(False)

        def _do_search(**_kwargs: Any) -> list[RadioStation]:
            return radio_browser.search_stations(
                name, tag=tag, country=country, safe_mode=self._safe_mode
            )

        self._task_manager.submit(
            "radio-search",
            _do_search,
            on_success=lambda _op, stations: self._on_search_done(stations, None),
            on_failure=lambda _op, exc: self._on_search_done([], exc),
        )

    def _on_search_done(self, stations: list[RadioStation], error: BaseException | None) -> None:
        self._search_btn.Enable(True)
        self._search_results = stations
        if error is not None:
            self._status.SetLabel(f"Search failed: {error}")
            return
        self._show_category(_SEARCH_RESULTS)
        self._announce(f"{len(stations)} search results")

    def _on_result_selected(self, event: object) -> None:
        index = event.GetIndex()
        if 0 <= index < len(self._current_results):
            station = self._current_results[index]
            self._details.SetValue(station.details_text)
            self._play_btn.Enable(True)
            self._favorite_btn.Enable(True)
            self._update_favorite_button_label(station)

    def _update_favorite_button_label(self, station: RadioStation) -> None:
        if self._favorites.contains(station):
            self._favorite_btn.SetLabel("Remove from &Favorites")
        else:
            self._favorite_btn.SetLabel("Add to &Favorites")

    def _selected_station(self) -> RadioStation | None:
        index = self._results.GetFirstSelected()
        if 0 <= index < len(self._current_results):
            return self._current_results[index]
        return None

    def _on_activate(self, _event: object) -> None:
        self._on_play(_event)

    def _on_play(self, _event: object) -> None:
        station = self._selected_station()
        if station is None:
            return
        self._controller.play_station(station)
        self._announce(f"Playing {station.name}")

    def _on_volume_slider(self, _event: object) -> None:
        self._controller.set_volume(self._volume_slider.GetValue())
        self._mute_btn.SetValue(False)

    def _on_mute_toggle(self, _event: object) -> None:
        self._controller.toggle_mute()
        state = getattr(self._controller, "state", None)
        if state is not None:
            self._mute_btn.SetValue(state.muted)

    def _on_toggle_favorite(self, _event: object) -> None:
        station = self._selected_station()
        if station is None:
            return
        if self._favorites.contains(station):
            self._favorites.remove(station.station_uuid or station.stream_url)
            self._announce(f"Removed {station.name} from Favorites")
        else:
            self._favorites.add(station)
            self._announce(f"Added {station.name} to Favorites")
        self._update_favorite_button_label(station)
        self._on_favorites_changed()
        if self._category_list.GetSelection() == _CATEGORIES.index(_FAVORITES):
            self._show_category(_FAVORITES)

    def _on_add_custom(self, _event: object) -> None:
        if self._on_open_add_custom is not None:
            self._on_open_add_custom(None)
            self.refresh_favorites_view()

    def _on_link_finder(self, _event: object) -> None:
        if self._on_open_link_finder is not None:
            self._on_open_link_finder()
            self.refresh_favorites_view()
