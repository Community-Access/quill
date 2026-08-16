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

from quill.core.radio import (
    acb_media,
    m3u_catalog,
    radio_browser,
    search_sources,
    soma_fm,
    tunein,
    xiph,
)
from quill.core.radio.directory_search import (
    iheart_search_stations,
    merge_and_rank,
    reading_services_search_stations,
    station_source_labels,
    tunein_search_stations,
    wxindex_search_stations,
)
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.core.radio.spotify_search import (
    SOURCE as _SPOTIFY_SOURCE,
)
from quill.core.radio.spotify_search import (
    is_spotify_station,
    open_link_label,
    spotify_search_stations,
    youtube_search_stations,
)
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.radio import library_search

_FAVORITES = "Favorites"
_ACB_MEDIA = acb_media.CATEGORY_LABEL
_SOMAFM = "SomaFM"
#: TuneIn's category tree (Music, Talk, Sports, Local, ...), browsed as folders.
_TUNEIN_BROWSE = "TuneIn"
#: Community M3U (junguler catalog): a genre-picker category, browsed on demand.
_M3U_GENRES = "Music Genres"
# NFB Radio is a single stream, so it lives only on the Station menu (next to ACB
# Media), not as a browse category here -- there is nothing to "browse".
#: Xiph/Icecast public directory: the other genre-picker (browse-by-genre) source.
_XIPH_DIR = "Xiph Directory"
#: RadioBrowser's most-voted stations -- browse what everyone's listening to.
_POPULAR = "Popular Stations"
_SEARCH_RESULTS = "Search Results"
#: Browsable-without-search categories come first; Search Results last. ACB
#: Media and NFB Radio are bundled (instant); SomaFM and Music Genres fetch on
#: demand. Kelly's request: pick a source and see its stations, no query needed.
_CATEGORIES = (
    _FAVORITES,
    _POPULAR,
    _ACB_MEDIA,
    _SOMAFM,
    _TUNEIN_BROWSE,
    _M3U_GENRES,
    _XIPH_DIR,
    _SEARCH_RESULTS,
)

#: The two genre-picker sources share one code path; each module exposes the
#: same fetch_genres / fetch_genre_stations / genre_display / CATALOG_CREDIT.
_GENRE_SOURCES = {_M3U_GENRES: m3u_catalog, _XIPH_DIR: xiph}

#: The browse sources offered as the Station menu's "Browse Stations" submenu,
#: in menu order -- each opens this dialog straight to that source. Favorites and
#: Search Results are not "browse a source" choices, so they are not listed.
BROWSE_MENU_CATEGORIES: tuple[str, ...] = (
    _POPULAR,
    _ACB_MEDIA,
    _SOMAFM,
    _TUNEIN_BROWSE,
    _M3U_GENRES,
    _XIPH_DIR,
)

#: Source-facet choices (the Unified Find Stations filter). "All sources" is the
#: default; the rest match RadioStation.source values a search can produce. A
#: RadioBrowser result has an empty source, so it filters under "Radio Browser".
#: #1194: this facet reads "Radio Browser" (two words), not the internal
#: "RadioBrowser" -- a screen-reader user hearing the run-together word thought
#: the source was gone. The label is spelled the human way here and everywhere it
#: is derived (directory_search.station_source_labels, _source_label below).
_ALL_SOURCES = "All sources"
_SOURCE_FACETS = (
    _ALL_SOURCES,
    "Radio Browser",
    "iHeart",
    "TuneIn",
    "SomaFM",
    "ACB Media",
    m3u_catalog.CATEGORY_LABEL,
    xiph.CATEGORY_LABEL,
    _SPOTIFY_SOURCE,
    "YouTube",
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
        on_report_bad_station: Callable[[RadioStation], None] | None = None,
        show_details: bool = True,
        windows: object | None = None,
        spotify_client_provider: Callable[[], object | None] | None = None,
        enabled_sources: object = None,
        catalog: object | None = None,
        source_facet: str = "",
        on_search_prefs_changed: Callable[[tuple[str, ...], str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._menu_id_refs: list[object] = []
        self._controller = controller
        self._favorites = favorites_store
        self._task_manager = task_manager
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._on_favorites_changed = on_favorites_changed or (lambda: None)
        self._on_open_add_custom = on_open_add_custom
        self._on_open_link_finder = on_open_link_finder
        self._on_report_bad_station = on_report_bad_station
        # Returns a signed-in SpotifyClient, or None when nobody has connected
        # Spotify (the common case) -- searching Spotify needs a token even
        # though it works on every account tier, playback tier included.
        self._spotify_client_provider = spotify_client_provider
        #: Which sources this search covers. Remembered across sessions: a
        #: preference you must re-set on every search is not a preference.
        self._enabled_sources = search_sources.normalize(enabled_sources)
        #: The local station catalog, for the instant search lane. Optional.
        self._catalog = catalog
        #: The remembered Source-facet choice, re-applied when the dialog opens.
        self._initial_source_facet = str(source_facet or "")
        self._on_search_prefs_changed = on_search_prefs_changed

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

        # Modeless wx.Frame (with the persistent menu bar + &Window menu, controls
        # on an inner panel) when a WindowManager is supplied by standalone Radio;
        # otherwise an unchanged modal wx.Dialog for embedded QUILL.
        self._windows = windows
        self._modeless = windows is not None
        if self._modeless:
            self._win = wx.Frame(parent, title="Internet Radio", style=wx.DEFAULT_FRAME_STYLE)
            self._surface = wx.Panel(self._win, style=wx.TAB_TRAVERSAL)
            self._build_surface_menu_bar()
            self._win.Bind(wx.EVT_CLOSE, self._on_close)
        else:
            self._win = wx.Dialog(
                parent, title="Internet Radio", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
            )
            self._surface = self._win
        self.dialog = self._win  # back-compat alias for callers that reference it
        self._win.SetMinSize((700, 520))
        self._win.SetSize((820, 600))
        root = wx.BoxSizer(wx.VERTICAL)

        search_box = wx.StaticBoxSizer(wx.HORIZONTAL, self._surface, "Search Stations")
        search_grid = wx.FlexGridSizer(cols=2, gap=(6, 4))
        search_grid.AddGrowableCol(1, 1)

        def _labeled_field(label: str, *, accessible_name: str) -> wx.TextCtrl:
            search_grid.Add(wx.StaticText(self._surface, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = wx.TextCtrl(self._surface, style=wx.TE_PROCESS_ENTER)
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
            wx.StaticText(self._surface, label="&Tag/genre (optional):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._tag_ctrl = wx.ComboBox(self._surface, style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER)
        self._tag_ctrl.SetName(
            "Tag or genre to narrow the search; pick one from the list or type your own, e.g. jazz"
        )
        search_grid.Add(self._tag_ctrl, 1, wx.EXPAND)

        search_grid.Add(
            wx.StaticText(self._surface, label="&Country (optional):"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._country_ctrl = wx.Choice(self._surface, choices=[_ANY_COUNTRY])
        self._country_ctrl.SetName(
            "Country to narrow the search; choose from the list, or leave as Any country"
        )
        self._country_ctrl.SetSelection(0)
        search_grid.Add(self._country_ctrl, 1, wx.EXPAND)
        search_box.Add(search_grid, 1, wx.EXPAND | wx.ALL, 6)
        search_col = wx.BoxSizer(wx.VERTICAL)
        self._search_btn = wx.Button(self._surface, label="&Search")
        self._search_btn.SetName("Search for stations matching these fields")
        # No alignment flag: vertical alignment flags assert-fail inside a
        # vertical sizer (wx 4.2+), which killed the dialog before it opened.
        search_col.Add(self._search_btn, 0)
        search_box.Add(search_col, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)
        root.Add(search_box, 0, wx.EXPAND | wx.ALL, 10)

        body = wx.BoxSizer(wx.HORIZONTAL)
        cat_col = wx.BoxSizer(wx.VERTICAL)
        cat_col.Add(wx.StaticText(self._surface, label="&Category"), 0, wx.BOTTOM, 4)
        self._category_list = wx.ListBox(self._surface, choices=list(_CATEGORIES))
        self._category_list.SetName(
            "Station category; Favorites, Popular Stations, ACB Media, SomaFM, "
            "TuneIn (a folder tree), Music Genres, and the Xiph Directory browse "
            "without a search, Search Results appears after a search"
        )
        self._category_list.SetSelection(0)
        cat_col.Add(self._category_list, 1, wx.EXPAND)
        body.Add(cat_col, 1, wx.EXPAND | wx.RIGHT, 10)

        results_col = wx.BoxSizer(wx.VERTICAL)
        results_col.Add(wx.StaticText(self._surface, label="&Stations"), 0, wx.BOTTOM, 4)
        facet_row = wx.BoxSizer(wx.HORIZONTAL)
        facet_row.Add(
            wx.StaticText(self._surface, label="So&urce:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self._source_facet = wx.Choice(self._surface, choices=list(_SOURCE_FACETS))
        self._source_facet.SetName("Show only results from one source")
        # Re-apply the remembered facet: a filter you must re-pick on every
        # search is not a filter. An unknown stored value falls back to
        # "All sources" rather than to an empty list.
        remembered = self._initial_source_facet
        self._source_facet.SetSelection(
            _SOURCE_FACETS.index(remembered) if remembered in _SOURCE_FACETS else 0
        )
        facet_row.Add(self._source_facet, 0, wx.RIGHT, 12)
        # Genre picker for the Music Genres (Community M3U) category. Empty and
        # disabled until that category is selected, then filled from the live
        # genre list; picking a genre browses it.
        self._genre_label = wx.StaticText(self._surface, label="&Genre:")
        facet_row.Add(self._genre_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self._genre_ctrl = wx.Choice(self._surface, choices=[])
        self._genre_ctrl.SetName("Music genre to browse (Community M3U catalog)")
        self._genre_ctrl.Enable(False)
        self._genre_slugs: list[str] = []
        facet_row.Add(self._genre_ctrl, 0)
        results_col.Add(facet_row, 0, wx.BOTTOM, 4)
        self._results = wx.ListCtrl(self._surface, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._results.SetName("Station results; arrow through to hear details of each")
        self._results.InsertColumn(0, "Name", width=240)
        self._results.InsertColumn(1, "Country", width=120)
        self._results.InsertColumn(2, "Format", width=110)
        self._results.InsertColumn(3, "Source", width=110)
        results_col.Add(self._results, 1, wx.EXPAND)
        # TuneIn's directory is a real tree, so it browses in a TreeCtrl that
        # takes the results area's place while the TuneIn category is selected:
        # folders expand (lazily fetched), Enter opens a folder or plays a
        # station. Hidden until TuneIn is chosen.
        self._tunein_tree = wx.TreeCtrl(
            self._surface,
            style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT | wx.BORDER_SIMPLE,
        )
        self._tunein_tree.SetName(
            "TuneIn categories; press Enter to open a folder or play a station"
        )
        self._tunein_tree.Hide()
        results_col.Add(self._tunein_tree, 1, wx.EXPAND)
        body.Add(results_col, 2, wx.EXPAND)
        root.Add(body, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        details_label = wx.StaticText(self._surface, label="Station details")
        root.Add(details_label, 0, wx.LEFT | wx.TOP, 10)
        self._details = wx.TextCtrl(
            self._surface, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self._details.SetName("Read-only details of the selected station")
        root.Add(self._details, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        if not show_details:
            root.Hide(details_label)
            root.Hide(self._details)  # View > Show Station Details (honored per surface)

        self._status = wx.StaticText(self._surface, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        volume_row = wx.BoxSizer(wx.HORIZONTAL)
        volume_row.Add(
            wx.StaticText(self._surface, label="Radio &volume:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._volume_slider = wx.Slider(self._surface, value=100, minValue=0, maxValue=100)
        self._volume_slider.SetName(
            "Internet Radio's own volume, separate from your system volume and screen reader"
        )
        volume_row.Add(self._volume_slider, 1, wx.EXPAND | wx.RIGHT, 6)
        self._mute_btn = wx.ToggleButton(self._surface, label="&Mute")
        self._mute_btn.SetName("Mute or unmute Internet Radio")
        volume_row.Add(self._mute_btn, 0)
        root.Add(volume_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._play_btn = wx.Button(self._surface, label="&Play")
        self._play_btn.SetName("Play the selected station")
        self._play_btn.Enable(False)
        self._favorite_btn = wx.Button(self._surface, label="Add to &Favorites")
        self._favorite_btn.SetName("Add or remove the selected station from Favorites")
        self._favorite_btn.Enable(False)
        self._more_btn = wx.Button(self._surface, label="&More Stations")
        self._more_btn.SetName("Load the next page of search results")
        self._more_btn.Enable(False)
        add_custom_btn = wx.Button(self._surface, label="Add &Custom Station...")
        add_custom_btn.SetName("Add a station by typing its own stream link")
        link_finder_btn = wx.Button(self._surface, label="Find Streams from a &Website...")
        link_finder_btn.SetName("Scan a website you type in for stream links")
        self._refresh_btn = wx.Button(self._surface, label="&Refresh")
        self._refresh_btn.SetName(
            "Re-fetch the current source from the internet -- the Music Genres "
            "list/stations, or the iHeart directory used by search"
        )
        close_btn = wx.Button(self._surface, wx.ID_CANCEL, "Close")
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

        self._surface.SetSizer(root)
        if self._modeless:
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(self._surface, 1, wx.EXPAND)
            self._win.SetSizer(outer)

        self._name_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        self._tag_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        # Picking a tag or a country fires the search immediately (as well as
        # the Search button), so the dropdowns feel like filters.
        self._tag_ctrl.Bind(wx.EVT_COMBOBOX, self._on_search)
        self._country_ctrl.Bind(wx.EVT_CHOICE, self._on_search)
        self._search_btn.Bind(wx.EVT_BUTTON, self._on_search)
        self._category_list.Bind(wx.EVT_LISTBOX, self._on_category_selected)
        self._tunein_tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self._on_tunein_expanding)
        self._tunein_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_tunein_activated)
        self._tunein_tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_tunein_tree_selected)
        self._results.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_result_selected)
        self._results.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_activate)
        self._results.Bind(wx.EVT_CONTEXT_MENU, self._on_results_context_menu)
        self._play_btn.Bind(wx.EVT_BUTTON, self._on_play)
        self._favorite_btn.Bind(wx.EVT_BUTTON, self._on_toggle_favorite)
        self._more_btn.Bind(wx.EVT_BUTTON, self._on_more_stations)
        add_custom_btn.Bind(wx.EVT_BUTTON, self._on_add_custom)
        link_finder_btn.Bind(wx.EVT_BUTTON, self._on_link_finder)
        self._refresh_btn.Bind(wx.EVT_BUTTON, self._on_refresh)
        self._genre_ctrl.Bind(wx.EVT_CHOICE, self._on_genre_selected)
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
        self._win.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

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

    def _build_surface_menu_bar(self) -> None:
        """Menu bar for the modeless frame: a &Close item + the shared &Window
        menu, so Alt lands on a real menu and Ctrl+Tab / Ctrl+1..9 traverse."""
        wx = self._wx
        menu_bar = wx.MenuBar()
        surface_menu = wx.Menu()
        close_id = wx.NewIdRef()
        surface_menu.Append(close_id, "&Close\tCtrl+W")
        self._win.Bind(wx.EVT_MENU, lambda _e: self._win.Close(), id=close_id)
        menu_bar.Append(surface_menu, "&Search")
        self._windows.install(self._win, menu_bar)
        self._win.SetMenuBar(menu_bar)
        self._menu_id_refs.append(close_id)

    def _on_close(self, event: object) -> None:
        previous = self._windows.previous_key(self._win)
        self._windows.unregister(self._win)
        self._announce("Exited Search Stations")
        self._on_favorites_changed()
        event.Skip()
        self._win.Destroy()
        if previous:
            self._windows.activate(previous)

    def show(self, *, initial_category: str | None = None, focus_search: bool = False) -> None:
        # Opened straight to a browse source (the Station menu's Browse submenu),
        # or focused on the search box (Search Stations...). Default stays the
        # Favorites view the constructor set.
        if initial_category is not None:
            self._show_category(initial_category)
        if focus_search:
            self._wx.CallAfter(self._name_ctrl.SetFocus)
        if self._modeless:
            from quill.ui.dialog_contract import show_modeless_surface

            self._windows.register(self._win, "Search Stations")
            show_modeless_surface(self._win, "Search Stations", announce=self._announce)
            return
        self._win.CentreOnParent()
        apply_modal_ids(self._win, cancel_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self._win, "Internet Radio", announce=self._announce)
        finally:
            self._win.Destroy()

    def refresh_favorites_view(self) -> None:
        if self._category_list.GetSelection() == _CATEGORIES.index(_FAVORITES):
            self._show_category(_FAVORITES)

    # ------------------------------------------------------------------
    # Population

    def _source_label(self, station: RadioStation) -> str:
        """The Source-column/facet label for *station* (Radio Browser default)."""
        return station.source or "Radio Browser"

    def _apply_source_facet(self, stations: list[RadioStation]) -> list[RadioStation]:
        """Filter *stations* by the current Source facet (All = everything)."""
        choice = self._source_facet.GetStringSelection() or _ALL_SOURCES
        if choice == _ALL_SOURCES:
            return stations
        # Match against every source that carried the station, not just the
        # winning label, so a SomaFM channel RadioBrowser also lists still
        # shows under the SomaFM facet (directory_search de-dups the two).
        return [s for s in stations if choice in station_source_labels(s)]

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
            # Blended non-Radio-Browser sources name themselves in the row so a
            # listener can tell where a station came from (iHeart, TuneIn, ...).
            label = station.display_name
            source = self._source_label(station)
            if source != "Radio Browser":
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
        self._save_search_prefs()
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
        # The genre picker applies to the genre-source categories only.
        self._genre_ctrl.Enable(category in _GENRE_SOURCES)
        # TuneIn browses in its own tree, which swaps in for the results list.
        self._set_tunein_view(category == _TUNEIN_BROWSE)
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
        elif category == _POPULAR:
            self._browse_async(
                lambda: radio_browser.popular_stations(safe_mode=self._safe_mode),
                loading="Loading the most popular stations...",
                done=lambda n: f"{n} of the most popular stations right now.",
                error="Could not load popular stations",
            )
        elif category == _SOMAFM:
            self._browse_async(
                lambda: soma_fm.search_stations("", safe_mode=self._safe_mode),
                loading="Loading SomaFM channels...",
                done=lambda n: f"{n} SomaFM channel{'' if n == 1 else 's'}.",
                error="Could not reach SomaFM",
            )
        elif category == _TUNEIN_BROWSE:
            self._populate_tunein_tree()
        elif category in _GENRE_SOURCES:
            self._genre_source = _GENRE_SOURCES[category]
            self._load_genres()
        else:
            status = (
                _search_result_summary(len(self._search_results), more=self._search_more_available)
                if self._search_results
                else "Search above to see results here."
            )
            self._fill_results(self._search_results, status=status)

    # -- browse-a-source (no search) --------------------------------------------

    def _browse_async(
        self,
        fetch: Callable[[], list[RadioStation]],
        *,
        loading: str,
        done: Callable[[int], str],
        error: str,
    ) -> None:
        """Fetch a source's stations off-thread and show them (Kelly's "browse
        without searching"). Any failure is announced, never fatal."""
        if self._safe_mode:
            self._status.SetLabel("Browsing sources is disabled in Safe Mode.")
            return
        self._status.SetLabel(loading)

        def _work(**_kwargs: Any) -> list[RadioStation]:
            try:
                return fetch()
            except Exception:  # noqa: BLE001 - reported via the empty-list path
                return []

        def _ok(_op: str, stations: object) -> None:
            rows = stations if isinstance(stations, list) else []
            self._wx.CallAfter(
                self._fill_results,
                rows,
                status=done(len(rows)) if rows else f"{error}, or nothing to show.",
            )
            self._wx.CallAfter(self._announce, done(len(rows)) if rows else error)

        def _fail(_op: str, exc: BaseException) -> None:
            self._wx.CallAfter(self._status.SetLabel, f"{error}: {exc}")

        self._task_manager.submit("radio-browse-source", _work, on_success=_ok, on_failure=_fail)

    def _load_genres(self) -> None:
        """Populate the genre picker from the current genre source (Community M3U
        or the Xiph directory), then wait for a genre pick. Both sources share
        this one path -- each exposes fetch_genres / genre_display / CATALOG_CREDIT."""
        source = self._genre_source
        self._fill_results([], status="")
        if self._safe_mode:
            self._status.SetLabel("Browsing this directory is disabled in Safe Mode.")
            return
        self._status.SetLabel("Loading genres...")

        def _work(**_kwargs: Any) -> list[str]:
            try:
                return list(source.fetch_genres(safe_mode=self._safe_mode))
            except Exception:  # noqa: BLE001 - reported via the empty-list path
                return []

        def _ok(_op: str, genres: object) -> None:
            self._wx.CallAfter(self._apply_genres, genres if isinstance(genres, list) else [])

        self._task_manager.submit("radio-genres", _work, on_success=_ok, on_failure=None)

    def _apply_genres(self, slugs: list[str]) -> None:
        source = self._genre_source
        self._genre_slugs = slugs
        self._genre_ctrl.Set([source.genre_display(slug) for slug in slugs])
        self._genre_ctrl.Enable(bool(slugs))
        if not slugs:
            self._status.SetLabel("Could not load the genre list. Try Refresh.")
            return
        message = f"{len(slugs)} genres from {source.CATALOG_CREDIT}. Pick a genre to browse it."
        self._status.SetLabel(message)
        self._announce(message)

    def _on_genre_selected(self, _event: object) -> None:
        source = self._genre_source
        index = self._genre_ctrl.GetSelection()
        if index < 0 or index >= len(self._genre_slugs):
            return
        slug = self._genre_slugs[index]
        display = source.genre_display(slug)
        label = source.CATEGORY_LABEL
        self._browse_async(
            lambda: source.fetch_genre_stations(slug, safe_mode=self._safe_mode),
            loading=f"Loading {display} stations...",
            done=lambda n: f"{n} {display} station{'' if n == 1 else 's'} ({label}).",
            error=f"Could not load {display}",
        )

    # -- TuneIn category browse (a real tree) -----------------------------------

    def _set_tunein_view(self, show_tree: bool) -> None:
        """Swap the TuneIn tree in for the results list (or back), one visible
        at a time in the same space."""
        if self._tunein_tree.IsShown() == show_tree:
            return
        self._tunein_tree.Show(show_tree)
        self._results.Show(not show_tree)
        self._surface.Layout()

    def _populate_tunein_tree(self) -> None:
        """Fill the TuneIn tree's top level (Music, Talk, Sports, Local, ...)."""
        tree = self._tunein_tree
        tree.DeleteAllItems()
        self._details.SetValue("")
        self._play_btn.Enable(False)
        self._favorite_btn.Enable(False)
        if self._safe_mode:
            self._status.SetLabel("The TuneIn directory is disabled in Safe Mode.")
            return
        self._tunein_root = tree.AddRoot("TuneIn")
        self._status.SetLabel("Loading TuneIn...")
        self._fetch_tunein_children(self._tunein_root, "")

    def _fetch_tunein_children(self, node: Any, target: str) -> None:
        """Fetch a node's TuneIn children off-thread and add them under it.

        *target* is a category's ``browse_url`` (or "" for the top level)."""

        def _work(**_kwargs: Any) -> list[Any]:
            try:
                return tunein.browse(target, safe_mode=self._safe_mode)
            except tunein.TuneInError:
                return []

        def _ok(_op: str, results: object) -> None:
            self._wx.CallAfter(
                self._add_tunein_children, node, results if isinstance(results, list) else []
            )

        self._task_manager.submit("radio-tunein-browse", _work, on_success=_ok, on_failure=None)

    def _add_tunein_children(self, node: Any, results: list[Any]) -> None:
        tree = self._tunein_tree
        if not node.IsOk():
            return
        tree.DeleteChildren(node)  # clear the "Loading..." placeholder, if any
        for result in results:
            label = result.title if result.is_station else f"{result.title}  [folder]"
            child = tree.AppendItem(node, label)
            tree.SetItemData(
                child,
                {
                    "kind": "station" if result.is_station else "category",
                    "guide_id": result.guide_id,
                    "drill": result.browse_url or result.guide_id,
                    "title": result.title,
                    "subtitle": result.subtitle,
                    "loaded": False,
                },
            )
            if not result.is_station:
                # A placeholder child gives the folder an expand arrow; it is
                # replaced by the real children the first time it is opened.
                placeholder = tree.AppendItem(child, "Loading...")
                tree.SetItemData(placeholder, {"kind": "placeholder"})
        categories = sum(1 for r in results if not r.is_station)
        stations = len(results) - categories
        status = (
            f"TuneIn: {categories} folder{'' if categories == 1 else 's'}, "
            f"{stations} station{'' if stations == 1 else 's'}. Enter opens a folder or plays."
            if results
            else "Nothing to browse here."
        )
        self._status.SetLabel(status)
        if node == getattr(self, "_tunein_root", None):
            self._announce(status)
            tree.SetFocus()
            first, _cookie = tree.GetFirstChild(node)
            if first.IsOk():
                tree.SelectItem(first)

    def _selected_tunein_data(self) -> dict | None:
        selection = self._tunein_tree.GetSelection()
        if not selection.IsOk():
            return None
        data = self._tunein_tree.GetItemData(selection)
        return data if isinstance(data, dict) else None

    def _on_tunein_expanding(self, event: Any) -> None:
        data = self._tunein_tree.GetItemData(event.GetItem())
        if not isinstance(data, dict) or data.get("kind") != "category" or data.get("loaded"):
            return
        data["loaded"] = True  # fetch once; a failed/empty fetch just leaves it empty
        self._status.SetLabel(f"Opening {data.get('title', 'folder')}...")
        self._fetch_tunein_children(event.GetItem(), data.get("drill") or data.get("guide_id", ""))

    def _on_tunein_activated(self, event: Any) -> None:
        data = self._tunein_tree.GetItemData(event.GetItem())
        if isinstance(data, dict) and data.get("kind") == "station":
            self._play_tunein_station(data["guide_id"], data["title"])
            return
        event.Skip()  # a folder: let the tree toggle it open/closed

    def _on_tunein_tree_selected(self, event: Any) -> None:
        data = self._tunein_tree.GetItemData(event.GetItem())
        is_station = isinstance(data, dict) and data.get("kind") == "station"
        if is_station:
            subtitle = data.get("subtitle") or ""
            self._details.SetValue(
                f"{data['title']}\n{subtitle}\nTuneIn -- press Enter or Play to tune in.".strip()
            )
        else:
            self._details.SetValue("")
        self._play_btn.Enable(is_station)
        self._favorite_btn.Enable(False)  # a TuneIn station has no stream until it plays

    def _play_tunein_station(self, guide_id: str, title: str) -> None:
        """Resolve a TuneIn station's stream off-thread, then play it."""
        self._status.SetLabel(f"Resolving {title}...")

        def _work(**_kwargs: Any) -> list[str]:
            try:
                return tunein.resolve_station_streams(guide_id, safe_mode=self._safe_mode)
            except tunein.TuneInError:
                return []

        def _ok(_op: str, streams: object) -> None:
            self._wx.CallAfter(
                self._play_resolved_tunein, title, streams if isinstance(streams, list) else []
            )

        self._task_manager.submit("radio-tunein-resolve", _work, on_success=_ok, on_failure=None)

    def _play_resolved_tunein(self, title: str, streams: list[str]) -> None:
        if not streams:
            self._status.SetLabel(f"Could not get a stream for {title}.")
            self._announce(f"Could not play {title}.")
            return
        station = RadioStation(name=title, stream_url=tunein.best_stream(streams), source="TuneIn")
        self._controller.play_station(station)
        self._announce(f"Playing {title}")
        self._refresh_play_button()

    def _on_refresh(self, _event: object) -> None:
        """Context-aware Refresh: re-fetch the Music Genres list when that
        category is active, otherwise re-fetch the iHeart search directory."""
        selection = self._category_list.GetSelection()
        category = _CATEGORIES[selection] if selection != self._wx.NOT_FOUND else ""
        if category in _GENRE_SOURCES:
            self._genre_source = _GENRE_SOURCES[category]
            self._load_genres()
            return
        self._on_refresh_directory(_event)

    # ------------------------------------------------------------------
    # Events

    def _on_category_selected(self, _event: object) -> None:
        selection = self._category_list.GetSelection()
        if selection != self._wx.NOT_FOUND:
            self._show_category(_CATEGORIES[selection])

    def _on_search(self, event: object) -> None:
        # Whether the finished search should move focus into the results list.
        # Arrowing through the Country choice (EVT_CHOICE) or the Tag combo's
        # list (EVT_COMBOBOX) fires a search per keystroke; stealing focus to
        # the results then makes the dropdown un-navigable -- one Down arrow and
        # focus jumps away. So only an explicit commit (the Search button, or
        # Enter in a text field) lands focus on the results; a dropdown pick
        # leaves focus where it is so the user can keep arrowing.
        wx = self._wx
        event_type = getattr(event, "GetEventType", lambda: None)()
        self._focus_results_after_search = event_type not in (
            wx.EVT_CHOICE.typeId,
            wx.EVT_COMBOBOX.typeId,
        )
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
            # The catalog lane (quill/ui/radio/catalog_search.py): local FTS
            # answers in ~1 ms, so an outage costs live rows, not the search.
            from quill.ui.radio.catalog_search import catalog_search_rows

            catalog_rows = catalog_search_rows(
                getattr(self, "_catalog", None), name, limit=_SEARCH_LIMIT
            )
            try:
                radio = (
                    radio_browser.search_stations(
                        name,
                        tag=tag,
                        country=country,
                        limit=_SEARCH_LIMIT,
                        safe_mode=self._safe_mode,
                    )
                    if self._source_on("radio_browser")
                    else []
                )
            except Exception:
                if not catalog_rows:
                    raise
                radio = []  # offline: the catalog carries the search
            radio = catalog_rows + radio
            # Blended in after the RadioBrowser page, each failure-tolerant so
            # one down source never blanks the list. Name/tag searches only:
            # these directories have no country field of their own, so a
            # country-only query skips them rather than returning noise. They
            # ride along with the first RadioBrowser page; "More Stations" pages
            # RadioBrowser alone.
            extras: list[RadioStation] = []
            query = name or tag
            if query:
                if self._source_on("somafm"):
                    try:
                        extras += soma_fm.search_stations(query, safe_mode=self._safe_mode)
                    except soma_fm.SomaFmError:
                        pass
                if self._source_on("tunein"):
                    extras += tunein_search_stations(query, safe_mode=self._safe_mode)
                # NOAA Weather Radio: a SAME code, callsign, or "County, ST"/state
                # query resolves to authoritative stations; anything else just
                # comes back empty, so this rides along unconditionally.
                if self._source_on("wxindex"):
                    extras += wxindex_search_stations(query, safe_mode=self._safe_mode)
                # Radio Reading Services: a name/tag/state match against the
                # curated ~20-service list; empty for anything else, so this
                # rides along unconditionally too.
                if self._source_on("reading_services"):
                    extras += reading_services_search_stations(query, safe_mode=self._safe_mode)
                # Spotify: search is open to every account tier, so these rows
                # ride along whenever the user has connected Spotify. They stay
                # useful on a free account -- Enter needs Premium, but "Open
                # Website" opens the track in Spotify's own app, where a free
                # account plays it normally.
                if self._source_on("spotify"):
                    extras += spotify_search_stations(
                        query,
                        client=self._spotify_client(),
                        safe_mode=self._safe_mode,
                    )
                # YouTube: yt-dlp's keyless ytsearch, the same extraction route
                # FreeTube/NewPipe/Invidious use. Each row is a page URL, so it
                # becomes an ordinary station you can play, favorite and record.
                if self._source_on("youtube"):
                    extras += youtube_search_stations(query, safe_mode=self._safe_mode)
            if name and self._source_on("iheart"):
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

    def _open_url(self, url: str, *, spotify: bool = False) -> None:
        """Open a station's web page in the default browser."""
        import webbrowser

        if url and webbrowser.open(url):
            self._announce("Opened in Spotify." if spotify else "Opened the station's website.")

    def _save_search_prefs(self) -> None:
        """Persist the source selection and facet, so both survive the session."""
        if self._on_search_prefs_changed is None:
            return
        try:
            self._on_search_prefs_changed(
                self._enabled_sources, self._source_facet.GetStringSelection() or ""
            )
        except Exception:  # noqa: BLE001 - a failed save must never block searching
            pass

    def _source_on(self, source_id: str) -> bool:
        """Whether this source is switched on for searching.

        A source that is off is never *contacted* -- this gates the fan-out
        itself, not the results afterwards -- so switching sources off makes a
        search quieter and faster, and stops its network traffic entirely.
        """
        return search_sources.is_enabled(self._enabled_sources, source_id)

    def _spotify_client(self) -> Any:
        """The signed-in Spotify client, or ``None``.

        Runs inside the off-thread search worker, so the provider must not
        touch wx -- it only reads the stored token bundle. A provider that
        raises is treated as "not signed in": Spotify is one optional source
        among many here, and a broken one must not fail the whole search.
        """
        if self._spotify_client_provider is None:
            return None
        try:
            return self._spotify_client_provider()
        except Exception:  # noqa: BLE001 -- an optional source, never fatal
            return None

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
        # to Tab into the list. A facet-dropdown pick (Country/Tag) suppresses
        # this so arrowing the dropdown does not fling focus to the results.
        if self._current_results and getattr(self, "_focus_results_after_search", True):
            self._results.SetFocus()
        # The libraries answer separately and append as they land, so a slow one
        # never holds up the stations. See quill/ui/radio/library_search.py.
        library_search.begin(self, self._search_query)

    def _show_category_for_library_results(self) -> None:
        """Re-render after a library's rows land, without moving the cursor.

        Somebody may already be arrowing the station results by the time a
        library answers; re-selecting row 0 under them would be worse than the
        rows arriving late.
        """
        index = self._results.GetFirstSelected()
        self._show_category(_SEARCH_RESULTS)
        if index >= 0 and index < len(self._current_results):
            self._results.Select(index)
            self._results.Focus(index)

    def _on_more_stations(self, _event: object) -> None:
        """Fetch and append the next page of results (#1064).
        See :mod:`quill.ui.radio.search_paging`."""
        from quill.ui.radio import search_paging

        search_paging.fetch_more(self)

    def _on_more_done(self, stations: list[RadioStation], error: BaseException | None) -> None:
        """Merge a new page in, landing the cursor on its first row."""
        from quill.ui.radio import search_paging

        search_paging.more_arrived(self, stations, error)

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
        if station.homepage:
            from_spotify = is_spotify_station(station)
            entries.append((
                open_link_label(station),
                lambda url=station.homepage, s=from_spotify: self._open_url(url, spotify=s),
            ))
        if self._on_report_bad_station is not None:
            entries.append((
                "Report &Bad Station...",
                lambda s=station: self._on_report_bad_station(s),
            ))
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
        # While the TuneIn tree is showing, Play acts on the selected tree node:
        # a station resolves and plays; a folder does nothing (Enter opens it).
        if self._tunein_tree.IsShown():
            data = self._selected_tunein_data()
            if isinstance(data, dict) and data.get("kind") == "station":
                self._play_tunein_station(data["guide_id"], data["title"])
            return
        station = self._selected_station()
        if station is None:
            return
        # One button, honest label: it stops the station it started.
        if self._is_station_playing(station):
            self._controller.stop()
            self._announce("Radio stopped")
        elif library_search.activate_row(self, station):
            pass  # a show or book row: resolved and played (or refused) by name
        else:
            self._controller.play_station(station)
            self._announce(f"Playing {station.name}")
        self._refresh_play_button()

    def _on_char_hook(self, event: object) -> None:
        """Handle Ctrl+Up/Ctrl+Down as Volume Up/Down from anywhere in the
        dialog (#1070); Escape closes the modeless frame; else pass through."""
        wx = self._wx
        if self._modeless and event.GetKeyCode() == wx.WXK_ESCAPE:
            self._win.Close()
            return
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
        # A TuneIn station has no resolved stream until it plays, so it can't be
        # saved straight from the browse tree.
        if self._tunein_tree.IsShown():
            self._announce("Play a TuneIn station first to add it to Favorites.")
            return
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
