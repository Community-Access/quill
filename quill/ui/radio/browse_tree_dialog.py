"""Browse Stations -- one unified tree of every internet-radio source.

A dedicated, search-free browse experience (its counterpart, Search Stations,
keeps the old field-based dialog). The whole window is a single ``wx.TreeCtrl``
whose top-level branches are the sources -- Favorites (your own saved folders
and streams, at the top for a quick jump), then Popular, Radio Browser (by
Genre), Weather/NOAA, ACB Media, NFB Radio, Radio Reading Services, SomaFM,
TuneIn, iHeart (A-Z genre sub-directories), and the catalogs (Community M3U, Xiph).
A "Find in this folder" box searches from the highlighted folder downward only
(loading that subtree, bounded), so results stay scoped and small; Clear drops
the results and puts the cursor back on the folder you searched from.
You expand a branch to reveal its stations (or its genres/folders, then their
stations); internet sources load lazily on first open, off the UI thread, while
Favorites is built instantly from local data. Enter (or the Play button) plays
the highlighted station -- the Play button reads "Stop" while that station is
the one playing. A rich Shift+F10 / right-click context menu offers Play/Stop,
Add/Remove Favorite (and "Add all stations to Favorites" on a folder), Copy
stream link, and Open website. Playback is the shared ``RadioPlayerController``
passed in, so closing the window never stops the stream.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio import (
    acb_media,
    iheart,
    m3u_catalog,
    networks,
    nfb_media,
    radio_browser,
    reading_services,
    soma_fm,
    tunein,
    xiph,
)
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.core.radio.spotify_search import open_link_label
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.radio import browse_position
from quill.ui.radio.browse_tree_helpers import (
    iheart_letter_groups as _iheart_letter_groups,
)
from quill.ui.radio.browse_tree_helpers import (
    wx_playable_stations as _wx_playable_stations,
)
from quill.ui.radio.browse_tree_helpers import (
    wx_state_folders as _wx_state_folders,
)

#: Top-level sources, in tree order: (label, kind, payload). "stations" sources
#: expand straight to stations; "genres" sources expand to genre folders; the
#: "tunein" source expands to TuneIn's own folder tree; "wx_states" expands to
#: State folders (see below).
_SOURCES: tuple[tuple[str, str, Any], ...] = (
    ("Favorites", "favorites", None),
    ("Popular Stations", "stations", "popular"),
    # #1194: a first-class Radio Browser node, browsable by genre via the same
    # "genres" protocol as Xiph/M3U (radio_browser.fetch_genres/genre_stations).
    ("Radio Browser (by Genre)", "genres", radio_browser),
    ("Weather / NOAA", "wx_states", None),
    ("ACB Media", "stations", "acb"),
    ("NFB Radio", "stations", "nfb"),
    ("Radio Reading Services", "stations", "reading_services"),
    ("SomaFM", "stations", "soma"),
    ("TuneIn", "tunein", ""),
    ("iHeart", "iheart", None),
    # #1384: well-known broadcasters grouped as one-click nodes, each a curated
    # Radio Browser query (see quill.core.radio.networks) -> no new egress site.
    ("Networks", "networks", None),
    ("Community M3U (Music Genres)", "genres", m3u_catalog),
    ("Xiph / Icecast Directory", "genres", xiph),
)


#: Node kinds that lazily load children when expanded.
_EXPANDABLE = (
    "stations",
    "genres",
    "genre",
    "tunein",
    "wx_states",
    "wx_state",
    "iheart",
    "iheart-genre",
    "iheart-letter",
    "networks",
    "network-group",
    "network",
)

#: Expandable kinds whose fetched children are already playable ``RadioStation``
#: leaves (as opposed to sub-folders that must be recursed). "iheart-genre" is
#: here because its raw fetch is the genre's stations -- the A-Z letters are
#: only a display grouping.
_LEAF_KINDS = frozenset({
    "stations",
    "genre",
    "wx_state",
    "iheart-genre",
    "iheart-letter",
    "network",
})

#: Bounds for "Find in this folder": how deep to recurse a subtree, the most
#: results to collect, and the most folder fetches to spend -- so searching from
#: a big branch (or TuneIn's remote tree) stays bounded instead of walking the
#: whole internet. Hitting a bound is reported, never silent.
_FIND_MAX_DEPTH = 6
_FIND_MAX_RESULTS = 2000
_FIND_MAX_FETCHES = 80


class BrowseTreeDialog:
    """Browse every station source in one lazily-loaded tree."""

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
        on_report_bad_station: Callable[[Any], None] | None = None,
        show_details: bool = True,
        windows: object | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._controller = controller
        self._favorites = favorites_store
        self._task_manager = task_manager
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._on_favorites_changed = on_favorites_changed or (lambda: None)
        self._on_report_bad_station = on_report_bad_station
        self._menu_id_refs: list[object] = []
        self._find_active = False
        self._find_return_node: Any = None
        # When a WindowManager is supplied (standalone Radio), this surface is a
        # modeless wx.Frame carrying the persistent menu bar + &Window menu, with
        # its controls on an inner panel for keyboard traversal; otherwise
        # (embedded QUILL) it stays a modal wx.Dialog, unchanged.
        self._windows = windows
        self._modeless = windows is not None
        if self._modeless:
            self._win = wx.Frame(parent, title="Browse Stations", style=wx.DEFAULT_FRAME_STYLE)
            self._surface = wx.Panel(self._win, style=wx.TAB_TRAVERSAL)
            self._build_surface_menu_bar()
            self._win.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
            self._win.Bind(wx.EVT_CLOSE, self._on_close)
        else:
            self._win = wx.Dialog(
                parent, title="Browse Stations", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
            )
            self._surface = self._win
        self.dialog = self._win  # back-compat alias for callers that reference it
        self._win.SetMinSize((560, 460))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(self._surface, label="&Stations (expand a source to browse it):"),
            0,
            wx.LEFT | wx.TOP,
            10,
        )
        self._tree = wx.TreeCtrl(
            self._surface,
            style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT | wx.BORDER_SIMPLE,
        )
        self._tree.SetName(
            "Station sources; expand one to browse its stations, Enter plays, "
            "Shift+F10 opens all actions"
        )
        root.Add(self._tree, 1, wx.EXPAND | wx.ALL, 10)

        find_row = wx.BoxSizer(wx.HORIZONTAL)
        find_row.Add(
            wx.StaticText(self._surface, label="&Find in this folder:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._find_ctrl = wx.TextCtrl(self._surface, style=wx.TE_PROCESS_ENTER)
        self._find_ctrl.SetName(
            "Find stations in the highlighted folder and everything below it; press Enter"
        )
        find_row.Add(self._find_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        self._find_btn = wx.Button(self._surface, label="Find")
        self._find_btn.SetName("Find in this folder")
        self._find_clear_btn = wx.Button(self._surface, label="C&lear")
        self._find_clear_btn.SetName("Clear the search and return to the folder")
        find_row.Add(self._find_btn, 0, wx.RIGHT, 6)
        find_row.Add(self._find_clear_btn, 0)
        root.Add(find_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self._details = wx.TextCtrl(
            self._surface, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self._details.SetName("Details of the highlighted station")
        root.Add(self._details, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        if not show_details:
            root.Hide(self._details)  # View > Show Station Details (honored per surface)

        volume_row = wx.BoxSizer(wx.HORIZONTAL)
        volume_row.Add(
            wx.StaticText(self._surface, label="Radio &volume:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._volume_slider = wx.Slider(self._surface, value=100, minValue=0, maxValue=100)
        self._volume_slider.SetName("Internet Radio volume")
        volume_row.Add(self._volume_slider, 1, wx.EXPAND | wx.RIGHT, 6)
        self._mute_btn = wx.ToggleButton(self._surface, label="&Mute")
        volume_row.Add(self._mute_btn, 0)
        root.Add(volume_row, 0, wx.EXPAND | wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._play_btn = wx.Button(self._surface, label="&Play")
        self._play_btn.Enable(False)
        self._favorite_btn = wx.Button(self._surface, label="Add to &Favorites")
        self._favorite_btn.Enable(False)
        self._refresh_btn = wx.Button(self._surface, label="&Refresh")
        self._refresh_btn.SetName("Reload the highlighted source from the internet")
        close_btn = wx.Button(self._surface, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close (playback continues)")
        btn_row.Add(self._play_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._favorite_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._refresh_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self._surface.SetSizer(root)
        if self._modeless:
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(self._surface, 1, wx.EXPAND)
            self._win.SetSizer(outer)

        self._tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self._on_expanding)
        self._tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_activated)
        self._tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_selected)
        self._tree.Bind(wx.EVT_TREE_ITEM_MENU, self._on_context_menu)
        self._play_btn.Bind(wx.EVT_BUTTON, lambda _e: self._play_selected())
        self._favorite_btn.Bind(wx.EVT_BUTTON, lambda _e: self._toggle_favorite())
        self._refresh_btn.Bind(wx.EVT_BUTTON, lambda _e: self._refresh_selected())
        self._volume_slider.Bind(wx.EVT_SLIDER, self._on_volume_slider)
        self._mute_btn.Bind(wx.EVT_TOGGLEBUTTON, self._on_mute)
        self._find_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_find)
        self._find_btn.Bind(wx.EVT_BUTTON, self._on_find)
        self._find_clear_btn.Bind(wx.EVT_BUTTON, self._clear_find)

        state = getattr(self._controller, "state", None)
        if state is not None:
            self._volume_slider.SetValue(state.volume_percent)
            self._mute_btn.SetValue(state.muted)

        self._populate_sources()

    # -- lifecycle --------------------------------------------------------------

    def _build_surface_menu_bar(self) -> None:
        """A small menu bar for the modeless frame: a &Close item plus the shared
        &Window menu, so Alt always lands on a real menu and Ctrl+Tab / Ctrl+1..9
        reach every open radio window."""
        wx = self._wx
        menu_bar = wx.MenuBar()
        surface_menu = wx.Menu()
        close_id = wx.NewIdRef()
        surface_menu.Append(close_id, "&Close\tCtrl+W")
        self._win.Bind(wx.EVT_MENU, lambda _e: self._win.Close(), id=close_id)
        menu_bar.Append(surface_menu, "&Browse")
        self._windows.install(self._win, menu_bar)
        self._win.SetMenuBar(menu_bar)
        self._menu_id_refs.append(close_id)

    def _on_char_hook(self, event: object) -> None:
        # A frame has no automatic Escape->Cancel; wire it to close.
        if event.GetKeyCode() == self._wx.WXK_ESCAPE:
            self._win.Close()
            return
        event.Skip()

    def _on_close(self, event: object) -> None:
        previous = self._windows.previous_key(self._win)
        self._windows.unregister(self._win)
        self._announce("Exited Browse Stations")
        self._on_favorites_changed()
        event.Skip()
        self._win.Destroy()
        if previous:
            self._windows.activate(previous)

    def show(self, *, initial_source: str | None = None) -> None:
        if initial_source is not None:
            self._expand_source(initial_source)
        if self._modeless:
            from quill.ui.dialog_contract import show_modeless_surface

            self._windows.register(self._win, "Browse Stations")
            show_modeless_surface(self._win, "Browse Stations", announce=self._announce)
            return
        self._win.CentreOnParent()
        apply_modal_ids(self._win, cancel_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self._win, "Browse Stations", announce=self._announce)
        finally:
            self._win.Destroy()

    # -- tree population --------------------------------------------------------

    def _populate_sources(self) -> None:
        tree = self._tree
        root = tree.AddRoot("Sources")
        for label, kind, payload in _SOURCES:
            node = tree.AppendItem(root, label)
            tree.SetItemData(node, {"kind": kind, "payload": payload, "loaded": False})
            tree.SetItemData(tree.AppendItem(node, "Loading..."), {"kind": "placeholder"})
            if kind == "favorites":
                self._favorites_root = node  # kept so a favorite add/remove can refresh it live
        browse_position.restore_selection(tree, root)  # browse position memory

    def _fetch_children(self, kind: str, payload: Any) -> list[Any]:
        """Off-thread fetch for an expandable node; returns raw children."""
        try:
            if kind == "stations":
                return list(_STATION_LOADERS[payload](self._safe_mode))
            if kind == "genres":
                return list(payload.fetch_genres(safe_mode=self._safe_mode))
            if kind == "genre":
                module, slug = payload
                return list(module.fetch_genre_stations(slug, safe_mode=self._safe_mode))
            if kind == "tunein":
                return list(tunein.browse(payload, safe_mode=self._safe_mode))
            if kind == "wx_states":
                return list(_wx_state_folders(safe_mode=self._safe_mode))
            if kind == "wx_state":
                return _wx_playable_stations(payload, safe_mode=self._safe_mode)
            if kind == "iheart":
                return list(iheart.fetch_genres(safe_mode=self._safe_mode))
            if kind == "iheart-genre":
                return list(iheart.fetch_genre_stations(payload, safe_mode=self._safe_mode))
            if kind == "iheart-letter":
                return list(payload)  # already-fetched stations, no network
            if kind == "networks":
                return list(networks.groups())  # local: group labels
            if kind == "network-group":
                return list(networks.networks_in_group(payload))  # local: Network folders
            if kind == "network":
                return networks.network_stations(payload, safe_mode=self._safe_mode)
        except Exception:  # noqa: BLE001 - a down source shows as empty, never fatal
            return []
        return []

    # -- find in this folder ----------------------------------------------------

    def _subtree_children(self, kind: str, raw: list[Any]) -> list[tuple[str, Any]]:
        """Map a folder node's fetched *raw* children to ``(kind, payload)``
        pairs to recurse, mirroring ``_add_children``'s folder mapping."""
        if kind == "genres":
            # A "genres" node's payload is the catalog module; it is not passed
            # here, so callers hand back child ("genre", (module, slug)) pairs.
            return []  # handled by _collect_leaf_nodes, which has the module
        if kind == "wx_states":
            return [("wx_state", state.slug) for state in raw]
        if kind == "iheart":
            return [("iheart-genre", genre.genre_id) for genre in raw]
        if kind == "networks":
            return [("network-group", group) for group in raw]
        if kind == "network-group":
            return [("network", network) for network in raw]
        return []

    def _leaf_name(self, node_data: dict) -> str:
        """The display name a search matches against for one collected leaf."""
        if node_data.get("kind") == "tunein-station":
            return str(node_data.get("title", ""))
        station = node_data.get("station")
        return station.name if station is not None else ""

    def _collect_matches(
        self, kind: str, payload: Any, ql: str, depth: int, acc: list[dict], budget: dict
    ) -> bool:
        """Recurse the subtree under (kind, payload), appending leaf node-data
        whose name contains *ql*. Returns True if a bound (depth/results/fetches)
        cut the walk short. Bounded so a search from a big branch or TuneIn's
        remote tree stays finite."""
        if len(acc) >= _FIND_MAX_RESULTS:
            return True
        if kind == "favorites":
            for fav in self._favorites.favorites_in_display_order():
                node = {"kind": "station", "station": fav.station}
                if ql in self._leaf_name(node).lower():
                    acc.append(node)
            return False
        if depth > _FIND_MAX_DEPTH or budget["fetches"] >= _FIND_MAX_FETCHES:
            return True
        budget["fetches"] += 1
        raw = self._fetch_children(kind, payload)
        if kind in _LEAF_KINDS:
            for station in raw:
                node = {"kind": "station", "station": station}
                if ql in self._leaf_name(node).lower():
                    acc.append(node)
                    if len(acc) >= _FIND_MAX_RESULTS:
                        return True
            return False
        capped = False
        if kind == "tunein":
            for result in raw:
                if getattr(result, "is_station", False):
                    node = {
                        "kind": "tunein-station",
                        "guide_id": result.guide_id,
                        "title": result.title,
                    }
                    if ql in self._leaf_name(node).lower():
                        acc.append(node)
                else:
                    capped = (
                        self._collect_matches(
                            "tunein", result.browse_url, ql, depth + 1, acc, budget
                        )
                        or capped
                    )
                if len(acc) >= _FIND_MAX_RESULTS:
                    return True
            return capped
        if kind == "genres":
            children = [("genre", (payload, slug)) for slug in raw]
        else:
            children = self._subtree_children(kind, raw)
        for child_kind, child_payload in children:
            capped = (
                self._collect_matches(child_kind, child_payload, ql, depth + 1, acc, budget)
                or capped
            )
            if len(acc) >= _FIND_MAX_RESULTS:
                return True
        return capped

    def _find_matches(self, kind: str, payload: Any, query: str) -> tuple[list[dict], bool]:
        """Collect leaf node-data under (kind, payload) matching *query*
        (case-insensitive), plus whether a bound cut the search short."""
        acc: list[dict] = []
        budget = {"fetches": 0}
        capped = self._collect_matches(kind, payload, query.strip().lower(), 0, acc, budget)
        return acc, capped

    def _find_anchor_node(self) -> Any:
        """The folder to search from: the highlighted node if it is a source or
        folder, else the nearest folder above it (so searching while on a
        station leaf searches the folder that station is in). None if nothing
        searchable is selected."""
        tree = self._tree
        try:
            node = tree.GetSelection()
        except RuntimeError:
            return None
        searchable = (*_EXPANDABLE, "favorites")
        while node is not None and node.IsOk():
            data = self._node_data(node)
            if data is not None and data.get("kind") in searchable:
                return node
            node = tree.GetItemParent(node)
        return None

    def _on_find(self, _event: Any = None) -> None:
        query = self._find_ctrl.GetValue().strip()
        if not query:
            self._announce("Type something to find in this folder.")
            return
        anchor = self._find_anchor_node()
        if anchor is None:
            self._announce("Highlight a source or folder to search in first.")
            return
        data = self._node_data(anchor)
        if data is None:
            return
        kind, payload = data["kind"], data.get("payload")
        label = self._tree.GetItemText(anchor)
        self._announce(f"Searching {label} for {query}...")

        def _work(**_kwargs: Any) -> tuple[list[dict], bool]:
            return self._find_matches(kind, payload, query)

        def _ok(_op: str, result: object) -> None:
            # Already on the UI thread (call_ui_safely marshals + guards this);
            # call directly. A second raw CallAfter would run outside that guard,
            # so a closed dialog would hit a destroyed TreeCtrl and raise.
            matches, capped = result if isinstance(result, tuple) else ([], False)
            self._show_find_results(anchor, label, matches, capped)

        self._task_manager.submit("radio-browse-find", _work, on_success=_ok, on_failure=None)

    def _show_find_results(
        self, anchor: Any, label: str, matches: list[dict], capped: bool
    ) -> None:
        if not self._tree:  # dialog closed while the search was in flight
            return
        tree = self._tree
        if not anchor.IsOk():
            return
        self._find_return_node = anchor
        self._find_active = True
        tree.DeleteChildren(anchor)
        for node_data in matches:
            leaf = tree.AppendItem(anchor, self._leaf_name(node_data))
            tree.SetItemData(leaf, node_data)
        if not matches:
            empty = tree.AppendItem(anchor, f"No matches in {label}.")
            tree.SetItemData(empty, {"kind": "placeholder"})
        anchor_data = self._node_data(anchor)
        if anchor_data is not None:
            anchor_data["loaded"] = True  # results replace the normal lazy children
        tree.Expand(anchor)
        count = len(matches)
        more = " Showing the first results; search a smaller folder for the rest." if capped else ""
        self._announce(
            f"{count} match{'es' if count != 1 else ''} in {label}."
            f"{more} Clear to return to the folder."
        )
        first, _cookie = tree.GetFirstChild(anchor)
        if first.IsOk():
            tree.SelectItem(first)
            tree.SetFocus()

    def _clear_find(self, _event: Any = None) -> None:
        self._find_ctrl.SetValue("")
        node = self._find_return_node
        self._find_return_node = None
        was_active = self._find_active
        self._find_active = False
        if node is None or not node.IsOk():
            return
        data = self._node_data(node)
        if data is not None and data.get("kind") in (*_EXPANDABLE, "favorites"):
            # Drop the result leaves and reset the folder to its unexpanded state,
            # so re-opening it browses normally again.
            data["loaded"] = False
            self._tree.DeleteChildren(node)
            self._tree.SetItemData(
                self._tree.AppendItem(node, "Loading..."), {"kind": "placeholder"}
            )
            self._tree.Collapse(node)
        self._tree.SelectItem(node)  # cursor back on the folder you searched from
        self._tree.SetFocus()
        if was_active:
            self._announce(f"Search cleared. Back on {self._tree.GetItemText(node)}.")

    def _add_children(self, node: Any, kind: str, raw: list[Any]) -> None:
        if not self._tree:  # dialog closed while children were being fetched
            return
        tree = self._tree
        if not node.IsOk():
            return
        tree.DeleteChildren(node)  # clear the "Loading..." placeholder
        if kind == "genres":
            module = tree.GetItemData(node)["payload"]
            for slug in raw:
                child = tree.AppendItem(node, module.genre_display(slug))
                tree.SetItemData(
                    child, {"kind": "genre", "payload": (module, slug), "loaded": False}
                )
                tree.SetItemData(tree.AppendItem(child, "Loading..."), {"kind": "placeholder"})
        elif kind == "wx_states":
            for state in raw:
                child = tree.AppendItem(node, f"{state.name} ({state.stations_with_feeds})")
                tree.SetItemData(
                    child, {"kind": "wx_state", "payload": state.slug, "loaded": False}
                )
                tree.SetItemData(tree.AppendItem(child, "Loading..."), {"kind": "placeholder"})
        elif kind == "iheart":
            for genre in raw:
                child = tree.AppendItem(node, genre.name)
                tree.SetItemData(
                    child, {"kind": "iheart-genre", "payload": genre.genre_id, "loaded": False}
                )
                tree.SetItemData(tree.AppendItem(child, "Loading..."), {"kind": "placeholder"})
        elif kind == "iheart-genre":
            for letter, stations in _iheart_letter_groups(raw):
                child = tree.AppendItem(node, letter)
                tree.SetItemData(
                    child, {"kind": "iheart-letter", "payload": stations, "loaded": False}
                )
                tree.SetItemData(tree.AppendItem(child, "Loading..."), {"kind": "placeholder"})
        elif kind == "networks":
            for group in raw:
                child = tree.AppendItem(node, group)
                tree.SetItemData(
                    child, {"kind": "network-group", "payload": group, "loaded": False}
                )
                tree.SetItemData(tree.AppendItem(child, "Loading..."), {"kind": "placeholder"})
        elif kind == "network-group":
            for network in raw:
                # The note (for syndicators) is spoken with the name so a listener
                # knows it is an affiliate search, not a single stream.
                label = (
                    f"{network.display_name} -- {network.note}"
                    if network.note
                    else network.display_name
                )
                child = tree.AppendItem(node, label)
                tree.SetItemData(child, {"kind": "network", "payload": network, "loaded": False})
                tree.SetItemData(tree.AppendItem(child, "Loading..."), {"kind": "placeholder"})
        elif kind == "tunein":
            for result in raw:
                if result.is_station:
                    child = tree.AppendItem(node, result.title)
                    tree.SetItemData(
                        child,
                        {
                            "kind": "tunein-station",
                            "guide_id": result.guide_id,
                            "title": result.title,
                        },
                    )
                else:
                    child = tree.AppendItem(node, f"{result.title}  [folder]")
                    tree.SetItemData(
                        child, {"kind": "tunein", "payload": result.browse_url, "loaded": False}
                    )
                    tree.SetItemData(tree.AppendItem(child, "Loading..."), {"kind": "placeholder"})
        else:  # "stations", "genre", or "wx_state" -> RadioStation leaves
            for station in raw:
                child = tree.AppendItem(node, station.display_name)
                tree.SetItemData(child, {"kind": "station", "station": station})
        count = tree.GetChildrenCount(node, False)
        self._announce(f"{count} item{'' if count == 1 else 's'}.")
        # #1188: leave the cursor on the just-expanded node (country/genre) --
        # do NOT jump it into the station list. The count announcement says
        # what's inside; the listener arrows down to enter the list when ready.

    def _add_favorites(self, node: Any, *, select: bool = True) -> None:
        """Build the local Favorites branch: unfiled stations first, then a
        node per folder holding its stations. Favorite leaves reuse the plain
        "station" kind, so Play / Add-Remove Favorite / context menu all work
        unchanged. Local data, so no network fetch. ``select=False`` rebuilds
        the branch without moving the selection (used for a live refresh after
        a favorite is added/removed, so focus stays where the user is)."""
        tree = self._tree
        if not node.IsOk():
            return
        tree.DeleteChildren(node)
        by_folder: dict[str, list[Any]] = {}
        for fav in self._favorites.favorites_in_display_order():
            by_folder.setdefault(fav.folder, []).append(fav)
        for fav in by_folder.get("", []):  # top-level (unfiled) stations
            leaf = tree.AppendItem(node, fav.display_label)
            tree.SetItemData(leaf, {"kind": "station", "station": fav.station})
        for folder in self._favorites.folders_in_display_order():  # then folders
            fnode = tree.AppendItem(node, f"{folder}  [folder]")
            tree.SetItemData(fnode, {"kind": "fav-folder", "folder": folder, "loaded": True})
            for fav in by_folder.get(folder, []):
                leaf = tree.AppendItem(fnode, fav.display_label)
                tree.SetItemData(leaf, {"kind": "station", "station": fav.station})
        count = tree.GetChildrenCount(node, False)
        if not count:
            empty = tree.AppendItem(node, "No favorites yet -- add stations from any source below.")
            tree.SetItemData(empty, {"kind": "placeholder"})
        if not select:
            return
        self._announce(f"Favorites: {count} item{'' if count == 1 else 's'}.")
        first, _cookie = tree.GetFirstChild(node)
        if first.IsOk():
            tree.SelectItem(first)

    def _refresh_favorites_branch(self) -> None:
        """Rebuild the Favorites branch in place after a favorite is added or
        removed, so the change shows immediately while the Browse window is
        open. A no-op until the branch has been expanded once (it builds fresh
        on first open) and it never moves the selection."""
        node = getattr(self, "_favorites_root", None)
        if node is None:
            return
        data = self._node_data(node)
        if not data or not data.get("loaded"):
            return
        self._add_favorites(node, select=False)

    # -- events -----------------------------------------------------------------

    def _node_data(self, node: Any) -> dict | None:
        if node is None or not node.IsOk():
            return None
        data = self._tree.GetItemData(node)
        return data if isinstance(data, dict) else None

    def _selected_data(self) -> dict | None:
        try:
            return self._node_data(self._tree.GetSelection())
        except RuntimeError:
            return None  # the tree is being torn down (a SEL_CHANGED during close)

    def _on_expanding(self, event: Any) -> None:
        node = event.GetItem()
        data = self._node_data(node)
        if data is not None and data.get("kind") == "favorites":
            if not data.get("loaded"):
                data["loaded"] = True
                self._add_favorites(node)
            return
        if data is None or data.get("kind") not in _EXPANDABLE:
            return
        if data.get("loaded"):
            return
        if self._safe_mode and data["kind"] != "stations":
            self._details.SetValue("Browsing directories is disabled in Safe Mode.")
        data["loaded"] = True
        self._announce("Loading...")

        def _work(**_kwargs: Any) -> list[Any]:
            return self._fetch_children(data["kind"], data.get("payload"))

        def _ok(_op: str, raw: object) -> None:
            # Already on the UI thread (call_ui_safely marshals + guards this);
            # call directly rather than scheduling a second unguarded CallAfter.
            self._add_children(node, data["kind"], raw if isinstance(raw, list) else [])

        self._task_manager.submit("radio-browse-tree", _work, on_success=_ok, on_failure=None)

    def _on_activated(self, event: Any) -> None:
        data = self._node_data(event.GetItem())
        if data and data.get("kind") in ("station", "tunein-station"):
            self._play_selected()
            return
        event.Skip()  # a source/folder toggles open

    def _on_selected(self, _event: Any) -> None:
        browse_position.remember(self._tree, self._tree.GetSelection())
        data = self._selected_data()
        if data and data.get("kind") == "station":
            station = data["station"]
            self._details.SetValue(station.details_text)
            self._play_btn.Enable(True)
            self._refresh_play_button(station)
            self._favorite_btn.Enable(True)
            self._update_favorite_label(station)
        elif data and data.get("kind") == "tunein-station":
            self._details.SetValue(f"{data['title']}\nTuneIn -- Enter or Play to tune in.")
            self._play_btn.Enable(True)
            self._play_btn.SetLabel("&Play")
            # The stream resolves lazily, but Add to Favorites now resolves it on
            # demand (#1210), so the button is live. Label it Add (we can't know
            # saved-state before resolving).
            self._favorite_btn.Enable(True)
            self._favorite_btn.SetLabel("Add to &Favorites")
        else:
            self._details.SetValue("")
            self._play_btn.Enable(False)
            self._play_btn.SetLabel("&Play")
            self._favorite_btn.Enable(False)

    def _refresh_play_button(self, station: RadioStation) -> None:
        """Label the Play button 'Stop' when the highlighted station is the one
        currently playing, so it reads as a live toggle (like the main window)."""
        self._play_btn.SetLabel("&Stop" if self._is_playing(station) else "&Play")

    # -- play / favorite --------------------------------------------------------

    def _play_selected(self) -> None:
        data = self._selected_data()
        if data is None:
            return
        if data.get("kind") == "tunein-station":
            self._play_tunein(data["guide_id"], data["title"])
            return
        if data.get("kind") != "station":
            return
        station = data["station"]
        if self._is_playing(station):
            self._controller.stop()
            self._announce("Radio stopped")
        else:
            self._controller.play_station(station)
            self._announce(f"Playing {station.display_name}")
        self._refresh_play_button(station)

    def _play_tunein(self, guide_id: str, title: str) -> None:
        self._details.SetValue(f"Resolving {title}...")

        def _work(**_kwargs: Any) -> list[str]:
            try:
                return tunein.resolve_station_streams(guide_id, safe_mode=self._safe_mode)
            except tunein.TuneInError:
                return []

        def _ok(_op: str, streams: object) -> None:
            # Already on the UI thread (call_ui_safely marshals + guards this);
            # call directly rather than scheduling a second unguarded CallAfter.
            self._tunein_resolved(title, streams if isinstance(streams, list) else [])

        self._task_manager.submit("radio-tunein-resolve", _work, on_success=_ok, on_failure=None)

    def _tunein_resolved(self, title: str, streams: list[str]) -> None:
        if not self._tree:  # dialog closed while the stream was resolving
            return
        if not streams:
            self._announce(f"Could not play {title}.")
            return
        self._controller.play_station(
            RadioStation(name=title, stream_url=tunein.best_stream(streams), source="TuneIn")
        )
        self._announce(f"Playing {title}")

    def _is_playing(self, station: RadioStation) -> bool:
        from quill.ui.radio.player_controller import RadioPlayerState

        state = self._controller.state
        return (
            state.station is not None
            and state.station.stream_url == station.stream_url
            and state.state in (RadioPlayerState.PLAYING, RadioPlayerState.CONNECTING)
        )

    def _update_favorite_label(self, station: RadioStation) -> None:
        saved = self._favorites.contains(station)
        self._favorite_btn.SetLabel("Remove from &Favorites" if saved else "Add to &Favorites")

    def _favorite_tunein(self, guide_id: str, title: str) -> None:
        """Resolve a TuneIn station's stream off-thread, then add it to Favorites.

        TuneIn leaves carry only a guide id until play time, so unlike directory
        stations they have no stream URL when the menu is built (#1210). Resolve
        it the same way playback does, then add the resolved station.
        """
        self._details.SetValue(f"Resolving {title}...")

        def _work(**_kwargs: Any) -> list[str]:
            try:
                return tunein.resolve_station_streams(guide_id, safe_mode=self._safe_mode)
            except tunein.TuneInError:
                return []

        def _ok(_op: str, streams: object) -> None:
            # Already on the UI thread (call_ui_safely marshals + guards this);
            # call directly rather than scheduling a second unguarded CallAfter.
            self._tunein_favorite_resolved(title, streams if isinstance(streams, list) else [])

        self._task_manager.submit("radio-tunein-favorite", _work, on_success=_ok, on_failure=None)

    def _tunein_favorite_resolved(self, title: str, streams: list[str]) -> None:
        if not self._tree:  # dialog closed while the stream was resolving
            return
        if not streams:
            self._announce(f"Could not add {title} to Favorites.")
            return
        station = RadioStation(name=title, stream_url=tunein.best_stream(streams), source="TuneIn")
        if self._favorites.contains(station):
            self._announce(f"{title} is already in your Favorites")
            return
        self._favorites.add(station)
        self._announce(f"Added {title} to Favorites")
        self._on_favorites_changed()
        self._refresh_favorites_branch()

    def _toggle_favorite(self) -> None:
        data = self._selected_data()
        if data is not None and data.get("kind") == "tunein-station":
            self._favorite_tunein(data["guide_id"], data["title"])
            return
        if data is None or data.get("kind") != "station":
            self._announce("Select a station to add it to Favorites.")
            return
        station = data["station"]
        if self._favorites.contains(station):
            self._favorites.remove(station.station_uuid or station.stream_url)
            self._announce(f"Removed {station.display_name} from Favorites")
        else:
            self._favorites.add(station)
            self._announce(f"Added {station.display_name} to Favorites")
        self._update_favorite_label(station)
        self._on_favorites_changed()
        self._refresh_favorites_branch()

    def _favorite_folder(self, node: Any) -> None:
        """Add every loaded station under a folder to Favorites in one go.
        Only the stations already loaded into the tree are added; if the folder
        hasn't been opened yet, ask the user to open it first (so a huge genre
        isn't fetched-and-favorited blind)."""
        tree = self._tree
        if not node.IsOk():
            return
        added = 0
        child, cookie = tree.GetFirstChild(node)
        loaded_any = False
        while child.IsOk():
            data = self._node_data(child)
            if data is not None and data.get("kind") == "station":
                loaded_any = True
                station = data["station"]
                if not self._favorites.contains(station):
                    self._favorites.add(station)
                    added += 1
            child, cookie = tree.GetNextChild(node, cookie)
        if not loaded_any:
            self._announce("Open the folder first to load its stations, then try again.")
            return
        if added:
            self._on_favorites_changed()
            self._refresh_favorites_branch()
        self._announce(
            f"Added {added} station{'' if added == 1 else 's'} to Favorites."
            if added
            else "Those stations are already in Favorites."
        )

    def _refresh_selected(self) -> None:
        """Re-fetch the highlighted node's source (or its parent source)."""
        node = self._tree.GetSelection()
        data = self._node_data(node)
        # Walk up to the nearest reloadable node (an internet source or the
        # local Favorites branch) and reload it.
        while data is not None and data.get("kind") not in (*_EXPANDABLE, "favorites"):
            node = self._tree.GetItemParent(node)
            data = self._node_data(node)
        if data is None:
            return
        if data.get("kind") == "favorites":
            self._add_favorites(node)  # local rebuild, no network
            return
        data["loaded"] = False
        self._tree.DeleteChildren(node)
        self._tree.SetItemData(self._tree.AppendItem(node, "Loading..."), {"kind": "placeholder"})
        self._tree.Expand(node)  # triggers _on_expanding, which reloads

    # -- context menu (Shift+F10 / right-click) ---------------------------------

    def _on_context_menu(self, event: Any) -> None:
        wx = self._wx
        node = event.GetItem()
        self._tree.SelectItem(node)
        data = self._node_data(node)
        if data is None:
            return
        entries: list[tuple[str, Callable[[], None]]] = []
        kind = data.get("kind")
        if kind == "station":
            station = data["station"]
            playing = self._is_playing(station)
            saved = self._favorites.contains(station)
            entries = [
                ("&Stop" if playing else "&Play", self._play_selected),
                (
                    "Remove from &Favorites" if saved else "Add to &Favorites",
                    self._toggle_favorite,
                ),
                ("&Copy Stream Link", lambda: self._copy_text(station.stream_url)),
            ]
            if station.homepage:
                # A saved Spotify favorite says "Open in Spotify": for a free
                # account that link is how the track actually plays, not a
                # footnote about the station's website.
                entries.append((
                    open_link_label(station),
                    lambda: self._open_url(station.homepage),
                ))
            if self._on_report_bad_station is not None:
                entries.append((
                    "Report &Bad Station...",
                    lambda s=station: self._on_report_bad_station(s),
                ))
        elif kind == "tunein-station":
            entries = [
                ("&Play", self._play_selected),
                (
                    "Add to &Favorites",
                    lambda: self._favorite_tunein(data["guide_id"], data["title"]),
                ),
            ]
        elif kind in _EXPANDABLE or kind == "fav-folder":
            entries = [("&Open", lambda: self._tree.Expand(node))]
            if kind in _EXPANDABLE:
                entries.append(("&Refresh", self._refresh_selected))
            entries.append(("Add All Stations to &Favorites", lambda: self._favorite_folder(node)))
        if not entries:
            return
        menu = wx.Menu()
        id_refs = []
        for label, handler in entries:
            item_id = wx.NewIdRef()
            id_refs.append(item_id)
            menu.Append(item_id, label)
            menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
        # A SEPARATE attribute: assigning self._menu_id_refs here would drop the
        # menu-bar Close id ref pinned in it, re-exposing the id-reuse bug where
        # a random menu item closes the window.
        self._context_menu_id_refs = id_refs  # pinned while the popup can fire
        self._tree.PopupMenu(menu)
        menu.Destroy()

    def _copy_text(self, text: str) -> None:
        wx = self._wx
        if text and wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
            self._announce("Stream link copied.")

    def _open_url(self, url: str) -> None:
        import webbrowser

        if url and webbrowser.open(url):
            self._announce("Opened the station's website.")

    # -- volume -----------------------------------------------------------------

    def _on_volume_slider(self, _event: Any) -> None:
        self._controller.set_volume(self._volume_slider.GetValue())
        self._mute_btn.SetValue(False)

    def _on_mute(self, _event: Any) -> None:
        self._controller.toggle_mute()
        state = getattr(self._controller, "state", None)
        if state is not None:
            self._mute_btn.SetValue(state.muted)

    # -- open straight to a source (from a menu) --------------------------------

    def _expand_source(self, label: str) -> None:
        tree = self._tree
        root = tree.GetRootItem()
        child, cookie = tree.GetFirstChild(root)
        while child.IsOk():
            if tree.GetItemText(child) == label:
                tree.SelectItem(child)
                tree.Expand(child)
                return
            child, cookie = tree.GetNextChild(root, cookie)


#: Off-thread station loaders for the flat "stations" sources, keyed by payload.
_STATION_LOADERS: dict[str, Callable[[bool], list[RadioStation]]] = {
    "popular": lambda safe: radio_browser.popular_stations(safe_mode=safe),
    "acb": lambda _safe: acb_media.acb_media_stations(),
    "nfb": lambda _safe: nfb_media.nfb_media_stations(),
    "reading_services": lambda safe: reading_services.list_reading_services(safe_mode=safe),
    "soma": lambda safe: soma_fm.search_stations("", safe_mode=safe),
}
