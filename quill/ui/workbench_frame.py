"""The Workbench window: Navigator tree, filter box, list, details and status bar.

GitHub PRD sections 3 and 9, provider-neutral (WordPress PRD section 3): the
frame arranges panes and routes keys; a :class:`WorkbenchProvider` supplies
the tree, the menus, the rows and their words. Principle 1 holds on every
screen: the tree says where you are, the list what is there, and the details
what this one is.

- A top-level ``wx.Frame`` with its own menu bar (built from the provider's
  wx-free table) and the focusable status bar of section 3.2.1. Alt+F4 and
  File > Close Workbench close it; Escape clears the filter, then goes Back,
  and never closes it.
- The tree is the native ``wx.TreeCtrl``, which NVDA, JAWS and Narrator read
  well (section 9). Names are short; the reader says level and state itself.
- F6 and Shift+F6 cycle tree, filter, list, details and status bar.
- Enter does the row's default action; Alt+Enter opens Properties; the
  context menu comes from the provider's action table, default first and
  Properties last.

Nothing is announced on focus, selection or opening (GATE-13). What is said
is a result the reader cannot see: a copy, a failed load, and the Alt+1 and
Alt+2 readouts the person asked for. Words go through the editor's announce
callback, which speaks and brailles (GATE-BRAILLE).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from quill.core.workbench.actions import ActionRow, ActionTable
from quill.core.workbench.filters import Query, describe, matches_words, parse
from quill.core.workbench.menus import MenuSpec
from quill.core.workbench.properties import SheetSpec
from quill.core.workbench.tree import NodeSpec, TreeSpec
from quill.ui.dpi import dip_size
from quill.ui.workbench_frame_actions import WorkbenchActionsMixin
from quill.ui.workbench_status_bar import StatusCell, WorkbenchStatusBar

__all__ = ["NodeRef", "WorkbenchFrame", "WorkbenchProvider"]

#: The verbs the frame does itself, whatever the provider; the rest are the provider's.
_FRAME_VERBS = frozenset({"open_on_github", "copy_link", "properties", "refresh", "help_view"})


@dataclass(frozen=True)
class NodeRef:
    """Where in the tree: a fixed node, or a template node of one *instance*."""

    template: str
    key: str
    instance: str = ""


class WorkbenchProvider(Protocol):
    """What a service gives the frame. Everything but :meth:`load` runs on the UI thread."""

    name: str
    tree: TreeSpec
    actions: ActionTable
    menu: tuple[MenuSpec, ...]
    go_nodes: Mapping[str, tuple[str, str]]

    def window_title(self, instance: str) -> str: ...
    def instances(self, template: str) -> Sequence[str]: ...
    def add_instance(self, template: str, address: str) -> NodeRef | None: ...
    def node_help(self, ref: NodeRef, node: NodeSpec) -> str: ...
    def unavailable(self, ref: NodeRef, node: NodeSpec) -> str: ...
    def load(self, ref: NodeRef, node: NodeSpec, query: Query) -> list[object]: ...
    def columns(self, node: NodeSpec) -> tuple[str, ...]: ...
    def cells(self, row: object, columns: tuple[str, ...]) -> list[str]: ...
    def detail(self, row: object) -> str: ...
    def row_type(self, node: NodeSpec, row: object) -> str: ...
    def url(self, ref: NodeRef, row: object | None) -> str: ...
    def properties(
        self, ref: NodeRef, row: object
    ) -> tuple[SheetSpec, dict[str, Any], str] | None: ...
    def supports(self, command_id: str) -> bool: ...
    def run(self, command_id: str, ref: NodeRef, row: object) -> bool: ...
    def status_cells(self, frame: WorkbenchFrame) -> Sequence[StatusCell]: ...
    def close(self) -> None: ...


Background = Callable[
    [str, Callable[[], Any], Callable[[Any], None], Callable[[BaseException], None]], None
]


class WorkbenchFrame(WorkbenchActionsMixin):
    """One Workbench window over one provider."""

    def __init__(
        self,
        provider: WorkbenchProvider,
        *,
        editor: Any = None,
        announce: Callable[[str], None] | None = None,
        run_background: Background | None = None,
        on_closed: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self.provider = provider
        self._editor = editor
        self._announce = announce or (lambda _text: None)
        self._run_background = run_background or self._task_manager_runner()
        self._on_closed = on_closed
        self.rows: list[object] = []
        self._loaded: list[object] = []
        self.query = Query()
        self.loading = False
        self.loaded_at = ""
        self.history: list[NodeRef] = []
        self.forward: list[NodeRef] = []
        self.current: NodeRef | None = None
        self._generation = 0
        self._items: dict[NodeRef, Any] = {}
        self._columns: tuple[str, ...] = ()
        self._navigating = False
        instance = next(iter(provider.instances("repository")), "")
        self.frame = wx.Frame(None, title=provider.window_title(instance))
        self.frame.SetSize(dip_size(self.frame, 980, 680))
        self._build()
        self.frame.Bind(wx.EVT_CLOSE, self._on_close)
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

    # -- construction -------------------------------------------------------------

    def _build(self) -> None:
        wx = self._wx
        panel = wx.Panel(self.frame)
        splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE)
        self.tree = wx.TreeCtrl(splitter, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT)
        self.tree.SetName("Navigator")
        self.tree.SetHelpText(
            "Where you are. Arrows move, Right and Left open and close a branch, "
            "and typing jumps to a name. F6 moves to the filter box."
        )
        right = wx.Panel(splitter)
        column = wx.BoxSizer(wx.VERTICAL)
        filter_row = wx.BoxSizer(wx.HORIZONTAL)
        filter_row.Add(
            wx.StaticText(right, label="Filte&r:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self.filter = wx.TextCtrl(right, style=wx.TE_PROCESS_ENTER)
        self.filter.SetName("Filter")
        self.filter.SetHelpText(
            "Plain words narrow the list on this device; qualifiers such as is:open or "
            "label:bug ask GitHub. Enter runs it, Escape clears it."
        )
        filter_row.Add(self.filter, 1, wx.EXPAND)
        column.Add(filter_row, 0, wx.EXPAND | wx.ALL, 4)
        self.list = wx.ListCtrl(right, style=wx.LC_REPORT)
        self.list.SetName("Items")
        self.list.SetHelpText(
            "What is here. Enter does the default action, the Applications key lists "
            "the rest, and Alt+Enter opens Properties."
        )
        column.Add(self.list, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 4)
        column.Add(wx.StaticText(right, label="&Details"), 0, wx.LEFT | wx.TOP, 4)
        self.details = wx.TextCtrl(right, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        self.details.SetName("Details")
        self.details.SetHelpText("The selected row in full, or what this view shows and needs.")
        column.Add(self.details, 1, wx.EXPAND | wx.ALL, 4)
        right.SetSizer(column)
        splitter.SplitVertically(self.tree, right, self.frame.FromDIP(280))
        splitter.SetMinimumPaneSize(self.frame.FromDIP(120))
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(splitter, 1, wx.EXPAND)
        self.status = WorkbenchStatusBar(
            self.frame,
            panel,
            self.provider.status_cells(self),
            copy_text=self.copy_text,
            show_help=lambda cell: self._say(f"{cell.name}. {cell.help}"),
        )
        outer.Add(self.status.panel, 0, wx.EXPAND)
        panel.SetSizer(outer)
        self.frame.SetStatusBarPane(-1)  # menu help must not overwrite the mirrored cells
        self._build_menu()
        self._build_tree()
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_tree_selected)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, lambda _e: self.list.SetFocus())
        self.tree.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self.show_node_menu())
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_row_selected)
        self.list.Bind(wx.EVT_LIST_ITEM_DESELECTED, lambda _e: self.status.refresh())
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self.default_action())
        self.list.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self.show_row_menu())
        self.filter.Bind(wx.EVT_TEXT_ENTER, lambda _e: self.apply_filter())

    def _build_menu(self) -> None:
        wx = self._wx
        bar = wx.MenuBar()
        for spec in self.provider.menu:
            menu = wx.Menu()
            for row in spec.rows:
                if row is None:
                    menu.AppendSeparator()
                    continue
                item = menu.Append(wx.ID_ANY, f"{row.label}\t{row.key}", row.help)
                self.frame.Bind(wx.EVT_MENU, lambda _e, c=row.command_id: self.run(c), item)
            bar.Append(menu, spec.title)
        self.frame.SetMenuBar(bar)

    def _build_tree(self) -> None:
        tree, spec = self.tree, self.provider.tree
        tree.DeleteAllItems()
        self._items.clear()
        root = tree.AddRoot("Workbench")

        def add(parent: Any, node: NodeSpec, ref: NodeRef) -> None:
            item = tree.AppendItem(
                parent, node.label if node.parent or not ref.instance else ref.instance
            )
            tree.SetItemData(item, ref)
            self._items[ref] = item
            if node.template:
                for instance in self.provider.instances(node.template):
                    add_template(item, node.template, instance)
            group = (
                spec.children(node.key, template=ref.template)
                if ref.template
                else spec.children(node.key)
            )
            for child in group:
                add(item, child, NodeRef(ref.template, child.key, ref.instance))

        def add_template(parent: Any, template: str, instance: str) -> None:
            for top in spec.children(None, template=template):
                add(parent, top, NodeRef(template, top.key, instance))

        for node in spec.roots():
            add(root, node, NodeRef("", node.key))

    # -- reading the model --------------------------------------------------------

    def node(self, ref: NodeRef) -> NodeSpec:
        spec = self.provider.tree
        return spec.template_node(ref.template, ref.key) if ref.template else spec.node(ref.key)

    def selected_indices(self) -> list[int]:
        found, index = [], self.list.GetFirstSelected()
        while index != -1:
            found.append(index)
            index = self.list.GetNextSelected(index)
        return [i for i in found if 0 <= i < len(self.rows)]

    def selected_row(self) -> object | None:
        chosen = self.selected_indices()
        return self.rows[chosen[0]] if chosen else None

    def where(self) -> str:
        """Alt+1's words: the tree path, and the filter in effect."""
        if self.current is None:
            return "Nowhere yet"
        labels: list[str] = []
        item = self._items.get(self.current)
        while item is not None and item.IsOk() and item != self.tree.GetRootItem():
            labels.insert(0, self.tree.GetItemText(item))
            item = self.tree.GetItemParent(item)
        filtered = "" if self.query.is_empty else f", filtered to {describe(self.query)}"
        return ", ".join(labels) + filtered

    # -- moving -------------------------------------------------------------------

    def select(self, ref: NodeRef, *, remember: bool = True) -> bool:
        """Select *ref*'s node in the tree (which loads it). False when it is not there."""
        item = self._items.get(ref)
        if item is None:
            return False
        self._navigating = not remember
        try:
            if self.tree.GetSelection() == item:
                self._show_node(ref, remember=remember)
            else:
                self.tree.SelectItem(item)
                self.tree.EnsureVisible(item)
        finally:
            self._navigating = False
        return True

    def _on_tree_selected(self, event: Any) -> None:
        item = event.GetItem()
        ref = self.tree.GetItemData(item) if item.IsOk() else None
        if isinstance(ref, NodeRef):
            self._show_node(ref, remember=not self._navigating)

    def _show_node(self, ref: NodeRef, *, remember: bool) -> None:
        if remember and self.current is not None and self.current != ref:
            self.history.append(self.current)
            self.forward.clear()
        self.current = ref
        node = self.node(ref)
        self.details.ChangeValue(self.provider.node_help(ref, node))
        self._set_columns(node)
        self.rows, self._loaded = [], []
        self.list.DeleteAllItems()
        reason = self.provider.unavailable(ref, node)
        if reason or not node.loader:
            if reason:
                self.details.ChangeValue(f"{self.provider.node_help(ref, node)}\n\n{reason}")
            self.loading = False
            self.status.refresh()
            return
        self.reload()

    def back(self) -> None:
        if not self.history:
            self._say("Nothing to go back to.")
            return
        if self.current is not None:
            self.forward.append(self.current)
        self.select(self.history.pop(), remember=False)

    def go_forward(self) -> None:
        if not self.forward:
            self._say("Nothing to go forward to.")
            return
        if self.current is not None:
            self.history.append(self.current)
        self.select(self.forward.pop(), remember=False)

    def go_parent(self) -> None:
        item = self.tree.GetSelection()
        parent = self.tree.GetItemParent(item) if item.IsOk() else None
        if parent is None or not parent.IsOk() or parent == self.tree.GetRootItem():
            return
        self.tree.SelectItem(parent)
        self.tree.SetFocus()

    def go(self, command_id: str) -> None:
        template, key = self.provider.go_nodes[command_id]
        instance = next(iter(self.provider.instances(template)), "") if template else ""
        if template and not instance:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return
        if self.select(NodeRef(template, key, instance)):
            self.tree.SetFocus()

    def panes(self) -> list[Any]:
        return [self.tree, self.filter, self.list, self.details]

    def cycle_pane(self, step: int) -> None:
        """F6 / Shift+F6: tree, filter, list, details, then the status bar."""
        focused = self._wx.Window.FindFocus()
        panes = self.panes()
        index = (
            len(panes)
            if self.status.has_focus()
            else next((i for i, pane in enumerate(panes) if pane is focused), -1)
        )
        target = (index + step) % (len(panes) + 1)
        if target == len(panes) and self.status.enter(focused):
            return
        panes[target % len(panes)].SetFocus()

    # -- loading ------------------------------------------------------------------

    def _set_columns(self, node: NodeSpec) -> None:
        self.list.ClearAll()
        self._columns = self.provider.columns(node)
        for index, name in enumerate(self._columns or ("name",)):
            self.list.InsertColumn(index, name.replace("_", " ").capitalize())

    def reload(self) -> None:
        ref = self.current
        if ref is None:
            return
        node = self.node(ref)
        if not node.loader:
            return
        self._generation += 1
        generation, query = self._generation, self.query
        self.loading = True
        self.status.refresh()
        self._run_background(
            f"Workbench {node.key}",
            lambda: self.provider.load(ref, node, query),
            lambda rows: self._loaded_rows(generation, rows),
            lambda error: self._load_failed(generation, node, error),
        )

    def _loaded_rows(self, generation: int, rows: list[object]) -> None:
        if generation != self._generation:
            return  # a stale answer for a node somebody already left
        import time

        self.loading = False
        self.loaded_at = time.strftime("%H:%M")
        self._loaded = list(rows)
        self._fill_list()

    def _load_failed(self, generation: int, node: NodeSpec, error: BaseException) -> None:
        if generation != self._generation:
            return
        self.loading = False
        self.status.refresh()
        message = f"Could not load {node.label}: {error}"
        self.details.ChangeValue(message)
        self._say(message)

    def _fill_list(self) -> None:
        words = self.query.words
        columns = self._columns or ("name",)
        self.rows = [
            row
            for row in self._loaded
            if not words or matches_words(" ".join(self.provider.cells(row, columns)), words)
        ]
        self.list.DeleteAllItems()
        for index, row in enumerate(self.rows):
            cells = self.provider.cells(row, columns)
            self.list.InsertItem(index, cells[0] if cells else "")
            for column, text in enumerate(cells[1:], start=1):
                self.list.SetItem(index, column, text)
        if self.rows:
            self.list.Select(0)
            self.list.Focus(0)
        self.status.refresh()

    def apply_filter(self) -> None:
        """Enter in the filter box: words filter here, qualifiers ask the service."""
        before = self.query
        self.query = parse(self.filter.GetValue())
        if self.query.conditions != before.conditions:
            self.reload()
        else:
            self._fill_list()
        self._say(f"{len(self.rows)} shown." if not self.loading else "Filtering.")

    def clear_filter(self) -> None:
        self.filter.ChangeValue("")
        self.apply_filter()

    # -- acting -------------------------------------------------------------------

    def _on_row_selected(self, _event: Any) -> None:
        row = self.selected_row()
        if row is not None:
            self.details.ChangeValue(self.provider.detail(row))
        self.status.refresh()

    def row_actions(self, row: object) -> tuple[list[ActionRow], list[ActionRow]]:
        assert self.current is not None
        return self.provider.actions.menu_for(self.provider.row_type(self.node(self.current), row))

    def default_action(self) -> None:
        row = self.selected_row()
        if row is None or self.current is None:
            return
        top, _more = self.row_actions(row)
        self.run(top[0].command_id)

    def can_run(self, command_id: str) -> bool:
        verb = command_id.rsplit(".", 1)[-1]
        return verb in _FRAME_VERBS or self.provider.supports(command_id)

    def run(self, command_id: str) -> None:
        """Do *command_id*: a menu row, a context-menu row or a key."""
        verb = command_id.rsplit(".", 1)[-1]
        actions: dict[str, Callable[[], None]] = {
            "next_pane": lambda: self.cycle_pane(1),
            "previous_pane": lambda: self.cycle_pane(-1),
            "back": self.back,
            "forward": self.go_forward,
            "go_parent": self.go_parent,
            "refresh": self.reload,
            "filter": self.filter.SetFocus,
            "properties": self.show_properties,
            "copy_link": self.copy_link,
            "open_on_github": self.open_in_browser,
            "where_am_i": lambda: self._say(self.where()),
            "say_selection": self.say_selection,
            "close": self.frame.Close,
            "switch_to_editor": self.switch_to_editor,
            "help_view": self.show_help,
            "open_address": self.open_address,
        }
        if command_id in self.provider.go_nodes:
            self.go(command_id)
        elif verb in actions:
            actions[verb]()
        elif self.current is not None and self.provider.run(
            command_id, self.current, self.selected_row()
        ):
            return
        else:
            self._say("Not in this preview of the Workbench yet. GitHub Items still has it.")

    # -- keys and closing ---------------------------------------------------------

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        focused = wx.Window.FindFocus()
        if self.status.has_focus():
            event.Skip()
            return
        if code == wx.WXK_ESCAPE and not event.HasAnyModifiers():
            if self.filter.GetValue():
                self.clear_filter()
            else:
                self.back()
            return
        if code == wx.WXK_BACK and focused in (self.tree, self.list):
            self.back()
            return
        event.Skip()

    def _say(self, text: str) -> None:
        self._announce(text)

    def _task_manager_runner(self) -> Background:
        from quill.stability.task_manager import TaskManager

        manager = TaskManager(max_workers=2)
        self._task_manager = manager

        def run(
            name: str,
            work: Callable[[], Any],
            done: Callable[[Any], None],
            failed: Callable[[BaseException], None],
        ) -> None:
            manager.submit(
                name,
                lambda **_kwargs: work(),
                on_success=lambda _op, result: done(result),
                on_failure=lambda _op, error: failed(error),
            )

        return run

    def show(self, ref: NodeRef | None = None) -> None:
        self.frame.Show()
        self.frame.Raise()
        start = ref or NodeRef("", self.provider.tree.roots()[0].key)
        if not self.select(start):
            self.select(NodeRef("", self.provider.tree.roots()[0].key))
        self.tree.SetFocus()

    def _on_close(self, event: Any) -> None:
        manager = getattr(self, "_task_manager", None)
        if manager is not None:
            manager.shutdown(wait=False, cancel_pending=True)
        try:
            self.provider.close()
        finally:
            if self._on_closed is not None:
                self._on_closed()
            event.Skip()
