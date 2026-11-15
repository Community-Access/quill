"""The WordPress provider for the Workbench window, and the one way to open it (PRD W1 to W4).

The window is the shared :class:`~quill.ui.workbench_frame.WorkbenchFrame`;
this module is everything particular to WordPress (WP-R-001): the tree of
:mod:`quill.core.wordpress.workbench_tree`, its lists from
:mod:`~quill.core.wordpress.workbench_load` and Needs My Attention from
:mod:`~quill.core.wordpress.workbench_attention`, the menus and context menus
of :mod:`~quill.core.wordpress.workbench_actions`, and the status bar cells
of section 4. What the commands do lives in three mixins beside it: the rows
(:mod:`quill.ui.wordpress_workbench_commands`), Properties, batch and undo
(:mod:`quill.ui.wordpress_workbench_sheets`), and people, permissions and
filters (:mod:`quill.ui.wordpress_workbench_people`). Search across every site
and the status bar cells are mixins too
(:mod:`quill.ui.wordpress_workbench_window_search`,
:mod:`quill.ui.wordpress_workbench_window_status`).

Every request goes through the connected site's own client
(:func:`quill.core.wordpress.sites.api_for`), so the Workbench adds no host
and no new way in; every call runs off the UI thread through the frame's
task runner; nothing is announced on focus or on opening (GATE-13), and what
is said goes through the editor's announce, which speaks and brailles.

The one way in from Tools > WordPress (W6): :func:`open_from_door`, which
the Tools > WordPress handlers in :mod:`quill.ui.wordpress_commands` call in
both editors. The retired classic management windows are not an alternate
route. QUILL Lite is never ahead.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from typing import Any

from quill.core.wordpress import site_taxonomies as tx
from quill.core.wordpress import site_types as stypes
from quill.core.wordpress import sites as st
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import load_account, load_site_info
from quill.core.wordpress.workbench_actions import (
    GO_NODES,
    LIST_KEYS,
    PREFIX,
    WINDOW_MENU,
    WORDPRESS_ACTIONS,
    WORDPRESS_KEYMAP_ID,
)
from quill.core.wordpress.workbench_attention import ATTENTION, gather
from quill.core.wordpress.workbench_filter import (
    FILTER_HELP,
    local_matches,
    params_for,
    resolve_terms,
)
from quill.core.wordpress.workbench_help import HOW_IT_THINKS, START_HERE, help_rows
from quill.core.wordpress.workbench_listing import page_limit
from quill.core.wordpress.workbench_load import SiteContext, load
from quill.core.wordpress.workbench_node_help import node_help as authored_help
from quill.core.wordpress.workbench_node_help import row_help
from quill.core.wordpress.workbench_permissions import AccessStore
from quill.core.wordpress.workbench_practice import practice_label, stop_process
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_tree import (
    DYNAMIC_NAMESPACE,
    DYNAMIC_TYPE,
    PLANNED_WORDS,
    START_NODE,
    WORDPRESS_TREE,
    door_node,
)
from quill.core.wordpress.workbench_type_nodes import type_children
from quill.core.workbench.filters import Query
from quill.core.workbench.history import ChangeHistory
from quill.core.workbench.properties import SheetSpec
from quill.core.workbench.tree import NodeSpec
from quill.ui.wordpress_workbench_across import WorkbenchAcrossCommands
from quill.ui.wordpress_workbench_bold import WorkbenchBoldCommands
from quill.ui.wordpress_workbench_commands import WorkbenchRowCommands
from quill.ui.wordpress_workbench_discovered import WorkbenchDiscoveredCommands
from quill.ui.wordpress_workbench_editor_side import WorkbenchEditorSide
from quill.ui.wordpress_workbench_forms_site import WorkbenchPluginCommands
from quill.ui.wordpress_workbench_gaps import WorkbenchGapCommands
from quill.ui.wordpress_workbench_guard import WorkbenchGuard, watch_writes
from quill.ui.wordpress_workbench_lists import WorkbenchListCommands
from quill.ui.wordpress_workbench_media_replace import WorkbenchMediaReplace
from quill.ui.wordpress_workbench_menu_items import WorkbenchMenuItemCommands
from quill.ui.wordpress_workbench_moderation import WorkbenchModerationCommands
from quill.ui.wordpress_workbench_options import WorkbenchOptionsCommands
from quill.ui.wordpress_workbench_parity import WorkbenchParityCommands
from quill.ui.wordpress_workbench_people import WorkbenchPeopleCommands
from quill.ui.wordpress_workbench_people_admin import WorkbenchPeopleAdminCommands
from quill.ui.wordpress_workbench_people_bulk import WorkbenchPeopleBulkCommands
from quill.ui.wordpress_workbench_roles import WorkbenchRolesCommands
from quill.ui.wordpress_workbench_scope_more import WorkbenchScopeMoreCommands
from quill.ui.wordpress_workbench_sheets import WorkbenchSheetCommands
from quill.ui.wordpress_workbench_site_check import WorkbenchSiteCheck
from quill.ui.wordpress_workbench_site_editor import WorkbenchSiteEditorCommands
from quill.ui.wordpress_workbench_site_types import WorkbenchSiteTypesCommands
from quill.ui.wordpress_workbench_sweep import WorkbenchSweepCommands
from quill.ui.wordpress_workbench_widgets import WorkbenchWidgetCommands
from quill.ui.wordpress_workbench_window_search import WorkbenchSearchCommands
from quill.ui.wordpress_workbench_window_status import WorkbenchStatusCells
from quill.ui.wordpress_workbench_wxr import WorkbenchWxrCommands
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame

__all__ = ["SEP", "WordPressWorkbenchProvider", "open_from_door", "open_workbench"]

SEP = "\x1f"
"""Between a site's name and a dynamic node's kind in a node's instance."""

#: The verbs on Delete, Shift+Delete and Ctrl+Z (LIST_KEYS): never from the status bar,
#: whose buttons pass those keys on to the menu instead of keeping them.
_LIST_VERBS = frozenset({"trash", "delete_permanently", "undo"})

#: Families whose filters and words go to the site; the rest filter the loaded rows.
_REMOTE = frozenset({"items", "media", "comments", "users", "terms", "patterns", "search"})


class WordPressWorkbenchProvider(
    WorkbenchPeopleBulkCommands,  # ahead of WorkbenchPeopleCommands: bulk Change Role, Remove
    WorkbenchModerationCommands,
    WorkbenchEditorSide,
    WorkbenchPeopleAdminCommands,
    WorkbenchSiteTypesCommands,
    WorkbenchSiteCheck,
    WorkbenchStatusCells,
    WorkbenchSearchCommands,
    WorkbenchMediaReplace,  # Media row > Replace File (media_replace)
    WorkbenchGapCommands,  # Earlier Versions, Check for Updates, Check Every Link
    WorkbenchWxrCommands,  # Tools > WXR Files
    WorkbenchRolesCommands,  # ahead of WorkbenchListCommands: Roles through a role plugin
    WorkbenchListCommands,
    WorkbenchDiscoveredCommands,
    WorkbenchOptionsCommands,
    WorkbenchBoldCommands,
    WorkbenchScopeMoreCommands,  # ahead of WorkbenchAcrossCommands: convert, merge, remove
    WorkbenchAcrossCommands,
    WorkbenchSweepCommands,
    WorkbenchRowCommands,
    WorkbenchSheetCommands,
    WorkbenchPeopleCommands,
    WorkbenchParityCommands,
    WorkbenchSiteEditorCommands,
    WorkbenchWidgetCommands,
    WorkbenchMenuItemCommands,
    WorkbenchPluginCommands,  # WooCommerce, The Events Calendar, Yoast SEO, QAF (Packages 8-13)
    WorkbenchGuard,  # every write checked by tier, every change in Change History
):
    """WordPress, for :class:`~quill.ui.workbench_frame.WorkbenchFrame`."""

    name = "WordPress Workbench"
    tree = WORDPRESS_TREE
    actions = WORDPRESS_ACTIONS
    menu = WINDOW_MENU
    go_nodes = GO_NODES
    filter_help = FILTER_HELP
    no_instance_text = "Connect a site first: File > WordPress > Connect a Site, in the editor."
    list_keys = LIST_KEYS
    keymap_id = WORDPRESS_KEYMAP_ID

    def __init__(
        self,
        commands: Any,
        *,
        announce: Callable[[str], None],
        data_dir: Any = None,
        safe_mode: bool = False,
        api_for: Callable[[st.SiteProfile], Any] | None = None,
    ) -> None:
        self.commands = commands
        self._api_for = api_for or (
            lambda profile: st.api_for(profile, opener=getattr(commands, "_opener", None))
        )
        self._announce = announce
        self.frame: WorkbenchFrame | None = None
        self._data_dir = data_dir
        self.access_store = AccessStore(data_dir)
        self.safe_mode = safe_mode
        self.history = ChangeHistory()
        self.view_as: dict[str, str] = {}
        self._contexts: dict[str, SiteContext] = {}
        self._types: dict[str, list[tuple[str, str]]] = {}
        self._taxonomies: dict[str, list[tuple[str, str]]] = {}
        self._statuses: dict[str, list[tuple[str, str]]] = {}
        self._waiting: dict[str, int] = {}
        self._profiles: dict[str, st.SiteProfile] = {}
        self._practice: Any = None
        self._practice_lock = threading.Lock()
        self._practice_closed = False
        self._lists_state()
        self.reload_profiles()

    # -- sites --------------------------------------------------------------------

    def reload_profiles(self) -> None:
        store = self.commands.sites()
        self._profiles = {}
        for profile in store.sites:
            # A practice site always says so, in every row, preview and status line.
            name = practice_label(profile.name or profile.host, profile.site_url)
            if name in self._profiles:
                name = f"{name} ({profile.host})"
            self._profiles[name] = profile

    def profile(self, site: str) -> st.SiteProfile | None:
        return self._profiles.get(site)

    def ctx(self, site: str) -> SiteContext:
        """The site's context, made on first use (no request until something loads)."""
        found = self._contexts.get(site)
        if found is None:
            profile = self._profiles[site]
            api = watch_writes(self._api_for(profile))  # notes each change it sends
            found = SiteContext(site, api, url=profile.site_url)
            self._contexts[site] = found
        return found

    def ensure(self, ctx: SiteContext) -> SiteContext:
        """Who you are and what the site offers, read once (off the UI thread)."""
        if ctx.account is None:
            ctx.account = load_account(ctx.api)
        if ctx.info is None:
            ctx.info = load_site_info(ctx.api)
        self.recheck(ctx)  # a plugin, theme or version change: read the claims again
        return ctx

    def discover(self, site: str) -> None:
        """Read *site*'s own post types and taxonomies, then add their nodes (off the UI thread)."""
        ctx = self.ensure(self.ctx(site))
        types = [(t.kind, t.name) for t in stypes.discover_writing_types(ctx.api)]
        taxonomies = [
            (t.slug, t.name)
            for t in tx.discover_taxonomies(ctx.api).values()
            if t.slug not in ("category", "post_tag", "nav_menu", "wp_pattern_category")
        ]
        self._types[site], self._taxonomies[site] = types, taxonomies
        self._statuses[site] = stypes.statuses_for(ctx.api)  # each type's status nodes

    @staticmethod
    def split(instance: str) -> tuple[str, str]:
        site, _sep, kind = instance.partition(SEP)
        return site, kind

    def site_of(self, ref: NodeRef | None) -> str:
        if ref is None or ref.template != "site":
            return ""
        return self.split(ref.instance)[0]

    def current_site(self) -> str:
        frame = self.frame
        site = self.site_of(frame.current if frame is not None else None)
        return site or next(iter(self._profiles), "")

    # -- the tree -----------------------------------------------------------------

    def window_title(self, instance: str) -> str:
        return self.name

    def instances(self, template: str) -> Sequence[str]:
        return tuple(self._profiles) if template == "site" else ()

    def current_instance(self, template: str) -> str:
        return self.current_site() if template == "site" else ""

    def add_instance(self, template: str, address: str) -> NodeRef | None:
        return None  # sites are connected from the editor, which keeps the password safe

    def dynamic_children(self, node: NodeSpec, ref: NodeRef) -> Sequence[tuple[str, str]]:
        if node.key.endswith("_group"):
            return self.group_children(node, ref)
        if node.key == "calendar_day":
            return self.day_children()
        site = self.split(ref.instance)[0]
        if node.key == DYNAMIC_NAMESPACE:
            return self.namespace_children(site)
        if node.key == DYNAMIC_TYPE:
            return type_children(site, SEP, self._types.get(site, []), self._statuses.get(site, []))
        found = self._taxonomies.get(site, [])
        return tuple((f"{site}{SEP}{kind}", label) for kind, label in found)

    def node_help(self, ref: NodeRef, node: NodeSpec) -> str:
        said = self._node_words(ref, node)
        frame = self.frame
        if frame is not None:  # F1 on the tree answers with this node's own sentence
            frame.tree.SetHelpText(f"{authored_help(node.key)} {said}".strip())
        return said

    def _node_words(self, ref: NodeRef, node: NodeSpec) -> str:
        if ref == NodeRef("", START_NODE):
            count = len(self._profiles)
            sites = f"You have {count} site{'s' if count != 1 else ''} connected."
            return f"{START_HERE}\n\n{sites}"
        if node.key == "how_it_thinks":
            return HOW_IT_THINKS
        site = self.site_of(ref)
        what = f"{node.label}, {site}." if site else f"{node.label}."
        if node.loader.startswith("attention:"):
            what += " Gathered from every connected site, newest first."
        if not node.loader:
            what += " Open it with Right Arrow to see what it holds."
        return what

    def unavailable(self, ref: NodeRef, node: NodeSpec) -> str:
        if node.loader.startswith("planned:"):
            return PLANNED_WORDS.get(node.loader.removeprefix("planned:"), "In a later phase.")
        if not self._profiles and (ref.template == "site" or node.loader.startswith("attention")):
            return self.no_instance_text
        return self.node_refusal(ref, node)

    # -- rows ---------------------------------------------------------------------

    def columns(self, node: NodeSpec) -> tuple[str, ...]:
        return self.chosen_columns(node)

    def remote_words(self, node: NodeSpec) -> bool:
        return node.loader.partition(":")[0] in _REMOTE

    def load(self, ref: NodeRef, node: NodeSpec, query: Query) -> list[object]:
        """A node's rows, off the UI thread."""
        family, _sep, what = node.loader.partition(":")
        if family == "help":
            return list(help_rows(what))
        if family == "sites":
            return [self._site_row(name) for name in self._profiles]
        if family in ("calendar", "watches", "practice"):
            return list(self.fixed_rows(family, what, ref.instance))
        if family == "across":
            return [r for r in self.across_list(what) if local_matches(r, query.conditions)]
        if family == "scan":
            return list(self.scan_rows(self.split(ref.instance)[0], what))
        if family == "sweep":
            return list(self.sweep_rows(self.split(ref.instance)[0], what))
        if family == "search":
            return self._search_all_sites(query)
        if family == "attention":
            contexts = []
            for name in self._profiles:
                try:
                    contexts.append(self.ensure(self.ctx(name)))
                except WordPressApiError:
                    contexts.append(self.ctx(name))
            rows = self.with_update_facts(gather(what, contexts))  # Updates, once asked
            if what == "waiting":
                self._waiting = {}
                for row in rows:
                    self._waiting[row.site] = self._waiting.get(row.site, 0) + 1
            return [row for row in rows if local_matches(row, query.conditions)]
        site, dynamic = self.split(ref.instance)
        ctx = self.ensure(self.ctx(site))
        remote = family in _REMOTE
        params: dict[str, object] = {}
        if remote and not query.is_empty:
            bases = [t.rest_base for t in (tx.cached_taxonomies(ctx.api) or {}).values()]
            params = params_for(query, resolve=resolve_terms(ctx.api), taxonomy_bases=bases)
        # Forms: a Gravity Forms filter is sent to the site (gravity_load_scope).
        scope = self.gravity_load_scope(ref, node.loader, query)
        with page_limit(self.pages_for_ref(ref)), scope as left:
            rows = load(ctx, node.loader, dict(node.preset), params, dynamic=dynamic)
            self.note_loaded(ref, len(rows))
        rows = self.with_update_facts(
            self.with_directory_facts(self.narrow_to_group(dynamic, rows))
        )
        if not remote and left:
            rows = [row for row in rows if local_matches(row, left)]
        return list(rows)

    def _site_row(self, name: str) -> WbRow:
        profile = self._profiles[name]
        ctx = self._contexts.get(name)
        role = ctx.account.role_name if ctx and ctx.account else (profile.role or "")
        return WbRow(
            "site",
            name,
            profile.id,
            {"site": name, "address": profile.site_url, "role": role},
            f"{name}, at {profile.site_url}" + (f", where you are {role}." if role else "."),
            link=profile.site_url,
        )

    def cells(self, row: object, columns: tuple[str, ...]) -> list[str]:
        if not isinstance(row, WbRow):
            return [str(row)]
        return [self.cell_for(row, column) for column in columns]

    def detail(self, row: object) -> str:
        frame = self.frame
        if frame is not None and isinstance(row, WbRow):  # F1 on the list: this row's kind
            frame.list.SetHelpText(row_help(row.kind))
        return row.detail if isinstance(row, WbRow) else str(row)

    def row_type(self, node: NodeSpec, row: object) -> str:
        kind = row.kind if isinstance(row, WbRow) else "fact"
        return kind if kind in self.actions.row_types else "fact"

    def url(self, ref: NodeRef, row: object | None) -> str:
        if isinstance(row, WbRow) and row.link:
            return row.link
        profile = self.profile(self.site_of(ref) or self.current_site())
        return profile.site_url if profile else ""

    def properties(self, ref: NodeRef, row: object) -> tuple[SheetSpec, dict[str, Any], str] | None:
        return None  # Alt+Enter is this provider's own sheet command (wordpress_workbench_sheets)

    # -- commands -----------------------------------------------------------------

    def supports(self, command_id: str) -> bool:
        """Offered now: known, allowed by the site role and by Workbench access."""
        if not command_id.startswith(PREFIX):
            return False
        frame = self.frame
        row = frame.selected_row() if frame is not None else None
        ref = frame.current if frame is not None else None
        return not self.refusal_for(command_id, row if isinstance(row, WbRow) else None, ref)

    def run(self, command_id: str, ref: NodeRef, row: object) -> bool:
        if self.frame is None or not command_id.startswith(PREFIX):
            return False
        chosen = row if isinstance(row, WbRow) else None
        command_id = self.picked_command(command_id, chosen)  # Enter inserts, when picking
        verb = command_id.removeprefix(PREFIX)
        reason = self.refusal_for(command_id, chosen, ref)  # every write, by its tier
        if verb in _LIST_VERBS and self.frame.status.has_focus():
            reason = "Delete and Ctrl+Z act on the list. F6 moves back to it."
        if reason:
            self.say(reason)
            return True
        handler = getattr(self, f"do_{verb}", None)
        if handler is None:
            self.say("That is not in this preview of the Workbench yet.")
            return True
        site = chosen.site if chosen is not None and chosen.site else self.site_of(ref)
        with self.running(self.running_for(command_id, self.label_for(command_id), site)):
            handler(ref, chosen)
        return True

    # -- plumbing the mixins share ------------------------------------------------

    def say(self, text: str) -> None:
        self._announce(text)

    @property
    def parent(self) -> Any:
        return self.frame.frame if self.frame is not None else None

    def show_modal(self, dialog: Any, label: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, label))

    def background(self, name: str, work: Callable[[], Any], done: Callable[[Any], None]) -> None:
        def failed(error: BaseException) -> None:
            said = error.plain if isinstance(error, WordPressApiError) else str(error)
            self.say(said or "That did not work.")

        frame = self.frame
        if frame is None:
            return
        work, done, settle = self.watched(work, done)  # a change sent is in Change History

        def failed_watched(error: BaseException) -> None:
            failed(error)
            settle()

        frame._run_background(f"WordPress Workbench: {name}", work, done, failed_watched)

    def selected_rows(self) -> list[WbRow]:
        frame = self.frame
        if frame is None:
            return []
        return [r for i in frame.selected_indices() if isinstance(r := frame.rows[i], WbRow)]

    def refresh(self) -> None:
        if self.frame is not None:
            self.frame.reload()

    def start(self) -> None:
        """Read each site's own types and taxonomies, then add their nodes to the tree."""
        for site in list(self._profiles):

            def done(_result: object, site: str = site) -> None:
                if self.frame is not None:
                    self.frame.rebuild_tree()
                    self.after_discovery()  # This Post in the Workbench, on a content type

            self.background(f"discovering {site}", lambda s=site: self.discover(s), done)

    def close(self) -> None:
        self.end_picking()
        with self._practice_lock:
            self._practice_closed = True
            process = self._practice
            self._practice = None
        if process is not None:
            stop_process(process)
        self._contexts.clear()


_OPEN: dict[str, WorkbenchFrame] = {}

#: The Needs My Attention keys, so a test can check each has a node.
ATTENTION_KEYS = tuple(ATTENTION)


def _start_ref(provider: WordPressWorkbenchProvider, node: str) -> NodeRef:
    site = provider.current_site()
    if node and site:
        return NodeRef("site", node, site)
    return NodeRef("", "inbox" if site else START_NODE)


def open_workbench(
    commands: Any,
    *,
    node: str = "",
    announce: Callable[[str], None] | None = None,
    safe_mode: bool = False,
    data_dir: Any = None,
) -> WorkbenchFrame:
    """Open the one WordPress Workbench (or bring it forward), at *node* of the current site."""
    say = announce or (lambda _text: None)
    existing = _OPEN.get("wordpress")
    if existing is not None:
        provider = existing.provider
        if isinstance(provider, WordPressWorkbenchProvider):
            provider.reload_profiles()
            existing.rebuild_tree()
            # Back from the editor with no place asked for: the node, row, filter and
            # scroll stay as they were left (complete.md WP-A).
            here = existing.current if not node else None
            existing.show(here or _start_ref(provider, node))
        return existing
    provider = WordPressWorkbenchProvider(
        commands, announce=say, data_dir=data_dir, safe_mode=safe_mode
    )
    frame = WorkbenchFrame(
        provider,
        editor=getattr(commands.host, "parent", None),
        announce=say,
        on_closed=lambda: _OPEN.pop("wordpress", None),
    )
    _OPEN["wordpress"] = frame
    frame.show(_start_ref(provider, node))
    provider.start()
    return frame


def open_from_door(commands: Any, command_id: str) -> bool:
    """Open the WordPress Workbench for a Tools > WordPress door."""
    import os

    open_workbench(
        commands,
        node=door_node(command_id),
        announce=commands.host.announce,
        safe_mode=os.environ.get("QUILL_SAFE_MODE", "") == "1",
        data_dir=getattr(commands, "_data_dir", None),
    )
    return True
