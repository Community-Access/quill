"""QuillBeacon desktop shell -- three-pane accessible UI (PRD 13.3).

Sidebar (destinations + collections) | Results (search + list) | Details.
Every pane is a named region; focus moves predictably; no drag-and-drop is
required for any action. Announcements go through the status bar. This is a
self-contained wx shell for the first slice; the production target moves the
engine into ``quill/apps/beacon.py`` on ``AppShellFrame`` (PRD 44.1).
"""

from __future__ import annotations

import os
import sys
import time
import webbrowser
from pathlib import Path

import wx

from quill.apps.beacon import a11y as a11y_mod
from quill.apps.beacon import (
    assist,
    capture,
    capture_bridge,
    db,
    exporters,
    external_player,
    importers,
    routing,
    search,
    uld,
)
from quill.apps.beacon import feeds as feeds_mod
from quill.apps.beacon import publish as publish_mod
from quill.apps.beacon.announce import Announcer
from quill.apps.beacon.commands import Command, CommandPalette
from quill.apps.beacon.dialogs import (
    A11ySettingsDialog,
    AttachmentsDialog,
    BuildSearchDialog,
    CollectionEditorDialog,
    PreferencesDialog,
    PublishDialog,
    QuickCaptureDialog,
    RadioProgramDialog,
    RepairReviewDialog,
    SmartCollectionsDialog,
    StatusCenterDialog,
    SyncHistoryDialog,
    SyncSettingsDialog,
    TrailEditorDialog,
    TrailStepDialog,
    parse_hhmm,
)
from quill.apps.beacon.model import (
    HEALTH_BROKEN,
    SCHEMA_VERSION,
)
from quill.apps.beacon.sync_ui import SyncController
from quill.apps.beacon.undo import UndoManager, restore_beacons, snapshot_beacons
from quill.ui.dialog_contract import show_message_box

_TITLE = "QuillBeacon"
_VERSION = "0.1.0"

# Destinations in the sidebar (PRD 13.1).
DESTINATIONS = [
    ("Home", "home"),
    ("Inbox", "inbox"),
    ("All Bookmarks", "all"),
    ("Collections", "collections"),
    ("Smart Collections", "smart"),
    ("Listen Later", "listen"),
    ("Podcasts", "podcasts"),
    ("Radio", "radio"),
    ("Recent", "recent"),
    ("Favorites", "favorites"),
    ("Needs Attention", "attention"),
    ("Archive", "archive"),
    ("Trash", "trash"),
]


def _name(ctrl: wx.Control, name: str) -> None:
    ctrl.SetName(name)


def _data_dir() -> Path:
    """Local-first store location. Mirrors quill.core.paths.app_data_dir."""
    from quill.apps.beacon import paths

    return paths.data_dir()


class BeaconFrame(wx.Frame):
    def __init__(self) -> None:
        super().__init__(None, title=_TITLE, size=(1100, 720))
        self.SetTitle(_TITLE)
        self.data_dir = _data_dir()
        self.store = db.BeaconStore(self.data_dir / "beacons.db")
        self.a11y = a11y_mod.load(self.data_dir)
        self.announcer = Announcer(self, verbosity=self.a11y.verbosity)
        self.undo = UndoManager(announcer=self.announcer.say)
        self.sync = SyncController(self.store, self.data_dir)
        self.publisher = publish_mod.PublishManager(self.store, self.data_dir)
        self.current_scope = "all"  # destination or collection name
        self.current_sort = "added"
        self.last_query = ""

        self._build_menu()
        self._build_ui()
        a11y_mod.apply_to_frame(self, self.a11y)
        self._refresh_sidebar()
        self._refresh_results()
        self._start_capture_bridge()
        self._start_tray()
        self._setup_auto_sync()
        self.announcer.say("QuillBeacon ready", "normal")
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_ICONIZE, self._on_iconize)
        self.Centre()

    # -- capture bridge (browser extensions, PRD 46) -------------------------

    def _start_capture_bridge(self) -> None:
        """Start the localhost capture bridge for browser extensions."""
        self.bridge = capture_bridge.CaptureBridge(
            str(self.data_dir / "beacons.db"),
            data_dir=str(self.data_dir),
            on_capture=self._on_bridge_capture,
        )
        try:
            port = self.bridge.start()
            # Record the port so extensions can discover it.
            (self.data_dir / "bridge_port.txt").write_text(str(port), encoding="utf-8")
            self.announcer.say(f"Capture bridge on port {port}", "verbose")
        except OSError:
            self.bridge = None
            self.announcer.say("Capture bridge unavailable", "verbose")

    def _on_bridge_capture(self, beacon) -> None:
        """A browser extension captured something: refresh and announce."""
        # Called from the bridge's HTTP thread; marshal onto the UI thread.
        wx.CallAfter(self._refresh_results)
        wx.CallAfter(self.announcer.say, f"Captured: {beacon.title}", "normal")

    def _on_capture_bridge_info(self, _e) -> None:
        """Show the bridge URL and token so the user can paste into extensions."""
        if not getattr(self, "bridge", None):
            show_message_box(
                "Capture bridge is not running.", "QuillBeacon", wx.OK | wx.ICON_INFORMATION, self
            )
            return
        msg = (
            f"Capture bridge: {self.bridge.base_url}\n\n"
            f"Token (paste into the extension Options):\n{self.bridge.token}"
        )
        dlg = wx.TextEntryDialog(
            self,
            msg,
            "QuillBeacon Capture Bridge",
            value=self.bridge.token,
            style=wx.TE_MULTILINE | wx.OK,
        )
        dlg.ShowModal()
        dlg.Destroy()

    # -- system tray + status center (PRD 13.4, 44.3) ------------------------

    def _start_tray(self) -> None:
        """Create the tray icon. Fail-safe: no tray support -> no icon."""
        try:
            from quill.apps.beacon.tray import TrayIcon

            self.tray = TrayIcon(
                self,
                on_capture=self._on_capture,
                on_sync_now=self._on_sync_now,
                on_status=self._on_status_center,
            )
        except Exception:
            self.tray = None

    def _on_iconize(self, _e) -> None:
        """Minimize to tray rather than the taskbar when a tray icon exists."""
        if getattr(self, "tray", None):
            self.Hide()

    def _status_rows(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        if getattr(self, "bridge", None):
            rows.append(("Capture bridge", f"running on {self.bridge.base_url}"))
        else:
            rows.append(("Capture bridge", "not running"))
        cfg = self.sync.config
        rows.append(("Sync transport", cfg.transport))
        rows.append(("Sync configured", "yes" if cfg.is_configured() else "no"))
        rows.append(("Vault", "unlocked" if self.sync.is_unlocked() else "locked"))
        if cfg.transport == "server" and cfg.device_token:
            h = self.sync.fetch_hints()
            if "new" in h:
                n = h["new"]
                rows.append(("Server hints", f"{n} new" if n else "up to date"))
            else:
                rows.append(("Server hints", h.get("error", "unavailable")))
        rows.append(("Library count", str(self.store.count(include_trashed=False))))
        rows.append((
            "Trash count",
            str(self.store.count(include_trashed=True) - self.store.count(include_trashed=False)),
        ))
        try:
            broken = self.store.conn.execute(
                "SELECT COUNT(*) AS n FROM beacons WHERE health='broken' AND trashed=0"
            ).fetchone()["n"]
            rows.append(("Needs attention", str(broken)))
        except Exception:
            pass
        return rows

    def _on_status_center(self, _e=None) -> None:
        dlg = StatusCenterDialog(
            self, status_provider=self._status_rows, announcer=self.announcer.say
        )
        dlg.ShowModal()
        dlg.Destroy()

    # -- collection / trail / repair editors (PRD 16, 17.4) ------------------

    def _on_collection_editor(self, _e) -> None:
        from quill.apps.beacon.model import Collection

        names = [c.name for c in self.store.list_collections()]
        # If a collection is selected in the sidebar, edit it; otherwise create.
        scope = self.current_scope or ""
        existing = None
        if scope.startswith("collection:"):
            existing = self.store.collection_by_name(scope.split(":", 1)[1])
        dlg = CollectionEditorDialog(self, collection=existing, existing_names=names)
        if dlg.ShowModal() == wx.ID_OK and dlg.result():
            r = dlg.result()
            col = Collection(
                collection_id=r["collection_id"],
                name=r["name"],
                description=r["description"],
                parent_id=r["parent_id"],
                sharing=r["sharing"],
                color=r["color"],
            )
            self.store.put_collection(col)
            self.store.conn.commit()
            self._refresh_sidebar()
            action = "updated" if r["collection_id"] else "saved"
            self.announcer.say(f"Collection {r['name']} {action}")
        dlg.Destroy()

    # -- publish a collection as a read-only web page (plan section 12) -------

    def _bridge_port(self) -> int | None:
        """The port the capture bridge is serving on, if any."""
        if getattr(self, "bridge", None):
            return self.bridge.port
        return capture_bridge.find_bridge_port(str(self.data_dir))

    def _publish_current_collection(self) -> dict:
        """Publish the currently-selected collection without a dialog.

        Returns the manager result dict. Used by the headless path and as the
        testable core of the publish action.
        """
        scope = self.current_scope or ""
        if not scope.startswith("collection:"):
            return {"error": "no collection selected"}
        name = scope.split(":", 1)[1]
        return self.publisher.publish(name, port=self._bridge_port())

    def _on_publish(self, _e) -> None:
        scope = self.current_scope or ""
        if not scope.startswith("collection:"):
            show_message_box(
                "Select a collection in the sidebar first.",
                "QuillBeacon",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return
        name = scope.split(":", 1)[1]
        dlg = PublishDialog(
            self, publisher=self.publisher, collection_name=name, port=self._bridge_port()
        )
        dlg.ShowModal()
        dlg.Destroy()

    def _on_trail_editor(self, _e) -> None:
        from quill.apps.beacon.model import Trail

        dlg = TrailEditorDialog(self, self.store)
        if dlg.ShowModal() == wx.ID_OK and dlg.result():
            r = dlg.result()
            kwargs = dict(title=r["title"], description=r["description"], steps=r["steps"])
            if r["trail_id"]:
                kwargs["trail_id"] = r["trail_id"]
            trail = Trail(**kwargs)
            self.store.put_trail(trail)
            self.store.conn.commit()
            self.announcer.say(f"Trail {r['title']} saved with {len(r['steps'])} step(s)")
        dlg.Destroy()

    def _on_smart_collections(self, _e) -> None:
        dlg = SmartCollectionsDialog(self, self.store)
        dlg.ShowModal()
        dlg.Destroy()
        self._refresh_sidebar()

    def _on_revalidate_health(self, _e) -> None:
        """On-demand link-health revalidation (PRD 13.4, 17.4).

        Local files are checked against the filesystem; web links are checked
        over the network only if the requests library is installed, and only
        after the user confirms. Fail-safe: a missing library or a failed check
        never corrupts the library.
        """
        from quill.apps.beacon import health

        will_network = health._has_requests() if hasattr(health, "_has_requests") else True
        confirm = show_message_box(
            "Re-check link health now?\n\n"
            + (
                "Web links will be checked over the network. "
                if will_network
                else "Web links will be skipped (requests not installed); "
                "only local files will be checked. "
            )
            + "Broken links are marked so you can review or repair them.",
            "Revalidate Health",
            style=wx.ICON_QUESTION | wx.YES_NO,
        )
        if confirm != wx.YES:
            return
        fetcher = None
        if will_network:
            try:
                fetcher = health.default_fetcher
            except Exception:
                fetcher = None
        summary = health.revalidate(self.store, fetcher=fetcher)
        self._refresh_results()
        self.announcer.say(
            f"Checked {summary['checked']}, "
            f"{summary['available']} available, {summary['broken']} broken, "
            f"{summary['skipped']} skipped"
        )
        show_message_box(
            f"Checked: {summary['checked']}\n"
            f"Available: {summary['available']}\n"
            f"Broken: {summary['broken']}\n"
            f"Skipped (no network check): {summary['skipped']}",
            "Revalidate Health",
            wx.OK,
        )

    def _on_repair_review(self, _e) -> None:
        b = self._selected_beacon()
        if not b:
            self.announcer.say("Select a beacon first")
            return
        if not b.locations:
            self.announcer.say("This beacon has no saved location to repair")
            return
        loc = b.locations[0]
        suggestion = uld.repair_suggestion(loc, content=None)
        dlg = RepairReviewDialog(self, beacon_title=b.title, suggestion=suggestion)
        if dlg.ShowModal() == wx.ID_OK:
            choice = dlg.choice()
            if choice == RepairReviewDialog.MARK_BROKEN:
                b.health = "broken"
                self.store.put_beacon(b)
                self._refresh_results()
                self.announcer.say("Marked broken for later")
            elif choice == RepairReviewDialog.ACCEPT_REPAIR:
                # Apply the proposed position/summary back to the location.
                pos = suggestion.get("position", {})
                if pos:
                    loc.positional_locator = pos
                loc.display_summary = suggestion.get("message") or loc.display_summary
                loc.confidence = suggestion.get("confidence", loc.confidence)
                self.store.put_beacon(b)
                self._refresh_results()
                self.announcer.say("Accepted repair")
            else:
                self.announcer.say("Kept old location")
        dlg.Destroy()

    # -- menu -----------------------------------------------------------------

    def _build_menu(self) -> None:
        mb = wx.MenuBar()

        m_file = wx.Menu()
        self._add(m_file, "&New Bookmark\tCtrl+N", self._on_capture, "Add a new bookmark")
        self._add(
            m_file, "&Import...\tCtrl+I", self._on_import, "Import bookmarks or subscriptions"
        )
        self._add(m_file, "&Export...\tCtrl+E", self._on_export, "Export the library")
        m_file.AppendSeparator()
        self._add(m_file, "E&xit\tCtrl+Q", lambda _e: self.Close(), "Exit QuillBeacon")
        mb.Append(m_file, "&File")

        m_edit = wx.Menu()
        self._add(m_edit, "&Open\tEnter", self._on_open, "Open the selected bookmark")
        self._add(m_edit, "&Trash\tDelete", self._on_trash, "Move to trash")
        self._add(m_edit, "&Restore\tShift+Delete", self._on_restore, "Restore from trash")
        self._add(m_edit, "Archive\tCtrl+Shift+A", self._on_archive, "Archive")
        self._add(m_edit, "Toggle &Favorite\tCtrl+D", self._on_favorite, "Toggle favorite")
        self._add(
            m_edit, "Add to &Collection...\tCtrl+L", self._on_add_collection, "Add to collection"
        )
        self._add(
            m_edit,
            "&Attachments...\tCtrl+Shift+E",
            self._on_attachments,
            "Add, view, or remove files, URLs, and notes attached to the selected beacon",
        )
        m_edit.AppendSeparator()
        self._add(
            m_edit,
            "&Undo\tCtrl+Z",
            self._on_undo,
            "Undo the last change (bulk ops undo as one step)",
        )
        m_edit.AppendSeparator()
        self._add(
            m_edit, "Bulk &Trash Selected\tCtrl+Shift+Y", self._on_bulk_trash, "Trash all selected"
        )
        self._add(
            m_edit,
            "Bulk &Archive Selected\tCtrl+Shift+H",
            self._on_bulk_archive,
            "Archive all selected",
        )
        self._add(
            m_edit,
            "Bulk &Restore Selected\tCtrl+Shift+U",
            self._on_bulk_restore,
            "Restore all selected from trash",
        )
        self._add(
            m_edit,
            "Bulk Toggle &Favorite\tCtrl+Shift+D",
            self._on_bulk_favorite,
            "Toggle favorite for all selected",
        )
        self._add(
            m_edit, "Bulk Add &Tag...\tCtrl+Shift+J", self._on_bulk_tag, "Add a tag to all selected"
        )
        self._add(
            m_edit,
            "Bulk Remove Ta&g...\tCtrl+Shift+V",
            self._on_bulk_remove_tag,
            "Remove a tag from all selected",
        )
        self._add(
            m_edit,
            "Bulk Add to Collec&tion...\tCtrl+Shift+O",
            self._on_bulk_add_collection,
            "Add all selected to a collection",
        )
        self._add(
            m_edit,
            "Bulk &Delete Selected\tCtrl+Shift+Delete",
            self._on_bulk_delete,
            "Permanently delete all selected (undoable)",
        )
        m_edit.AppendSeparator()
        self._add(m_edit, "&Find Duplicates", self._on_duplicates, "Find duplicate bookmarks")
        mb.Append(m_edit, "&Edit")

        m_view = wx.Menu()
        self._add(m_view, "&Search\tCtrl+F", lambda _e: self.search_box.SetFocus(), "Focus search")
        self._add(
            m_view,
            "&Build Search...\tCtrl+Shift+F",
            self._on_build_search,
            "Build a structured search",
        )
        self._add(
            m_view,
            "&Save Search as Smart Collection...\tCtrl+Shift+G",
            self._on_save_search,
            "Save the current search as a live Smart Collection",
        )
        self._add(
            m_view, "Command &Palette\tCtrl+Shift+P", self._on_palette, "Open command palette"
        )
        self._add(
            m_view,
            "&Accessibility Settings...",
            self._on_a11y_settings,
            "Verbosity, high contrast, text scale, reduced motion",
        )
        self._add(
            m_view,
            "&Preferences...\tCtrl+,",
            self._on_preferences,
            "Accessibility, sync, capture bridge, and published pages",
        )
        m_view.AppendSeparator()
        self._add(m_view, "&Where Am I?\tF1", self._on_where_am_i, "Announce current context")
        self._add(m_view, "&Next Pane\tF6", self._on_next_pane, "Move to next pane")
        mb.Append(m_view, "&View")

        m_media = wx.Menu()
        self._add(
            m_media,
            "&Subscribe to Podcast...\tCtrl+Shift+S",
            self._on_subscribe,
            "Subscribe to a podcast feed",
        )
        self._add(
            m_media,
            "&Refresh Feeds\tCtrl+Shift+R",
            self._on_refresh_feeds,
            "Refresh subscribed podcast feeds",
        )
        self._add(
            m_media,
            "Play in &Player\tCtrl+Shift+L",
            self._on_play_in_player,
            "Open the selected episode in the built-in player",
        )
        self._add(
            m_media,
            "Play in External &Player",
            self._on_play_external,
            "Hand off to VLC, mpv, or the system player with resume time",
        )
        m_media.AppendSeparator()
        self._add(
            m_media,
            "Add Radio &Station...",
            self._on_add_station,
            "Save a radio station stream with fallback alternates",
        )
        self._add(
            m_media,
            "Add Radio &Program...",
            self._on_add_program,
            "Capture a radio program with schedule metadata",
        )
        mb.Append(m_media, "&Media")

        m_tools = wx.Menu()
        self._add(
            m_tools,
            "Capture &Bridge...\tCtrl+Shift+B",
            self._on_capture_bridge_info,
            "Show the capture bridge URL and token for browser extensions",
        )
        m_tools.AppendSeparator()
        self._add(
            m_tools,
            "&Collection Editor...\tCtrl+Shift+C",
            self._on_collection_editor,
            "Edit the selected collection, or create a new one",
        )
        self._add(
            m_tools, "&Trail Editor...", self._on_trail_editor, "Create or edit a learning trail"
        )
        self._add(
            m_tools,
            "Smart &Collections Manager...",
            self._on_smart_collections,
            "Edit or delete saved searches (Smart Collections)",
        )
        self._add(
            m_tools,
            "Review Location &Repair...",
            self._on_repair_review,
            "Review a proposed repair for a broken or shifted location",
        )
        self._add(
            m_tools,
            "Revalidate &Health...",
            self._on_revalidate_health,
            "Re-check whether saved links are still reachable (web links use the network)",
        )
        self._add(
            m_tools,
            "Publish Collection...\tCtrl+Shift+W",
            self._on_publish,
            "Publish the selected collection as a read-only web page",
        )
        self._add(
            m_tools,
            "External &Player...",
            self._on_external_player,
            "Choose the external media player and per-type defaults",
        )
        m_tools.AppendSeparator()
        self._add(
            m_tools,
            "&Status Center...",
            self._on_status_center,
            "Capture bridge, sync, and library health at a glance",
        )
        mb.Append(m_tools, "&Tools")

        m_sync = wx.Menu()
        self._add(
            m_sync,
            "Sync &Settings...",
            self._on_sync_settings,
            "Configure sync: folder or server, sign in, unlock the vault",
        )
        self._add(m_sync, "Sync &Now", self._on_sync_now, "Push and pull changes now")
        self._add(
            m_sync,
            "Sync &History...",
            self._on_sync_history,
            "View sync history, conflicts, and roll back",
        )
        self._add(
            m_sync,
            "&Auto Sync...",
            self._on_auto_sync,
            "Set an automatic sync interval (off by default)",
        )
        mb.Append(m_sync, "&Sync")

        m_assist = wx.Menu()
        self._add(
            m_assist,
            "Suggest &Tags\tCtrl+Shift+T",
            self._on_suggest_tags,
            "Suggest tags for the selected beacon from its text",
        )
        self._add(
            m_assist,
            "Suggest &Relationships\tCtrl+Shift+K",
            self._on_suggest_relationships,
            "Suggest related beacons by shared tags, collections, or domain",
        )
        self._add(
            m_assist,
            "&Summarize Note\tCtrl+Shift+M",
            self._on_summarize,
            "Produce an extractive summary of the selected beacon's note",
        )
        mb.Append(m_assist, "&Assist")

        m_help = wx.Menu()
        self._add(m_help, "&About", self._on_about, "About QuillBeacon")
        mb.Append(m_help, "&Help")

        self.SetMenuBar(mb)

    def _add(self, menu, label, handler, hint: str = "") -> None:
        item = menu.Append(wx.ID_ANY, label, helpString=hint)
        self.Bind(wx.EVT_MENU, handler, item)

    # -- UI -------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = wx.BoxSizer(wx.VERTICAL)
        self.CreateStatusBar()
        self.SetStatusText("QuillBeacon")

        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.splitter.SetName("Main split")

        # Sidebar
        sidebar = wx.Panel(self.splitter, style=wx.TAB_TRAVERSAL)
        sidebar.SetName("Sidebar")
        sb_sizer = wx.BoxSizer(wx.VERTICAL)
        sb_label = wx.StaticText(sidebar, label="&Destinations")
        sb_sizer.Add(sb_label, 0, wx.ALL, 6)
        self.dest_list = wx.ListBox(sidebar, style=wx.LB_SINGLE)
        _name(
            self.dest_list,
            "Destinations and collections. Enter to open, F2 to rename a collection.",
        )
        sb_sizer.Add(self.dest_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        self.new_col_btn = wx.Button(sidebar, label="New &Collection")
        _name(self.new_col_btn, "New collection")
        sb_sizer.Add(self.new_col_btn, 0, wx.EXPAND | wx.ALL, 6)
        sidebar.SetSizer(sb_sizer)

        # Right: search + results + details
        right = wx.Panel(self.splitter, style=wx.TAB_TRAVERSAL)
        right.SetName("Results and details")
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        search_row = wx.BoxSizer(wx.HORIZONTAL)
        self.search_box = wx.SearchCtrl(right)
        self.search_box.SetDescriptiveText("Search bookmarks  (type:episode tag:research ...)")
        _name(self.search_box, "Search bookmarks. Press Enter to search, Escape to clear.")
        search_row.Add(self.search_box, 1, wx.EXPAND | wx.ALL, 6)
        self.sort_combo = wx.ComboBox(
            right,
            choices=["added", "title", "opened", "mostOpened", "type", "health", "relevance"],
            style=wx.CB_READONLY,
        )
        self.sort_combo.SetSelection(0)
        _name(self.sort_combo, "Sort order")
        search_row.Add(self.sort_combo, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        right_sizer.Add(search_row, 0, wx.EXPAND)

        self.results = wx.ListCtrl(right, style=wx.LC_REPORT | wx.LC_VIRTUAL)
        self.results.SetName(
            "Bookmarks list. Enter opens, Delete trashes, F2 edits, F1 announces. "
            "Ctrl+Space or Shift+arrows select multiple for bulk actions."
        )
        self.results.AppendColumn("Title", width=260)
        self.results.AppendColumn("Type", width=110)
        self.results.AppendColumn("Location", width=200)
        self.results.AppendColumn("Collection", width=120)
        self.results.AppendColumn("Tags", width=120)
        self.results.AppendColumn("Date", width=120)
        self.results.AppendColumn("Health", width=90)
        right_sizer.Add(self.results, 1, wx.EXPAND | wx.ALL, 6)

        details_label = wx.StaticText(right, label="&Details")
        right_sizer.Add(details_label, 0, wx.LEFT | wx.RIGHT, 8)
        self.details = wx.TextCtrl(right, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        _name(self.details, "Details for the selected bookmark")
        right_sizer.Add(self.details, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        right_sizer.SetItemMinSize(self.details, (-1, 140))

        right.SetSizer(right_sizer)

        self.splitter.SplitVertically(sidebar, right, 240)
        self.splitter.SetMinimumPaneSize(180)
        root.Add(self.splitter, 1, wx.EXPAND)
        self.SetSizer(root)

        # Bindings
        self.search_box.Bind(wx.EVT_TEXT, self._on_search_text)
        self.search_box.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, lambda _e: self._refresh_results())
        self.search_box.Bind(wx.EVT_KEY_DOWN, self._on_search_key)
        self.sort_combo.Bind(wx.EVT_COMBOBOX, lambda _e: self._on_sort_change())
        self.dest_list.Bind(wx.EVT_LISTBOX, self._on_destination)
        self.dest_list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_destination)
        self.new_col_btn.Bind(wx.EVT_BUTTON, self._on_new_collection)
        self.results.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_open)
        self.results.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self.results.Bind(wx.EVT_KEY_DOWN, self._on_results_key)

        self._results_cache: list = []
        self.search_box.SetFocus()

    # -- sidebar --------------------------------------------------------------

    def _refresh_sidebar(self) -> None:
        self.dest_list.Clear()
        for label, _key in DESTINATIONS:
            self.dest_list.Append(label)
        for col in self.store.list_collections():
            self.dest_list.Append(f"  {col.name}")
        for ss in self.store.list_saved_searches():
            self.dest_list.Append(f"  [smart] {ss.name}")
        for tr in self.store.list_trails():
            done = sum(1 for s in tr.steps if s.get("completed"))
            self.dest_list.Append(f"  > {tr.title} ({done}/{len(tr.steps)})")

    def _on_destination(self, _e) -> None:
        sel = self.dest_list.GetSelection()
        if sel < 0:
            return
        n_dest = len(DESTINATIONS)
        cols = self.store.list_collections()
        n_col = len(cols)
        searches = self.store.list_saved_searches()
        n_smart = len(searches)
        if sel < n_dest:
            self.current_scope = DESTINATIONS[sel][1]
        elif sel < n_dest + n_col:
            self.current_scope = f"collection:{cols[sel - n_dest].name}"
        elif sel < n_dest + n_col + n_smart:
            idx = sel - n_dest - n_col
            if 0 <= idx < n_smart:
                self.current_scope = f"smart:{searches[idx].search_id}"
        else:
            trails = self.store.list_trails()
            idx = sel - n_dest - n_col - n_smart
            if 0 <= idx < len(trails):
                self._open_trail(trails[idx])
                return
        self._refresh_results()

    def _open_trail(self, trail) -> None:
        """Open the step-through view for a trail (PRD 17.4)."""
        dlg = TrailStepDialog(
            self,
            self.store,
            trail,
            on_open_beacon=self._open_beacon_by_id,
            announcer=self.announcer.say,
        )
        dlg.ShowModal()
        dlg.Destroy()
        self._refresh_sidebar()

    def _open_beacon_by_id(self, beacon_id: str) -> None:
        b = self.store.get_beacon(beacon_id)
        if b is None:
            return
        self._open_beacon(b)

    def _on_new_collection(self, _e) -> None:
        name = wx.GetTextFromUser("Collection name:", "New Collection", "")
        if name:
            self.store._ensure_collection(name)
            self.store.conn.commit()
            self._refresh_sidebar()
            self.announcer.say(f"Collection {name} created")

    # -- search / results -----------------------------------------------------

    def _on_search_text(self, _e) -> None:
        self.last_query = self.search_box.GetValue()
        self._refresh_results()

    def _on_search_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.search_box.Clear()
            self._refresh_results()
            return
        if event.GetKeyCode() == wx.WXK_DOWN:
            self.results.SetFocus()
            if self.results.GetItemCount():
                self.results.SetItemState(0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            return
        event.Skip()

    def _on_sort_change(self) -> None:
        self.current_sort = self.sort_combo.GetValue()
        self._refresh_results()

    def _scope_filter(self) -> str:
        """Fold the destination scope into the query string."""
        scope = self.current_scope
        if scope == "all":
            return self.last_query
        if scope == "inbox":
            return (self.last_query + " inbox").strip()
        if scope == "favorites":
            return (self.last_query + " favorite").strip()
        if scope == "trash":
            return (self.last_query + " trash").strip()
        if scope == "attention":
            return (self.last_query + " health:broken").strip()
        if scope == "archive":
            return (self.last_query + " not:archived").strip()  # archive view handled below
        if scope.startswith("collection:"):
            col = scope.split(":", 1)[1]
            return (self.last_query + f' collection:"{col}"').strip()
        return self.last_query

    def _refresh_results(self) -> None:
        # Smart Collections evaluate their saved grammar live (PRD 15.6).
        if self.current_scope.startswith("smart:"):
            sid = self.current_scope.split(":", 1)[1]
            ss = self.store.get_saved_search(sid)
            if ss is None:
                self._results_cache = []
                self.results.SetItemCount(0)
                self.announcer.say("Smart collection not found")
                return
            try:
                results = search.evaluate_saved_search(self.store, ss, limit=2000)
            except Exception as ex:
                self.announcer.say(f"Smart collection error: {ex}")
                results = []
            self._results_cache = results
            self.results.SetItemCount(len(results))
            if results:
                self.results.RefreshItem(0)
            self.announcer.announce_count(len(results), filtered=True)
            if results:
                self._show_details(results[0])
            return

        query = self._scope_filter()
        try:
            results = search.search(self.store, query, sort=self.current_sort, limit=2000)
        except Exception as ex:  # never let a bad query crash the UI
            self.announcer.say(f"Search error: {ex}")
            results = []
        self._results_cache = results
        self.results.SetItemCount(len(results))
        if results:
            self.results.RefreshItem(0)
        self.announcer.announce_count(len(results), filtered=bool(query.strip()))
        if results:
            self._show_details(results[0])

    def OnGetItemText(self, item: int, column: int) -> str:  # noqa: N802 (wx virtual)
        if item >= len(self._results_cache):
            return ""
        b = self._results_cache[item]
        res = self.store.get_resource(b.resource_id) if b.resource_id else None
        if column == 0:
            return b.title or (res.title if res else "")
        if column == 1:
            return res.type if res else ""
        if column == 2:
            return b.locations[0].display_summary if b.locations else ""
        if column == 3:
            return ", ".join(b.collections)
        if column == 4:
            return ", ".join(b.tags)
        if column == 5:
            return time.strftime("%Y-%m-%d", time.localtime(b.date_added / 1000))
        if column == 6:
            return b.health
        return ""

    def _on_select(self, _e) -> None:
        sel = self.results.GetFirstSelected()
        if 0 <= sel < len(self._results_cache):
            self._show_details(self._results_cache[sel])
            self.announcer.say(
                f"{sel + 1} of {len(self._results_cache)}: {self._results_cache[sel].title}",
                "verbose",
            )

    def _show_details(self, b) -> None:
        res = self.store.get_resource(b.resource_id) if b.resource_id else None
        lines = [f"Title: {b.title}"]
        if res:
            lines.append(f"Type: {res.type}")
            lines.append(f"URL/Path: {res.primary_uri}")
        lines.append(f"Health: {b.health}")
        lines.append(f"Favorite: {'yes' if b.favorite else 'no'}")
        lines.append(f"Tags: {', '.join(b.tags) or '(none)'}")
        lines.append(f"Collections: {', '.join(b.collections) or '(none)'}")
        lines.append(
            f"Added: {time.strftime('%Y-%m-%d %H:%M', time.localtime(b.date_added / 1000))}"
        )
        lines.append(f"Opened: {b.open_count} times")
        if b.note:
            lines.append("")
            lines.append(f"Note: {b.note}")
        for i, loc in enumerate(b.locations):
            lines.append("")
            lines.append(f"Location {i + 1}: {loc.display_summary or loc.type}")
            if loc.text_quote.get("exact"):
                lines.append(f'  Quote: "{loc.text_quote["exact"]}"')
            if loc.media_start_ms is not None:
                lines.append(f"  Time: {uld._fmt_time(loc.media_start_ms)}")
        rels = self.store.relationships_for(b.beacon_id)
        if rels:
            lines.append("")
            lines.append("Related:")
            for r in rels:
                other = r.tgt_beacon if r.src_beacon == b.beacon_id else r.src_beacon
                ob = self.store.get_beacon(other)
                lines.append(f"  {r.type}: {ob.title if ob else other}")
        self.details.SetValue("\n".join(lines))

    def _on_results_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_DELETE:
            self._on_trash(event)
            return
        if event.GetKeyCode() == wx.WXK_F2:
            self._on_rename(event)
            return
        event.Skip()

    # -- actions --------------------------------------------------------------

    def _on_capture(self, _e=None) -> None:
        dlg = QuickCaptureDialog(self, collections=[c.name for c in self.store.list_collections()])
        if dlg.ShowModal() == wx.ID_OK:
            r = dlg.result()
            if not r:
                return
            beacon, res = capture.capture(
                r["url"],
                title=r["title"],
                note=r["note"],
                tags=r["tags"],
                collections=[r["collection"]] if r["collection"] else [],
                favorite=r["favorite"],
                capture_source="ui:quickcapture",
            )
            routed = routing.route(beacon, res, routing.load_rules(self.data_dir))
            self.store.put_beacon(beacon, resource=res)
            self._refresh_sidebar()
            self._refresh_results()
            if routed:
                self.announcer.say(f"Bookmark added to Inbox and filed in {routed}")
            else:
                self.announcer.say(f"Bookmark added to {'Inbox' if beacon.in_inbox else 'library'}")
            if r["open"]:
                self._open_beacon(beacon)
        dlg.Destroy()

    def _open_beacon(self, b) -> None:
        res = self.store.get_resource(b.resource_id) if b.resource_id else None
        if not res or not res.primary_uri:
            self.announcer.say("No openable address for this bookmark")
            return
        uri = res.primary_uri
        if res.type in ("file", "folder"):
            if not Path(uri).exists():
                self.announcer.say("File or folder not found. Marked as broken.")
                self.store.conn.execute(
                    "UPDATE beacons SET health=? WHERE beacon_id=?", (HEALTH_BROKEN, b.beacon_id)
                )
                self.store.conn.commit()
                self._refresh_results()
                return
            if sys.platform.startswith("win"):
                os.startfile(uri)  # noqa: S606 (local user file)
            else:
                import subprocess

                subprocess.Popen(["open", uri] if sys.platform == "darwin" else ["xdg-open", uri])
        else:
            webbrowser.open(uri)
        self.store.record_open(b.beacon_id)
        self.announcer.say(f"Opened {b.title}")

    def _on_open(self, _e) -> None:
        sel = self.results.GetFirstSelected()
        if 0 <= sel < len(self._results_cache):
            self._open_beacon(self._results_cache[sel])

    def _selected_beacon(self):
        sel = self.results.GetFirstSelected()
        if 0 <= sel < len(self._results_cache):
            return self._results_cache[sel]
        return None

    def _selected_beacons(self) -> list:
        """Return all selected beacons (multi-select). Falls back to the
        single focused item when nothing is multi-selected."""
        sel = self.results.GetFirstSelected()
        if sel < 0:
            return []
        idxs = [sel]
        nxt = self.results.GetNextSelected(sel)
        while nxt != -1:
            idxs.append(nxt)
            nxt = self.results.GetNextSelected(nxt)
        return [self._results_cache[i] for i in idxs if 0 <= i < len(self._results_cache)]

    # -- bulk operations + undo (PRD 18.5, 44.3) ----------------------------

    def _bulk(self, label: str, beacon_ids: list[str], apply_fn) -> None:
        """Snapshot, apply a bulk mutation, push a single composite undo."""
        if not beacon_ids:
            self.announcer.say("Nothing selected")
            return
        snaps = snapshot_beacons(self.store, beacon_ids)
        apply_fn()
        self.undo.push(
            label,
            lambda: restore_beacons(self.store, snaps),
        )
        self._refresh_results()
        self.announcer.say(f"{label}: {len(beacon_ids)} item(s)")

    def _on_bulk_trash(self, _e) -> None:
        bs = self._selected_beacons()
        ids = [b.beacon_id for b in bs]
        self._bulk("Trash", ids, lambda: [self.store.trash(i) for i in ids])

    def _on_bulk_archive(self, _e) -> None:
        bs = self._selected_beacons()
        ids = [b.beacon_id for b in bs]
        self._bulk("Archive", ids, lambda: [self.store.archive(i) for i in ids])

    def _on_bulk_restore(self, _e) -> None:
        bs = self._selected_beacons()
        ids = [b.beacon_id for b in bs]
        self._bulk("Restore", ids, lambda: [self.store.restore(i) for i in ids])

    def _on_bulk_favorite(self, _e) -> None:
        bs = self._selected_beacons()
        ids = [b.beacon_id for b in bs]
        # Toggle toward favorite-on if any is off, else off.
        target = not all(b.favorite for b in bs)

        def apply():
            for b in bs:
                b.favorite = target
                self.store.put_beacon(b)

        self._bulk(f"Favorite {'on' if target else 'off'}", ids, apply)

    def _on_bulk_tag(self, _e) -> None:
        bs = self._selected_beacons()
        if not bs:
            self.announcer.say("Select items first")
            return
        tag = wx.GetTextFromUser("Tag to add to all selected:", "Bulk Tag", "")
        if not tag:
            return
        ids = [b.beacon_id for b in bs]

        def apply():
            for b in bs:
                b.tags = list(dict.fromkeys(b.tags + [tag]))
                self.store.put_beacon(b)

        self._bulk(f"Tag {tag}", ids, apply)

    def _on_bulk_remove_tag(self, _e) -> None:
        bs = self._selected_beacons()
        if not bs:
            self.announcer.say("Select items first")
            return
        # Gather the tags present across the selection so the user picks one.
        present = sorted({t for b in bs for t in b.tags})
        if not present:
            self.announcer.say("None of the selected items have tags")
            return
        msg = "Tag to remove from all selected:\n" + ", ".join(present)
        tag = wx.GetTextFromUser(msg, "Bulk Remove Tag", "")
        if not tag:
            return
        ids = [b.beacon_id for b in bs]

        def apply():
            for b in bs:
                if tag in b.tags:
                    b.tags = [t for t in b.tags if t != tag]
                    self.store.put_beacon(b)

        self._bulk(f"Remove tag {tag}", ids, apply)

    def _on_bulk_add_collection(self, _e) -> None:
        bs = self._selected_beacons()
        if not bs:
            self.announcer.say("Select items first")
            return
        existing = [c.name for c in self.store.list_collections()]
        prompt = "Add all selected to collection:\n" + (
            "existing: " + ", ".join(existing) if existing else "(type a new name)"
        )
        name = wx.GetTextFromUser(prompt, "Bulk Add to Collection", "")
        if not name:
            return
        self.store._ensure_collection(name)
        self.store.conn.commit()
        ids = [b.beacon_id for b in bs]

        def apply():
            for b in bs:
                b.collections = list(dict.fromkeys(b.collections + [name]))
                self.store.put_beacon(b)

        self._bulk(f"Add to {name}", ids, apply)
        self._refresh_sidebar()

    def _on_bulk_delete(self, _e) -> None:
        """Permanent delete. Confirm, then purge. Undo restores from snapshot."""
        bs = self._selected_beacons()
        if not bs:
            self.announcer.say("Select items first")
            return
        if (
            show_message_box(
                f"Permanently delete {len(bs)} item(s)? This can be undone with Ctrl+Z.",
                "Delete",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
                self,
            )
            != wx.YES
        ):
            return
        ids = [b.beacon_id for b in bs]
        snaps = snapshot_beacons(self.store, ids)
        # Permanent delete removes the row and its join/FTS rows.
        for b in bs:
            self.store.delete_permanent(b.beacon_id)
        self.undo.push(
            "Delete",
            lambda: restore_beacons(self.store, snaps),
        )
        self._refresh_results()
        self.announcer.say(f"Deleted {len(bs)} item(s). Ctrl+Z to undo.")

    def _on_undo(self, _e) -> None:
        self.undo.undo()
        self._refresh_results()

    def _on_trash(self, _e) -> None:
        b = self._selected_beacon()
        if b:
            self.store.trash(b.beacon_id)
            self._refresh_results()
            self.announcer.say(f"Moved to trash: {b.title}")

    def _on_restore(self, _e) -> None:
        b = self._selected_beacon()
        if b:
            self.store.restore(b.beacon_id)
            self._refresh_results()
            self.announcer.say(f"Restored: {b.title}")

    def _on_archive(self, _e) -> None:
        b = self._selected_beacon()
        if b:
            self.store.archive(b.beacon_id)
            self._refresh_results()
            self.announcer.say(f"Archived: {b.title}")

    def _on_favorite(self, _e) -> None:
        b = self._selected_beacon()
        if b:
            b.favorite = not b.favorite
            self.store.put_beacon(b)
            self._refresh_results()
            self.announcer.say(f"Favorite {'on' if b.favorite else 'off'}: {b.title}")

    def _on_rename(self, _e) -> None:
        b = self._selected_beacon()
        if not b:
            return
        new = wx.GetTextFromUser("New title:", "Rename Bookmark", b.title)
        if new:
            b.title = new
            self.store.put_beacon(b)
            self._refresh_results()

    def _on_add_collection(self, _e) -> None:
        b = self._selected_beacon()
        if not b:
            return
        name = wx.GetTextFromUser("Add to collection:", "Add to Collection", "")
        if name:
            b.collections = list(dict.fromkeys(b.collections + [name]))
            self.store.put_beacon(b)
            self._refresh_sidebar()
            self._refresh_results()
            self.announcer.say(f"Added to {name}")

    def _on_attachments(self, _e) -> None:
        b = self._selected_beacon()
        if not b:
            self.announcer.say("Select a bookmark first")
            return
        dlg = AttachmentsDialog(self, self.store, b.beacon_id, b.title)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_duplicates(self, _e) -> None:
        groups = search.find_duplicates(self.store)
        if not groups:
            self.announcer.say("No duplicates found")
            return
        names = "; ".join(", ".join(b.title for b in g) for g in groups)
        self.announcer.say(f"{len(groups)} duplicate group(s)")
        show_message_box(f"{len(groups)} duplicate group(s):\n\n{names}", "Duplicates", wx.OK)

    def _on_build_search(self, _e) -> None:
        dlg = BuildSearchDialog(self)
        if dlg.ShowModal() in (wx.ID_OK, wx.ID_YES):
            q = dlg.result()
            if q is not None:
                self.search_box.SetValue(q)
                self.last_query = q
                self._refresh_results()
        dlg.Destroy()

    def _on_save_search(self, _e) -> None:
        """Save the current query/sort/scope as a live Smart Collection (PRD 15.6)."""
        from quill.apps.beacon.model import SavedSearch

        query = self.last_query or self.search_box.GetValue()
        if not query.strip():
            self.announcer.say("Enter a search first, then save it")
            return
        name = wx.GetTextFromUser("Smart Collection name:", "Save Search", query[:40])
        if not name:
            return
        scope = ""
        if self.current_scope.startswith("collection:"):
            scope = self.current_scope.split(":", 1)[1]
        ss = SavedSearch(
            name=name,
            query=query,
            sort=self.current_sort,
            scope_collection=scope,
        )
        self.store.put_saved_search(ss)
        self._refresh_sidebar()
        self.announcer.say(f"Smart collection {name} saved")

    def _on_import(self, _e) -> None:
        with wx.FileDialog(
            self,
            "Import",
            wildcard=(
                "Bookmark files (*.html;*.htm;*.opml;*.m3u;*.pls;*.csv;*.json;*.txt)|"
                "*.html;*.htm;*.opml;*.m3u;*.pls;*.csv;*.json;*.txt|All files|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()
        try:
            items = importers.import_file(path)
        except Exception as ex:
            show_message_box(f"Import failed: {ex}", "QuillBeacon", style=wx.ICON_ERROR)
            return
        added = 0
        rules = routing.load_rules(self.data_dir)
        for beacon, res in items:
            existing = (
                self.store.find_resource_by_canonical(res.canonical_id)
                if res.canonical_id
                else None
            )
            if existing:
                continue  # skip duplicates silently with a count
            routing.route(beacon, res, rules)
            self.store.put_beacon(beacon, resource=res)
            added += 1
        self._refresh_sidebar()
        self._refresh_results()
        self.announcer.say(
            f"Imported {added} of {len(items)}; {len(items) - added} duplicates skipped"
        )

    def _on_export(self, _e) -> None:
        formats = [
            ("JSON archive", "json"),
            ("HTML bookmarks", "html"),
            ("Markdown", "md"),
            ("CSV", "csv"),
            ("OPML", "opml"),
            ("M3U", "m3u"),
            ("Plain text", "txt"),
        ]
        dlg = wx.SingleChoiceDialog(self, "Export format:", "Export", [f for f, _ in formats])
        if dlg.ShowModal() == wx.ID_CANCEL:
            dlg.Destroy()
            return
        fmt = formats[dlg.GetSelection()][1]
        dlg.Destroy()
        with wx.FileDialog(
            self,
            "Export",
            defaultFile=f"quillbeacon-export.{fmt}",
            wildcard=f"*.{fmt}",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
            path = fd.GetPath()
        text = {
            "json": exporters.export_json,
            "html": exporters.export_html,
            "md": exporters.export_markdown,
            "csv": exporters.export_csv,
            "opml": exporters.export_opml,
            "m3u": exporters.export_m3u,
            "txt": exporters.export_text,
        }[fmt](self.store)
        Path(path).write_text(text, encoding="utf-8")
        self.announcer.say(f"Exported to {path}")

    def _on_a11y_settings(self, _e) -> None:
        dlg = A11ySettingsDialog(self, self.a11y)
        if dlg.ShowModal() == wx.ID_OK and dlg.result():
            r = dlg.result()
            self.a11y = a11y_mod.A11ySettings(
                verbosity=r["verbosity"],
                high_contrast=r["high_contrast"],
                scale_index=r["scale_index"],
                reduced_motion=r["reduced_motion"],
            )
            a11y_mod.save(self.data_dir, self.a11y)
            self.announcer.set_verbosity(self.a11y.verbosity)
            a11y_mod.apply_to_frame(self, self.a11y)
            self.announcer.say(
                f"Accessibility: verbosity {self.a11y.verbosity}, "
                f"contrast {'on' if self.a11y.high_contrast else 'off'}, "
                f"scale {int(self.a11y.text_scale * 100)} percent"
            )
        dlg.Destroy()

    def _on_preferences(self, _e) -> None:
        """Unified Preferences hub (Ctrl+Comma).

        Applies the inline-editable settings (accessibility fields and the
        auto-sync interval); heavier actions are handled inside the dialog.
        """
        dlg = PreferencesDialog(self, self)
        if dlg.ShowModal() == wx.ID_OK and dlg.result():
            self._apply_preferences(dlg.result())
        dlg.Destroy()

    def _apply_preferences(self, r: dict) -> None:
        """Apply a Preferences result dict (a11y fields + auto-sync interval)."""
        self.a11y = a11y_mod.A11ySettings(
            verbosity=r["verbosity"],
            high_contrast=r["high_contrast"],
            scale_index=r["scale_index"],
            reduced_motion=r["reduced_motion"],
        )
        a11y_mod.save(self.data_dir, self.a11y)
        self.announcer.set_verbosity(self.a11y.verbosity)
        a11y_mod.apply_to_frame(self, self.a11y)
        secs = r["auto_sync_seconds"]
        self.sync.config.auto_sync_seconds = secs
        self.sync.save_config(self.sync.config)
        self._apply_auto_sync_interval()
        self.announcer.say(
            f"Preferences applied. Auto-sync "
            f"{'off' if not secs else f'every {secs // 60} minute(s)'}"
        )

    def _on_palette(self, _e) -> None:
        cmds = [
            Command("New Bookmark", "Ctrl+N", self._on_capture),
            Command("Import", "Ctrl+I", self._on_import),
            Command("Export", "Ctrl+E", self._on_export),
            Command("Build Search", "Ctrl+Shift+F", self._on_build_search),
            Command("Save Search as Smart Collection", "Ctrl+Shift+G", self._on_save_search),
            Command("Find Duplicates", "", self._on_duplicates),
            Command("Open Selected", "Enter", self._on_open),
            Command("Trash Selected", "Delete", self._on_trash),
            Command("Restore Selected", "Shift+Delete", self._on_restore),
            Command("Archive Selected", "Ctrl+Shift+A", self._on_archive),
            Command("Toggle Favorite", "Ctrl+D", self._on_favorite),
            Command("Rename Selected", "F2", self._on_rename),
            Command("Add to Collection", "Ctrl+L", self._on_add_collection),
            Command("Undo", "Ctrl+Z", self._on_undo),
            Command("Bulk Trash Selected", "Ctrl+Shift+Y", self._on_bulk_trash),
            Command("Bulk Archive Selected", "Ctrl+Shift+H", self._on_bulk_archive),
            Command("Bulk Restore Selected", "Ctrl+Shift+U", self._on_bulk_restore),
            Command("Bulk Toggle Favorite", "Ctrl+Shift+D", self._on_bulk_favorite),
            Command("Bulk Add Tag", "Ctrl+Shift+J", self._on_bulk_tag),
            Command("Bulk Delete Selected", "Ctrl+Shift+Delete", self._on_bulk_delete),
            Command("Subscribe to Podcast", "Ctrl+Shift+S", self._on_subscribe),
            Command("Refresh Feeds", "Ctrl+Shift+R", self._on_refresh_feeds),
            Command("Play in Player", "Ctrl+Shift+L", self._on_play_in_player),
            Command("Add Radio Station", "", self._on_add_station),
            Command("Add Radio Program", "", self._on_add_program),
            Command("Capture Bridge", "Ctrl+Shift+B", self._on_capture_bridge_info),
            Command("Collection Editor", "", self._on_collection_editor),
            Command("Trail Editor", "", self._on_trail_editor),
            Command("Review Location Repair", "", self._on_repair_review),
            Command("Sync Settings", "", self._on_sync_settings),
            Command("Sync Now", "", self._on_sync_now),
            Command("Sync History", "", self._on_sync_history),
            Command("Status Center", "", self._on_status_center),
            Command("Play in External Player", "", self._on_play_external),
            Command("Suggest Tags", "Ctrl+Shift+T", self._on_suggest_tags),
            Command("Suggest Relationships", "Ctrl+Shift+K", self._on_suggest_relationships),
            Command("Summarize Note", "Ctrl+Shift+M", self._on_summarize),
            Command("Where Am I?", "F1", self._on_where_am_i),
            Command("Accessibility Settings", "", self._on_a11y_settings),
            Command("Preferences", "Ctrl+,", self._on_preferences),
        ]
        dlg = CommandPalette(self, cmds)
        if dlg.ShowModal() == wx.ID_OK and dlg.chosen():
            dlg.chosen().handler(None)
        dlg.Destroy()

    def _on_where_am_i(self, _e) -> None:
        sel = self.results.GetFirstSelected()
        ctx = {
            "area": "Bookmarks list",
            "collection": self.current_scope,
            "search": self.last_query,
            "sort": self.current_sort,
            "selected": self._results_cache[sel].title
            if 0 <= sel < len(self._results_cache)
            else None,
            "position": sel + 1 if sel >= 0 else None,
            "count": len(self._results_cache),
        }
        self.announcer.say(self.announcer.where_am_i(ctx), "verbose")

    def _on_next_pane(self, _e) -> None:
        # Cycle sidebar -> search -> results -> details.
        if self.dest_list.HasFocus():
            self.search_box.SetFocus()
        elif self.search_box.HasFocus():
            self.results.SetFocus()
        elif self.results.HasFocus():
            self.details.SetFocus()
        else:
            self.dest_list.SetFocus()

    def _on_about(self, _e) -> None:
        show_message_box(
            f"{_TITLE} {_VERSION}\nSchema v{SCHEMA_VERSION}\n"
            "Find your way back to anything.\n\n"
            "Local-first. No account required. Library: "
            f"{self.data_dir / 'beacons.db'}",
            "About QuillBeacon",
            wx.OK,
        )

    # -- media (Phase 3) ------------------------------------------------------

    def _on_subscribe(self, _e) -> None:
        url = wx.GetTextFromUser("Podcast feed URL:", "Subscribe to Podcast", "https://")
        if not url or url == "https://":
            return
        try:
            feeds_mod.subscribe(self.store, url)
        except Exception as ex:
            show_message_box(f"Could not fetch feed: {ex}", "QuillBeacon", style=wx.ICON_ERROR)
            return
        self._refresh_sidebar()
        self._refresh_results()
        self.announcer.say("Subscribed. New episodes added to Inbox.")

    def _on_refresh_feeds(self, _e) -> None:
        shows = [
            b
            for b in self.store.list_beacons(limit=10000)
            if (self.store.get_resource(b.resource_id) or None)
            and self.store.get_resource(b.resource_id).type == "podcastShow"
        ]
        if not shows:
            self.announcer.say("No podcast subscriptions to refresh")
            return
        total_new = 0
        for b in shows:
            res = self.store.get_resource(b.resource_id)
            try:
                _show, new = feeds_mod.refresh(self.store, res.primary_uri)
                total_new += new
            except Exception as ex:
                self.announcer.say(f"Refresh failed for {b.title}: {ex}")
        self._refresh_results()
        self.announcer.say(f"Refreshed. {total_new} new episode(s).")

    def _on_play_in_player(self, _e) -> None:
        b = self._selected_beacon()
        if not b:
            self.announcer.say("Select an episode first")
            return
        res = self.store.get_resource(b.resource_id) if b.resource_id else None
        if not res or res.type not in (
            "podcastEpisode",
            "podcastChapter",
            "timePoint",
            "timeRange",
            "radioStream",
            "radioStation",
            "video",
        ):
            self.announcer.say("Selected item is not playable media")
            return
        from quill.apps.beacon import player

        self._player = player.PlayerFrame(self, self.store, b.beacon_id)
        self._player.Show()
        self.announcer.say(f"Player opened: {b.title}")

    def _on_play_external(self, _e) -> None:
        b = self._selected_beacon()
        if not b:
            self.announcer.say("Select an item first")
            return
        res = self.store.get_resource(b.resource_id) if b.resource_id else None
        if not res or not res.primary_uri:
            self.announcer.say("No media URL for this item")
            return
        start_ms = b.locations[0].media_start_ms if b.locations else None
        # Honor the user's external-player settings: per-type player + custom
        # path, falling back to whichever of VLC/mpv is installed.
        settings = external_player.load_settings(self.data_dir)
        if settings.default_player == external_player.PLAYER_DEFAULT and not settings.per_type:
            import shutil as _sh

            settings.default_player = (
                external_player.PLAYER_VLC
                if _sh.which("vlc")
                else external_player.PLAYER_MPV
                if _sh.which("mpv")
                else external_player.PLAYER_DEFAULT
            )
        res2 = external_player.launch(
            res.primary_uri, start_ms, settings=settings, resource_type=res.type
        )
        if res2.get("ok"):
            self.store.record_open(b.beacon_id)
            self.announcer.say(res2.get("message", "Opened in external player"))
        else:
            self.announcer.say(res2.get("message", "Could not open external player"))

    def _on_external_player(self, _e) -> None:
        """Configure the external media player (path + per-type defaults)."""
        from quill.apps.beacon.dialogs import PlayerSettingsDialog

        settings = external_player.load_settings(self.data_dir)
        dlg = PlayerSettingsDialog(self, settings=settings)
        if dlg.ShowModal() == wx.ID_OK and dlg.result():
            new = dlg.result()
            external_player.save_settings(self.data_dir, new)
            self.announcer.say("External player settings saved")
        dlg.Destroy()

    # -- radio depth (PRD 9.1, 44.3) ----------------------------------------

    def _on_add_station(self, _e) -> None:
        from quill.apps.beacon import radio

        url = wx.GetTextFromUser("Radio stream URL:", "Add Radio Station", "https://")
        if not url or url == "https://":
            return
        title = wx.GetTextFromUser("Station name:", "Add Radio Station", "")
        beacon, res = radio.station_from_stream(url, title=title)
        self.store.put_beacon(beacon, resource=res)
        self._refresh_sidebar()
        self._refresh_results()
        n_alt = len(res.metadata.get("alternates", []))
        self.announcer.say(
            f"Station saved. {n_alt} fallback URL(s) stored. "
            "Use Review Location Repair if the stream goes dark."
        )

    def _on_add_program(self, _e) -> None:
        from quill.apps.beacon import radio

        dlg = RadioProgramDialog(self)
        if dlg.ShowModal() != wx.ID_OK or not dlg.result():
            dlg.Destroy()
            return
        r = dlg.result()
        dlg.Destroy()
        beacon, res = radio.capture_program(
            station=r["station"],
            program=r["program"],
            host=r["host"],
            start_ms=parse_hhmm(r["start"]),
            end_ms=parse_hhmm(r["end"]),
            url=r["url"],
        )
        self.store.put_beacon(beacon, resource=res)
        self._refresh_sidebar()
        self._refresh_results()
        self.announcer.say(f"Program saved: {beacon.title}")

    # -- sync (PRD 45, 45.9, 46.2) -------------------------------------------

    def _on_sync_settings(self, _e) -> None:
        dlg = SyncSettingsDialog(self, self.sync)
        dlg.ShowModal()
        dlg.Destroy()
        self._refresh_results()
        # Transport may have just been configured: (re)apply the auto-sync timer.
        self._apply_auto_sync_interval()

    def _on_sync_now(self, _e) -> None:
        res = self.sync.sync_now()
        if "error" in res:
            show_message_box(res["error"], "Sync", wx.ICON_ERROR, self)
            return
        conflicts = res.get("conflicts") or []
        msg = f"Synced. Pushed {res.get('pushed', 0)}, pulled {res.get('pulled', 0)}."
        if conflicts:
            msg += f" {len(conflicts)} conflict(s) need review in Sync History."
        self._refresh_results()
        self.announcer.say(msg)

    # -- auto-sync timer (PRD 45.10; off by default) -------------------------

    AUTO_SYNC_CHOICES = [
        ("Off", 0),
        ("5 minutes", 300),
        ("15 minutes", 900),
        ("30 minutes", 1800),
        ("1 hour", 3600),
    ]

    def _setup_auto_sync(self) -> None:
        """Start the background sync timer if the user has enabled it.

        Off by default (``auto_sync_seconds == 0``). The timer only fires when
        sync is configured and the vault is unlocked; otherwise it quietly
        waits, so an unconfigured install never touches the network.
        """
        self._sync_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_auto_sync_tick, self._sync_timer)
        self._apply_auto_sync_interval()

    def _apply_auto_sync_interval(self) -> None:
        secs = self.sync.config.auto_sync_seconds
        if secs and secs > 0 and self.sync.config.is_configured():
            # wx.Timer uses milliseconds.
            self._sync_timer.Start(secs * 1000)
        else:
            self._sync_timer.Stop()

    def _on_auto_sync_tick(self, _e) -> None:
        if not self.sync.config.is_configured() or not self.sync.is_unlocked():
            return  # not ready; leave the timer running for when it is
        res = self.sync.sync_now()
        if "error" in res:
            self.announcer.say(f"Auto-sync failed: {res['error']}", "minimal")
            return
        self._refresh_results()
        conflicts = res.get("conflicts") or []
        msg = f"Auto-synced. Pushed {res.get('pushed', 0)}, pulled {res.get('pulled', 0)}."
        if conflicts:
            msg += f" {len(conflicts)} conflict(s) need review."
        self.announcer.say(msg, "minimal")

    def _on_auto_sync(self, _e) -> None:
        """Choose an automatic sync interval (off by default)."""
        current = self.sync.config.auto_sync_seconds
        labels = [label for label, _ in self.AUTO_SYNC_CHOICES]
        dlg = wx.SingleChoiceDialog(self, "Automatic sync interval:", "Auto Sync", labels)
        _name(dlg, "Auto sync interval chooser")
        # preselect
        for i, (_label, secs) in enumerate(self.AUTO_SYNC_CHOICES):
            if secs == current:
                dlg.SetSelection(i)
                break
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        secs = self.AUTO_SYNC_CHOICES[dlg.GetSelection()][1]
        dlg.Destroy()
        self.sync.config.auto_sync_seconds = secs
        self.sync.save_config(self.sync.config)
        self._apply_auto_sync_interval()
        if secs:
            self.announcer.say(f"Auto-sync every {secs // 60} minute(s)")
        else:
            self.announcer.say("Auto-sync off")

    def _on_sync_history(self, _e) -> None:
        dlg = SyncHistoryDialog(self, self.sync, on_rollback=self._do_rollback)
        dlg.ShowModal()
        dlg.Destroy()
        self._refresh_results()

    def _do_rollback(self, backup_name: str) -> None:
        """Restore a pre-sync snapshot: close, overwrite, reopen, refresh."""
        self.store.close()
        ok = self.sync.restore_backup(backup_name)
        self.store = db.BeaconStore(self.data_dir / "beacons.db")
        self.sync.store = self.store
        if ok:
            self._refresh_sidebar()
            self._refresh_results()
            self.announcer.say(f"Rolled back to {backup_name}")
        else:
            self.announcer.say("Rollback failed; library reopened from current DB")

    def handle_verify_url(self, url: str) -> bool:
        """Handle a quillsync://verify?... link (custom-scheme handoff).

        Returns True if the link was a verify link and was processed. Fail-safe:
        any error is announced, never raised.
        """
        if not url or not url.startswith("quillsync://verify"):
            return False
        from urllib.parse import parse_qs, urlparse

        q = parse_qs(urlparse(url).query)
        token = (q.get("token") or [""])[0]
        device = (q.get("device") or ["beacon"])[0]
        if not token:
            self.announcer.say("Sign-in link missing a token")
            return True
        res = self.sync.verify_magic_link(token, device)
        if "error" in res:
            show_message_box(res["error"], "Sign-in", wx.ICON_ERROR, self)
        else:
            show_message_box(
                "Signed in. This device is registered.", "Sign-in", wx.ICON_INFORMATION, self
            )
        return True

    # -- intelligent assistance (Phase 5, PRD 47) -----------------------------

    def _on_suggest_tags(self, _e) -> None:
        b = self._selected_beacon()
        if not b:
            self.announcer.say("Select a beacon first")
            return
        text = " ".join([b.title or "", b.note or ""])
        suggested = assist.suggest_tags(text, existing=b.tags, limit=5)
        if not suggested:
            self.announcer.say("No new tag suggestions")
            return
        b.tags = list(dict.fromkeys(b.tags + suggested))
        self.store.put_beacon(b)
        self._refresh_results()
        self.announcer.say("Added tags: " + ", ".join(suggested))

    def _on_suggest_relationships(self, _e) -> None:
        b = self._selected_beacon()
        if not b:
            self.announcer.say("Select a beacon first")
            return
        rels = assist.suggest_relationships(self.store, b.beacon_id, limit=5)
        if not rels:
            self.announcer.say("No relationship suggestions")
            return
        from quill.apps.beacon.model import Relationship

        added = 0
        for r in rels:
            self.store.add_relationship(
                Relationship(
                    src_beacon=b.beacon_id, tgt_beacon=r["beacon_id"], note="; ".join(r["reasons"])
                )
            )
            added += 1
        self.announcer.say(f"Added {added} relationship(s). {rels[0]['title']} top match.")

    def _on_summarize(self, _e) -> None:
        b = self._selected_beacon()
        if not b:
            self.announcer.say("Select a beacon first")
            return
        summary = assist.extractive_summary(b.note or b.title or "")
        if not summary:
            self.announcer.say("Nothing to summarize")
            return
        show_message_box(summary, "Summary", wx.OK | wx.ICON_INFORMATION, self)
        self.announcer.say("Summary shown")

    def _on_close(self, _e) -> None:
        if getattr(self, "_sync_timer", None):
            try:
                self._sync_timer.Stop()
            except Exception:
                pass
        if getattr(self, "tray", None):
            try:
                self.tray.RemoveIcon()
                self.tray.Destroy()
            except Exception:
                pass
        if getattr(self, "bridge", None):
            self.bridge.stop()
        self.store.close()
        self.Destroy()


def run() -> int:
    """Entry point: create the wx app and show the frame."""
    app = wx.App()
    frame = BeaconFrame()
    frame.Show()
    # OS custom-scheme handoff: a quillsync://verify link may be passed as the
    # first argv when the OS launches us to handle the scheme.
    for arg in sys.argv[1:]:
        if arg.startswith("quillsync://"):
            frame.handle_verify_url(arg)
            break
    app.MainLoop()
    return 0
