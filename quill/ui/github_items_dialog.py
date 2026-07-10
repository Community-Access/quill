"""Modal GitHub items viewer: issues, PRs, branches, commits, tags, releases,
and workflow runs (#924).

A list-over-detail dialog modeled on GHManage (https://github.com/kellylford/GHManage)
-- the reference viewer -- adapted to Quill's conventions:

- Modal, shown via ``show_modal_dialog`` + ``apply_modal_ids`` (never ShowModal).
- Transport is the wx-free :class:`~quill.core.github.items_provider.GitHubItemsProvider`
  (PyGithub). The mixin constructs the provider (after consent + token + Safe
  Mode checks); this dialog only fetches and renders.
- All fetches run on daemon threads and update the UI via ``wx.CallAfter``
  (``# GATE-40-OK``). The UI thread never blocks on the network.
- Accessibility (first-class): every control has a ``SetName``; a Quick/Full
  list mode (GHManage parity) spells out ``col: value`` per cell in Full mode so
  a screen reader reads a self-describing line; selection announces the row;
  Alt+N/Alt+P jumps between comments in the details box; Enter opens in the
  browser, and on a branch row drills into that branch's commits.
- v1 is read-only. Mutating actions (close/reopen/comment) are out of scope.

The wx-free view-model formatting (cells, details, comment positions) lives in
:mod:`quill.ui.github_items_view` so it is unit-testable without a display.
"""

from __future__ import annotations

import threading
import webbrowser
from typing import TYPE_CHECKING

from quill.core.github.items_provider import (
    DEFAULT_PAGE_LIMIT,
    GitHubBranch,
    GitHubItem,
    GitHubItemsError,
    GitHubItemsProvider,
)
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.github_items_view import (
    SORT_ORDERS,
    VIEW_BRANCHES,
    VIEW_COLUMNS,
    VIEW_COMMITS,
    VIEW_ISSUES,
    VIEW_RELEASES,
    VIEW_RUNS,
    VIEW_TAGS,
    VIEWS,
    item_detail,
    model_detail,
    model_label,
    model_url,
    row_cells,
    sort_items,
    view_label,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class GitHubItemsDialog:
    """Modal list-over-detail viewer for a repository's GitHub items."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        *,
        initial_repo: str = "",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._announce = announce_cb or (lambda _m: None)
        self._repo = initial_repo.strip()
        self._view = VIEW_ISSUES
        self._show = "both"  # issues / prs / both (issues view only)
        self._state = "open"  # open / closed / all (issues view only)
        self._sort = "number_desc"
        self._list_mode = "quick"  # "quick" or "full" (GHManage parity)
        self._page = 1  # page cap = page * DEFAULT_PAGE_LIMIT for "View more"
        self._rows: list[object] = []
        self._drill_branch: str | None = None
        # Per-selection comment thread + positions for Alt+N/Alt+P navigation.
        self._comments: list[dict[str, str]] = []
        self._comment_positions: list[tuple[int, int]] = []
        self._current_comment = -1
        self._comment_target: tuple[str, int] | None = None  # (repo, number) loading

        self.dialog = wx.Dialog(
            parent,
            title="GitHub Items",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((720, 520))
        self.dialog.SetSize((820, 600))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        # Repository row
        repo_row = wx.BoxSizer(wx.HORIZONTAL)
        repo_row.Add(
            wx.StaticText(panel, label="Repository (owner/repo):"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._repo_ctrl = wx.TextCtrl(panel, value=self._repo, style=wx.TE_PROCESS_ENTER)
        self._repo_ctrl.SetName("Repository in owner slash repo format")
        self._load_btn = wx.Button(panel, label="Load")
        self._load_btn.SetName("Load repository")
        repo_row.Add(self._repo_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        repo_row.Add(self._load_btn)
        root.Add(repo_row, 0, wx.EXPAND | wx.ALL, 10)

        # Filter row: View / Show / State / Sort / List mode
        filt = wx.BoxSizer(wx.HORIZONTAL)
        filt.Add(wx.StaticText(panel, label="&View:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self._view_choice = wx.Choice(panel, choices=[label for _, label in VIEWS])
        self._view_choice.SetName("View")
        self._view_choice.SetSelection(0)
        filt.Add(self._view_choice, 0, wx.RIGHT, 10)

        filt.Add(wx.StaticText(panel, label="&Show:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self._show_choice = wx.Choice(panel, choices=["Both", "Issues", "PRs"])
        self._show_choice.SetName("Show issues PRs or both")
        self._show_choice.SetSelection(0)
        filt.Add(self._show_choice, 0, wx.RIGHT, 10)

        filt.Add(wx.StaticText(panel, label="&State:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self._state_choice = wx.Choice(panel, choices=["Open", "Closed", "All"])
        self._state_choice.SetName("State filter")
        self._state_choice.SetSelection(0)
        filt.Add(self._state_choice, 0, wx.RIGHT, 10)

        filt.Add(wx.StaticText(panel, label="&Sort:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self._sort_choice = wx.Choice(panel, choices=[label for _, label in SORT_ORDERS])
        self._sort_choice.SetName("Sort order")
        self._sort_choice.SetSelection(0)
        filt.Add(self._sort_choice, 0, wx.RIGHT, 10)

        filt.Add(
            wx.StaticText(panel, label="&List mode:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self._mode_choice = wx.Choice(panel, choices=["Quick (compact)", "Full (field names)"])
        self._mode_choice.SetName("List mode")
        self._mode_choice.SetSelection(0)
        filt.Add(self._mode_choice, 1, wx.EXPAND)
        root.Add(filt, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # List
        self._list = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SIMPLE,
        )
        self._list.SetName("GitHub items list")
        root.Add(self._list, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Details
        root.Add(wx.StaticText(panel, label="Details"), 0, wx.LEFT | wx.TOP, 6)
        self._details = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        self._details.SetName("Details")
        root.Add(self._details, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        # Status + buttons
        self._status = wx.StaticText(panel, label="Enter a repository and click Load.")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._refresh_btn = wx.Button(panel, label="Refresh")
        self._refresh_btn.SetName("Refresh")
        self._more_btn = wx.Button(panel, label="View More")
        self._more_btn.SetName("View more results")
        self._open_btn = wx.Button(panel, label="Open in Browser")
        self._open_btn.SetName("Open selected item in browser")
        self._goto_btn = wx.Button(panel, label="Go To #...")
        self._goto_btn.SetName("Go to issue or PR by number")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        cancel_btn.SetName("Close dialog")
        for b in (self._refresh_btn, self._more_btn, self._open_btn, self._goto_btn):
            btn_row.Add(b, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        self.dialog.SetSizer(root)

        # Bindings
        self._load_btn.Bind(wx.EVT_BUTTON, self._on_load)
        self._repo_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_load)
        self._view_choice.Bind(wx.EVT_CHOICE, self._on_view_changed)
        self._show_choice.Bind(wx.EVT_CHOICE, lambda _e: self._reload())
        self._state_choice.Bind(wx.EVT_CHOICE, lambda _e: self._reload())
        self._sort_choice.Bind(wx.EVT_CHOICE, lambda _e: self._reload())
        self._mode_choice.Bind(wx.EVT_CHOICE, self._on_mode_changed)
        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_activate)
        self._list.Bind(wx.EVT_LIST_KEY_DOWN, self._on_list_key)
        self._refresh_btn.Bind(wx.EVT_BUTTON, lambda _e: self._reload())
        self._more_btn.Bind(wx.EVT_BUTTON, self._on_more)
        self._open_btn.Bind(wx.EVT_BUTTON, lambda _e: self._open_selected())
        self._goto_btn.Bind(wx.EVT_BUTTON, self._on_goto)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._apply_filter_enablement()
        self._rebuild_columns()

    # ------------------------------------------------------------------
    # Public entry point

    def show(self) -> None:
        wx = self._wx
        # Kick off the initial load before entering the modal loop; the worker
        # posts its results via wx.CallAfter, which the modal loop pumps.
        if self._repo:
            self._on_load(None)
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, "GitHub Items", announce=self._announce)
        finally:
            self.dialog.Destroy()

    # ------------------------------------------------------------------
    # Loading

    def _on_load(self, _event: object) -> None:
        full_name = self._repo_ctrl.GetValue().strip()
        if not full_name:
            self._set_status("Enter a repository name (owner/repo) first.")
            self._repo_ctrl.SetFocus()
            return
        if "/" not in full_name:
            self._set_status("Repository must be in owner/repo format.")
            self._repo_ctrl.SetFocus()
            return
        self._repo = full_name
        self._page = 1
        self._reload()

    def _reload(self) -> None:
        if not self._repo:
            return
        limit = self._page * DEFAULT_PAGE_LIMIT
        self._set_loading(True)
        self._set_status(f"Loading {self._repo} ({view_label(self._view)})...")
        self._clear_list()
        threading.Thread(  # GATE-40-OK: items loader; bounded by limit (page * 30).
            target=self._load_worker,
            args=(self._repo, self._view, self._show, self._state, limit),
            daemon=True,
        ).start()

    def _load_worker(self, repo: str, view: str, show: str, state: str, limit: int) -> None:
        wx = self._wx
        try:
            rows = self._fetch(repo, view, show, state, limit)
        except GitHubItemsError as exc:
            wx.CallAfter(self._on_load_error, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            wx.CallAfter(self._on_load_error, str(exc))
            return
        wx.CallAfter(self._on_rows_loaded, rows, view)

    def _fetch(self, repo: str, view: str, show: str, state: str, limit: int) -> list[object]:
        if view == VIEW_ISSUES:
            out: list[object] = []
            if show in ("issues", "both"):
                out += self._provider.fetch_issues(repo, state=state, limit=limit)
            if show in ("prs", "both"):
                out += self._provider.fetch_pulls(repo, state=state, limit=limit)
            return sort_items([r for r in out if isinstance(r, GitHubItem)], self._sort)
        if view == VIEW_BRANCHES:
            return self._provider.fetch_branches(repo, limit=limit)
        if view == VIEW_COMMITS:
            return self._provider.fetch_commits(repo, branch=self._drill_branch, limit=limit)
        if view == VIEW_TAGS:
            return self._provider.fetch_tags(repo, limit=limit)
        if view == VIEW_RELEASES:
            return self._provider.fetch_releases(repo, limit=limit)
        if view == VIEW_RUNS:
            return self._provider.fetch_workflow_runs(repo, limit=limit)
        return []

    def _on_rows_loaded(self, rows: list[object], view: str) -> None:
        if view != self._view:
            return  # a stale worker for a view the user already left
        self._rows = rows
        self._populate_list()
        self._set_loading(False)
        count = len(rows)
        noun = view_label(self._view)
        self._set_status(
            f"{self._repo} - {count} {noun}{'' if count == 1 else 's'}. "
            "Enter=open/drill  Ctrl+R=refresh  Ctrl+O=browser  Ctrl+G=go to  "
            f"Alt+N/Alt+P=comment  List={self._list_mode}"
        )
        if count:
            self._list.SetFocus()
            self._list.Select(0)
            self._list.Focus(0)
            self._show_detail(0)

    def _on_load_error(self, message: str) -> None:
        self._set_loading(False)
        self._set_status(f"Error: {message}")

    def _on_more(self, _event: object) -> None:
        self._page += 1
        self._reload()

    # ------------------------------------------------------------------
    # List rendering + list mode

    def _rebuild_columns(self) -> None:
        self._list.DeleteAllItems()
        self._list.DeleteAllColumns()
        for i, col in enumerate(VIEW_COLUMNS[self._view]):
            self._list.InsertColumn(i, col, width=140 if col == "title" else 90)

    def _populate_list(self) -> None:
        self._list.DeleteAllItems()
        columns = VIEW_COLUMNS[self._view]
        full = self._list_mode == "full"
        for i, model in enumerate(self._rows):
            cells = row_cells(model, columns, full=full)
            self._list.InsertItem(i, cells[0])
            for j, value in enumerate(cells[1:], start=1):
                self._list.SetItem(i, j, value)

    def _on_mode_changed(self, _event: object) -> None:
        self._list_mode = "full" if self._mode_choice.GetSelection() == 1 else "quick"
        self._populate_list()

    def _clear_list(self) -> None:
        self._rows = []
        self._list.DeleteAllItems()
        self._details.Clear()
        self._comments = []
        self._comment_positions = []
        self._current_comment = -1

    # ------------------------------------------------------------------
    # Selection / details / comment navigation

    def _on_select(self, event: object) -> None:
        idx = getattr(event, "GetIndex", lambda: -1)()
        self._show_detail(idx)
        if self._list_mode == "full" and 0 <= idx < len(self._rows):
            cells = row_cells(self._rows[idx], VIEW_COLUMNS[self._view], full=True)
            self._announce(", ".join(c for c in cells if c))

    def _show_detail(self, idx: int) -> None:
        self._comments = []
        self._comment_positions = []
        self._current_comment = -1
        if idx < 0 or idx >= len(self._rows):
            self._details.Clear()
            return
        model = self._rows[idx]
        if isinstance(model, GitHubItem):
            text, positions = item_detail(model, [])
            self._details.SetValue(text)
            self._comment_positions = positions
            self._fetch_comments(idx, model)
        else:
            self._details.SetValue(model_detail(model))

    def _fetch_comments(self, idx: int, item: GitHubItem) -> None:
        # Off-thread so the UI never blocks on the network; comments append to
        # the detail box when they arrive and populate the Alt+N/Alt+P map.
        self._comment_target = (self._repo, item.number)

        def worker() -> None:
            wx = self._wx
            target = self._comment_target
            try:
                comments = self._provider.fetch_issue_comments(self._repo, item.number)
            except GitHubItemsError as exc:
                wx.CallAfter(self._on_comment_error, str(exc))
                return
            wx.CallAfter(self._on_comments_loaded, idx, target, comments)

        threading.Thread(  # GATE-40-OK: per-selection comment thread fetch.
            target=worker, daemon=True
        ).start()

    def _on_comments_loaded(
        self, idx: int, target: tuple[str, int], comments: list[dict[str, str]]
    ) -> None:
        # Only apply if the selection that started the fetch is still current.
        if target != self._comment_target:
            return
        if idx >= len(self._rows) or not isinstance(self._rows[idx], GitHubItem):
            return
        item = self._rows[idx]
        text, positions = item_detail(item, comments)
        self._details.SetValue(text)
        self._comments = comments
        self._comment_positions = positions
        self._current_comment = -1
        if comments:
            self._announce(f"{len(comments)} comments loaded. Alt+N to jump to the first.")

    def _on_comment_error(self, message: str) -> None:
        # Non-fatal: the detail box already has the body; just note the miss.
        self._announce(f"Could not load comments: {message}")

    def _navigate_comment(self, direction: int) -> None:
        if not self._comment_positions:
            self._announce("No comments to navigate.")
            return
        new_idx = self._current_comment + direction
        if new_idx < 0:
            self._announce("Already at first comment.")
            return
        if new_idx >= len(self._comment_positions):
            self._announce("Already at last comment.")
            return
        self._current_comment = new_idx
        line, length = self._comment_positions[new_idx]
        start = self._line_to_position(line)
        end = self._line_to_position(line + length)
        self._details.SetFocus()
        self._details.SetSelection(start, end)
        self._details.ShowPosition(start)
        self._announce(f"Comment {new_idx + 1} of {len(self._comment_positions)}")

    def _line_to_position(self, line: int) -> int:
        text = self._details.GetValue()
        pos = 0
        current = 0
        for ch in text:
            if current >= line:
                break
            if ch == "\n":
                current += 1
            pos += 1
        return pos

    # ------------------------------------------------------------------
    # Activation / drill-down / open in browser / go to

    def _on_activate(self, _event: object) -> None:
        idx = self._list.GetFirstSelected()
        if idx < 0 or idx >= len(self._rows):
            return
        model = self._rows[idx]
        if self._view == VIEW_BRANCHES and isinstance(model, GitHubBranch):
            self._drill_branch = model.name
            self._switch_view(VIEW_COMMITS)
            return
        url = model_url(model)
        if url:
            webbrowser.open(url)
            self._announce(f"Opened {model_label(model)} in browser")

    def _open_selected(self) -> None:
        idx = self._list.GetFirstSelected()
        if idx < 0 or idx >= len(self._rows):
            self._announce("Select an item first.")
            return
        url = model_url(self._rows[idx])
        if url:
            webbrowser.open(url)
            self._announce(f"Opened {model_label(self._rows[idx])} in browser")

    def _on_goto(self, _event: object) -> None:
        wx = self._wx
        if self._view != VIEW_ISSUES or not self._rows:
            self._announce("Go To works in the Issues & PRs view after loading.")
            return
        dlg = wx.NumberEntryDialog(
            self.dialog, "Enter the issue or PR number:", "Go To #", "Go To", 1, 1, 1_000_000
        )
        if self._show_modal(dlg, "Go To") != wx.ID_OK:
            dlg.Destroy()
            return
        number = dlg.GetValue()
        dlg.Destroy()
        for i, model in enumerate(self._rows):
            if isinstance(model, GitHubItem) and model.number == number:
                self._list.SetFocus()
                self._list.Select(i)
                self._list.Focus(i)
                self._show_detail(i)
                self._announce(f"Jumped to #{number} - {model.title}")
                return
        self._announce(f"#{number} not found in the current list.")

    def _show_modal(self, dlg: object, title: str) -> int:
        # Stock wx dialogs (NumberEntryDialog) already ship accessible OK/Cancel
        # buttons with native Escape handling, so they need no apply_modal_ids
        # (the dialog-button contract is for custom dialogs). Mirror the
        # Mastodon _prompt pattern: show_modal_dialog alone.
        return show_modal_dialog(dlg, title, announce=self._announce)

    # ------------------------------------------------------------------
    # View switching + filter enablement

    def _on_view_changed(self, _event: object) -> None:
        view = VIEWS[self._view_choice.GetSelection()][0]
        if view == self._view:
            return
        self._drill_branch = None  # leaving Branches cancels any drill target
        self._switch_view(view)

    def _switch_view(self, view: str) -> None:
        self._view = view
        self._page = 1
        self._rebuild_columns()
        self._apply_filter_enablement()
        self._reload()

    def _apply_filter_enablement(self) -> None:
        issues_view = self._view == VIEW_ISSUES
        for ctrl in (self._show_choice, self._state_choice, self._sort_choice):
            ctrl.Enable(issues_view)

    # ------------------------------------------------------------------
    # Keyboard

    def _on_list_key(self, event: object) -> None:
        key = event.GetKeyCode()
        if key == ord("R"):
            self._reload()
        elif key == ord("M"):
            self._cycle_list_mode()
        else:
            event.Skip()

    def _cycle_list_mode(self) -> None:
        self._mode_choice.SetSelection(1 if self._list_mode == "quick" else 0)
        self._on_mode_changed(None)

    def _on_char_hook(self, event: object) -> None:
        wx = self._wx
        key = event.GetKeyCode()
        mod = event.GetModifiers()
        if key == ord("R") and mod == wx.MOD_CONTROL:
            self._reload()
        elif key == ord("O") and mod == wx.MOD_CONTROL:
            self._open_selected()
        elif key == ord("G") and mod == wx.MOD_CONTROL:
            self._on_goto(None)
        elif key == ord("N") and mod == wx.MOD_ALT:
            self._navigate_comment(1)
        elif key == ord("P") and mod == wx.MOD_ALT:
            self._navigate_comment(-1)
        else:
            event.Skip()

    # ------------------------------------------------------------------
    # Helpers

    def _set_loading(self, loading: bool) -> None:
        self._load_btn.Enable(not loading)
        self._repo_ctrl.Enable(not loading)
        self._refresh_btn.Enable(not loading)
        self._more_btn.Enable(not loading)

    def _set_status(self, message: str) -> None:
        self._status.SetLabel(message)
        parent = self._status.GetParent()
        if parent is not None:
            parent.Layout()
        if message:
            self._announce(message)


__all__ = ["GitHubItemsDialog"]
