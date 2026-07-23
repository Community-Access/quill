"""QUILL Social desktop shell -- accessible three-pane UI (PRD 9, 10, 29).

Navigation tree | item list | details. Every pane is a named region, focus
moves predictably and is never stolen by a background refresh (PRD 28.3), and
every action is reachable by keyboard, menu, and the command center (PRD 3.2).
Up/Down move between items; Left/Right read the configured fields of the
focused item (PRD 10.1); Enter opens details. State is spoken through the
announcer and mirrored in the status bar so nothing important is hidden.

This is a self-contained shell for the first slice; the production target moves
the engine onto ``quill.ui.app_shell.AppShellFrame`` (PRD 44).
"""

from __future__ import annotations

import webbrowser
from datetime import UTC

import wx

from quill_social import __title__, __version__, paths
from quill_social import a11y as a11y_mod
from quill_social import keymap as keymap_mod
from quill_social.adapters import oauth
from quill_social.adapters.base import AdapterError
from quill_social.adapters.github import MockGitHub
from quill_social.adapters.registry import adapter_for
from quill_social.capabilities import CapabilityRegistry
from quill_social.db import SocialStore
from quill_social.fields import FieldProfile, read_fields, render_row
from quill_social.model import Account, PublicationPlan, Workspace, now_ms
from quill_social.security.credentials import (
    InMemoryCredentialStore,
    WindowsCredentialManagerStore,
)
from quill_social.services import analytics as analytics_svc
from quill_social.services import catchup as catchup_svc
from quill_social.services import ecosystem as ecosystem_svc
from quill_social.services import smartfolder as smartfolder_svc
from quill_social.services.ai import accessibility as ai_a11y
from quill_social.services.ai import understand as ai_understand
from quill_social.services.scheduler import Scheduler
from quill_social.services.thread_publisher import publish_thread
from quill_social.services.thread_splitter import mastodon_counter, split_thread
from quill_social.ui.announce import Announcer
from quill_social.ui.commands import Command, CommandPalette
from quill_social.ui.composer import ComposerDialog
from quill_social.ui.manage import (
    NotificationPoliciesDialog,
    OutboxDialog,
    PluginManagerDialog,
    SafetyCenterDialog,
)
from quill_social.ui.media_player import MediaPlayerDialog
from quill_social.ui.studio import (
    AgendaDialog,
    ApprovalsDialog,
    DraftsDialog,
    QueueScheduleDialog,
)
from quill_social.whereami import WhereAmI

# Navigation destinations (PRD 9.2). Each is (label, scope_id).
NAV_TREE = [
    (
        "Home",
        "home",
        [
            ("Unified Home", "home:all"),
            ("Unread", "home:unread"),
        ],
    ),
    (
        "Attention",
        "attention",
        [
            ("Mentions", "attention:mentions"),
            ("Notifications", "attention:notifications"),
            ("Flagged", "attention:flagged"),
        ],
    ),
    (
        "Library",
        "library",
        [
            ("Bookmarks", "library:bookmarks"),
            ("Favourites", "library:favourites"),
            ("Saved Searches", "library:searches"),
        ],
    ),
    (
        "Publishing",
        "publishing",
        [
            ("Drafts", "pub:drafts"),
            ("Queue", "pub:queued"),
            ("Scheduled", "pub:scheduled"),
            ("Failed", "pub:failed"),
            ("Sent", "pub:published"),
        ],
    ),
    (
        "Discover",
        "discover",
        [
            ("Search Results", "discover:search"),
            ("Catch Up", "discover:catchup"),
        ],
    ),
    (
        "GitHub",
        "github",
        [
            ("Notifications", "gh:notifications"),
            ("Issues", "gh:issues"),
            ("Pull Requests", "gh:prs"),
            ("Discussions", "gh:discussions"),
            ("Releases", "gh:releases"),
        ],
    ),
]


class SocialFrame(wx.Frame):
    def __init__(self) -> None:
        super().__init__(None, title=__title__, size=(1180, 760))
        self.data_dir = paths.data_dir()
        self.store = SocialStore(paths.db_path())
        self.a11y = a11y_mod.load(self.data_dir)
        self.keymap = keymap_mod.load(self.data_dir)
        self.caps = CapabilityRegistry()
        self.profile = FieldProfile()
        self.credentials = _make_credential_store()
        self.announcer = Announcer(self, verbosity=self.a11y.verbosity)

        self.current_scope = "home:all"
        self.current_scope_label = "Unified Home"
        self.last_search = ""
        self._items: list = []
        self._field_index = 0
        self._closing = False

        self._first_run_seed()
        self._load_caps()
        self._build_menu()
        self._build_ui()
        a11y_mod.apply_to_frame(self, self.a11y)
        self._refresh_from_network(announce=False)
        self._populate_nav()
        self._load_scope(self.current_scope, self.current_scope_label)
        self.CreateStatusBar()
        self.SetStatusText("QUILL Social ready. Press F1 for help.")
        self.announcer.say("QUILL Social ready", "normal")

        # Local scheduler tier (PRD 18.3): while the app is open, publish plans
        # whose time has arrived. A wx.Timer keeps the UI thread free.
        self.scheduler = Scheduler(self.store, self._resolve_adapter)
        self._sched_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_sched_tick, self._sched_timer)
        self._sched_timer.Start(30_000)

        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Centre()

    def _resolve_adapter(self, account_id: str):
        """Resolve an account's adapter, passing credentials when supported."""
        acct = self.store.get_account(account_id)
        try:
            return adapter_for(acct, self.credentials)
        except TypeError:
            return adapter_for(acct)

    def _on_sched_tick(self, _e) -> None:
        """Publish any due local-tier plans (PRD 18.3, 18.12)."""
        if self._closing:
            return
        try:
            results = self.scheduler.run_due()
        except Exception:
            return
        published = [r for r in results if r.published]
        if published:
            self._refresh_from_network(announce=False)
            self._load_scope(self.current_scope, self.current_scope_label)
            self.announcer.say(f"Scheduler published {len(published)} post(s).", "normal")

    # -- first run ------------------------------------------------------------

    def _first_run_seed(self) -> None:
        """Give a brand-new install a workspace and a local demo account.

        The mock account makes the whole app usable immediately, before any real
        credential is entered (PRD 42), and is clearly labeled as a demo.
        """
        if self.store.list_accounts():
            return
        ws = self.store.put_workspace(Workspace(name="Personal", position=0))
        self.store.put_account(
            Account(
                account_id="acct_mock",
                network="mock",
                handle="@you@mock.social",
                display_name="You (demo)",
                local_alias="Demo timeline",
                workspace_id=ws.workspace_id,
                is_default=True,
            )
        )

    def _load_caps(self) -> None:
        for acct in self.store.list_accounts():
            self.caps.seed_from_network(acct.account_id, acct.network)

    # -- menu -----------------------------------------------------------------

    def _build_menu(self) -> None:
        bar = wx.MenuBar()

        m_file = wx.Menu()
        self._menu_item(m_file, "Add &Account...\tCtrl+Shift+A", self._on_add_account)
        self._menu_item(m_file, "&Preferences...", self._on_preferences)
        m_file.AppendSeparator()
        self._menu_item(m_file, "E&xit\tAlt+F4", lambda _e: self.Close())
        bar.Append(m_file, "&File")

        m_compose = wx.Menu()
        self._menu_item(m_compose, "&New Post\tCtrl+N", lambda _e: self.cmd_compose())
        self._menu_item(m_compose, "&Reply\tCtrl+R", lambda _e: self.cmd_reply())
        self._menu_item(m_compose, "&Quote\tCtrl+Q", lambda _e: self.cmd_quote())
        bar.Append(m_compose, "&Compose")

        m_item = wx.Menu()
        self._menu_item(m_item, "&Boost / Repost\tCtrl+Shift+R", lambda _e: self.cmd_repost())
        self._menu_item(m_item, "&Favourite\tCtrl+F", lambda _e: self.cmd_favourite())
        self._menu_item(m_item, "&Bookmark\tAlt+B", lambda _e: self.cmd_bookmark())
        self._menu_item(m_item, "Flag for follow-&up", lambda _e: self.cmd_flag())
        self._menu_item(
            m_item, "Open co&nversation\tCtrl+G", lambda _e: self.cmd_open_conversation()
        )
        self._menu_item(m_item, "&Open links\tCtrl+O", lambda _e: self.cmd_open_links())
        self._menu_item(m_item, "Mark &read\tCtrl+K", lambda _e: self.cmd_mark_read())
        m_item.AppendSeparator()
        self._menu_item(m_item, "&Accessibility check", lambda _e: self.cmd_accessibility_check())
        self._menu_item(m_item, "Send to &QUILL", lambda _e: self.cmd_send_to_quill())
        self._menu_item(m_item, "&Play media\tCtrl+Enter", lambda _e: self.cmd_play_media())
        bar.Append(m_item, "&Item")

        m_studio = wx.Menu()
        self._menu_item(m_studio, "&Drafts...", lambda _e: self.cmd_drafts())
        self._menu_item(m_studio, "&Agenda / Calendar...", lambda _e: self.cmd_agenda())
        self._menu_item(m_studio, "&Queue schedule...", lambda _e: self.cmd_queue_schedule())
        self._menu_item(m_studio, "A&pprovals...", lambda _e: self.cmd_approvals())
        bar.Append(m_studio, "&Studio")

        m_tools = wx.Menu()
        self._menu_item(
            m_tools, "&Command Center\tCtrl+Shift+C", lambda _e: self.cmd_command_center()
        )
        self._menu_item(m_tools, "&Where Am I\tCtrl+Shift+I", lambda _e: self.cmd_where_am_i())
        self._menu_item(m_tools, "&Search\tCtrl+L", lambda _e: self.cmd_focus_search())
        self._menu_item(m_tools, "&Refresh\tF5", lambda _e: self.cmd_refresh())
        self._menu_item(m_tools, "Catch &Up", lambda _e: self.cmd_catchup())
        m_tools.AppendSeparator()
        self._menu_item(m_tools, "&Insights / Analytics", lambda _e: self.cmd_analytics())
        self._menu_item(m_tools, "Safety Cen&ter", lambda _e: self.cmd_safety_center())
        self._menu_item(
            m_tools, "&Notification policies", lambda _e: self.cmd_notification_policies()
        )
        self._menu_item(m_tools, "&Plugins", lambda _e: self.cmd_plugins())
        self._menu_item(m_tools, "&Outbox", lambda _e: self.cmd_outbox())
        self._menu_item(m_tools, "Summari&ze this feed (AI)", lambda _e: self.cmd_summarize_feed())
        bar.Append(m_tools, "&Tools")

        m_help = wx.Menu()
        self._menu_item(m_help, "&Help\tF1", lambda _e: self.cmd_help())
        self._menu_item(m_help, "&About", self._on_about)
        bar.Append(m_help, "&Help")

        self.SetMenuBar(bar)

    def _menu_item(self, menu, label, handler) -> None:
        item = menu.Append(wx.ID_ANY, label)
        self.Bind(wx.EVT_MENU, handler, item)

    # -- ui -------------------------------------------------------------------

    def _build_ui(self) -> None:
        splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE | wx.SP_3D)
        splitter.SetMinimumPaneSize(180)

        # Left: navigation tree.
        left = wx.Panel(splitter)
        lsz = wx.BoxSizer(wx.VERTICAL)
        lsz.Add(wx.StaticText(left, label="Navigation"), 0, wx.ALL, 4)
        self.nav = wx.TreeCtrl(
            left,
            style=wx.TR_HAS_BUTTONS
            | wx.TR_HIDE_ROOT
            | wx.TR_SINGLE
            | wx.TR_LINES_AT_ROOT
            | wx.TR_FULL_ROW_HIGHLIGHT,
        )
        self.nav.SetName("Navigation")
        lsz.Add(self.nav, 1, wx.EXPAND | wx.ALL, 4)
        left.SetSizer(lsz)

        # Right: search + list + details.
        right = wx.SplitterWindow(splitter, style=wx.SP_LIVE_UPDATE | wx.SP_3D)
        right.SetMinimumPaneSize(120)

        top = wx.Panel(right)
        tsz = wx.BoxSizer(wx.VERTICAL)
        srow = wx.BoxSizer(wx.HORIZONTAL)
        srow.Add(wx.StaticText(top, label="Search:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.search = wx.TextCtrl(top, style=wx.TE_PROCESS_ENTER)
        self.search.SetName("Search posts")
        srow.Add(self.search, 1)
        tsz.Add(srow, 0, wx.EXPAND | wx.ALL, 4)

        self.list = wx.ListCtrl(top, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER)
        self.list.SetName("Timeline")
        self.list.InsertColumn(0, "Post", width=760)
        tsz.Add(self.list, 1, wx.EXPAND | wx.ALL, 4)
        top.SetSizer(tsz)

        bottom = wx.Panel(right)
        bsz = wx.BoxSizer(wx.VERTICAL)
        bsz.Add(wx.StaticText(bottom, label="Details"), 0, wx.ALL, 4)
        self.details = wx.TextCtrl(bottom, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.details.SetName("Post details")
        bsz.Add(self.details, 1, wx.EXPAND | wx.ALL, 4)
        bottom.SetSizer(bsz)

        right.SplitHorizontally(top, bottom, -220)
        splitter.SplitVertically(left, right, 240)

        self.nav.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_nav_changed)
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_item_selected)
        self.list.Bind(wx.EVT_LIST_ITEM_FOCUSED, self._on_item_selected)
        self.search.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._run_search())

    def _populate_nav(self) -> None:
        self.nav.DeleteAllItems()
        root = self.nav.AddRoot("root")
        self._nav_nodes = {}
        first_child = None
        for label, scope, children in NAV_TREE:
            parent = self.nav.AppendItem(root, label)
            self.nav.SetItemData(parent, (scope, label))
            for clabel, cscope in children:
                node = self.nav.AppendItem(parent, clabel)
                self.nav.SetItemData(node, (cscope, clabel))
                self._nav_nodes[cscope] = node
                if first_child is None:
                    first_child = node
            self.nav.Expand(parent)
        if first_child:
            self.nav.SelectItem(first_child)

    # -- data loading ---------------------------------------------------------

    def _refresh_from_network(self, *, announce: bool = True) -> None:
        """Pull each active account's home timeline into the local store.

        Failures are per-account and never crash the app or block other
        accounts (PRD 32.3). Live adapters that are not wired report a clear
        state instead of an opaque error.
        """
        pulled = 0
        for acct in self.store.list_accounts(include_paused=False):
            adapter = self._resolve_adapter(acct.account_id)
            try:
                for it in adapter.home_timeline(limit=60):
                    it.account_id = acct.account_id
                    self.store.upsert_item(it)
                    pulled += 1
                for it in adapter.notifications(limit=20):
                    it.account_id = acct.account_id
                    self.store.upsert_item(it)
            except AdapterError as exc:
                if announce:
                    self.announcer.say(f"{acct.label}: {exc}", "normal")
            except Exception as exc:  # pragma: no cover - defensive
                if announce:
                    self.announcer.say(f"{acct.label}: refresh failed ({exc})", "normal")
        if announce:
            self.announcer.say(f"Refreshed. {pulled} posts.", "normal")

    def _scope_items(self, scope: str) -> list:
        if scope == "home:all":
            return self.store.list_items(limit=500)
        if scope == "home:unread":
            return self.store.list_items(unread_only=True, limit=500)
        if scope == "attention:mentions":
            return [it for it in self.store.list_items(limit=500) if "@you" in it.text]
        if scope == "attention:notifications":
            return [
                it for it in self.store.list_items(limit=500) if "@you" in it.text or it.is_reply
            ]
        if scope == "attention:flagged":
            return self.store.list_items(flagged=True, limit=500)
        if scope == "library:bookmarks":
            return self.store.list_items(bookmarked=True, limit=500)
        if scope == "library:favourites":
            return self.store.list_items(favourited=True, limit=500)
        if scope == "discover:search":
            return self.store.search_items(self.last_search) if self.last_search else []
        if scope == "discover:catchup":
            return self._catchup_items()
        if scope.startswith("smart:"):
            folder_id = scope.split(":", 1)[1]
            folders = {f.folder_id: f for f in self.store.list_folders(kind="smart")}
            folder = folders.get(folder_id)
            if folder:
                return smartfolder_svc.evaluate(self.store.list_items(limit=500), folder.rule)
        return []

    def _catchup_items(self) -> list:
        items = self.store.list_items(limit=500)
        items = catchup_svc.collapse_reposts(items)
        items = catchup_svc.collapse_cross_network(items)
        return items

    def _load_scope(self, scope: str, label: str) -> None:
        self.current_scope = scope
        self.current_scope_label = label
        if scope.startswith("pub:"):
            self._load_publishing(scope, label)
            return
        if scope.startswith("gh:"):
            self._load_github(scope, label)
            return
        self._items = self._scope_items(scope)
        self._render_list()
        unread = sum(1 for it in self._items if not it.read)
        self.announcer.say(f"{label}. {len(self._items)} items, {unread} unread.", "normal")

    def _load_publishing(self, scope: str, label: str) -> None:
        self.list.DeleteAllItems()
        self._items = []
        if scope == "pub:drafts":
            drafts = self.store.list_drafts()
            for i, d in enumerate(drafts):
                preview = (d.text[:80] or "(empty)").replace("\n", " ")
                self.list.InsertItem(i, f"Draft: {preview}")
            self.announcer.say(f"{label}. {len(drafts)} drafts.", "normal")
            self._draft_rows = drafts
            return
        state = scope.split(":", 1)[1]
        plans = self.store.list_plans(state=state)
        for i, p in enumerate(plans):
            when = _fmt_ms(p.scheduled_for) if p.scheduled_for else "now"
            self.list.InsertItem(i, f"{p.network} -> {p.state}, {when}, retries {p.retry_count}")
        self.announcer.say(f"{label}. {len(plans)} items.", "normal")

    def _load_github(self, scope: str, label: str) -> None:
        """Render GitHub items as text rows (PRD 24.1).

        Backed by the deterministic MockGitHub so the collaboration surface is
        navigable out of the box; the live adapter plugs in behind the same
        interface. GitHub rows are not SocialItems, so item commands stay inert.
        """
        self.list.DeleteAllItems()
        self._items = []
        gh = MockGitHub()
        try:
            if scope == "gh:notifications":
                objs = gh.notifications()
            elif scope == "gh:issues":
                objs = gh.issues("")
            elif scope == "gh:prs":
                objs = gh.pull_requests("")
            elif scope == "gh:discussions":
                objs = gh.discussions("")
            else:
                objs = gh.releases("")
        except AdapterError as exc:
            self.list.InsertItem(0, str(exc))
            self.announcer.say(str(exc), "normal")
            return
        for i, o in enumerate(objs):
            d = o.to_dict()
            num = d.get("number")
            title = d.get("title") or d.get("subject") or d.get("tag") or "(item)"
            state = d.get("state", "")
            labels = " ".join(d.get("labels", []) or [])
            head = f"#{num} " if num else ""
            tail = f" [{state}]" if state else ""
            row = f"{head}{title}{tail}{(' ' + labels) if labels else ''}".strip()
            self.list.InsertItem(i, row)
        self.announcer.say(f"{label}. {len(objs)} items.", "normal")

    def _render_list(self, *, keep_selection: bool = False) -> None:
        sel = self.list.GetFirstSelected() if keep_selection else -1
        self.list.DeleteAllItems()
        accounts = {a.account_id: a for a in self.store.list_accounts()}
        now = now_ms()
        for i, it in enumerate(self._items):
            row = render_row(
                it, self.profile, account=accounts.get(it.account_id), settings=self.a11y, now=now
            )
            idx = self.list.InsertItem(i, row or "(no text)")
            if not it.read:
                # Read state is spoken, never color-only (PRD 6.5); we still bold
                # unread rows for low-vision users as a secondary cue.
                font = self.list.GetFont()
                font.SetWeight(wx.FONTWEIGHT_BOLD)
                self.list.SetItemFont(idx, font)
        if self._items:
            target = sel if 0 <= sel < len(self._items) else 0
            self.list.Select(target)
            self.list.Focus(target)

    # -- selection + field navigation -----------------------------------------

    def _current_item(self):
        idx = self.list.GetFirstSelected()
        if 0 <= idx < len(self._items):
            return self._items[idx]
        return None

    def _on_item_selected(self, event) -> None:
        if self._closing:
            return
        self._field_index = 0
        item = self._current_item()
        if item is not None:
            self._show_details(item)
            if not item.read:
                self.store.set_read(item.item_id, True)
                item.read = True
        if event:
            event.Skip()

    def _show_details(self, item) -> None:
        accounts = {a.account_id: a for a in self.store.list_accounts()}
        acct = accounts.get(item.account_id)
        lines = [
            f"Author: {item.author_display} {item.author_handle}",
            f"Network: {item.network}" + (f" ({acct.label})" if acct else ""),
            f"When: {_fmt_ms(item.created_at)}",
            f"Visibility: {item.visibility}",
        ]
        if item.content_warning:
            lines.append(f"Content warning: {item.content_warning}")
        if item.is_repost:
            lines.append(f"Boosted by {item.reblog_by}")
        if item.is_reply:
            lines.append("This is a reply.")
        lines.append("")
        lines.append(item.text)
        if item.media:
            lines.append("")
            for m in item.media:
                alt = m.alt_text or "(no alt text -- undescribed)"
                lines.append(f"Media ({m.kind}): {alt}")
        if item.poll:
            lines.append("")
            lines.append(
                f"Poll, {item.poll.total_votes} votes" + (", you voted" if item.poll.voted else "")
            )
            for opt in item.poll.options:
                lines.append(f"  {opt.title}: {opt.votes}")
        lines.append("")
        lines.append(
            f"Replies {item.reply_count}, boosts {item.reblog_count}, "
            f"favourites {item.favourite_count}"
        )
        if item.missing_alt_count:
            lines.append(f"Accessibility: {item.missing_alt_count} media without alt text.")
        self.details.SetValue("\n".join(lines))

    def _announce_field(self, delta: int) -> None:
        item = self._current_item()
        if item is None:
            return
        accounts = {a.account_id: a for a in self.store.list_accounts()}
        pairs = read_fields(
            item, self.profile, account=accounts.get(item.account_id), settings=self.a11y
        )
        if not pairs:
            return
        self._field_index = (self._field_index + delta) % len(pairs)
        label, value = pairs[self._field_index]
        self.announcer.say(f"{label}: {value}", "normal", interrupt=True)

    # -- keyboard dispatch ----------------------------------------------------

    def _on_char_hook(self, event: wx.KeyEvent) -> None:
        # Field navigation only when the list has focus.
        if self.FindFocus() is self.list:
            code = event.GetKeyCode()
            if code == wx.WXK_LEFT:
                self._announce_field(-1)
                return
            if code == wx.WXK_RIGHT:
                self._announce_field(1)
                return
        chord = keymap_mod.chord_from_event(event)
        command_id = self.keymap.command_for(chord) if chord else None
        if command_id and self._dispatch(command_id):
            return
        event.Skip()

    def _dispatch(self, command_id: str) -> bool:
        handler = {
            "compose": self.cmd_compose,
            "reply": self.cmd_reply,
            "quote": self.cmd_quote,
            "repost": self.cmd_repost,
            "favourite": self.cmd_favourite,
            "bookmark": self.cmd_bookmark,
            "open_conversation": self.cmd_open_conversation,
            "open_links": self.cmd_open_links,
            "mark_read": self.cmd_mark_read,
            "command_center": self.cmd_command_center,
            "where_am_i": self.cmd_where_am_i,
            "refresh": self.cmd_refresh,
            "search": self.cmd_focus_search,
            "help": self.cmd_help,
        }.get(command_id)
        if handler is None:
            return False
        handler()
        return True

    # -- navigation events ----------------------------------------------------

    def _on_nav_changed(self, event) -> None:
        if self._closing:
            return
        node = event.GetItem()
        try:
            data = self.nav.GetItemData(node)
        except RuntimeError:
            return  # tree being torn down
        if not data:
            return
        scope, label = data
        if scope in ("home", "attention", "library", "publishing", "discover", "github"):
            return  # parent header, not a feed
        self._load_scope(scope, label)

    def _run_search(self) -> None:
        self.last_search = self.search.GetValue().strip()
        node = self._nav_nodes.get("discover:search")
        if node:
            self.nav.SelectItem(node)
        self._load_scope("discover:search", "Search Results")

    # -- commands -------------------------------------------------------------

    def cmd_compose(self) -> None:
        self._open_composer()

    def cmd_reply(self) -> None:
        item = self._current_item()
        if item is None:
            self.announcer.error("Select a post to reply to.")
            return
        self._open_composer(reply_to=item)

    def cmd_quote(self) -> None:
        item = self._current_item()
        if item is None:
            self.announcer.error("Select a post to quote.")
            return
        self._open_composer(quote_of=item.remote_id)

    def _open_composer(self, *, reply_to=None, quote_of: str = "") -> None:
        accounts = self.store.list_accounts(include_paused=False)
        if not accounts:
            self.announcer.error("Add an account first.")
            return
        caps = {a.account_id: self.caps.get(a.account_id, a.network) for a in accounts}
        dlg = ComposerDialog(
            self, accounts, caps, store=self.store, reply_to=reply_to, quote_of=quote_of
        )
        self.announcer.say("Composer open. Editor has focus.", "normal")
        if dlg.ShowModal() == wx.ID_OK and dlg.result_draft:
            self._handle_compose_result(
                dlg.result_action,
                dlg.result_draft,
                schedule_at=getattr(dlg, "result_schedule_at", None),
            )
        dlg.Destroy()

    def _handle_compose_result(self, action: str, draft, *, schedule_at=None) -> None:
        if action == "save":
            self.store.put_draft(draft)
            self.announcer.say("Draft saved.", "normal")
            return
        if action == "schedule":
            self.store.put_draft(draft)
            when = schedule_at or (now_ms() + 60_000)
            for account_id in draft.targets:
                acct = self.store.get_account(account_id)
                self.store.put_plan(
                    PublicationPlan(
                        draft_id=draft.draft_id,
                        account_id=account_id,
                        network=acct.network if acct else "mock",
                        tier="local",
                        scheduled_for=when,
                        state="scheduled",
                    )
                )
            self.announcer.say(
                f"Scheduled for {len(draft.targets)} account(s) at "
                f"{_fmt_ms(when)}. The local scheduler runs while the app is "
                "open.",
                "normal",
            )
            return
        # publish now
        self._publish_now(draft)

    def _publish_now(self, draft) -> None:
        results = []
        for account_id in draft.targets:
            acct = self.store.get_account(account_id)
            if acct is None:
                continue
            adapter = self._resolve_adapter(account_id)
            caps = self.caps.get(account_id, acct.network)
            counter = mastodon_counter if acct.network == "mastodon" else len
            try:
                if draft.thread_mode:
                    split = split_thread(draft.text, caps.char_limit, counter=counter)
                    res = publish_thread(
                        adapter,
                        split.texts(),
                        run_id=draft.draft_id,
                        visibility=draft.visibility,
                        content_warning=draft.content_warning,
                    )
                    results.append((acct.label, res.summary()))
                else:
                    from quill_social.adapters.base import PublishRequest

                    adapter.publish(
                        PublishRequest(
                            text=draft.text,
                            visibility=draft.visibility,
                            content_warning=draft.content_warning,
                        )
                    )
                    results.append((acct.label, "Published."))
            except AdapterError as exc:
                results.append((acct.label, f"Failed: {exc}"))
        self._refresh_from_network(announce=False)
        self._load_scope(self.current_scope, self.current_scope_label)
        msg = "; ".join(f"{label}: {status}" for label, status in results)
        self.announcer.say(msg or "Nothing published.", "normal")

    def _toggle_flag(self, column: str, verb: str) -> None:
        item = self._current_item()
        if item is None:
            self.announcer.error("Select a post first.")
            return
        new_value = not getattr(item, column)
        self.store.set_flag(item.item_id, column, new_value)
        setattr(item, column, new_value)
        acct = self.store.get_account(item.account_id)
        if acct and column in ("favourited", "bookmarked", "reblogged"):
            try:
                adapter = self._resolve_adapter(acct.account_id)
                {
                    "favourited": adapter.set_favourite,
                    "bookmarked": adapter.set_bookmark,
                    "reblogged": adapter.set_reblog,
                }[column](item.remote_id, new_value)
            except AdapterError:
                pass
        state = "on" if new_value else "off"
        self.announcer.say(f"{verb} {state}.", "normal")

    def cmd_favourite(self) -> None:
        self._toggle_flag("favourited", "Favourite")

    def cmd_bookmark(self) -> None:
        self._toggle_flag("bookmarked", "Bookmark")

    def cmd_repost(self) -> None:
        self._toggle_flag("reblogged", "Boost")

    def cmd_flag(self) -> None:
        self._toggle_flag("flagged", "Follow-up flag")

    def cmd_mark_read(self) -> None:
        item = self._current_item()
        if item is None:
            return
        self.store.set_read(item.item_id, True)
        item.read = True
        self.announcer.say("Marked read.", "normal")

    def cmd_open_conversation(self) -> None:
        item = self._current_item()
        if item is None:
            self.announcer.error("Select a post first.")
            return
        thread = self.store.list_items(thread_root=item.thread_root or item.remote_id, limit=100)
        if not thread:
            thread = [item]
        self._items = sorted(thread, key=lambda x: x.created_at)
        self._render_list()
        self.announcer.say(f"Conversation. {len(self._items)} posts.", "normal")

    def cmd_open_links(self) -> None:
        item = self._current_item()
        if item is None:
            return
        import re

        urls = re.findall(r"https?://\S+", item.text)
        if not urls:
            self.announcer.say("No links in this post.", "normal")
            return
        for url in urls:
            webbrowser.open(url)
        self.announcer.say(f"Opened {len(urls)} link(s).", "normal")

    def cmd_refresh(self) -> None:
        self._refresh_from_network(announce=True)
        self._load_scope(self.current_scope, self.current_scope_label)

    def cmd_focus_search(self) -> None:
        self.search.SetFocus()
        self.announcer.say("Search. Type a query and press Enter.", "normal")

    def cmd_catchup(self) -> None:
        node = self._nav_nodes.get("discover:catchup")
        if node:
            self.nav.SelectItem(node)
        self._load_scope("discover:catchup", "Catch Up")

    # -- analytics, safety, AI, ecosystem (PRD 33, 27, 21, 20) ----------------

    def cmd_analytics(self) -> None:
        """Show measured metrics as accessible data tables (PRD 33.2)."""
        all_items = self.store.list_items(limit=1000)
        own = [it for it in all_items if "you" in it.author_handle.lower()]
        report = analytics_svc.compute_metrics(own, all_items, plans=self.store.list_plans())
        blocks = [analytics_svc.to_markdown(t) for t in report.tables()]
        self._show_text("Insights", "\n\n".join(blocks))
        self.announcer.say(
            f"Insights. {report.posts_sent} posts sent, "
            f"{report.replies_received} replies received.",
            "normal",
        )

    def cmd_safety_center(self) -> None:
        """Open the unified Safety Center (PRD 27.1)."""
        self._modal(SafetyCenterDialog(self, self.store))
        self.announcer.say("Safety Center closed.", "normal")

    def cmd_notification_policies(self) -> None:
        """Open the notification policy editor (PRD 25)."""
        self._modal(NotificationPoliciesDialog(self, self.store))

    def cmd_plugins(self) -> None:
        """Open the plugin manager (PRD 34)."""
        self._modal(PluginManagerDialog(self, self.store))

    def cmd_outbox(self) -> None:
        """Open the offline outbox (PRD 32)."""
        self._modal(OutboxDialog(self, self.store))

    def cmd_drafts(self) -> None:
        """Manage drafts; open a chosen draft in the composer (PRD 15.2)."""
        dlg = DraftsDialog(self, self.store)
        dlg.ShowModal()
        chosen = getattr(dlg, "chosen_draft_id", None)
        dlg.Destroy()
        if chosen:
            self._open_composer_for_draft(chosen)

    def cmd_agenda(self) -> None:
        """Open the accessible publishing calendar (PRD 18.5)."""
        self._modal(AgendaDialog(self, self.store))

    def cmd_queue_schedule(self) -> None:
        """Edit a posting queue schedule (PRD 18.4)."""
        self._modal(QueueScheduleDialog(self, self.store))

    def cmd_approvals(self) -> None:
        """Open the approvals workflow (PRD 18.8)."""
        self._modal(ApprovalsDialog(self, self.store))

    def cmd_play_media(self) -> None:
        """Play the focused post's media in the accessible player (PRD 19)."""
        item = self._current_item()
        if item is None or not item.media:
            self.announcer.say("This post has no media to play.", "normal")
            return
        self._modal(MediaPlayerDialog(self, item.media))

    def _open_composer_for_draft(self, draft_id: str) -> None:
        draft = self.store.get_draft(draft_id)
        if draft is None:
            return
        accounts = self.store.list_accounts(include_paused=False)
        caps = {a.account_id: self.caps.get(a.account_id, a.network) for a in accounts}
        dlg = ComposerDialog(self, accounts, caps, store=self.store)
        try:
            dlg.editor.SetValue(draft.text)
            if draft.content_warning:
                dlg.cw.SetValue(draft.content_warning)
            dlg.thread_mode.SetValue(draft.thread_mode)
        except Exception:
            pass
        if dlg.ShowModal() == wx.ID_OK and dlg.result_draft:
            self.store.delete_draft(draft_id)
            self._handle_compose_result(
                dlg.result_action,
                dlg.result_draft,
                schedule_at=getattr(dlg, "result_schedule_at", None),
            )
        dlg.Destroy()

    def _modal(self, dlg) -> None:
        """Show a dialog modally and destroy it. Central so teardown is uniform."""
        try:
            dlg.ShowModal()
        finally:
            dlg.Destroy()

    def cmd_summarize_feed(self) -> None:
        """AI summary of the visible feed that always lists its sources (PRD 12.6)."""
        if not self._items:
            self.announcer.error("Nothing to summarize here.")
            return
        summary = ai_understand.summarize(self._items[:25])
        text = (
            f"{summary.text}\n\nSources: {len(summary.sources)} posts. "
            "AI output is a draft; every source is listed and inspectable."
        )
        self._show_text("Summary", text)
        self.announcer.say(summary.text[:200], "normal", interrupt=True)

    def cmd_accessibility_check(self) -> None:
        """Run the accessibility assistant on the focused post (PRD 21.5)."""
        item = self._current_item()
        if item is None:
            self.announcer.error("Select a post first.")
            return
        issues = ai_a11y.check_item(item)
        if not issues:
            self.announcer.say("No accessibility issues found on this post.", "normal")
            self._show_text("Accessibility check", "No issues found.")
            return
        lines = [
            f"{i.severity.upper()}: {i.message}"
            + (f"\n  Suggestion: {i.suggestion}" if i.suggestion else "")
            for i in issues
        ]
        self._show_text("Accessibility check", "\n".join(lines))
        self.announcer.say(
            f"{len(issues)} accessibility issue(s). " + issues[0].message, "normal", interrupt=True
        )

    def cmd_send_to_quill(self) -> None:
        """Export the focused post or its conversation to QUILL markdown (PRD 20.1)."""
        item = self._current_item()
        if item is None:
            self.announcer.error("Select a post first.")
            return
        thread = self.store.list_items(
            thread_root=item.thread_root or item.remote_id, limit=100
        ) or [item]
        thread = sorted(thread, key=lambda x: x.created_at)
        intent = ecosystem_svc.send_to_quill(thread, title=f"Thread by {item.author_display}")
        export_dir = self.data_dir / "exports"
        export_dir.mkdir(exist_ok=True)
        path = export_dir / f"{item.item_id}.md"
        path.write_text(intent.markdown, encoding="utf-8")
        self.announcer.say(f"{intent.describe()} Saved to {path}.", "normal")
        self._show_text(
            "Send to QUILL", f"{intent.describe()}\n\nSaved to:\n{path}\n\n" + intent.markdown
        )

    def _show_text(self, title: str, text: str) -> None:
        TextReportDialog(self, title, text).ShowModal()

    def cmd_command_center(self) -> None:
        commands = self._build_commands()
        dlg = CommandPalette(self, commands)
        if dlg.ShowModal() == wx.ID_OK and dlg.chosen():
            dlg.Destroy()
            dlg.chosen().handler()
            return
        dlg.Destroy()

    def cmd_where_am_i(self) -> None:
        item = self._current_item()
        idx = self.list.GetFirstSelected()
        acct = None
        if item:
            acct = self.store.get_account(item.account_id)
        w = WhereAmI(
            workspace="Personal",
            account=acct.label if acct else "",
            network=item.network if item else "",
            feed=self.current_scope_label,
            position=idx + 1 if idx >= 0 else 0,
            total=len(self._items),
            unread=sum(1 for it in self._items if not it.read),
            sort_state="newest first",
            post_type=(
                "reply"
                if item and item.is_reply
                else "boost"
                if item and item.is_repost
                else "post"
            )
            if item
            else "",
            visibility=item.visibility if item else "",
            media_state=(f"{len(item.media)} media" if item and item.media else ""),
            moderation_state=(
                ", ".join(item.moderation_labels) if item and item.moderation_labels else ""
            ),
        )
        text = w.announce()
        self.announcer.say(text, "normal", interrupt=True)
        self.SetStatusText(text)

    def cmd_help(self) -> None:
        HelpDialog(self, self.keymap).ShowModal()

    def _build_commands(self) -> list[Command]:
        has_item = self._current_item() is not None
        km = self.keymap
        return [
            Command(
                "compose",
                "New post",
                self.cmd_compose,
                synonyms=["write", "toot", "skeet"],
                shortcut=km.chord_for("compose"),
            ),
            Command(
                "reply",
                "Reply",
                self.cmd_reply,
                is_available=lambda: has_item,
                unavailable_reason="Select a post to reply to.",
                shortcut=km.chord_for("reply"),
            ),
            Command(
                "quote",
                "Quote post",
                self.cmd_quote,
                is_available=lambda: has_item,
                unavailable_reason="Select a post to quote.",
                shortcut=km.chord_for("quote"),
            ),
            Command(
                "repost",
                "Boost / repost",
                self.cmd_repost,
                is_available=lambda: has_item,
                shortcut=km.chord_for("repost"),
            ),
            Command(
                "favourite",
                "Favourite",
                self.cmd_favourite,
                is_available=lambda: has_item,
                shortcut=km.chord_for("favourite"),
            ),
            Command(
                "bookmark",
                "Bookmark",
                self.cmd_bookmark,
                is_available=lambda: has_item,
                shortcut=km.chord_for("bookmark"),
            ),
            Command(
                "open_conversation",
                "Open conversation",
                self.cmd_open_conversation,
                is_available=lambda: has_item,
                shortcut=km.chord_for("open_conversation"),
            ),
            Command("catchup", "Catch up", self.cmd_catchup, synonyms=["digest"]),
            Command(
                "accessibility_check",
                "Accessibility check",
                self.cmd_accessibility_check,
                is_available=lambda: has_item,
                synonyms=["a11y", "alt text", "audit"],
            ),
            Command(
                "send_to_quill",
                "Send to QUILL",
                self.cmd_send_to_quill,
                is_available=lambda: has_item,
                synonyms=["export", "document"],
            ),
            Command(
                "summarize_feed",
                "Summarize this feed",
                self.cmd_summarize_feed,
                synonyms=["ai", "summary", "digest"],
            ),
            Command(
                "analytics",
                "Insights and analytics",
                self.cmd_analytics,
                synonyms=["metrics", "stats"],
            ),
            Command(
                "safety_center",
                "Safety center",
                self.cmd_safety_center,
                synonyms=["moderation", "filters", "mute", "block"],
            ),
            Command(
                "notification_policies",
                "Notification policies",
                self.cmd_notification_policies,
                synonyms=["quiet hours", "digest"],
            ),
            Command("plugins", "Plugins", self.cmd_plugins, synonyms=["extensions", "add-ons"]),
            Command("outbox", "Outbox", self.cmd_outbox, synonyms=["offline", "pending"]),
            Command("drafts", "Drafts", self.cmd_drafts, synonyms=["saved posts"]),
            Command(
                "agenda",
                "Agenda / calendar",
                self.cmd_agenda,
                synonyms=["schedule", "calendar", "queue"],
            ),
            Command(
                "queue_schedule",
                "Queue schedule",
                self.cmd_queue_schedule,
                synonyms=["posting times", "slots"],
            ),
            Command("approvals", "Approvals", self.cmd_approvals, synonyms=["review", "workflow"]),
            Command(
                "play_media",
                "Play media",
                self.cmd_play_media,
                is_available=lambda: bool(
                    has_item and self._current_item() and self._current_item().media
                ),
                synonyms=["audio", "video", "player"],
            ),
            Command("refresh", "Refresh", self.cmd_refresh, shortcut=km.chord_for("refresh")),
            Command("search", "Search", self.cmd_focus_search, shortcut=km.chord_for("search")),
            Command(
                "where_am_i",
                "Where am I",
                self.cmd_where_am_i,
                synonyms=["context"],
                shortcut=km.chord_for("where_am_i"),
            ),
            Command("add_account", "Add account", lambda: self._on_add_account(None)),
            Command("preferences", "Preferences", lambda: self._on_preferences(None)),
            Command("help", "Help", self.cmd_help, shortcut=km.chord_for("help")),
        ]

    # -- dialogs --------------------------------------------------------------

    def _on_add_account(self, _e) -> None:
        AddAccountDialog(self).run_and_apply(self)

    def _on_preferences(self, _e) -> None:
        PreferencesDialog(self, self.a11y).run_and_apply(self)

    def _on_about(self, _e) -> None:
        wx.MessageBox(
            f"{__title__} {__version__}\n\n"
            "Accessibility-first social workspace for Mastodon and Bluesky.\n"
            "Every conversation within reach.",
            "About QUILL Social",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )

    def _on_close(self, _e) -> None:
        self._closing = True
        try:
            if getattr(self, "_sched_timer", None):
                self._sched_timer.Stop()
        except Exception:
            pass
        try:
            a11y_mod.save(self.data_dir, self.a11y)
            keymap_mod.save(self.data_dir, self.keymap)
            self.store.close()
        except Exception:
            pass
        self.Destroy()


# -- small dialogs ------------------------------------------------------------


class TextReportDialog(wx.Dialog):
    """A read-only, screen-reader-reviewable text report (analytics, summaries).

    Used for any command that produces a block of text the user reviews rather
    than acts on. The text control gets focus so a screen reader lands in the
    content, and the whole report is selectable and copyable.
    """

    def __init__(self, parent, title: str, text: str):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        ctrl = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        ctrl.SetName(title)
        ctrl.SetValue(text)
        sizer.Add(ctrl, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.CreateButtonSizer(wx.OK), 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetSize((620, 520))
        ctrl.SetFocus()
        ctrl.SetInsertionPoint(0)


class HelpDialog(wx.Dialog):
    """Context help listing every command and its current shortcut (PRD 10.4)."""

    def __init__(self, parent, keymap):
        super().__init__(
            parent, title="QUILL Social Help", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        sizer = wx.BoxSizer(wx.VERTICAL)
        text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        text.SetName("Help")
        lines = [
            "QUILL Social -- keyboard guide",
            "",
            "Up/Down: previous/next post.",
            "Left/Right: read the previous/next field of the focused post.",
            "Enter: open the focused post in Details.",
            "",
            "Shortcuts (remappable in Preferences):",
        ]
        for cmd, chord in sorted(keymap.as_dict().items()):
            lines.append(f"  {cmd.replace('_', ' ')}: {chord}")
        lines += [
            "",
            "The demo timeline is a local mock network so you can try every "
            "feature before adding a real account. Use File > Add Account to "
            "connect Mastodon or Bluesky.",
        ]
        text.SetValue("\n".join(lines))
        sizer.Add(text, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.CreateButtonSizer(wx.OK), 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetSize((560, 520))


# Common Mastodon instances offered in the Add Account picker. The field is an
# editable combo box, so this is a convenience list, not a restriction -- type
# any server. Grows over time.
INSTANCE_PRESETS = [
    "caneandable.social",
    "mastodon.online",
    "mastodon.social",
    "tweesecake.social",
]

_NETWORK_GUIDANCE = {
    "mastodon": (
        "Mastodon: pick or type your server, then choose Sign in with browser. "
        "Your browser opens the server's approval page; approve access, copy the "
        "code it shows, paste it below, and choose Finish sign-in. No app setup "
        "needed."
    ),
    "bluesky": (
        "Bluesky: set the server to bsky.social (or your PDS) and your full "
        "handle (for example name.bsky.social). Choose Open app password page, "
        "create an app password, and paste it below -- not your main password."
    ),
    "mock": (
        "Mock: a local demo network. No server or credential is needed; it is "
        "for trying the app offline."
    ),
}

_BLUESKY_APP_PASSWORDS_URL = "https://bsky.app/settings/app-passwords"


class AddAccountDialog(wx.Dialog):
    """Add an account with an in-app OAuth browser sign-in (PRD 11.1, 31.1).

    Mastodon uses the accessible out-of-band OAuth flow: Sign in with browser
    registers the app with the server (once, cached), opens the approval page,
    and -- after you paste the code -- exchanges it for an access token. Bluesky
    uses an app password. Either way the secret goes to the OS credential vault,
    never the database, and Verify connection tests it before you commit.
    """

    def __init__(self, parent):
        super().__init__(
            parent, title="Add Account", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._frame = parent
        self._oauth: tuple[str, str, str] | None = None  # instance, client_id, secret
        self._token = ""  # access token obtained via OAuth

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(self, label="&Network:"), 0, wx.LEFT | wx.TOP, 6)
        self.network = wx.Choice(self, choices=["mastodon", "bluesky", "mock"])
        self.network.SetName("Network")
        self.network.SetSelection(0)
        sizer.Add(self.network, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        sizer.Add(wx.StaticText(self, label="&Server / instance:"), 0, wx.LEFT | wx.TOP, 6)
        self.instance = wx.ComboBox(
            self, value=INSTANCE_PRESETS[0], choices=INSTANCE_PRESETS, style=wx.CB_DROPDOWN
        )
        self.instance.SetName("Server or instance")
        sizer.Add(self.instance, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        sizer.Add(wx.StaticText(self, label="&Handle:"), 0, wx.LEFT | wx.TOP, 6)
        self.handle = wx.TextCtrl(self)
        self.handle.SetName("Handle")
        sizer.Add(self.handle, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        # OAuth row: sign-in button, code entry, finish button.
        self.signin_btn = wx.Button(self, label="&Sign in with browser")
        sizer.Add(self.signin_btn, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        sizer.Add(
            wx.StaticText(self, label="Authorization &code (from the browser):"),
            0,
            wx.LEFT | wx.TOP,
            6,
        )
        crow = wx.BoxSizer(wx.HORIZONTAL)
        self.code = wx.TextCtrl(self)
        self.code.SetName("Authorization code")
        self.code.Enable(False)
        crow.Add(self.code, 1, wx.RIGHT, 6)
        self.finish_btn = wx.Button(self, label="&Finish sign-in")
        self.finish_btn.Enable(False)
        crow.Add(self.finish_btn, 0)
        sizer.Add(crow, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        sizer.Add(
            wx.StaticText(self, label="Or paste an access &token / app password:"),
            0,
            wx.LEFT | wx.TOP,
            6,
        )
        self.secret = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self.secret.SetName("Access token or app password")
        sizer.Add(self.secret, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        self.guidance = wx.StaticText(self, label=_NETWORK_GUIDANCE["mastodon"])
        self.guidance.SetName("Guidance")
        self.guidance.Wrap(430)
        sizer.Add(self.guidance, 0, wx.ALL, 6)

        vrow = wx.BoxSizer(wx.HORIZONTAL)
        self.verify_btn = wx.Button(self, label="&Verify connection")
        vrow.Add(self.verify_btn, 0, wx.RIGHT, 8)
        self.status = wx.StaticText(self, label="")
        self.status.SetName("Status")
        vrow.Add(self.status, 1, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(vrow, 0, wx.EXPAND | wx.ALL, 6)

        sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetSize((480, 560))

        self.network.Bind(wx.EVT_CHOICE, self._on_network)
        self.signin_btn.Bind(wx.EVT_BUTTON, self._on_signin)
        self.finish_btn.Bind(wx.EVT_BUTTON, self._on_finish)
        self.verify_btn.Bind(wx.EVT_BUTTON, self._on_verify)

    # -- state helpers --------------------------------------------------------

    def _temp_account(self) -> Account:
        return Account(
            network=self.network.GetStringSelection(),
            handle=self.handle.GetValue().strip(),
            display_name=self.handle.GetValue().strip(),
            instance=self.instance.GetValue().strip(),
        )

    def _effective_secret(self) -> str:
        """The OAuth token if we have one, else whatever was pasted."""
        return self._token or self.secret.GetValue().strip()

    def _set_status(self, text: str) -> None:
        self.status.SetLabel(text)
        self.Layout()

    def _on_network(self, _e) -> None:
        net = self.network.GetStringSelection()
        self.guidance.SetLabel(_NETWORK_GUIDANCE.get(net, ""))
        self.guidance.Wrap(430)
        self._oauth = None
        self._token = ""
        self.code.SetValue("")
        self.code.Enable(False)
        self.finish_btn.Enable(False)
        self._set_status("")
        if net == "mastodon":
            self.signin_btn.SetLabel("&Sign in with browser")
            self.signin_btn.Enable(True)
            if self.instance.GetValue() in ("", "bsky.social"):
                self.instance.SetValue(INSTANCE_PRESETS[0])
        elif net == "bluesky":
            self.signin_btn.SetLabel("Open app &password page")
            self.signin_btn.Enable(True)
            self.instance.SetValue("bsky.social")
        else:
            self.signin_btn.SetLabel("&Sign in with browser")
            self.signin_btn.Enable(False)
        self.Layout()

    # -- OAuth flow -----------------------------------------------------------

    def _on_signin(self, _e) -> None:
        net = self.network.GetStringSelection()
        if net == "bluesky":
            webbrowser.open(_BLUESKY_APP_PASSWORDS_URL)
            self._set_status(
                "Opened Bluesky app passwords. Create one and paste it below with your handle."
            )
            return
        if net != "mastodon":
            self._set_status("This network needs no browser sign-in.")
            return
        instance = self.instance.GetValue().strip()
        if not instance:
            self._set_status("Enter your Mastodon server first.")
            return
        self._set_status(f"Registering with {instance}...")
        wx.SafeYield(self)
        try:
            client_id, client_secret = oauth.register_app(instance, self._frame.data_dir)
            url = oauth.auth_url(instance, client_id, client_secret)
        except Exception as exc:  # noqa: BLE001 - report any server/client failure
            self._set_status(f"Sign-in could not start: {exc}")
            return
        self._oauth = (instance, client_id, client_secret)
        webbrowser.open(url)
        self.code.Enable(True)
        self.finish_btn.Enable(True)
        self.code.SetFocus()
        self._set_status(
            "Browser opened. Approve access, copy the code it shows, paste it in "
            "the Authorization code field, and choose Finish sign-in."
        )

    def _on_finish(self, _e) -> None:
        if not self._oauth:
            self._set_status("Choose Sign in with browser first.")
            return
        code = self.code.GetValue().strip()
        if not code:
            self._set_status("Paste the authorization code from the browser.")
            return
        instance, client_id, client_secret = self._oauth
        self._set_status("Exchanging the code for an access token...")
        wx.SafeYield(self)
        try:
            self._token = oauth.exchange_code(instance, client_id, client_secret, code)
        except Exception as exc:  # noqa: BLE001 - surface auth failures to the user
            self._set_status(f"Could not get a token: {exc}")
            return
        self._set_status(
            "Signed in. Choose Verify connection to test it, or OK to add the account."
        )

    def _on_verify(self, _e) -> None:
        """Test the credential against the live network without persisting it."""
        net = self.network.GetStringSelection()
        if net == "mock":
            self._set_status("Mock network needs no credential.")
            return
        secret = self._effective_secret()
        if not secret:
            self._set_status("Sign in, or paste a token / app password first.")
            return
        if net == "bluesky" and not self.handle.GetValue().strip():
            self._set_status("Bluesky needs your handle to sign in.")
            return
        tmp = InMemoryCredentialStore()
        acct = self._temp_account()
        tmp.store(net, acct.account_id, secret)
        self._set_status("Connecting...")
        wx.SafeYield(self)
        try:
            adapter = adapter_for(acct, tmp)
            items = adapter.home_timeline(limit=1)
            self._set_status(
                f"Connected to {net}. Fetched {len(items)} post(s). Choose OK to add the account."
            )
        except AdapterError as exc:
            self._set_status(f"Could not connect: {exc}")
        except Exception as exc:  # noqa: BLE001 - surface any client error to the user
            self._set_status(f"Connection error: {exc}")

    def run_and_apply(self, frame) -> None:
        net = self.network.GetStringSelection()
        if self.ShowModal() == wx.ID_OK and (
            self.handle.GetValue().strip() or self.instance.GetValue().strip()
        ):
            acct = self._temp_account()
            frame.store.put_account(acct)
            frame.caps.seed_from_network(acct.account_id, acct.network)
            secret = self._effective_secret()
            if secret and net != "mock":
                try:
                    frame.credentials.store(acct.network, acct.account_id, secret)
                    frame.announcer.say(
                        f"Added {acct.label}; credential stored securely. Press F5 to refresh.",
                        "normal",
                    )
                except Exception:
                    frame.announcer.say(
                        f"Added {acct.label}; could not store the credential.", "normal"
                    )
            else:
                frame.announcer.say(f"Added {acct.label}.", "normal")
        self.Destroy()


class PreferencesDialog(wx.Dialog):
    """Accessibility preferences (PRD 28.5)."""

    def __init__(self, parent, settings):
        super().__init__(parent, title="Preferences")
        self._settings = settings
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="Announcement verbosity:"), 0, wx.ALL, 6)
        self.verbosity = wx.Choice(self, choices=["minimal", "normal", "verbose"])
        self.verbosity.SetName("Verbosity")
        self.verbosity.SetStringSelection(settings.verbosity)
        sizer.Add(self.verbosity, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        self.high_contrast = wx.CheckBox(self, label="High contrast")
        self.high_contrast.SetValue(settings.high_contrast)
        sizer.Add(self.high_contrast, 0, wx.ALL, 6)
        self.speak_network = wx.CheckBox(self, label="Speak network on each row")
        self.speak_network.SetValue(settings.speak_network_prefix)
        sizer.Add(self.speak_network, 0, wx.ALL, 6)
        self.speak_engagement = wx.CheckBox(self, label="Speak engagement counts on each row")
        self.speak_engagement.SetValue(settings.speak_engagement)
        sizer.Add(self.speak_engagement, 0, wx.ALL, 6)
        sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizerAndFit(sizer)

    def run_and_apply(self, frame) -> None:
        if self.ShowModal() == wx.ID_OK:
            self._settings.verbosity = self.verbosity.GetStringSelection()
            self._settings.high_contrast = self.high_contrast.GetValue()
            self._settings.speak_network_prefix = self.speak_network.GetValue()
            self._settings.speak_engagement = self.speak_engagement.GetValue()
            a11y_mod.save(frame.data_dir, self._settings)
            frame.announcer.set_verbosity(self._settings.verbosity)
            a11y_mod.apply_to_frame(frame, self._settings)
            frame._render_list(keep_selection=True)
            frame.announcer.say("Preferences saved.", "normal")
        self.Destroy()


def _make_credential_store():
    """Prefer the OS credential vault; fall back to an in-memory store (PRD 31.1).

    Secrets never touch the database -- only an opaque reference is persisted.
    """
    try:
        if WindowsCredentialManagerStore.available():
            return WindowsCredentialManagerStore()
    except Exception:
        pass
    return InMemoryCredentialStore()


def _fmt_ms(ms: int | None) -> str:
    if not ms:
        return "unknown"
    from datetime import datetime

    return datetime.fromtimestamp(ms / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")


def run() -> int:
    app = wx.App()
    frame = SocialFrame()
    frame.Show()
    app.MainLoop()
    return 0
