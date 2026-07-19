"""Browse Stations -- one unified tree of every internet-radio source.

A dedicated, search-free browse experience (its counterpart, Search Stations,
keeps the old field-based dialog). The whole window is a single ``wx.TreeCtrl``
whose top-level branches are the sources -- Favorites (your own saved folders
and streams, at the top for a quick jump), then Popular, Weather/NOAA, ACB
Media, NFB Radio, SomaFM, TuneIn, and the genre catalogs (Community M3U, Xiph).
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
    m3u_catalog,
    nfb_media,
    radio_browser,
    soma_fm,
    tunein,
    xiph,
)
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.ui.dialog_contract import apply_modal_ids

#: Top-level sources, in tree order: (label, kind, payload). "stations" sources
#: expand straight to stations; "genres" sources expand to genre folders; the
#: "tunein" source expands to TuneIn's own folder tree.
_SOURCES: tuple[tuple[str, str, Any], ...] = (
    ("Favorites", "favorites", None),
    ("Popular Stations", "stations", "popular"),
    ("Weather / NOAA", "stations", "weather"),
    ("ACB Media", "stations", "acb"),
    ("NFB Radio", "stations", "nfb"),
    ("SomaFM", "stations", "soma"),
    ("TuneIn", "tunein", ""),
    ("Community M3U (Music Genres)", "genres", m3u_catalog),
    ("Xiph / Icecast Directory", "genres", xiph),
)


#: Node kinds that lazily load children when expanded.
_EXPANDABLE = ("stations", "genres", "genre", "tunein")


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
    ) -> None:
        import wx

        self._wx = wx
        self._controller = controller
        self._favorites = favorites_store
        self._task_manager = task_manager
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._on_favorites_changed = on_favorites_changed or (lambda: None)
        self._menu_id_refs: list[object] = []

        self.dialog = wx.Dialog(
            parent, title="Browse Stations", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((560, 460))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(self.dialog, label="&Stations (expand a source to browse it):"),
            0,
            wx.LEFT | wx.TOP,
            10,
        )
        self._tree = wx.TreeCtrl(
            self.dialog,
            style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT | wx.BORDER_SIMPLE,
        )
        self._tree.SetName(
            "Station sources; expand one to browse its stations, Enter plays, "
            "Shift+F10 opens all actions"
        )
        root.Add(self._tree, 1, wx.EXPAND | wx.ALL, 10)

        self._details = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self._details.SetName("Details of the highlighted station")
        root.Add(self._details, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        volume_row = wx.BoxSizer(wx.HORIZONTAL)
        volume_row.Add(
            wx.StaticText(self.dialog, label="Radio &volume:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._volume_slider = wx.Slider(self.dialog, value=100, minValue=0, maxValue=100)
        self._volume_slider.SetName("Internet Radio volume")
        volume_row.Add(self._volume_slider, 1, wx.EXPAND | wx.RIGHT, 6)
        self._mute_btn = wx.ToggleButton(self.dialog, label="&Mute")
        volume_row.Add(self._mute_btn, 0)
        root.Add(volume_row, 0, wx.EXPAND | wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._play_btn = wx.Button(self.dialog, label="&Play")
        self._play_btn.Enable(False)
        self._favorite_btn = wx.Button(self.dialog, label="Add to &Favorites")
        self._favorite_btn.Enable(False)
        self._refresh_btn = wx.Button(self.dialog, label="&Refresh")
        self._refresh_btn.SetName("Reload the highlighted source from the internet")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close (playback continues)")
        btn_row.Add(self._play_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._favorite_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._refresh_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self._on_expanding)
        self._tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_activated)
        self._tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_selected)
        self._tree.Bind(wx.EVT_TREE_ITEM_MENU, self._on_context_menu)
        self._play_btn.Bind(wx.EVT_BUTTON, lambda _e: self._play_selected())
        self._favorite_btn.Bind(wx.EVT_BUTTON, lambda _e: self._toggle_favorite())
        self._refresh_btn.Bind(wx.EVT_BUTTON, lambda _e: self._refresh_selected())
        self._volume_slider.Bind(wx.EVT_SLIDER, self._on_volume_slider)
        self._mute_btn.Bind(wx.EVT_TOGGLEBUTTON, self._on_mute)

        state = getattr(self._controller, "state", None)
        if state is not None:
            self._volume_slider.SetValue(state.volume_percent)
            self._mute_btn.SetValue(state.muted)

        self._populate_sources()

    # -- lifecycle --------------------------------------------------------------

    def show(self, *, initial_source: str | None = None) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        if initial_source is not None:
            self._expand_source(initial_source)
        try:
            show_modal_dialog(self.dialog, "Browse Stations", announce=self._announce)
        finally:
            self.dialog.Destroy()

    # -- tree population --------------------------------------------------------

    def _populate_sources(self) -> None:
        tree = self._tree
        root = tree.AddRoot("Sources")
        for label, kind, payload in _SOURCES:
            node = tree.AppendItem(root, label)
            tree.SetItemData(node, {"kind": kind, "payload": payload, "loaded": False})
            tree.SetItemData(tree.AppendItem(node, "Loading..."), {"kind": "placeholder"})
        first, _cookie = tree.GetFirstChild(root)
        if first.IsOk():
            tree.SelectItem(first)

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
        except Exception:  # noqa: BLE001 - a down source shows as empty, never fatal
            return []
        return []

    def _add_children(self, node: Any, kind: str, raw: list[Any]) -> None:
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
        else:  # "stations" or "genre" -> RadioStation leaves
            for station in raw:
                child = tree.AppendItem(node, station.display_name)
                tree.SetItemData(child, {"kind": "station", "station": station})
        count = tree.GetChildrenCount(node, False)
        self._announce(f"{count} item{'' if count == 1 else 's'}.")
        if count:
            first, _cookie = tree.GetFirstChild(node)
            if first.IsOk():
                tree.SelectItem(first)

    def _add_favorites(self, node: Any) -> None:
        """Build the local Favorites branch: unfiled stations first, then a
        node per folder holding its stations. Favorite leaves reuse the plain
        "station" kind, so Play / Add-Remove Favorite / context menu all work
        unchanged. Local data, so no network fetch."""
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
        self._announce(f"Favorites: {count} item{'' if count == 1 else 's'}.")
        first, _cookie = tree.GetFirstChild(node)
        if first.IsOk():
            tree.SelectItem(first)

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
            self._wx.CallAfter(
                self._add_children, node, data["kind"], raw if isinstance(raw, list) else []
            )

        self._task_manager.submit("radio-browse-tree", _work, on_success=_ok, on_failure=None)

    def _on_activated(self, event: Any) -> None:
        data = self._node_data(event.GetItem())
        if data and data.get("kind") in ("station", "tunein-station"):
            self._play_selected()
            return
        event.Skip()  # a source/folder toggles open

    def _on_selected(self, _event: Any) -> None:
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
            self._favorite_btn.Enable(False)  # unresolved until it plays
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
            self._wx.CallAfter(
                self._tunein_resolved, title, streams if isinstance(streams, list) else []
            )

        self._task_manager.submit("radio-tunein-resolve", _work, on_success=_ok, on_failure=None)

    def _tunein_resolved(self, title: str, streams: list[str]) -> None:
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

    def _toggle_favorite(self) -> None:
        data = self._selected_data()
        if data is None or data.get("kind") != "station":
            self._announce("Play a TuneIn station first to add it to Favorites.")
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
                entries.append(("Open &Website", lambda: self._open_url(station.homepage)))
        elif kind == "tunein-station":
            entries = [("&Play", self._play_selected)]
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
        self._menu_id_refs = id_refs  # pinned while the popup can fire
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
    "weather": lambda safe: radio_browser.noaa_weather_stations(safe_mode=safe),
    "acb": lambda _safe: acb_media.acb_media_stations(),
    "nfb": lambda _safe: nfb_media.nfb_media_stations(),
    "soma": lambda safe: soma_fm.search_stations("", safe_mode=safe),
}
