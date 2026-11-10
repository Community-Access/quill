"""Accessible list/detail browser and editor for GitHub Projects v2."""

from __future__ import annotations

import threading
import webbrowser
from typing import TYPE_CHECKING

from quill.core.github.projects import (
    GitHubProject,
    GitHubProjectBoard,
    GitHubProjectItem,
    GitHubProjectsError,
    fetch_project,
    list_projects,
)
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    dialog_alive,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size
from quill.ui.github_projects_dialog_actions import GitHubProjectsActionsMixin
from quill.ui.spoken_name import set_spoken_name

if TYPE_CHECKING:
    from quill.core.github.items_provider import GitHubItemsProvider


class GitHubProjectsDialog(GitHubProjectsActionsMixin):
    """Browse projects as a linear list and edit supported fields/relationships."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        *,
        initial_repo: str = "",
        announce_cb=None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._token = provider.token or ""
        self._announce = announce_cb or (lambda _message: None)
        self._projects: list[GitHubProject] = []
        self._board: GitHubProjectBoard | None = None
        self._items: list[GitHubProjectItem] = []
        self._selected_item_id = ""
        self._load_token = 0
        self._write_token = 0
        self._write_in_flight = False
        self.dialog = wx.Dialog(
            parent,
            title="GitHub Projects and Dependencies",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 760, 520))
        self.dialog.SetSize(dip_size(self.dialog, 900, 700))
        root = wx.BoxSizer(wx.VERTICAL)

        repo_row = wx.BoxSizer(wx.HORIZONTAL)
        repo_row.Add(
            wx.StaticText(self.dialog, label="Repository owner/repo:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._repo = wx.TextCtrl(self.dialog, value=initial_repo, style=wx.TE_PROCESS_ENTER)
        self._repo.SetHelpText("The repository, as owner/name. Enter loads its Projects.")
        self._repo.SetName("Repository whose GitHub Projects to load")
        repo_row.Add(self._repo, 1, wx.RIGHT, 6)
        self._load_btn = wx.Button(self.dialog, label="&Load Projects")
        self._load_btn.SetHelpText("Load the repository named in the box above.")
        self._load_btn.SetName("Load Projects for this repository")
        repo_row.Add(self._load_btn)
        root.Add(repo_row, 0, wx.EXPAND | wx.ALL, 8)

        project_row = wx.BoxSizer(wx.HORIZONTAL)
        project_row.Add(
            wx.StaticText(self.dialog, label="&Project:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._project_choice = wx.Choice(self.dialog, choices=[])
        self._project_choice.SetHelpText(
            "The repository's Project boards. Choose one to list its items."
        )
        self._project_choice.SetName("GitHub Project to view")
        project_row.Add(self._project_choice, 1)
        root.Add(project_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        root.Add(wx.StaticText(self.dialog, label="Project items"), 0, wx.LEFT, 8)
        self._list = wx.ListBox(self.dialog, choices=[])
        self._list.SetHelpText("The board's items. Arrow to one to read it below.")
        self._list.SetName("Project items; ready work is marked in each row")
        set_spoken_name(self._list, "GitHub Project items")
        root.Add(self._list, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        root.Add(
            wx.StaticText(self.dialog, label="Selected item and dependencies"),
            0,
            wx.LEFT | wx.TOP,
            8,
        )
        self._details = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        self._details.SetHelpText("The selected item in full, read-only.")
        self._details.SetName("Selected project item fields, blockers, and sub-issues")
        root.Add(self._details, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._status = wx.StaticText(
            self.dialog, label="Choose a repository and load its Projects."
        )
        self._status.SetName("GitHub Projects status")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        self._next_btn = wx.Button(self.dialog, label="&Next Unblocked")
        self._next_btn.SetHelpText("Move to the next item that nothing is blocking.")
        self._next_btn.SetName("Select the next open issue or pull request without an open blocker")
        self._open_btn = wx.Button(self.dialog, label="Open on GitHub")
        self._open_btn.SetHelpText("Open the selected item on GitHub in your browser.")
        self._open_btn.SetName("Open the selected project item on GitHub")
        self._actions_btn = wx.Button(self.dialog, label="&Actions...")
        self._actions_btn.SetHelpText("More things to do with the selected item, as a menu.")
        self._actions_btn.SetName("Edit project fields, blockers, and sub-issues")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetHelpText("Close this window. Escape does the same.")
        close_btn.SetName("Close GitHub Projects")
        for button in (self._next_btn, self._open_btn, self._actions_btn):
            actions.Add(button, 0, wx.RIGHT, 6)
        actions.AddStretchSpacer()
        actions.Add(close_btn)
        root.Add(actions, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)

        self._repo.Bind(wx.EVT_TEXT_ENTER, self._load_projects)
        self._load_btn.Bind(wx.EVT_BUTTON, self._load_projects)
        self._project_choice.Bind(wx.EVT_CHOICE, self._load_board)
        self._list.Bind(wx.EVT_LISTBOX, self._select)
        apply_listbox_activation(self._list, self._open)
        self._list.Bind(wx.EVT_CONTEXT_MENU, self._context_menu)
        self._actions_btn.Bind(wx.EVT_BUTTON, self._context_menu)
        self._next_btn.Bind(wx.EVT_BUTTON, self._next_unblocked)
        self._open_btn.Bind(wx.EVT_BUTTON, self._open)
        self._next_btn.Enable(False)
        self._open_btn.Enable(False)
        self._actions_btn.Enable(False)

    def show(self) -> None:
        wx = self._wx
        if self._repo.GetValue().strip():
            self._load_projects(None)
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(
                self.dialog, "GitHub Projects and Dependencies", announce=self._announce
            )
        finally:
            self.dialog.Destroy()

    def _load_projects(self, _event: object) -> None:
        repository = self._repo.GetValue().strip()
        if repository.count("/") != 1:
            self._status.SetLabel("Enter a repository as owner/repo.")
            self._repo.SetFocus()
            return
        self._load_token += 1
        token = self._load_token
        self._status.SetLabel(f"Loading Projects for {repository}...")

        def worker() -> None:
            try:
                result = list_projects(self._token, repository)
                self._wx.CallAfter(
                    self._projects_loaded, token, result.items, result.complete, result.warning, ""
                )
            except GitHubProjectsError as exc:
                self._wx.CallAfter(self._projects_loaded, token, (), False, "", str(exc))

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: explicit GitHub read.

    def _projects_loaded(
        self,
        token: int,
        projects: tuple[GitHubProject, ...],
        complete: bool,
        warning: str,
        error: str,
    ) -> None:
        if token != self._load_token or not dialog_alive(self.dialog):
            return
        self._projects = list(projects)
        self._board = None
        self._items = []
        self._list.Set([])
        self._details.SetValue("")
        self._project_choice.Set([f"{row.title} (#{row.number})" for row in self._projects])
        if error:
            message = f"Could not load Projects: {error}"
        elif not complete:
            message = f"{len(self._projects)} Projects loaded; results may be incomplete. {warning}"
        else:
            message = f"{len(self._projects)} Projects loaded."
        self._status.SetLabel(message)
        self._announce(message)
        if self._projects:
            self._project_choice.SetSelection(0)
            self._load_board(None)

    def _load_board(self, _event: object) -> None:
        index = self._project_choice.GetSelection()
        if index < 0 or index >= len(self._projects):
            return
        selected = self._selected()
        if selected is not None:
            self._selected_item_id = selected.node_id
        project = self._projects[index]
        self._load_token += 1
        token = self._load_token
        self._status.SetLabel(f"Loading {project.title}...")

        def worker() -> None:
            try:
                board = fetch_project(self._token, project.node_id)
                self._wx.CallAfter(self._board_loaded, token, board, "")
            except GitHubProjectsError as exc:
                self._wx.CallAfter(self._board_loaded, token, None, str(exc))

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: explicit board read.

    def _board_loaded(self, token: int, board: GitHubProjectBoard | None, error: str) -> None:
        if token != self._load_token or not dialog_alive(self.dialog):
            return
        self._board = board
        self._items = list(board.items) if board is not None else []
        self._list.Set([_item_label(item) for item in self._items])
        self._details.SetValue("")
        self._next_btn.Enable(bool(board and board.next_unblocked_work))
        self._open_btn.Enable(False)
        self._actions_btn.Enable(bool(self._items))
        if error:
            message = f"Could not load Project: {error}"
        elif board is not None and not board.complete:
            message = f"{len(self._items)} items loaded; the board is incomplete. {board.warning}"
        else:
            message = f"{len(self._items)} items loaded."
        self._status.SetLabel(message)
        self._announce(message)
        if self._items:
            restore = next(
                (i for i, row in enumerate(self._items) if row.node_id == self._selected_item_id),
                0,
            )
            self._list.SetSelection(restore)
            self._select(None)

    def _selected(self) -> GitHubProjectItem | None:
        index = self._list.GetSelection()
        return self._items[index] if 0 <= index < len(self._items) else None

    def _select(self, _event: object) -> None:
        item = self._selected()
        self._selected_item_id = item.node_id if item is not None else ""
        self._details.SetValue(_item_detail(item) if item is not None else "")
        self._open_btn.Enable(bool(item and item.url))
        self._actions_btn.Enable(item is not None)

    def _next_unblocked(self, _event: object) -> None:
        if self._board is None:
            return
        ready = self._board.next_unblocked_work
        if not ready:
            self._announce("No open issue or pull request is currently unblocked.")
            return
        current = self._selected()
        current_index = next(
            (
                index
                for index, row in enumerate(ready)
                if current and row.node_id == current.node_id
            ),
            -1,
        )
        next_item = ready[(current_index + 1) % len(ready)]
        index = next(
            index for index, row in enumerate(self._items) if row.node_id == next_item.node_id
        )
        self._list.SetSelection(index)
        self._select(None)
        self._announce(f"Selected unblocked work: {next_item.title}.")

    def _open(self, _event: object) -> None:
        item = self._selected()
        if item is not None and item.url:
            self._announce(
                "Opened on GitHub." if webbrowser.open(item.url) else "Could not open the link."
            )

    def _context_menu(self, _event: object) -> None:
        item = self._selected()
        if item is None:
            self._announce("Select a project item first.")
            return
        wx = self._wx
        menu = wx.Menu()
        handlers = []

        def add(label: str, callback, enabled: bool = True) -> None:
            item_id = wx.NewIdRef()
            menu.Append(item_id, label)
            menu.Enable(item_id, enabled)
            menu.Bind(wx.EVT_MENU, lambda _event, action=callback: action(), id=item_id)
            handlers.append(item_id)

        add("Open on GitHub", lambda: self._open(None), bool(item.url))
        add("Edit Project Field...", self._edit_field, bool(self._board and self._board.fields))
        is_issue = item.kind == "issue"
        add("Add Blocker...", lambda: self._add_relation("blocked_by"), is_issue)
        add(
            "Remove Blocker...",
            lambda: self._remove_relation("blocked_by"),
            is_issue and bool(item.blocked_by),
        )
        add("Add Sub-issue...", lambda: self._add_relation("sub_issue"), is_issue)
        add(
            "Remove Sub-issue...",
            lambda: self._remove_relation("sub_issue"),
            is_issue and bool(item.sub_issues),
        )
        menu.AppendSeparator()
        add("Refresh Board", lambda: self._load_board(None))
        try:
            self._actions_btn.PopupMenu(menu)
        finally:
            menu.Destroy()


def _item_label(item: GitHubProjectItem) -> str:
    kind = "Issue" if item.kind == "issue" else "PR" if item.kind == "pull_request" else "Draft"
    state = item.state or "Draft"
    readiness = "Blocked" if item.is_blocked else "Ready" if state.casefold() == "open" else state
    suffix = f" [{readiness}]" if item.kind in {"issue", "pull_request"} else ""
    return f"{kind} {item.repository}#{item.number}: {item.title} ({state}){suffix}"


def _item_detail(item: GitHubProjectItem) -> str:
    lines = [_item_label(item)]
    if item.values:
        lines.extend(f"{name}: {value}" for name, value in item.values)
    if item.blocked_by:
        lines.append("Blocked by:")
        lines.extend(
            f"  {row.repository}#{row.number}: {row.title} ({row.state})" for row in item.blocked_by
        )
    if item.blocking:
        lines.append("Blocking:")
        lines.extend(
            f"  {row.repository}#{row.number}: {row.title} ({row.state})" for row in item.blocking
        )
    if item.sub_issues or item.sub_issue_total:
        lines.append(
            f"Sub-issues: {item.sub_issue_completed} of {item.sub_issue_total} complete "
            f"({item.sub_issue_percent:.0f}%)"
        )
        lines.extend(
            f"  {row.repository}#{row.number}: {row.title} ({row.state})" for row in item.sub_issues
        )
    if item.url:
        lines.append(item.url)
    return "\n".join(lines)


__all__ = ["GitHubProjectsDialog"]
