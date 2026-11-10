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
- Unified GitHub Management additions (merged from the GHManage/fastgh
  review): **Pinned repositories** (the Pinned... menu — pin the loaded repo,
  jump to any pinned one), **Favorites** (Ctrl+D bookmarks the selected row;
  the Favorites... menu reopens any bookmark in the browser, across repos),
  **advanced search** (Ctrl+F focuses a repo-scoped search box that takes
  full GitHub search syntax — ``label:bug author:x is:pr`` — over Issues &
  PRs), and **local git sync** (the repository field prefills from the
  current document's own git checkout when it has a GitHub origin remote).
- Batch actions (the Batch... menu: close/reopen/label several checked
  items at once) and single-item write actions (the Actions... menu: new
  issue/PR, merge a PR, delete a branch, re-run a workflow run, and reply
  to/edit/delete a comment on top of the Alt+N/Alt+P navigation) are the
  only writes this dialog makes against GitHub, and every one requires an
  authenticated session -- the anonymous viewer stays fully read-only. Each
  write is named explicitly in its own confirmation before it runs; the
  four highest-consequence ones (merge, delete a branch, and anything else
  that goes through :class:`~quill.ui.github_repo_admin_dialogs.TypedConfirmDialog`)
  require retyping the exact name/number rather than a plain Yes/No.
- Further GHManage parity: **Compare Branches** (Com&pare... / Ctrl+Shift+B,
  Branches view only) shows ahead/behind counts, the commits between two
  branches, and the changed files -- read-only, so it needs no authenticated
  session -- rendered by
  :class:`~quill.ui.github_compare_branches_dialog.GitHubCompareBranchesDialog`.
  **Column selection** (Colu&mns...) toggles which columns are shown per
  view. **Backspace** in the Commits view (reached by pressing Enter on a
  branch) steps back to the Branches list. The repository field accepts a
  pasted GitHub URL or ``git@github.com:`` remote, not just ``owner/repo``
  (:func:`~quill.ui.github_items_view.parse_repo_reference`).

The wx-free view-model formatting (cells, details, comment positions) lives in
:mod:`quill.ui.github_items_view` so it is unit-testable without a display;
the pinned/favorites store is :mod:`quill.core.github.saved_items` and the
checkout detection :mod:`quill.core.github.local_repo`.
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
    GitHubRelease,
    GitHubReleaseAsset,
    GitHubRepoForkInfo,
)
from quill.core.github.references import GitHubReference
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size
from quill.ui.github_items_dialog_ai import GitHubItemsAiMixin
from quill.ui.github_items_dialog_branches import GitHubBranchActionsMixin
from quill.ui.github_items_dialog_copilot import GitHubItemsCopilotMixin
from quill.ui.github_items_dialog_filter import GitHubQuickFilterMixin
from quill.ui.github_items_dialog_housekeeping import GitHubItemsHousekeepingMixin
from quill.ui.github_items_dialog_issue_templates import GitHubIssueTemplatesMixin
from quill.ui.github_items_dialog_menus import GitHubItemsMenusMixin
from quill.ui.github_items_dialog_navigation import GitHubNavigationMixin
from quill.ui.github_items_dialog_reactions import GitHubItemsReactionsMixin
from quill.ui.github_items_dialog_references import GitHubReferenceMixin
from quill.ui.github_items_dialog_releases import GitHubItemsReleaseMixin
from quill.ui.github_items_dialog_repository import GitHubRepositoryToolsMixin
from quill.ui.github_items_dialog_review import GitHubItemsReviewMixin
from quill.ui.github_items_dialog_run_actions import GitHubRunActionsUiMixin
from quill.ui.github_items_dialog_workflows import GitHubWorkflowsMixin
from quill.ui.github_items_view import (
    SORT_ORDERS,
    VIEW_BRANCHES,
    VIEW_COLUMNS,
    VIEW_COMMITS,
    VIEW_ISSUES,
    VIEW_RELEASES,
    VIEW_RUNS,
    VIEW_TAGS,
    VIEW_WORKFLOWS,
    VIEWS,
    item_detail,
    model_detail,
    model_label,
    model_url,
    parse_repo_reference,
    release_drill_status,
    row_cells,
    sort_items,
    view_label,
)
from quill.ui.spoken_name import set_spoken_name

if TYPE_CHECKING:
    from collections.abc import Callable


class GitHubItemsDialog(
    GitHubItemsHousekeepingMixin,
    GitHubReferenceMixin,
    GitHubIssueTemplatesMixin,
    GitHubItemsReleaseMixin,
    GitHubItemsReviewMixin,
    GitHubItemsAiMixin,
    GitHubNavigationMixin,
    GitHubBranchActionsMixin,
    GitHubQuickFilterMixin,
    GitHubWorkflowsMixin,
    GitHubRunActionsUiMixin,
    GitHubRepositoryToolsMixin,
    GitHubItemsMenusMixin,
    GitHubItemsReactionsMixin,
    GitHubItemsCopilotMixin,
):
    """Modal list-over-detail viewer for a repository's GitHub items."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        *,
        initial_repo: str = "",
        initial_reference: GitHubReference | None = None,
        open_file_reference_cb: Callable[[str], None] | None = None,
        announce_cb: Callable[[str], None] | None = None,
        ai_acquire_cb: Callable[[], Callable[[str], str] | None] | None = None,
        start_issue_worktree_cb: Callable[[object, str, int, str, bool], None] | None = None,
        gist_source_cb: Callable[[], tuple[str, str]] | None = None,
        initial_view: str = "",
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._open_file_reference_cb = open_file_reference_cb
        self._announce = announce_cb or (lambda _m: None)
        self._start_issue_worktree_cb = start_issue_worktree_cb
        self._gist_source_cb = gist_source_cb  # Explore's New Gist starts from it
        # Resolves QUILL's AI connection on demand (may prompt; UI thread) and
        # returns a summarize(text) callable safe to run off-thread, or None.
        self._ai_acquire = ai_acquire_cb
        self._repo = initial_repo.strip()
        self._initial_reference = initial_reference
        # A reference decides the view; otherwise the opener's choice (the
        # GitHub menu's Actions Runs and Releases), else Issues.
        known_views = {key for key, _label in VIEWS}
        self._view = (
            VIEW_BRANCHES
            if initial_reference is not None and initial_reference.kind == "branch"
            else initial_view
            if initial_view in known_views
            else VIEW_ISSUES
        )
        self._show = "both"  # issues / prs / both (issues view only)
        self._state = "open"  # open / closed / all (issues view only)
        if initial_reference is not None and initial_reference.kind == "issue":
            self._show = "issues"
            self._state = "all"
        elif initial_reference is not None and initial_reference.kind == "pull_request":
            self._show = "prs"
            self._state = "all"
        self._sort = "number_desc"
        self._list_mode = "quick"  # "quick" or "full" (GHManage parity)
        # Pinned repos + favorites + column choices (GHManage parity),
        # persisted across sessions.
        from quill.core.github.saved_items import GitHubSavedItems

        self._saved = GitHubSavedItems.load()
        # Per-view visible column subset (GHManage parity, Columns... menu);
        # seeded from the saved store, defaulting to every column visible.
        self._visible_columns: dict[str, list[str]] = {
            view: self._saved.get_columns(view, list(cols)) for view, cols in VIEW_COLUMNS.items()
        }
        self._page = 1  # page cap = page * DEFAULT_PAGE_LIMIT for "View more"
        self._rows: list[object] = []
        # The fetched set; self._rows is its quick-filtered view.
        self._unfiltered_rows: list[object] = []
        self._quick_filter_query = ""  # GHManage parity, Ctrl+Shift+F
        self._drill_branch: str | None = None
        # When set, the Releases view shows this release's assets (download
        # counts, most-downloaded first) instead of the releases list; Backspace
        # clears it. Mirrors _drill_branch (Branches -> Commits) but stays within
        # the Releases view slot since assets belong to a specific release.
        self._drill_release: GitHubRelease | None = None
        self._search_query = ""  # non-empty = issues view shows search results
        self._restore_navigation(provider, initial_reference)
        # Per-selection comment thread + positions for Alt+N/Alt+P navigation.
        self._comments: list[dict[str, str]] = []
        self._comment_positions: list[tuple[int, int]] = []
        self._current_comment = -1
        self._comment_target: tuple[str, int] | None = None  # (repo, number) loading
        # Fork/upstream (View Upstream): fetched alongside the items list, not
        # blocking it -- a separate, small single-repo call, since list-response
        # rows never carry the parent (only the single-repo GET does).
        self._fork_info: GitHubRepoForkInfo | None = None

        self.dialog = wx.Dialog(
            parent,
            title="GitHub Items",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 720, 520))
        self.dialog.SetSize(dip_size(self.dialog, 820, 600))
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
        self._repo_ctrl.SetHelpText(
            "Type owner/name, or paste a GitHub link, then press Enter to load it."
        )
        self._repo_ctrl.SetName("Repository in owner slash repo format")
        self._load_btn = wx.Button(panel, label="Load")
        self._load_btn.SetHelpText(
            "Load the issues, branches or runs of the repository typed above."
        )
        self._load_btn.SetName("Load repository")
        # No access key: Alt+P moves between comments, and every other letter of the
        # name is taken in this window (GATE-14: no key rather than a duplicate).
        self._pinned_btn = wx.Button(panel, label="Pinned...")
        self._pinned_btn.SetHelpText(
            "Pick a pinned repository to load, or pin or unpin the loaded one."
        )
        self._pinned_btn.SetName("Pinned repositories menu")
        self._favorites_btn = wx.Button(panel, label="Fa&vorites...")
        self._favorites_btn.SetHelpText(
            "Items you marked with Ctrl+D, in any repository, to open in a browser."
        )
        self._favorites_btn.SetName("Favorited items menu")
        self._explore_btn = wx.Button(panel, label="&Explore...")
        self._explore_btn.SetHelpText(
            "Searches, notifications, people and repository views beyond this list."
        )
        self._explore_btn.SetName(
            "Explore My Work, activity, people, repositories, labels, and Pages"
        )
        self._projects_btn = wx.Button(panel, label="Pro&jects...")
        self._projects_btn.SetHelpText(
            "GitHub Projects: browse items and change their fields. Needs sign-in."
        )
        self._projects_btn.SetName("Browse and edit GitHub Projects, blockers, and sub-issues")
        self._upstream_btn = wx.Button(panel, label="View &Upstream")
        self._upstream_btn.SetHelpText("For a fork, loads the repository it was forked from.")
        self._upstream_btn.SetName(
            "Open the repository this fork was forked from; enabled only for forks"
        )
        self._upstream_btn.Enable(False)
        self._files_btn = wx.Button(panel, label="&Files...")
        self._files_btn.SetName("Browse the repository's files at any branch, tag or commit")
        self._files_btn.SetHelpText("Folders and files, README, file history and blame.")
        self._milestones_btn = wx.Button(panel, label="Milestones...")
        self._milestones_btn.SetName("List, create, edit and close milestones")
        self._milestones_btn.SetHelpText("Each milestone's percent done, open and closed counts.")
        repo_row.Add(self._repo_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        repo_row.Add(self._load_btn, 0, wx.RIGHT, 6)
        repo_row.Add(self._pinned_btn, 0, wx.RIGHT, 6)
        repo_row.Add(self._favorites_btn, 0, wx.RIGHT, 6)
        repo_row.Add(self._explore_btn, 0, wx.RIGHT, 6)
        repo_row.Add(self._projects_btn, 0, wx.RIGHT, 6)
        repo_row.Add(self._upstream_btn, 0, wx.RIGHT, 6)
        repo_row.Add(self._files_btn, 0, wx.RIGHT, 6)
        repo_row.Add(self._milestones_btn)
        root.Add(repo_row, 0, wx.EXPAND | wx.ALL, 10)

        # Search row: full GitHub search syntax, scoped to the loaded repo
        # (Unified GitHub Management review, "Advanced Filtering").
        search_row = wx.BoxSizer(wx.HORIZONTAL)
        search_row.Add(
            wx.StaticText(panel, label="Searc&h (GitHub syntax):"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._search_ctrl = wx.TextCtrl(panel, value=self._search_query, style=wx.TE_PROCESS_ENTER)
        self._search_ctrl.SetHelpText(
            "GitHub search syntax, such as is:open label:bug. Empty restores the list."
        )
        self._search_ctrl.SetName(
            "Search issues and pull requests with full GitHub search syntax; "
            "empty search restores the normal list"
        )
        self._search_btn = wx.Button(panel, label="Search")
        self._search_btn.SetHelpText(
            "Run the search typed in the search box against the loaded repository."
        )
        self._search_btn.SetName("Run search")
        self._reference_btn = wx.Button(panel, label="Open Link...")
        self._reference_btn.SetHelpText(
            "Paste a GitHub link or owner/name#42 to go straight to it."
        )
        self._reference_btn.SetName("Open a GitHub URL or repository reference")
        search_row.Add(self._search_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        search_row.Add(self._search_btn, 0, wx.RIGHT, 12)
        search_row.Add(
            wx.StaticText(panel, label="&Quick filter:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._quick_filter_ctrl = wx.TextCtrl(
            panel, value=self._quick_filter_query, style=wx.TE_PROCESS_ENTER
        )
        self._quick_filter_ctrl.SetHelpText(
            "Narrows the loaded list as you type. Nothing is fetched."
        )
        self._quick_filter_ctrl.SetName(
            "Quick filter; narrows the currently loaded list as you type, no network "
            "request -- Escape clears it"
        )
        search_row.Add(self._quick_filter_ctrl, 1, wx.EXPAND)
        search_row.Add(self._reference_btn, 0, wx.LEFT, 6)
        root.Add(search_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Filter row: View / Show / State / Sort / List mode
        filt = wx.BoxSizer(wx.HORIZONTAL)
        filt.Add(wx.StaticText(panel, label="V&iew:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self._view_choice = wx.Choice(panel, choices=[label for _, label in VIEWS])
        self._view_choice.SetHelpText(
            "What the list shows: issues and pull requests, branches, commits and more."
        )
        self._view_choice.SetName("View")
        self._view_choice.SetSelection(
            next(i for i, (key, _) in enumerate(VIEWS) if key == self._view)
        )
        filt.Add(self._view_choice, 0, wx.RIGHT, 10)

        filt.Add(wx.StaticText(panel, label="&Show:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self._show_choice = wx.Choice(panel, choices=["Both", "Issues", "PRs"])
        self._show_choice.SetHelpText("In Issues and PRs, show issues, pull requests or both.")
        self._show_choice.SetName("Show issues PRs or both")
        self._show_choice.SetSelection({"both": 0, "issues": 1, "prs": 2}[self._show])
        filt.Add(self._show_choice, 0, wx.RIGHT, 10)

        filt.Add(wx.StaticText(panel, label="S&tate:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self._state_choice = wx.Choice(panel, choices=["Open", "Closed", "All"])
        self._state_choice.SetHelpText("Show open, closed or all issues and pull requests.")
        self._state_choice.SetName("State filter")
        self._state_choice.SetSelection({"open": 0, "closed": 1, "all": 2}[self._state])
        filt.Add(self._state_choice, 0, wx.RIGHT, 10)

        filt.Add(wx.StaticText(panel, label="S&ort:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self._sort_choice = wx.Choice(panel, choices=[label for _, label in SORT_ORDERS])
        self._sort_choice.SetHelpText("The order of issues and pull requests in the list.")
        self._sort_choice.SetName("Sort order")
        self._sort_choice.SetSelection(
            next(index for index, (key, _label) in enumerate(SORT_ORDERS) if key == self._sort)
        )
        filt.Add(self._sort_choice, 0, wx.RIGHT, 10)

        filt.Add(
            wx.StaticText(panel, label="&List mode:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self._mode_choice = wx.Choice(panel, choices=["Quick (compact)", "Full (field names)"])
        self._mode_choice.SetHelpText(
            "Quick reads values only; Full says each column's name before its value."
        )
        self._mode_choice.SetName("List mode")
        self._mode_choice.SetSelection(0)
        filt.Add(self._mode_choice, 1, wx.EXPAND | wx.RIGHT, 10)

        self._columns_btn = wx.Button(panel, label="Colu&mns...")
        self._columns_btn.SetHelpText("Choose which columns this view's list shows.")
        self._columns_btn.SetName("Choose which columns are shown in the list for this view")
        filt.Add(self._columns_btn, 0)
        root.Add(filt, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        history_row = wx.BoxSizer(wx.HORIZONTAL)
        self._back_btn = wx.Button(panel, label="Back")
        self._back_btn.SetName("Return to the previous GitHub repository or item")
        self._back_btn.SetHelpText(
            "Restore the previous repository, view, filters, and selected row."
        )
        self._forward_btn = wx.Button(panel, label="Forward")
        self._forward_btn.SetName("Move forward to the next GitHub repository or item")
        self._forward_btn.SetHelpText(
            "Restore the next repository, view, filters, and selected row."
        )
        self._back_btn.Enable(False)
        self._forward_btn.Enable(False)
        history_row.Add(self._back_btn, 0, wx.RIGHT, 6)
        history_row.Add(self._forward_btn, 0)
        history_row.AddStretchSpacer()
        root.Add(history_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        # List. Multi-select so batch actions can operate on several checked
        # rows at once (Unified GitHub Management "Batch Operations"); the
        # details pane follows the most recently selected row.
        self._list = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT | wx.BORDER_SIMPLE,
        )
        self._list.SetHelpText(
            "Enter opens the row; the Applications key lists what you can do with it. Ctrl+Shift+L "
            "says how much of the GitHub API rate limit is left."
        )
        self._list.SetName("GitHub items list; select several rows for batch actions")
        set_spoken_name(self._list, "GitHub items; select several rows for batch actions")
        root.Add(self._list, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Details
        root.Add(wx.StaticText(panel, label="Details"), 0, wx.LEFT | wx.TOP, 6)
        self._details = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        self._details.SetHelpText(
            "The selected row in full. Alt+N and Alt+P move between comments."
        )
        self._details.SetName("Details")
        root.Add(self._details, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        # Status + buttons
        self._status = wx.StaticText(panel, label="Enter a repository and click Load.")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._refresh_btn = wx.Button(panel, label="Refresh")
        self._refresh_btn.SetHelpText("Load this view again from GitHub. Ctrl+R does the same.")
        self._refresh_btn.SetName("Refresh")
        self._more_btn = wx.Button(panel, label="View More")
        self._more_btn.SetHelpText("Load the next page of results.")
        self._more_btn.SetName("View more results")
        self._open_btn = wx.Button(panel, label="Open in Browser")
        self._open_btn.SetHelpText("Open the selected row on GitHub in your browser.")
        self._open_btn.SetName("Open selected item in browser")
        self._goto_btn = wx.Button(panel, label="Go To #...")
        self._goto_btn.SetHelpText("Jump to an issue or pull request by its number.")
        self._goto_btn.SetName("Go to issue or PR by number")
        self._diff_btn = wx.Button(panel, label="&Diff...")
        self._diff_btn.SetHelpText(
            "The selected pull request's changed files, one comparison per file."
        )
        self._diff_btn.SetName(
            "View the selected pull request's changed files as accessible comparisons"
        )
        self._review_btn = wx.Button(panel, label="&Review...")
        self._review_btn.SetName(
            "Open the selected pull request's review threads, checks, and review actions"
        )
        self._review_btn.SetHelpText(
            "Read review threads and check runs, and submit an approval or review request."
        )
        self._summarize_btn = wx.Button(panel, label="Summari&ze")
        self._summarize_btn.SetHelpText(
            "An AI summary of the selected issue or pull request's discussion."
        )
        self._summarize_btn.SetName("Summarize the selected discussion with AI")
        self._compare_btn = wx.Button(panel, label="&Compare...")
        self._compare_btn.SetHelpText(
            "Compare two branches: commits ahead and behind, and changed files."
        )
        self._compare_btn.SetName(
            "Compare two branches: ahead/behind counts, commits, and changed files"
        )
        self._batch_btn = wx.Button(panel, label="&Batch...")
        self._batch_btn.SetHelpText(
            "Close, reopen, label, set a milestone or assign every selected item."
        )
        self._batch_btn.SetName(
            "Batch actions on the checked items: close, reopen, add label, "
            "set milestone, add assignees"
        )
        self._actions_btn = wx.Button(panel, label="&Actions...")
        self._actions_btn.SetHelpText(
            "Write actions for this view: new issue, merge, delete branch, re-run."
        )
        self._actions_btn.SetName(
            "Write actions for the current view: new issue or pull request, merge, "
            "delete branch, re-run workflow, reply to or edit or delete a comment"
        )
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        cancel_btn.SetHelpText("Close GitHub Items. Escape does the same.")
        cancel_btn.SetName("Close dialog")
        for b in (
            self._refresh_btn,
            self._more_btn,
            self._open_btn,
            self._goto_btn,
            self._diff_btn,
            self._review_btn,
            self._summarize_btn,
            self._compare_btn,
            self._batch_btn,
            self._actions_btn,
        ):
            btn_row.Add(b, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        # Bindings
        self._load_btn.Bind(wx.EVT_BUTTON, self._on_load)
        self._repo_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_load)
        self._view_choice.Bind(wx.EVT_CHOICE, self._on_view_changed)
        self._show_choice.Bind(wx.EVT_CHOICE, lambda _e: self._reload())
        self._state_choice.Bind(wx.EVT_CHOICE, lambda _e: self._reload())
        self._sort_choice.Bind(wx.EVT_CHOICE, lambda _e: self._reload())
        self._mode_choice.Bind(wx.EVT_CHOICE, self._on_mode_changed)
        self._back_btn.Bind(wx.EVT_BUTTON, self._go_back)
        self._forward_btn.Bind(wx.EVT_BUTTON, self._go_forward)
        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_activate)
        self._list.Bind(wx.EVT_LIST_KEY_DOWN, self._on_list_key)
        self._list.Bind(wx.EVT_CONTEXT_MENU, self._on_item_context_menu)
        self._details.Bind(wx.EVT_CONTEXT_MENU, self._on_item_context_menu)
        self._refresh_btn.Bind(wx.EVT_BUTTON, lambda _e: self._reload())
        self._more_btn.Bind(wx.EVT_BUTTON, self._on_more)
        self._open_btn.Bind(wx.EVT_BUTTON, lambda _e: self._open_selected())
        self._goto_btn.Bind(wx.EVT_BUTTON, self._on_goto)
        self._pinned_btn.Bind(wx.EVT_BUTTON, self._on_pinned_menu)
        self._favorites_btn.Bind(wx.EVT_BUTTON, self._on_favorites_menu)
        self._explore_btn.Bind(wx.EVT_BUTTON, self._on_explore)
        self._projects_btn.Bind(wx.EVT_BUTTON, self._on_projects)
        self._upstream_btn.Bind(wx.EVT_BUTTON, self._on_view_upstream)
        self._files_btn.Bind(wx.EVT_BUTTON, lambda _e: self._open_repo_files())
        self._milestones_btn.Bind(wx.EVT_BUTTON, lambda _e: self._open_milestones())
        self._search_btn.Bind(wx.EVT_BUTTON, self._on_search)
        self._reference_btn.Bind(wx.EVT_BUTTON, self._on_open_reference)
        self._search_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        # Emptying the search box drops back to the normal list right away,
        # exactly as running an empty search does (search_reset.py).
        from quill.ui.search_reset import bind_empty_query_reset

        bind_empty_query_reset(
            self._search_ctrl,
            lambda: self._on_search(None) if self._search_query else None,
        )
        self._quick_filter_ctrl.Bind(wx.EVT_TEXT, self._on_quick_filter_changed)
        self._diff_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_diff())
        self._review_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_review())
        self._summarize_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_summarize())
        self._compare_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_compare_branches())
        self._columns_btn.Bind(wx.EVT_BUTTON, self._on_columns_menu)
        self._batch_btn.Bind(wx.EVT_BUTTON, self._on_batch_menu)
        self._actions_btn.Bind(wx.EVT_BUTTON, self._on_actions_menu)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._apply_filter_enablement()
        self._rebuild_columns()
        self._update_navigation_buttons()

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
            self._save_navigation_state()
            self.dialog.Destroy()

    # ------------------------------------------------------------------
    # Loading

    def _on_load(self, _event: object) -> None:
        raw = self._repo_ctrl.GetValue().strip()
        if not raw:
            self._set_status("Enter a repository name (owner/repo) first.")
            self._repo_ctrl.SetFocus()
            return
        # Accepts owner/repo, a github.com URL, or a git@github.com: remote --
        # whatever a user is most likely to have pasted (GHManage parity).
        full_name = parse_repo_reference(raw)
        if full_name is None:
            self._set_status("Repository must be owner/repo, or a GitHub URL.")
            self._repo_ctrl.SetFocus()
            return
        if full_name != raw:
            self._repo_ctrl.SetValue(full_name)
        if full_name != self._repo:
            # A different repository starts clean: a stale search or quick
            # filter would silently narrow the new repo's list.
            self._search_query = ""
            self._search_ctrl.SetValue("")
            self._quick_filter_query = ""
            self._quick_filter_ctrl.ChangeValue("")
        self._repo = full_name
        self._page = 1
        self._reload()
        self._fetch_fork_info_async(full_name)

    def _fetch_fork_info_async(self, repo: str) -> None:
        """Fetch fork/parent info off the UI thread -- a separate, small call
        from the items list (list-response rows never carry the parent), so
        it must never block or interfere with the main list load."""
        self._fork_info = None
        self._upstream_btn.Enable(False)
        threading.Thread(  # GATE-40-OK: single-repo lookup, bounded, no pagination.
            target=self._fork_info_worker,
            args=(repo,),
            daemon=True,
        ).start()

    def _fork_info_worker(self, repo: str) -> None:
        wx = self._wx
        try:
            info = self._provider.fetch_fork_info(repo)
        except Exception:  # noqa: BLE001 - fork info is a nicety, never worth surfacing an error for
            return
        wx.CallAfter(self._on_fork_info_loaded, repo, info)

    def _on_fork_info_loaded(self, repo: str, info: GitHubRepoForkInfo) -> None:
        if repo != self._repo:
            return  # the user moved on to a different repo before this returned
        self._fork_info = info
        self._upstream_btn.Enable(info.is_fork and bool(info.parent_full_name))
        if info.is_fork and info.parent_full_name:
            self._announce(
                f"{repo} is a fork of {info.parent_full_name}. View Upstream is enabled."
            )

    def _on_view_upstream(self, _event: object) -> None:
        if self._fork_info is None or not self._fork_info.parent_full_name:
            return
        self._repo_ctrl.SetValue(self._fork_info.parent_full_name)
        self._on_load(None)

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
            rows = self._load_reference_rows(
                repo,
                view,
                self._fetch(repo, view, show, state, limit),
            )
        except GitHubItemsError as exc:
            wx.CallAfter(self._on_load_error, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            wx.CallAfter(self._on_load_error, str(exc))
            return
        wx.CallAfter(self._on_rows_loaded, rows, view)

    def _fetch(self, repo: str, view: str, show: str, state: str, limit: int) -> list[object]:
        if view == VIEW_ISSUES:
            if self._search_query:
                # Advanced filtering: full GitHub search syntax, repo-scoped.
                found = self._provider.search_items(repo, self._search_query, limit=limit)
                return sort_items(found, self._sort)
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
        if view == VIEW_WORKFLOWS:
            return self._provider.fetch_workflows(repo, limit=limit)
        if view == VIEW_RUNS:
            return self._provider.fetch_workflow_runs(repo, limit=limit)
        return []

    def _on_rows_loaded(self, rows: list[object], view: str) -> None:
        if view != self._view:
            return  # a stale worker for a view the user already left
        self._unfiltered_rows = rows
        if self._repo:
            self._saved.remember_repo(self._repo)
        self._set_loading(False)
        self._apply_quick_filter(move_focus=True)
        self._restore_saved_selection()
        self._select_initial_reference()
        if self._resume_selection_missing:
            self._update_navigation_buttons()
            return
        self._record_navigation_location()

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
        for i, col in enumerate(self._current_columns()):
            self._list.InsertColumn(i, col, width=140 if col == "title" else 90)

    def _populate_list(self) -> None:
        self._list.DeleteAllItems()
        columns = self._current_columns()
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
        # A fresh load (repo change or Refresh) leaves any release-asset drill;
        # rebuild the columns so the ListCtrl matches the (non-drill) view again.
        self._drill_release = None
        self._rows = []
        self._unfiltered_rows = []
        self._list.DeleteAllItems()
        self._details.Clear()
        self._comments = []
        self._comment_positions = []
        self._current_comment = -1
        self._rebuild_columns()

    # ------------------------------------------------------------------
    # Selection / details / comment navigation

    def _on_select(self, event: object) -> None:
        idx = getattr(event, "GetIndex", lambda: -1)()
        self._show_detail(idx)
        if not self._quick_filter_has_focus():
            self._record_navigation_location()
        if self._list_mode == "full" and 0 <= idx < len(self._rows):
            cells = row_cells(self._rows[idx], self._current_columns(), full=True)
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
        if self._view == VIEW_RELEASES:
            if self._drill_release is None and isinstance(model, GitHubRelease):
                self._enter_release_drill(model)
                return
            if self._drill_release is not None and isinstance(model, GitHubReleaseAsset):
                if model.browser_download_url:
                    webbrowser.open(model.browser_download_url)
                    self._announce(f"Opening download for {model.name} in browser")
                else:
                    self._announce("This asset has no download link.")
                return
        if self._view == VIEW_WORKFLOWS:
            self._run_selected_workflow(model)
            return
        url = model_url(model)
        if url:
            webbrowser.open(url)
            self._announce(f"Opened {model_label(model)} in browser")

    def _enter_release_drill(self, release: GitHubRelease) -> None:
        """Show *release*'s assets (most-downloaded first) in place of the
        releases list. The assets are already in hand from the releases fetch,
        so this is an instant client-side switch -- no extra network call."""
        self._drill_release = release
        self._unfiltered_rows = list(release.assets)
        self._rows = list(release.assets)
        # A quick filter typed for the releases columns rarely means anything
        # for the asset columns -- reset it, as the branch/view switches do.
        self._quick_filter_query = ""
        self._quick_filter_ctrl.ChangeValue("")
        self._rebuild_columns()  # swap to RELEASE_ASSET_COLUMNS
        self._populate_list()
        self._set_status(release_drill_status(release))
        if release.assets:
            self._list.SetFocus()
            self._list.Select(0)
            self._list.Focus(0)
            self._show_detail(0)
        else:
            self._details.Clear()
            self._announce(
                f"{release.tag} has no downloadable assets. Backspace returns to the releases list."
            )

    def _exit_release_drill(self) -> None:
        """Backspace out of a release's asset breakdown, back to the releases
        list (mirrors Backspace out of a branch's Commits drill-down)."""
        # _reload -> _clear_list resets _drill_release and rebuilds the columns.
        self._reload()
        self._announce("Back to releases.")

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
    # Search / pinned repositories / favorites (Unified GitHub Management)

    def _on_search(self, _event: object) -> None:
        """Run (or clear) a repo-scoped GitHub-syntax search over issues + PRs."""
        query = self._search_ctrl.GetValue().strip()
        if not self._repo:
            self._announce("Load a repository first, then search it.")
            self._repo_ctrl.SetFocus()
            return
        self._search_query = query
        if self._view != VIEW_ISSUES:
            self._view_choice.SetSelection(0)
            self._switch_view(VIEW_ISSUES)
            return
        self._page = 1
        self._reload()
        if not query:
            self._announce("Search cleared; showing the normal list.")

    # ------------------------------------------------------------------
    # PR diff / AI summary / batch actions (Unified GitHub Management)

    def _selected_indices(self) -> list[int]:
        indices: list[int] = []
        index = self._list.GetFirstSelected()
        while index != -1:
            indices.append(index)
            index = self._list.GetNextSelected(index)
        return indices

    def _on_diff(self) -> None:
        """Open the selected PR's changed files in the accessible diff viewer."""
        idx = self._list.GetFirstSelected()
        model = self._rows[idx] if 0 <= idx < len(self._rows) else None
        if not isinstance(model, GitHubItem) or not model.is_pr:
            self._announce("Select a pull request row first; Diff works on PRs.")
            return
        self._set_status(f"Loading files for PR #{model.number}...")

        def worker() -> None:
            wx = self._wx
            try:
                diff = self._provider.fetch_pull_diff(self._repo, model.number)
            except GitHubItemsError as exc:
                wx.CallAfter(self._set_status, f"Error: {exc}")
                return
            wx.CallAfter(self._show_diff_dialog, diff)

        threading.Thread(  # GATE-40-OK: PR file inventory fetch.
            target=worker, daemon=True
        ).start()

    def _on_batch_menu(self, _event: object) -> None:
        """Batch close / reopen / label over the selected rows, behind consent."""
        wx = self._wx
        if self._view != VIEW_ISSUES:
            self._announce("Batch actions work in the Issues & PRs view.")
            return
        if not self._provider.is_authenticated:
            self._announce(
                "Batch actions need a signed-in GitHub account; this session is read-only."
            )
            return
        selected = self._selected_indices()
        numbers = [
            self._rows[i].number
            for i in selected
            if 0 <= i < len(self._rows) and isinstance(self._rows[i], GitHubItem)
        ]
        if not numbers:
            self._announce("Select one or more issue or PR rows first.")
            return
        menu = wx.Menu()
        close_id, reopen_id, label_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        count = len(numbers)
        menu.Append(close_id, f"Close {count} selected")
        menu.Append(reopen_id, f"Reopen {count} selected")
        menu.Append(label_id, f"Add label to {count} selected...")
        extras: dict[int, object] = {}

        def _extra(label: str, handler: object) -> None:
            item_id = wx.NewIdRef()
            menu.Append(item_id, label)
            extras[int(item_id)] = handler

        self._add_batch_extras(_extra, numbers)

        def _on_pick(event: object) -> None:
            picked = int(event.GetId())
            if picked in extras:
                extras[picked]()
            elif picked == int(close_id):
                self._run_batch(numbers, state="closed")
            elif picked == int(reopen_id):
                self._run_batch(numbers, state="open")
            elif picked == int(label_id):
                dlg = wx.TextEntryDialog(
                    self.dialog, "Label to add to the selected items:", "Add label"
                )
                if self._show_modal(dlg, "Add label") == wx.ID_OK:
                    label = dlg.GetValue().strip()
                    if label:
                        self._run_batch(numbers, add_labels=(label,))
                dlg.Destroy()

        menu.Bind(wx.EVT_MENU, _on_pick)
        try:
            self._batch_btn.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _run_batch(
        self,
        numbers: list[int],
        *,
        state: str | None = None,
        add_labels: tuple[str, ...] = (),
    ) -> None:
        wx = self._wx
        # The consent surface: name the exact action and the exact items —
        # this is the one place the viewer writes to GitHub.
        action = (
            f"Close {len(numbers)} item(s)"
            if state == "closed"
            else f"Reopen {len(numbers)} item(s)"
            if state == "open"
            else f"Add label {add_labels[0]!r} to {len(numbers)} item(s)"
        )
        listing = ", ".join(f"#{n}" for n in numbers[:20])
        if len(numbers) > 20:
            listing += f" and {len(numbers) - 20} more"
        confirm = wx.MessageDialog(
            self.dialog,
            f"{action} in {self._repo}?\n\n{listing}\n\n"
            "This changes the items on GitHub for everyone watching them.",
            "Confirm batch change",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        if hasattr(confirm, "SetYesNoLabels"):
            confirm.SetYesNoLabels(action, "Cancel")
        try:
            answer = self._show_modal(confirm, "Confirm batch change")
        finally:
            confirm.Destroy()
        if answer != wx.ID_YES:
            self._announce("Batch change cancelled.")
            return
        self._set_status(f"{action}...")

        def worker() -> None:
            try:
                errors = self._provider.update_items(
                    self._repo, numbers, state=state, add_labels=add_labels
                )
            except GitHubItemsError as exc:
                wx.CallAfter(self._set_status, f"Error: {exc}")
                return
            wx.CallAfter(self._on_batch_done, len(numbers), errors)

        threading.Thread(  # GATE-40-OK: explicit, consented batch write.
            target=worker, daemon=True
        ).start()

    def _on_batch_done(self, requested: int, errors: list[str]) -> None:
        done = requested - len(errors)
        message = f"Batch change applied to {done} of {requested} item(s)."
        if errors:
            message += " Failed: " + "; ".join(errors[:5])
        self._set_status(message)
        self._reload()

    # ------------------------------------------------------------------
    # Write actions: new issue/PR, merge, delete branch, re-run workflow,
    # and comment reply/edit/delete on top of the Alt+N/Alt+P navigation
    # above. One context-sensitive menu (mirrors the Batch... menu's shape)
    # rather than a wall of mostly-disabled buttons -- what's offered
    # depends on the current view, the selected row, and whether the cursor
    # is parked on a specific comment.

    def _merge_selected_pr(self) -> None:
        selected = self._selected_indices()
        if len(selected) != 1:
            return
        model = self._rows[selected[0]]
        if not isinstance(model, GitHubItem):
            return
        from quill.ui.github_repo_admin_dialogs import TypedConfirmDialog

        if not TypedConfirmDialog(
            self.dialog,
            title="Confirm Merge",
            message=(
                f"Merge pull request #{model.number} ({model.title!r}) into "
                f"{model.base_branch!r} in {self._repo}? This changes the target branch "
                "for everyone."
            ),
            expected=str(model.number),
        ).show():
            self._announce("Merge cancelled.")
            return
        self._set_status(f"Merging #{model.number}...")
        number = model.number

        def worker() -> None:
            wx = self._wx
            try:
                sha = self._provider.merge_pull_request(self._repo, number)
            except GitHubItemsError as exc:
                wx.CallAfter(self._set_status, f"Error: {exc}")
                return
            wx.CallAfter(self._on_merge_done, number, sha)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: consented merge.

    def _on_merge_done(self, number: int, sha: str) -> None:
        self._set_status(f"Merged #{number} ({sha[:7]})")
        self._reload()

    def _reply_to_thread(self) -> None:
        if self._comment_target is None:
            self._announce("Select an issue or pull request first.")
            return
        repo, number = self._comment_target
        wx = self._wx
        with wx.TextEntryDialog(
            self.dialog,
            "Reply:",
            "Reply to Thread",
            style=wx.OK | wx.CANCEL | wx.CENTRE | wx.TE_MULTILINE,
        ) as dlg:
            if self._show_modal(dlg, "Reply to Thread") != wx.ID_OK:
                return
            body = dlg.GetValue().strip()
        if not body:
            return
        self._set_status("Posting reply...")

        def worker() -> None:
            try:
                self._provider.create_comment(repo, number, body)
            except GitHubItemsError as exc:
                wx.CallAfter(self._set_status, f"Error: {exc}")
                return
            wx.CallAfter(self._on_comment_posted, number)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: consented reply.

    def _on_comment_posted(self, number: int) -> None:
        self._set_status("Reply posted")
        idx = self._list.GetFirstSelected()
        if 0 <= idx < len(self._rows) and isinstance(self._rows[idx], GitHubItem):
            if self._rows[idx].number == number:
                self._fetch_comments(idx, self._rows[idx])

    def _edit_current_comment(self) -> None:
        if self._current_comment < 0 or self._current_comment >= len(self._comments):
            self._announce("Navigate to a comment first (Alt+N).")
            return
        comment = self._comments[self._current_comment]
        comment_id = comment.get("id", "")
        if not comment_id:
            self._announce("This comment cannot be edited.")
            return
        wx = self._wx
        with wx.TextEntryDialog(
            self.dialog, "Edit comment:", "Edit Comment", value=comment.get("body", "")
        ) as dlg:
            if self._show_modal(dlg, "Edit Comment") != wx.ID_OK:
                return
            body = dlg.GetValue().strip()
        if not body:
            return
        repo = self._repo
        self._set_status("Saving comment...")

        def worker() -> None:
            try:
                self._provider.edit_comment(repo, int(comment_id), body)
            except GitHubItemsError as exc:
                wx.CallAfter(self._set_status, f"Error: {exc}")
                return
            wx.CallAfter(self._on_comment_edited)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: consented edit.

    def _on_comment_edited(self) -> None:
        self._set_status("Comment updated")
        idx = self._list.GetFirstSelected()
        if 0 <= idx < len(self._rows) and isinstance(self._rows[idx], GitHubItem):
            self._fetch_comments(idx, self._rows[idx])

    def _delete_current_comment(self) -> None:
        if self._current_comment < 0 or self._current_comment >= len(self._comments):
            self._announce("Navigate to a comment first (Alt+N).")
            return
        comment = self._comments[self._current_comment]
        comment_id = comment.get("id", "")
        if not comment_id:
            self._announce("This comment cannot be deleted.")
            return
        from quill.ui.github_repo_admin_dialogs import TypedConfirmDialog

        if not TypedConfirmDialog(
            self.dialog,
            title="Confirm Delete Comment",
            message="Delete this comment? This cannot be undone.",
            expected="delete",
        ).show():
            self._announce("Delete cancelled.")
            return
        repo = self._repo
        wx = self._wx
        self._set_status("Deleting comment...")

        def worker() -> None:
            try:
                self._provider.delete_comment(repo, int(comment_id))
            except GitHubItemsError as exc:
                wx.CallAfter(self._set_status, f"Error: {exc}")
                return
            wx.CallAfter(self._on_comment_deleted)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: consented delete.

    def _on_comment_deleted(self) -> None:
        self._set_status("Comment deleted")
        idx = self._list.GetFirstSelected()
        if 0 <= idx < len(self._rows) and isinstance(self._rows[idx], GitHubItem):
            self._fetch_comments(idx, self._rows[idx])

    def _confirm_action(self, message: str, title: str) -> bool:
        wx = self._wx
        dlg = wx.MessageDialog(
            self.dialog, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        )
        try:
            return self._show_modal(dlg, title) == wx.ID_YES
        finally:
            dlg.Destroy()

    # ------------------------------------------------------------------
    # View switching + filter enablement

    def _on_view_changed(self, _event: object) -> None:
        view = VIEWS[self._view_choice.GetSelection()][0]
        if view == self._view:
            return
        self._drill_branch = None  # leaving Branches cancels any drill target
        self._drill_release = None  # leaving Releases cancels any asset drill
        self._switch_view(view)

    def _switch_view(self, view: str) -> None:
        self._view = view
        self._page = 1
        # A quick filter typed for one view's columns rarely means anything
        # for another view's -- reset it rather than silently narrowing.
        self._quick_filter_query = ""
        self._quick_filter_ctrl.ChangeValue("")
        self._rebuild_columns()
        self._apply_filter_enablement()
        self._reload()

    def _apply_filter_enablement(self) -> None:
        issues_view = self._view == VIEW_ISSUES
        for ctrl in (self._show_choice, self._state_choice, self._sort_choice):
            ctrl.Enable(issues_view)
        for ctrl in (self._diff_btn, self._review_btn, self._summarize_btn, self._batch_btn):
            ctrl.Enable(issues_view)
        self._compare_btn.Enable(self._view == VIEW_BRANCHES)

    # ------------------------------------------------------------------
    # Keyboard

    def _on_list_key(self, event: object) -> None:
        key = event.GetKeyCode()
        if key == ord("R"):
            self._reload()
        elif key == ord("M"):
            self._cycle_list_mode()
        elif key == self._wx.WXK_BACK and self._view == VIEW_COMMITS and self._drill_branch:
            # Step back out of a branch's Commits drill-down (GHManage parity).
            # Plain Backspace, so this is list-scoped rather than global --
            # otherwise it would eat Backspace in the repo/search text fields.
            self._drill_branch = None
            self._switch_view(VIEW_BRANCHES)
        elif (
            key == self._wx.WXK_BACK
            and self._view == VIEW_RELEASES
            and self._drill_release is not None
        ):
            # Step back out of a release's asset breakdown to the releases list.
            self._exit_release_drill()
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
        elif key == ord("D") and mod == wx.MOD_CONTROL:
            self._favorite_selected()
        elif key == ord("F") and mod == wx.MOD_CONTROL:
            self._search_ctrl.SetFocus()
        elif key == ord("N") and mod == wx.MOD_ALT:
            self._navigate_comment(1)
        elif key == ord("P") and mod == wx.MOD_ALT:
            self._navigate_comment(-1)
        elif key == ord("B") and mod == (wx.MOD_CONTROL | wx.MOD_SHIFT):
            self._on_compare_branches()
        elif key == ord("F") and mod == (wx.MOD_CONTROL | wx.MOD_SHIFT):
            self._quick_filter_ctrl.SetFocus()
        elif key == ord("W") and mod == (wx.MOD_CONTROL | wx.MOD_SHIFT) and self._view == VIEW_RUNS:
            self._show_failure_digest()
        elif key == ord("L") and mod == (wx.MOD_CONTROL | wx.MOD_SHIFT):
            self._show_api_rate_limit()
        elif key == wx.WXK_ESCAPE and self._quick_filter_query and self._quick_filter_has_focus():
            # ChangeValue (not SetValue) so this doesn't also fire EVT_TEXT
            # and re-run the filter a second time, silently, with announce=False.
            self._quick_filter_ctrl.ChangeValue("")
            self._quick_filter_query = ""
            self._apply_quick_filter(move_focus=False)
        else:
            event.Skip()

    # ------------------------------------------------------------------
    # Helpers

    def _set_loading(self, loading: bool) -> None:
        self._load_btn.Enable(not loading)
        self._repo_ctrl.Enable(not loading)
        self._refresh_btn.Enable(not loading)
        self._more_btn.Enable(not loading)

    def _set_status(self, message: str, *, announce: bool = True) -> None:
        self._status.SetLabel(message)
        parent = self._status.GetParent()
        if parent is not None:
            parent.Layout()
        if message and announce:
            self._announce(message)


__all__ = ["GitHubItemsDialog"]
