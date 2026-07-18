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

from quill.core.radio import acb_media, radio_browser, soma_fm
from quill.core.radio.directory_search import (
    iheart_search_stations,
    merge_and_rank,
    tunein_search_stations,
)
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.ui.dialog_contract import apply_modal_ids

_FAVORITES = "Favorites"
_ACB_MEDIA = acb_media.CATEGORY_LABEL
_SEARCH_RESULTS = "Search Results"
_CATEGORIES = (_FAVORITES, _ACB_MEDIA, _SEARCH_RESULTS)

#: Source-facet choices (the Unified Find Stations filter). "All sources" is the
#: default; the rest match RadioStation.source values a search can produce. A
#: RadioBrowser result has an empty source, so it filters under "RadioBrowser".
_ALL_SOURCES = "All sources"
_SOURCE_FACETS = (
    _ALL_SOURCES,
    "RadioBrowser",
    "iHeart",
    "TuneIn",
    "SomaFM",
    "ACB Media",
    "Website",
)

#: How many stations a search returns (#1064). RadioBrowser's own API caps a
#: single request at 200; we ask for all of it (ordered most-listened first)
#: instead of the library default of 50, which was quietly hiding the long
#: tail of a broad search like "news". When a result set actually reaches the
#: cap, the dialog says so and suggests narrowing, rather than pretending the
#: 200th station is the last one that exists.
_SEARCH_LIMIT = 200


def _search_result_summary(count: int, *, more: bool = False) -> str:
    """The spoken/visible summary of a finished search (#1064).

    Pure so it's unit-testable without wx. When *more* is set (the last page
    filled, so the directory has further matches), it points the listener at
    the More Stations button and at narrowing -- so a broad search like "news"
    no longer looks like the 200th station is the last one in the world.
    """
    if count == 0:
        return "No stations found. Try a different name, tag, or country."
    plural = "" if count == 1 else "s"
    if more:
        return (
            f"{count} stations, most-listened first -- press More Stations for the "
            "next page, or add a tag or country to narrow the list."
        )
    return f"{count} station{plural} found."


#: The "no country filter" entry shown first in the Country dropdown (#2 /
#: quill-radio #2 -- country/genre are now pickable, not typo-prone free text).
_ANY_COUNTRY = "(Any country)"

#: Session cache of RadioBrowser's country/tag lists, so re-opening Browse
#: Stations doesn't refetch them. Populated off-thread on first open.
_directory_choices_cache: tuple[list[str], list[str]] | None = None


def country_query(choice_label: str) -> str:
    """The RadioBrowser country filter for a Country-dropdown label (pure).

    The "(Any country)" sentinel means no filter; every other label is the
    country name itself. Testable without wx.
    """
    label = choice_label.strip()
    return "" if label in ("", _ANY_COUNTRY) else label


def looks_like_url(text: str) -> bool:
    """True when *text* is a website address, not a station-name query (pure).

    Lets the one search box fold in "Find Streams from a Website": an entry
    that is a URL (explicit scheme, or a bare ``host.tld/...`` with no spaces)
    is scanned for streams instead of run as a directory name search.
    """
    value = text.strip()
    if not value or " " in value:
        return False
    if value.lower().startswith(("http://", "https://")):
        return True
    host = value.split("/", 1)[0]
    return "." in host and " " not in host and not host.endswith(".")


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
        #: The unfiltered list behind _current_results, so the Source facet can
        #: filter what's shown without re-running the search.
        self._all_results: list[RadioStation] = []
        self._fill_status: str = ""
        self._search_results: list[RadioStation] = []
        # Pagination state for #1064: the query behind the current results, the
        # RadioBrowser and SomaFM halves kept apart so paging appends only more
        # RadioBrowser rows, the next page's offset, and whether the last page
        # was full (so more may exist).
        self._search_rb: list[RadioStation] = []
        #: SomaFM + TuneIn + iHeart results, blended after the RadioBrowser page
        #: and kept at the end across "More Stations" paging (which pages only
        #: RadioBrowser).
        self._search_extras: list[RadioStation] = []
        #: The iHeart sitemap station index, fetched once per dialog session on
        #: the first search that needs it (2 GETs), then filtered in-process.
        self._iheart_index_cache: list[Any] | None = None
        self._search_query = ""
        self._search_tag = ""
        self._search_country = ""
        self._search_offset = 0
        self._search_more_available = False

        self.dialog = wx.Dialog(
            parent, title="Internet Radio", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((700, 520))
        self.dialog.SetSize((820, 600))
        root = wx.BoxSizer(wx.VERTICAL)

        search_box = wx.StaticBoxSizer(wx.HORIZONTAL, self.dialog, "Search Stations")
        search_grid = wx.FlexGridSizer(cols=2, gap=(6, 4))
        search_grid.AddGrowableCol(1, 1)

        def _labeled_field(label: str, *, accessible_name: str) -> wx.TextCtrl:
            search_grid.Add(wx.StaticText(self.dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
            ctrl.SetName(accessible_name)
            search_grid.Add(ctrl, 1, wx.EXPAND)
            return ctrl

        self._name_ctrl = _labeled_field(
            "Station &name:", accessible_name="Station name to search for"
        )
        # Tag/genre and Country are pickable dropdowns (quill-radio #2), filled
        # off-thread from RadioBrowser's own lists so they are not typo-prone
        # free text. Tag stays an editable combo so a rare custom tag still
        # works; Country is a plain choice with an "Any" default.
        search_grid.Add(
            wx.StaticText(self.dialog, label="&Tag/genre (optional):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._tag_ctrl = wx.ComboBox(self.dialog, style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER)
        self._tag_ctrl.SetName(
            "Tag or genre to narrow the search; pick one from the list or type your own, e.g. jazz"
        )
        search_grid.Add(self._tag_ctrl, 1, wx.EXPAND)

        search_grid.Add(
            wx.StaticText(self.dialog, label="&Country (optional):"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._country_ctrl = wx.Choice(self.dialog, choices=[_ANY_COUNTRY])
        self._country_ctrl.SetName(
            "Country to narrow the search; choose from the list, or leave as Any country"
        )
        self._country_ctrl.SetSelection(0)
        search_grid.Add(self._country_ctrl, 1, wx.EXPAND)
        search_box.Add(search_grid, 1, wx.EXPAND | wx.ALL, 6)
        search_col = wx.BoxSizer(wx.VERTICAL)
        self._search_btn = wx.Button(self.dialog, label="&Search")
        self._search_btn.SetName("Search for stations matching these fields")
        # No alignment flag: vertical alignment flags assert-fail inside a
        # vertical sizer (wx 4.2+), which killed the dialog before it opened.
        search_col.Add(self._search_btn, 0)
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
        facet_row = wx.BoxSizer(wx.HORIZONTAL)
        facet_row.Add(
            wx.StaticText(self.dialog, label="So&urce:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self._source_facet = wx.Choice(self.dialog, choices=list(_SOURCE_FACETS))
        self._source_facet.SetName("Show only results from one source")
        self._source_facet.SetSelection(0)
        facet_row.Add(self._source_facet, 0)
        results_col.Add(facet_row, 0, wx.BOTTOM, 4)
        self._results = wx.ListCtrl(self.dialog, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._results.SetName("Station results; arrow through to hear details of each")
        self._results.InsertColumn(0, "Name", width=240)
        self._results.InsertColumn(1, "Country", width=120)
        self._results.InsertColumn(2, "Format", width=110)
        self._results.InsertColumn(3, "Source", width=110)
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
        self._more_btn = wx.Button(self.dialog, label="&More Stations")
        self._more_btn.SetName("Load the next page of search results")
        self._more_btn.Enable(False)
        add_custom_btn = wx.Button(self.dialog, label="Add &Custom Station...")
        add_custom_btn.SetName("Add a station by typing its own stream link")
        link_finder_btn = wx.Button(self.dialog, label="Find Streams from a &Website...")
        link_finder_btn.SetName("Scan a website you type in for stream links")
        self._refresh_btn = wx.Button(self.dialog, label="&Refresh Directory")
        self._refresh_btn.SetName("Re-fetch the iHeart station directory used by search")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close (playback continues)")
        btn_row.Add(self._play_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._favorite_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._more_btn, 0, wx.RIGHT, 6)
        btn_row.Add(add_custom_btn, 0, wx.RIGHT, 6)
        btn_row.Add(link_finder_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._refresh_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._name_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        self._tag_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        # Picking a tag or a country fires the search immediately (as well as
        # the Search button), so the dropdowns feel like filters.
        self._tag_ctrl.Bind(wx.EVT_COMBOBOX, self._on_search)
        self._country_ctrl.Bind(wx.EVT_CHOICE, self._on_search)
        self._search_btn.Bind(wx.EVT_BUTTON, self._on_search)
        self._category_list.Bind(wx.EVT_LISTBOX, self._on_category_selected)
        self._results.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_result_selected)
        self._results.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_activate)
        self._results.Bind(wx.EVT_CONTEXT_MENU, self._on_results_context_menu)
        self._play_btn.Bind(wx.EVT_BUTTON, self._on_play)
        self._favorite_btn.Bind(wx.EVT_BUTTON, self._on_toggle_favorite)
        self._more_btn.Bind(wx.EVT_BUTTON, self._on_more_stations)
        add_custom_btn.Bind(wx.EVT_BUTTON, self._on_add_custom)
        link_finder_btn.Bind(wx.EVT_BUTTON, self._on_link_finder)
        self._refresh_btn.Bind(wx.EVT_BUTTON, self._on_refresh_directory)
        self._source_facet.Bind(wx.EVT_CHOICE, self._on_source_facet)
        self._volume_slider.Bind(wx.EVT_SLIDER, self._on_volume_slider)
        self._mute_btn.Bind(wx.EVT_TOGGLEBUTTON, self._on_mute_toggle)
        # #1070: Ctrl+Up/Ctrl+Down (Volume Up/Down) must work while browsing.
        # This is a modal dialog, so the frame's Playback-menu accelerators
        # never fire here; and the results ListCtrl (the default focus after a
        # search) claims bare Up/Down for its own row navigation. A dialog-wide
        # CHAR_HOOK catches the Ctrl chord before any child control sees it,
        # regardless of where focus sits (list, slider, buttons), and leaves
        # bare Up/Down untouched so list navigation and the slider still work.
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

        state = getattr(self._controller, "state", None)
        if state is not None:
            self._volume_slider.SetValue(state.volume_percent)
            self._mute_btn.SetValue(state.muted)

        self._show_category(_FAVORITES)
        self._populate_directory_choices()

    def _populate_directory_choices(self) -> None:
        """Fill the Tag and Country dropdowns from RadioBrowser, off-thread.

        Cached for the session so re-opening the dialog is instant; skipped in
        Safe Mode (no network). A fetch failure just leaves the dropdowns with
        their defaults -- the user can still type a tag and search without a
        country filter."""
        global _directory_choices_cache
        if self._safe_mode:
            return
        if _directory_choices_cache is not None:
            self._apply_directory_choices(*_directory_choices_cache)
            return

        def _fetch(**_kwargs: Any) -> tuple[list[str], list[str]]:
            try:
                countries = radio_browser.list_countries(safe_mode=self._safe_mode)
            except radio_browser.RadioBrowserError:
                countries = []
            try:
                tags = radio_browser.list_tags(safe_mode=self._safe_mode)
            except radio_browser.RadioBrowserError:
                tags = []
            return countries, tags

        def _done(_op: str, payload: tuple[list[str], list[str]]) -> None:
            global _directory_choices_cache
            _directory_choices_cache = payload
            self._wx.CallAfter(self._apply_directory_choices, *payload)

        self._task_manager.submit(
            "radio-directory-choices", _fetch, on_success=_done, on_failure=lambda *_a: None
        )

    def _apply_directory_choices(self, countries: list[str], tags: list[str]) -> None:
        """Populate the Country choice and Tag combo (UI thread), preserving the
        current selection/text."""
        if countries and self._country_ctrl.GetCount() <= 1:
            current = self._country_ctrl.GetStringSelection()
            self._country_ctrl.Set([_ANY_COUNTRY, *countries])
            index = self._country_ctrl.FindString(current) if current else 0
            self._country_ctrl.SetSelection(index if index != self._wx.NOT_FOUND else 0)
        if tags and self._tag_ctrl.GetCount() == 0:
            typed = self._tag_ctrl.GetValue()
            self._tag_ctrl.Set(tags)
            self._tag_ctrl.SetValue(typed)

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

    def _source_label(self, station: RadioStation) -> str:
        """The Source-column/facet label for *station* (RadioBrowser default)."""
        return station.source or "RadioBrowser"

    def _apply_source_facet(self, stations: list[RadioStation]) -> list[RadioStation]:
        """Filter *stations* by the current Source facet (All = everything)."""
        choice = self._source_facet.GetStringSelection() or _ALL_SOURCES
        if choice == _ALL_SOURCES:
            return stations
        return [s for s in stations if self._source_label(s) == choice]

    def _fill_results(self, stations: list[RadioStation], *, status: str) -> None:
        # Keep the full list so the Source facet can filter without re-searching.
        self._all_results = stations
        self._fill_status = status
        self._render_results()

    def _render_results(self) -> None:
        stations = self._apply_source_facet(self._all_results)
        self._current_results = stations
        self._results.DeleteAllItems()
        for row, station in enumerate(stations):
            # Blended non-RadioBrowser sources name themselves in the row so a
            # listener can tell where a station came from (iHeart, TuneIn, ...).
            label = station.display_name
            source = self._source_label(station)
            if source != "RadioBrowser":
                label = f"{label} - via {source}"
            self._results.InsertItem(row, label)
            self._results.SetItem(row, 1, station.country)
            bitrate = f"{station.bitrate_kbps}k" if station.bitrate_kbps else ""
            fmt = " ".join(part for part in (station.codec, bitrate) if part)
            self._results.SetItem(row, 2, fmt)
            self._results.SetItem(row, 3, source)
        self._status.SetLabel(self._fill_status)
        self._play_btn.Enable(False)
        self._favorite_btn.Enable(False)
        self._details.SetValue("")
        if stations:
            self._results.Select(0)
            self._results.Focus(0)

    def _on_source_facet(self, _event: object) -> None:
        """Re-render the current results filtered by the chosen source."""
        self._render_results()
        self._announce(
            _search_result_summary(len(self._current_results))
            + f" -- {self._source_facet.GetStringSelection()}"
        )

    def _on_refresh_directory(self, _event: object) -> None:
        """Re-fetch the iHeart station directory (its 2-GET sitemap index) off
        thread, so a stale/expanded catalog is picked up without restarting.
        TuneIn and RadioBrowser are always live, so only iHeart is cached."""
        if self._safe_mode:
            self._status.SetLabel("Refreshing the directory is disabled in Safe Mode.")
            return
        self._refresh_btn.Enable(False)
        self._status.SetLabel("Refreshing the iHeart directory...")

        def _do_refresh(**_kwargs: Any) -> int:
            from quill.core.radio import iheart

            try:
                index = iheart.fetch_station_index(safe_mode=self._safe_mode)
            except iheart.IHeartError:
                index = []
            self._iheart_index_cache = index
            return len(index)

        self._task_manager.submit(
            "radio-refresh-directory",
            _do_refresh,
            on_success=lambda _op, count: self._wx.CallAfter(self._on_refresh_done, count, None),
            on_failure=lambda _op, exc: self._wx.CallAfter(self._on_refresh_done, 0, exc),
        )

    def _on_refresh_done(self, count: int, error: BaseException | None) -> None:
        self._refresh_btn.Enable(True)
        if error is not None:
            self._status.SetLabel(f"Could not refresh the directory: {error}")
            return
        message = f"iHeart directory refreshed: {count} stations."
        self._status.SetLabel(message)
        self._announce(message)

    def _search_website(self, url: str) -> None:
        """Scan *url* for streams and show them as ``source="Website"`` results,
        folding the website finder into the one search box."""
        self._status.SetLabel(f"Scanning {url} for streams...")
        self._search_btn.Enable(False)
        self._more_btn.Enable(False)

        def _do_scan(**_kwargs: Any) -> list[RadioStation]:
            from quill.core.radio import link_finder

            try:
                result = link_finder.scan_page_for_streams(url, safe_mode=self._safe_mode)
            except link_finder.LinkFinderError:
                return []
            return [
                RadioStation(
                    name=candidate.label or candidate.reason or "Website stream",
                    stream_url=candidate.url,
                    homepage=url,
                    source="Website",
                )
                for candidate in result.candidates
            ]

        self._task_manager.submit(
            "radio-website-scan",
            _do_scan,
            on_success=lambda _op, stations: self._wx.CallAfter(
                self._on_website_scan_done, stations, None
            ),
            on_failure=lambda _op, exc: self._wx.CallAfter(self._on_website_scan_done, [], exc),
        )

    def _on_website_scan_done(
        self, stations: list[RadioStation], error: BaseException | None
    ) -> None:
        self._search_btn.Enable(True)
        if error is not None:
            self._status.SetLabel(f"Website scan failed: {error}")
            return
        self._search_rb = []
        self._search_extras = stations
        self._search_results = merge_and_rank([stations], self._search_query)
        self._search_more_available = False
        self._more_btn.Enable(False)
        self._show_category(_SEARCH_RESULTS)
        count = len(self._search_results)
        self._announce(
            f"{count} stream{'' if count == 1 else 's'} found on the website."
            if count
            else "No streams found on that website."
        )

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
                _search_result_summary(len(self._search_results), more=self._search_more_available)
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
        country = country_query(self._country_ctrl.GetStringSelection())
        if not (name or tag or country):
            self._status.SetLabel("Type a station name, tag, or country to search.")
            return
        if self._safe_mode:
            self._status.SetLabel("Internet Radio search is disabled in Safe Mode.")
            return
        # Fold in the website scanner: a URL in the name box is scanned for
        # streams instead of run as a directory search (the "Find Streams from a
        # Website..." button stays as an explicit shortcut).
        if looks_like_url(name):
            self._search_website(name)
            return
        self._status.SetLabel("Searching stations...")
        self._search_btn.Enable(False)
        self._more_btn.Enable(False)
        # Remember the query so "More Stations" can page the same search.
        self._search_query, self._search_tag, self._search_country = name, tag, country
        self._search_offset = 0

        def _do_search(**_kwargs: Any) -> tuple[list[RadioStation], list[RadioStation]]:
            radio = radio_browser.search_stations(
                name, tag=tag, country=country, limit=_SEARCH_LIMIT, safe_mode=self._safe_mode
            )
            # Blended in after the RadioBrowser page, each failure-tolerant so
            # one down source never blanks the list. Name/tag searches only:
            # these directories have no country field of their own, so a
            # country-only query skips them rather than returning noise. They
            # ride along with the first RadioBrowser page; "More Stations" pages
            # RadioBrowser alone.
            extras: list[RadioStation] = []
            query = name or tag
            if query:
                try:
                    extras += soma_fm.search_stations(query, safe_mode=self._safe_mode)
                except soma_fm.SomaFmError:
                    pass
                extras += tunein_search_stations(query, safe_mode=self._safe_mode)
            if name:
                extras += iheart_search_stations(
                    self._iheart_index(), name, safe_mode=self._safe_mode
                )
            return radio, extras

        self._task_manager.submit(
            "radio-search",
            _do_search,
            on_success=lambda _op, payload: self._on_search_done(payload, None),
            on_failure=lambda _op, exc: self._on_search_done(([], []), exc),
        )

    def _iheart_index(self) -> list[Any]:
        """The iHeart sitemap station index, fetched once per session (2 GETs).

        Runs inside the off-thread search worker. A fetch failure caches an
        empty list so a broken/blocked iHeart never re-hammers the network on
        every keystroke's search.
        """
        if self._iheart_index_cache is None:
            from quill.core.radio import iheart

            try:
                self._iheart_index_cache = iheart.fetch_station_index(safe_mode=self._safe_mode)
            except iheart.IHeartError:
                self._iheart_index_cache = []
        return self._iheart_index_cache

    def _on_search_done(
        self,
        payload: tuple[list[RadioStation], list[RadioStation]],
        error: BaseException | None,
    ) -> None:
        self._search_btn.Enable(True)
        if error is not None:
            self._status.SetLabel(f"Search failed: {error}")
            return
        radio, extras = payload
        self._search_rb = radio
        self._search_extras = extras
        # Unified merge: de-dup across sources (a stream on two directories, or
        # the same station name+country twice) and float exact-name matches up.
        self._search_results = merge_and_rank([radio, extras], self._search_query)
        self._search_offset = len(radio)
        self._search_more_available = len(radio) >= _SEARCH_LIMIT
        self._more_btn.Enable(self._search_more_available)
        self._show_category(_SEARCH_RESULTS)
        self._announce(
            _search_result_summary(len(self._search_results), more=self._search_more_available)
        )
        # Land keyboard focus in the results list when a search returns something,
        # so the user is placed on the first result (already selected/focused as
        # row 0 by _render_results) instead of being left on the search box having
        # to Tab into the list.
        if self._current_results:
            self._results.SetFocus()

    def _on_more_stations(self, _event: object) -> None:
        """Fetch and append the next page of RadioBrowser results (#1064)."""
        if not self._search_more_available:
            return
        self._more_btn.Enable(False)
        self._status.SetLabel("Loading more stations...")
        offset = self._search_offset
        name, tag, country = self._search_query, self._search_tag, self._search_country

        def _do_more(**_kwargs: Any) -> list[RadioStation]:
            return radio_browser.search_stations(
                name,
                tag=tag,
                country=country,
                limit=_SEARCH_LIMIT,
                offset=offset,
                safe_mode=self._safe_mode,
            )

        self._task_manager.submit(
            "radio-search-more",
            _do_more,
            on_success=lambda _op, stations: self._on_more_done(stations, None),
            on_failure=lambda _op, exc: self._on_more_done([], exc),
        )

    def _on_more_done(self, stations: list[RadioStation], error: BaseException | None) -> None:
        if error is not None:
            self._status.SetLabel(f"Could not load more: {error}")
            self._more_btn.Enable(True)  # let the user try again
            return
        first_new_index = len(self._search_results)
        self._search_rb = self._search_rb + stations
        self._search_results = merge_and_rank(
            [self._search_rb, self._search_extras], self._search_query
        )
        self._search_offset += len(stations)
        self._search_more_available = len(stations) >= _SEARCH_LIMIT
        self._more_btn.Enable(self._search_more_available)
        self._show_category(_SEARCH_RESULTS)
        # Land focus on the first newly added station so the reader picks up
        # right where the previous page ended, not back at the top.
        if stations and first_new_index < len(self._current_results):
            self._results.Select(first_new_index)
            self._results.Focus(first_new_index)
            self._results.EnsureVisible(first_new_index)
        self._announce(
            f"Added {len(stations)} more; {len(self._search_results)} stations now."
            if stations
            else "No more stations."
        )

    def _on_result_selected(self, event: object) -> None:
        index = event.GetIndex()
        if 0 <= index < len(self._current_results):
            station = self._current_results[index]
            self._details.SetValue(station.details_text)
            self._play_btn.Enable(True)
            self._favorite_btn.Enable(True)
            self._update_favorite_button_label(station)
            self._refresh_play_button()

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

    def _on_results_context_menu(self, _event: object) -> None:
        """Shift+F10 / right-click on a result: every action for the
        highlighted station, mirroring the main page's favorites tree."""
        import wx

        station = self._selected_station()
        if station is None:
            return
        playing = self._is_station_playing(station)
        saved = self._favorites.contains(station)
        entries = [
            ("&Stop" if playing else "&Play", lambda: self._on_play(None)),
            (
                "Remove from &Favorites" if saved else "Add to &Favorites",
                lambda: self._on_toggle_favorite(None),
            ),
        ]
        menu = wx.Menu()
        id_refs = []
        for label, handler in entries:
            item_id = wx.NewIdRef()
            id_refs.append(item_id)
            menu.Append(item_id, label)
            menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
        self._context_menu_id_refs = id_refs  # pinned while the popup can fire
        self._results.PopupMenu(menu)
        menu.Destroy()

    def _is_station_playing(self, station: RadioStation) -> bool:
        from quill.ui.radio.player_controller import RadioPlayerState

        state = self._controller.state
        return (
            state.station is not None
            and state.station.stream_url == station.stream_url
            and state.state in (RadioPlayerState.PLAYING, RadioPlayerState.CONNECTING)
        )

    def _refresh_play_button(self) -> None:
        station = self._selected_station()
        stopping = station is not None and self._is_station_playing(station)
        self._play_btn.SetLabel("&Stop" if stopping else "&Play")
        self._play_btn.SetName("Stop this station" if stopping else "Play the selected station")

    def _on_play(self, _event: object) -> None:
        station = self._selected_station()
        if station is None:
            return
        # One button, honest label: it stops the station it started.
        if self._is_station_playing(station):
            self._controller.stop()
            self._announce("Radio stopped")
        else:
            self._controller.play_station(station)
            self._announce(f"Playing {station.name}")
        self._refresh_play_button()

    def _on_char_hook(self, event: object) -> None:
        """Handle Ctrl+Up/Ctrl+Down as Volume Up/Down from anywhere in the
        dialog (#1070); everything else passes through untouched."""
        wx = self._wx
        if event.ControlDown() and not event.ShiftDown() and not event.AltDown():
            code = event.GetKeyCode()
            if code == wx.WXK_UP:
                self._adjust_volume(up=True)
                return
            if code == wx.WXK_DOWN:
                self._adjust_volume(up=False)
                return
        event.Skip()

    def _adjust_volume(self, *, up: bool) -> None:
        """Step the radio volume and keep the dialog's own slider/mute in sync.

        Goes through the controller (the single source of truth every surface
        shares), then mirrors the new level onto this dialog's slider and mute
        button and announces it, matching the wording of the Playback menu's
        Volume Up/Down.
        """
        if up:
            self._controller.volume_up()
        else:
            self._controller.volume_down()
        state = getattr(self._controller, "state", None)
        if state is None:
            return
        self._volume_slider.SetValue(state.volume_percent)
        self._mute_btn.SetValue(state.muted)
        self._announce(f"Radio volume {state.volume_percent}")

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
