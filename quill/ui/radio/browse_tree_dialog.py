"""Browse Stations -- one unified tree of every internet-radio source.

A dedicated, search-free browse experience (its counterpart, Search Stations,
keeps the old field-based dialog). The whole window is a single ``wx.TreeCtrl``
whose top-level branches are the sources: Favorites first for a quick jump, then
Popular / Trending / Recently Changed, the geographic and language axes, Weather,
the accessibility services (ACB, NFB, Radio Reading Services), SomaFM, TuneIn,
iHeart, Networks, the catalogs, and Apple Podcasts.

**This module no longer knows what any of those are.** It knows that a node is a
folder you can open or a leaf you can play, and it hands every id back to
:mod:`quill.core.radio.browse_sources`, which is wx-free and unit-tested without
a UI. Adding a source is one entry in ``ROOT_SOURCES`` and one handler there --
not a new node-kind string plus edits in six places in this file, which is what
the tenth source would have cost under the old shape.

A "Find in this folder" box searches from the highlighted folder downward only
(loading that subtree, bounded), so results stay scoped and small; Clear drops
the results and puts the cursor back on the folder you searched from. Internet
sources load lazily on first open, off the UI thread, while Favorites is built
instantly from local data. Enter (or the Play button) plays the highlighted
station -- the Play button reads "Stop" while that station is the one playing. A
rich Shift+F10 / right-click context menu offers Play/Stop, Add/Remove Favorite
(and "Add all stations to Favorites" on a folder), Copy stream link, and Open
website. Playback is the shared ``RadioPlayerController`` passed in, so closing
the window never stops the stream.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from quill.core.radio import browse_helpers, browse_sources
from quill.core.radio.browse_nodes import BrowseNode
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.radio import browse_position

#: Item data for the "Loading..." child that makes a node look expandable.
_PLACEHOLDER = {"kind": "placeholder"}


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
        download_host: object | None = None,
        visible_sources: object | None = None,
        catalog: object | None = None,
        on_offline_catalog: object | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._controller = controller
        self._favorites = favorites_store
        self._task_manager = task_manager
        self._safe_mode = safe_mode
        # Downloads are queued on the app shell, not on this window: the queue
        # must be the one View > Downloads watches and the one that survives
        # this window closing. A dialog-local queue here meant a download
        # started from the tree was invisible to the monitor and unstoppable
        # from the menu -- two views of "the queue" that were never the same
        # queue. Falls back to self so a bare dialog (tests) still works.
        self._download_host = download_host or self
        #: Which root branches to build. The listener's own choice (Station >
        #: Choose Browse Sources...), under the rule search follows: a branch
        #: that is off is not in the tree at all, so it is never opened and
        #: therefore never contacted. ``None`` means never set -> the defaults.
        self._visible_sources = visible_sources
        #: The local station catalog (CatalogStore) or None. Handed straight
        #: to browse(); this window never queries it -- the one-chokepoint rule.
        self._catalog = catalog
        self._on_offline_catalog = on_offline_catalog
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
            self._win.Bind(wx.EVT_CLOSE, self._on_close)
        else:
            self._win = wx.Dialog(
                parent, title="Browse Stations", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
            )
            self._surface = self._win
        self.dialog = self._win  # back-compat alias for callers that reference it
        # Both shapes: Ctrl+F jumps to the Find box from anywhere in the window.
        self._win.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._win.SetMinSize((560, 460))
        root = wx.BoxSizer(wx.VERTICAL)

        # Find sits ABOVE the tree -- physically and in the tab order -- so it
        # is one Shift+Tab away from the tree instead of a lap around the
        # buttons (asked for by name, 2026-08-16).
        find_row = wx.BoxSizer(wx.HORIZONTAL)
        find_row.Add(
            wx.StaticText(self._surface, label="&Find in this folder:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._find_ctrl = wx.TextCtrl(self._surface, style=wx.TE_PROCESS_ENTER)
        self._find_ctrl.SetName(
            "Find in the highlighted folder and everything below it; press Enter"
        )
        find_row.Add(self._find_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        self._find_btn = wx.Button(self._surface, label="Find")
        self._find_btn.SetName("Find in this folder")
        self._find_clear_btn = wx.Button(self._surface, label="C&lear")
        self._find_clear_btn.SetName("Clear the search and return to the folder")
        find_row.Add(self._find_btn, 0, wx.RIGHT, 6)
        find_row.Add(self._find_clear_btn, 0)
        root.Add(find_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

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
        # Tab order: Find box, tree, then the Find/Clear buttons -- so
        # Shift+Tab from the tree lands directly on the Find box.
        self._find_ctrl.MoveBeforeInTabOrder(self._tree)
        self._find_btn.MoveAfterInTabOrder(self._tree)
        self._find_clear_btn.MoveAfterInTabOrder(self._find_btn)

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
        wx = self._wx
        # Ctrl+F: straight to the Find box, from wherever focus is.
        if (
            event.ControlDown()
            and not event.ShiftDown()
            and not event.AltDown()
            and event.GetKeyCode() == ord("F")
        ):
            self._find_ctrl.SelectAll()
            self._find_ctrl.SetFocus()
            self._announce("Find in this folder")
            return
        # A frame has no automatic Escape->Cancel; wire it to close.
        if self._modeless and event.GetKeyCode() == wx.WXK_ESCAPE:
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
        roots = browse_sources.visible_roots(self._visible_sources)
        for node_id, label in roots:
            node = tree.AppendItem(root, label)
            tree.SetItemData(node, {"node_id": node_id, "label": label, "loaded": False})
            tree.SetItemData(tree.AppendItem(node, "Loading..."), dict(_PLACEHOLDER))
            if node_id == "favorites":
                self._favorites_root = node  # kept so an add/remove can refresh it live
        if not roots:
            # Every branch hidden is a legal choice, but an empty window with no
            # explanation reads as a broken one. One row that says the way back.
            empty = tree.AppendItem(
                root, "All sources are hidden. Choose Browse Sources from the menu to show some."
            )
            tree.SetItemData(empty, dict(_PLACEHOLDER))
        browse_position.restore_selection(tree, root)  # browse position memory

    def _fetch_children(self, node_id: str) -> list[BrowseNode]:
        """Off-thread fetch for one node. All the knowledge lives in core."""
        return browse_sources.browse(
            node_id,
            safe_mode=self._safe_mode,
            favorites=self._favorites,
            # getattr: tests build this dialog with __new__ and no __init__.
            catalog=getattr(self, "_catalog", None),
        )

    # -- find in this folder (quill/ui/radio/browse_find.py, GATE-11) -----------

    def _placeholder(self) -> dict:
        """The not-yet-loaded marker, for the find module to rebuild rows with."""
        return dict(_PLACEHOLDER)

    def _is_folder_data(self, data: dict | None) -> bool:
        """True when *data* describes something openable rather than playable."""
        return (
            bool(data)
            and bool(data.get("node_id"))
            and data.get("station") is None
            and not data.get("resolve_lazily")
            and not data.get("is_action")
        )

    def _on_find(self, _event: Any = None) -> None:
        from quill.ui.radio import browse_find

        browse_find.on_find(self)

    def _clear_find(self, _event: Any = None) -> None:
        from quill.ui.radio import browse_find

        browse_find.clear_find(self)

    # -- building rows ----------------------------------------------------------

    def _leaf_data(self, child: BrowseNode) -> dict:
        """Item data for a playable row -- a station now, or one to resolve."""
        return {
            "node_id": child.node_id,
            "label": child.label,
            "station": child.station,
            "resolve_lazily": child.resolve_lazily,
            "note": child.note,
        }

    def _add_children(self, node: Any, children: list[BrowseNode], *, failed: bool = False) -> None:
        """Turn one node's children into tree rows.

        Two cases, and only two. Everything a source wants to say about a row --
        how many children it has, that it opens in a browser, that it must be
        resolved before it can play -- rides along on the BrowseNode instead of
        needing a branch here.
        """
        if not self._tree:  # dialog closed while children were being fetched
            return
        tree = self._tree
        if not node.IsOk():
            return
        tree.DeleteChildren(node)  # clear the "Loading..." placeholder
        if not children:
            # A branch that came back empty because it could not be reached is
            # worth trying again, so it is not marked as loaded. One that is
            # genuinely empty is left alone -- re-fetching an empty folder on
            # every expand would be a network request for a known answer.
            if failed or browse_sources.last_error_was_network():
                self._forget_load(node)
        for child in children:
            item = tree.AppendItem(node, self._row_label(child))
            tree.SetItemData(item, self._row_data(child))
            if child.is_folder:
                tree.SetItemData(tree.AppendItem(item, "Loading..."), dict(_PLACEHOLDER))
        count = tree.GetChildrenCount(node, False)
        self._announce(self._children_summary(node, count, failed=failed))
        from quill.ui.radio import browse_prefetch

        # Read one level ahead: the first few child folders fetch now, so
        # walking downward stays ahead of the listener.
        browse_prefetch.read_ahead(
            self, [c.node_id for c in children if c.is_folder and not c.is_action]
        )
        # #1188: leave the cursor on the just-expanded node -- do NOT jump it
        # into the station list. The count announcement says what is inside; the
        # listener arrows down to enter the list when ready.

    def _forget_load(self, node: Any) -> None:
        """Let a branch be fetched again next time it is opened.

        ``loaded`` is set *before* the fetch, so without this a branch that
        failed could never be retried by closing and reopening it -- the one
        gesture anybody would try.
        """
        data = self._node_data(node)
        if data is not None:
            data["loaded"] = False

    def _row_label(self, child: BrowseNode) -> str:
        """The text of one row. See :func:`browse_helpers.row_label`."""
        return browse_helpers.row_label(child)

    def _row_data(self, child: BrowseNode) -> dict:
        if child.is_folder or child.is_action:
            return {
                "node_id": child.node_id,
                "label": child.label,
                "loaded": False,
                "is_action": child.is_action,
                "child_count": child.child_count,
            }
        return self._leaf_data(child)

    def _children_summary(self, node: Any, count: int, *, failed: bool = False) -> str:
        """What to say after expanding.

        An empty branch must distinguish "there is nothing here" from "this
        source could not be reached": reading the second as the first is how a
        listener concludes a working source is broken, or the reverse. When the
        fetch is *known* to have failed on the network the message says so
        plainly, with the way back; the hedged wording is kept for sources that
        swallow their own errors and return nothing.
        """
        if count:
            return f"{count} item{'' if count == 1 else 's'}."
        data = self._node_data(node) or {}
        label = data.get("label", "this folder")
        node_id = str(data.get("node_id", ""))
        if self._safe_mode and browse_sources.needs_network(node_id):
            return f"{label} is disabled in Safe Mode."
        if failed:
            if getattr(self, "_catalog", None) is not None and callable(
                getattr(self, "_on_offline_catalog", None)
            ):
                # The once-per-session offline sentence (catalog UX, 6.5): the
                # app being quietly fine without the internet is the feature.
                self._on_offline_catalog()
            return f"{label} could not be reached. Close and reopen it to try again."
        if browse_sources.needs_network(node_id):
            return f"Nothing in {label}. It may be empty, or the source could not be reached."
        return f"Nothing in {label}."

    def _add_favorites(self, node: Any, *, select: bool = True) -> None:
        """Build the local Favorites branch.

        Favorites is the one source built from local data, so it never waits on
        a fetch; it still goes through the same ``browse_sources`` handler as
        everything else, so its rows are ordinary rows. ``select=False`` rebuilds
        without moving the selection, for the live refresh after a favorite is
        added or removed, so focus stays where the listener is.
        """
        if not node.IsOk():
            return
        children = self._fetch_children("favorites")
        self._add_children(node, children)
        if not children:
            empty = self._tree.AppendItem(
                node, "No favorites yet -- add stations from any source below."
            )
            self._tree.SetItemData(empty, dict(_PLACEHOLDER))
        if not select:
            return
        first, _cookie = self._tree.GetFirstChild(node)
        if first.IsOk():
            self._tree.SelectItem(first)

    def _refresh_favorites_branch(self) -> None:
        """Rebuild the Favorites branch in place after a favorite is added or
        removed, so the change shows immediately while the window is open. A
        no-op until the branch has been expanded once, and it never moves the
        selection."""
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

    def _is_playable(self, data: dict | None) -> bool:
        """True when activating this row should play something."""
        return bool(data) and (data.get("station") is not None or bool(data.get("resolve_lazily")))

    def _on_expanding(self, event: Any) -> None:
        node = event.GetItem()
        data = self._node_data(node)
        if not self._is_folder_data(data) or data is None:
            return
        if data.get("loaded"):
            return
        data["loaded"] = True
        node_id = str(data["node_id"])
        if node_id == "favorites":
            self._add_favorites(node)  # local, instant, no task manager
            return
        from quill.ui.radio import browse_prefetch

        ready = browse_prefetch.take(self, node_id)
        if ready is not None:
            self._add_children(node, ready)  # prefetched while you arrowed here
            return
        if self._safe_mode and browse_sources.needs_network(node_id):
            self._details.SetValue("Browsing this source is disabled in Safe Mode.")
        self._announce("Loading...")

        def _work(**_kwargs: Any) -> tuple[list[BrowseNode], bool]:
            children = self._fetch_children(node_id)
            # Asked on the SAME thread that browsed: the failure record is kept
            # per thread, so reading it later from the UI-thread callback would
            # read the UI thread's own, always-empty slot -- and a branch that
            # failed on the network would be marked loaded and never retried.
            return children, (not children and browse_sources.last_error_was_network())

        def _ok(_op: str, raw: object) -> None:
            # Already on the UI thread (call_ui_safely marshals + guards this);
            # call directly rather than scheduling a second unguarded CallAfter.
            children, net_failed = raw if isinstance(raw, tuple) else ([], False)
            self._add_children(
                node, children if isinstance(children, list) else [], failed=bool(net_failed)
            )

        def _failed(_op: str, error: BaseException) -> None:
            """Clear the placeholder and say so.

            Without this the branch keeps its "Loading..." row for the rest of
            the session and says nothing -- a tree that is permanently about to
            finish, which is the most misleading state it could be left in.
            ``browse()`` swallows a source's own errors, so reaching here means
            something unexpected, and the honest response is to let it be tried
            again.
            """
            self._forget_load(node)
            self._add_children(node, [], failed=True)

        self._task_manager.submit("radio-browse-tree", _work, on_success=_ok, on_failure=_failed)

    def _on_activated(self, event: Any) -> None:
        data = self._node_data(event.GetItem())
        if self._is_playable(data):
            self._play_selected()
            return
        if data is not None and data.get("is_action"):
            # A row that acts rather than opens -- "Add a Server...". What it
            # does lives in browse_actions, so this window never learns a
            # source-specific behaviour. See quill/ui/radio/browse_actions.py.
            from quill.ui.radio import browse_actions

            browse_actions.perform(self, str(data.get("node_id", "")))
            return
        event.Skip()  # a source/folder toggles open

    def _reload_source_branch(self, node_id: str) -> None:
        """Re-fetch one top-level source by id, after an action changed what it
        contains. See :mod:`quill.ui.radio.browse_refresh`."""
        from quill.ui.radio import browse_refresh

        browse_refresh.reload_source_branch(self, node_id)

    def _on_selected(self, _event: Any) -> None:
        browse_position.remember(self._tree, self._tree.GetSelection())
        data = self._selected_data()
        from quill.ui.radio import browse_prefetch

        # Landing on a collapsed folder starts its fetch now, so the expand
        # that usually follows opens instantly instead of loading.
        browse_prefetch.note_selected(self, data)
        station = data.get("station") if data else None
        if station is not None:
            self._details.SetValue(station.details_text)
            self._play_btn.Enable(True)
            self._refresh_play_button(station)
            self._favorite_btn.Enable(True)
            self._update_favorite_label(station)
        elif self._is_playable(data) and data is not None:
            note = data.get("note") or "resolves when you play it"
            self._details.SetValue(f"{data['label']}\n{note.capitalize()}.")
            self._play_btn.Enable(True)
            self._play_btn.SetLabel("&Play")
            # The stream resolves lazily, but Add to Favorites resolves it on
            # demand (#1210), so the button is live. Label it Add -- we cannot
            # know the saved state before resolving.
            self._favorite_btn.Enable(True)
            self._favorite_btn.SetLabel("Add to &Favorites")
        elif self._is_folder_data(data) and data is not None:
            # A branch explains where its answers come from (catalog UX, 6.5):
            # "Answers from your catalog, updated 2 hours ago." or "Asks the
            # internet each time; nothing is stored." Detail-panel only --
            # never a per-row suffix.
            from quill.core.radio.browse_nodes import split_id
            from quill.core.radio.catalog import read as catalog_read

            kind, _args = split_id(str(data.get("node_id", "")))
            sentence = catalog_read.provenance_sentence(getattr(self, "_catalog", None), kind)
            label_text = str(data.get("label", ""))
            self._details.SetValue(label_text + chr(10) + sentence)
            self._play_btn.Enable(False)
            self._play_btn.SetLabel("&Play")
            self._favorite_btn.Enable(False)
        elif data is not None and data.get("is_action"):
            # An action row explains itself while merely highlighted, so nobody
            # has to press Enter to learn what Enter would do.
            note = str(data.get("note") or "")
            detail = f"{data['label']}\n{note.capitalize()}. " if note else f"{data['label']}\n"
            self._details.SetValue(f"{detail}Press Enter to use it.")
            self._play_btn.Enable(False)
            self._play_btn.SetLabel("&Play")
            self._favorite_btn.Enable(False)
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
        station = data.get("station")
        if station is None:
            if data.get("resolve_lazily"):
                self._resolve_then(data, self._play_station)
            return
        self._play_station(station)

    def _play_station(self, station: RadioStation) -> None:
        if self._is_playing(station):
            self._controller.stop()
            self._announce("Radio stopped")
        else:
            self._controller.play_station(station)
            self._announce(f"Playing {station.display_name}")
        self._refresh_play_button(station)

    def _resolve_then(self, data: dict, then: Callable[[RadioStation], None]) -> None:
        """Resolve a lazy leaf off-thread, then hand the station to *then*.

        One path for both Play and Add to Favorites, and for every source that
        needs it -- TuneIn today, anything else tomorrow -- instead of the two
        near-identical TuneIn-specific methods this replaces.
        """
        label = str(data.get("label", ""))
        node_id = str(data.get("node_id", ""))
        self._details.SetValue(f"Resolving {label}...")

        def _work(**_kwargs: Any) -> RadioStation | None:
            return browse_sources.resolve(node_id, safe_mode=self._safe_mode)

        def _ok(_op: str, resolved: object) -> None:
            # Already on the UI thread (call_ui_safely marshals + guards this).
            if not self._tree:  # window closed while the stream was resolving
                return
            if not isinstance(resolved, RadioStation) or not resolved.stream_url:
                self._announce(f"Could not play {label}.")
                return
            # The source resolves a URL; the row already knew the name, so it
            # supplies one when the resolver did not (TuneIn returns none).
            then(replace(resolved, name=resolved.name or label))

        self._task_manager.submit("radio-browse-resolve", _work, on_success=_ok, on_failure=None)

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

    def _add_favorite_station(self, station: RadioStation) -> None:
        if self._favorites.contains(station):
            self._announce(f"{station.display_name} is already in your Favorites")
            return
        self._favorites.add(station)
        self._announce(f"Added {station.display_name} to Favorites")
        self._on_favorites_changed()
        self._refresh_favorites_branch()

    def _toggle_favorite(self) -> None:
        data = self._selected_data()
        if data is None or not self._is_playable(data):
            self._announce("Select a station to add it to Favorites.")
            return
        station = data.get("station")
        if station is None:
            self._resolve_then(data, self._add_favorite_station)
            return
        if self._favorites.contains(station):
            self._favorites.remove(station.station_uuid or station.stream_url)
            self._announce(f"Removed {station.display_name} from Favorites")
        else:
            self._favorites.add(station)
            self._announce(f"Added {station.display_name} to Favorites")
        self._update_favorite_label(station)
        self._on_favorites_changed()
        self._refresh_favorites_branch()

    def _loaded_stations_under(self, node: Any) -> list[Any]:
        """The stations already loaded under *node*, in tree order.

        Only what is loaded, deliberately -- exactly like Add All to Favorites.
        A folder nobody has opened has no children to read, and fetching them to
        decide whether a context menu should carry an item would make opening a
        menu a network request.
        """
        tree = self._tree
        rows: list[Any] = []
        if not node.IsOk():
            return rows
        child, cookie = tree.GetFirstChild(node)
        while child.IsOk():
            data = self._node_data(child)
            station = data.get("station") if data else None
            if station is not None:
                rows.append(station)
            child, cookie = tree.GetNextChild(node, cookie)
        return rows

    def _favorite_folder(self, node: Any) -> None:
        """Add every loaded station under a folder to Favorites in one go.

        Only the stations already loaded into the tree are added; if the folder
        has not been opened yet, ask the listener to open it first, so a huge
        genre is not fetched-and-favorited blind.
        """
        tree = self._tree
        if not node.IsOk():
            return
        added = 0
        loaded_any = False
        child, cookie = tree.GetFirstChild(node)
        while child.IsOk():
            data = self._node_data(child)
            station = data.get("station") if data else None
            if station is not None:
                loaded_any = True
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
        """Re-fetch the highlighted node's source (or its parent source).
        See :mod:`quill.ui.radio.browse_refresh`."""
        from quill.ui.radio import browse_refresh

        browse_refresh.refresh_selected(self)

    # -- context menu (Shift+F10 / right-click) ---------------------------------

    def _on_context_menu(self, event: Any) -> None:
        """The row's own menu. Built in ``browse_tree_menu`` (GATE-11)."""
        from quill.ui.radio import browse_tree_menu

        browse_tree_menu.show_for_event(self, event)

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

    def _expand_source(self, source: str) -> None:
        """Land on one top-level branch, by its label or its id.

        Both accepted because callers know different things: a menu item knows
        the label it shows, code knows the stable id -- and matching on the id
        keeps a caller working when a label is reworded.
        """
        tree = self._tree
        root = tree.GetRootItem()
        child, cookie = tree.GetFirstChild(root)
        while child.IsOk():
            data = self._node_data(child) or {}
            if tree.GetItemText(child) == source or data.get("node_id") == source:
                tree.SelectItem(child)
                tree.Expand(child)
                return
            child, cookie = tree.GetNextChild(root, cookie)
