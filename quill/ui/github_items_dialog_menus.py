"""Context, pinned repository, and favorites menus for GitHub items."""

from __future__ import annotations

import webbrowser
from urllib.parse import quote

from quill.core.github.items_provider import (
    GitHubBranch,
    GitHubItem,
    GitHubRelease,
    GitHubReleaseAsset,
)
from quill.ui.github_context_rows import ContextRows
from quill.ui.github_items_view import (
    VIEW_BRANCHES,
    VIEW_ISSUES,
    VIEW_RELEASES,
    VIEW_RUNS,
    VIEW_WORKFLOWS,
    model_label,
    model_url,
)


class GitHubItemsMenusMixin:
    """Native menus for selected items and saved navigation."""

    def _on_explore(self, _event: object) -> None:
        from quill.ui.github_explore_dialog import GitHubExploreDialog

        chosen = False
        reference: object = None

        def use_repo(repo: str) -> None:
            nonlocal chosen
            chosen = True
            self._repo_ctrl.SetValue(repo)

        def open_reference(target: object) -> None:
            # A notification's issue opens here, at that issue (Explore closes first).
            nonlocal reference
            reference = target

        dialog = GitHubExploreDialog(
            self.dialog,
            self._provider,
            initial_repo=self._repo,
            on_repo_select=use_repo,
            announce_cb=self._announce,
            on_start_issue_worktree=self._start_issue_worktree_cb,
            on_open_reference=open_reference,
            gist_source_cb=getattr(self, "_gist_source_cb", None),
        )
        dialog.show()
        if reference is not None:
            self._apply_initial_reference(reference)
        elif chosen:
            self._on_load(None)

    def _on_projects(self, _event: object) -> None:
        if not self._provider.is_authenticated:
            self._announce("Sign in to GitHub to view and update Projects.")
            return
        from quill.ui.github_projects_dialog import GitHubProjectsDialog

        GitHubProjectsDialog(
            self.dialog,
            self._provider,
            initial_repo=self._repo,
            announce_cb=self._announce,
        ).show()

    def _copy_item_text(self, value: str, label: str) -> None:
        wx = self._wx
        if not wx.TheClipboard.Open():
            self._announce("Could not open the clipboard.")
            return
        try:
            copied = wx.TheClipboard.SetData(wx.TextDataObject(value))
        finally:
            wx.TheClipboard.Close()
        self._announce(f"Copied {label}." if copied else f"Could not copy {label}.")

    def _on_item_context_menu(self, event: object) -> None:
        """Offer the selected row's read and write actions at the point of use."""
        wx = self._wx
        if event is not None and event.GetEventObject() is self._list:
            position = event.GetPosition()
            if position != wx.DefaultPosition:
                index, _flags = self._list.HitTest(self._list.ScreenToClient(position))
                if 0 <= index < len(self._rows):
                    self._list.Select(index)
                    self._list.Focus(index)
                    self._show_detail(index)
        index = self._list.GetFirstSelected()
        model = self._rows[index] if 0 <= index < len(self._rows) else None
        menu = wx.Menu()
        rows = ContextRows()
        if model is not None:
            self._fill_item_context_rows(rows, model)
        else:
            # Nothing selected: the view's own rows. The API rate limit is on no
            # context menu (Ctrl+Shift+L says it; GitHub PRD section 5, rule 5).
            add = rows.add
            add("Refresh\tCtrl+R", self._reload, bool(self._repo))
            add("Browse Repository Files...", self._open_repo_files, bool(self._repo))
            add("Milestones...", self._open_milestones, bool(self._repo))
            if self._provider.is_authenticated and self._repo and self._view == VIEW_ISSUES:
                add("New Issue...", self._new_issue)
                add("New Pull Request...", self._new_pull_request)
        rows.populate(wx, menu, item_selected=model is not None)
        try:
            self._list.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _fill_item_context_rows(self, rows: ContextRows, model: object) -> None:
        """The selected row's own actions, default first (GitHub PRD section 5).

        The first row is what Enter does. Codespaces is offered only on a pull
        request or a branch, and repository-wide rows (Files, Milestones, the
        rate limit) stay off an item's menu: each keeps its button or key.
        """
        add = rows.add
        signed_in = self._provider.is_authenticated
        is_item = isinstance(model, GitHubItem)
        is_pr = is_item and model.is_pr
        url = model_url(model)

        def activate() -> None:
            self._on_activate(None)  # Enter's own handler

        if isinstance(model, GitHubBranch):
            add("Commits", activate)
        elif isinstance(model, GitHubRelease) and self._view == VIEW_RELEASES:
            add("Assets", activate)
        elif isinstance(model, GitHubReleaseAsset):
            add("Download", activate, bool(model.browser_download_url))
        elif self._view == VIEW_WORKFLOWS:
            add("Run Workflow on Branch...", lambda: self._run_selected_workflow(model), signed_in)
        else:
            add("Open on GitHub", self._open_selected, bool(url))
        if is_pr:
            add("Open Review...", self._on_review)
            add("Open File Differences...", self._on_diff)
            if signed_in and not model.is_merged:
                add(f"Merge Pull Request #{model.number}...", self._merge_selected_pr)
        elif isinstance(model, GitHubBranch):
            add("Compare Branches...", self._on_compare_branches)
            if signed_in:
                add(f"Delete Branch {model.name!r}...", self._delete_selected_branch)
        elif self._view == VIEW_RUNS:
            add("View Jobs and Logs...", self._view_jobs_for_selected)
            self._add_run_actions(add)
            if signed_in:
                add("Re-run Workflow", self._rerun_selected_workflow)
            add("View Artifacts...", self._view_artifacts_for_selected)
        elif self._view == VIEW_RELEASES:
            self._add_release_actions(add)
        add("Copy Link", lambda: self._copy_item_text(url, "item link"), bool(url))
        add("Copy Details", lambda: self._copy_item_text(self._details.GetValue(), "details"))
        add("Open on GitHub", self._open_selected, bool(url))
        if is_pr or isinstance(model, GitHubBranch):
            add("Open in GitHub Codespaces...", lambda: self._open_in_codespaces(model))
        self._add_copilot_and_commit_actions(add, model)
        if is_item:
            add("Summarize Discussion", self._on_summarize, self._ai_acquire is not None)
            add("View Timeline...", self._view_timeline_for_selected)
            add("React...", self._react_to_selected_item, signed_in)
            if self._current_comment >= 0:
                add("React to This Comment...", self._react_to_current_comment, signed_in)
            self._add_issue_housekeeping(rows, model)
            if self._start_issue_worktree_cb is not None:
                kind = "pull request" if is_pr else "issue"
                add(
                    f"Start {kind} #{model.number} in Local Worktree...",
                    lambda item=model: self._start_issue_worktree_cb(
                        self.dialog, self._repo, item.number, item.title, item.is_pr
                    ),
                )
        add("Add to or Remove from Favorites\tCtrl+D", self._favorite_selected)
        if signed_in and self._view in (VIEW_ISSUES, VIEW_BRANCHES, VIEW_RUNS, VIEW_WORKFLOWS):
            add("More Write Actions...", lambda: self._on_actions_menu(None))

    def _on_actions_menu(self, _event: object) -> None:
        """The Actions... button: write actions for the current view."""
        wx = self._wx
        if not self._repo:
            self._announce("Load a repository first.")
            return
        if not self._provider.is_authenticated:
            self._announce(
                "Write actions need a signed-in GitHub account; this session is read-only."
            )
            return
        menu = wx.Menu()
        entries: list[tuple[object, object]] = []

        def _add(label: str, handler: object) -> None:
            item_id = wx.NewIdRef()
            menu.Append(item_id, label)
            entries.append((item_id, handler))

        if self._view == VIEW_ISSUES:
            _add("New Issue...", self._new_issue)
            _add("New Pull Request...", self._new_pull_request)
            selected = self._selected_indices()
            if len(selected) == 1:
                model = self._rows[selected[0]]
                if isinstance(model, GitHubItem) and model.is_pr and not model.is_merged:
                    _add(f"Merge Pull Request #{model.number}...", self._merge_selected_pr)
            if self._current_comment >= 0:
                _add("Edit This Comment...", self._edit_current_comment)
                _add("Delete This Comment...", self._delete_current_comment)
                _add("React to This Comment...", self._react_to_current_comment)
            if self._comment_target is not None:
                _add("Reply to Thread...", self._reply_to_thread)
        elif self._view == VIEW_BRANCHES:
            selected = self._selected_indices()
            if len(selected) == 1 and isinstance(self._rows[selected[0]], GitHubBranch):
                branch = self._rows[selected[0]]
                _add(f"Delete Branch {branch.name!r}...", self._delete_selected_branch)
        elif self._view == VIEW_WORKFLOWS:
            selected = self._selected_indices()
            if len(selected) == 1:
                workflow = self._rows[selected[0]]
                _add(
                    f"Run {workflow.name!r} on Branch...",
                    lambda: self._run_selected_workflow(workflow),
                )
        elif self._view == VIEW_RUNS:
            selected = self._selected_indices()
            if len(selected) == 1:
                _add("Re-run Workflow", self._rerun_selected_workflow)
                _add("View Jobs and Logs...", self._view_jobs_for_selected)
                _add("View Artifacts...", self._view_artifacts_for_selected)
                self._add_run_actions(_add)
        elif self._view == VIEW_RELEASES:
            self._add_release_actions(_add)

        if not entries:
            menu.Destroy()
            self._announce("No write actions available here. Select a row first.")
            return

        def _on_pick(event: object) -> None:
            picked = event.GetId()
            for item_id, handler in entries:
                if int(picked) == int(item_id):
                    handler()
                    return

        menu.Bind(wx.EVT_MENU, _on_pick)
        try:
            self._actions_btn.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _open_in_codespaces(self, model: object) -> None:
        if not self._repo or "/" not in self._repo:
            self._announce("Load a repository before opening Codespaces.")
            return
        url = f"https://codespaces.new/{self._repo}"
        branch_text = ""
        if isinstance(model, GitHubBranch):
            url += f"/tree/{quote(model.name, safe='')}"
            branch_text = f"\nBranch: {model.name}"
        wx = self._wx
        dialog = wx.MessageDialog(
            self.dialog,
            f"Open GitHub Codespaces for {self._repo}?{branch_text}\n\n"
            "Starting a Codespace can incur charges. QUILL will open GitHub's "
            "page only; it will not create a Codespace or attach your GitHub token.",
            "Open GitHub Codespaces",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        try:
            if self._show_modal(dialog, "Open GitHub Codespaces") != wx.ID_YES:
                return
        finally:
            dialog.Destroy()
        self._announce(
            "Opened the GitHub Codespaces page. Review the billing and configuration choices there."
            if webbrowser.open(url, new=2)
            else "Could not open GitHub Codespaces in a browser."
        )

    def _on_pinned_menu(self, _event: object) -> None:
        """Pinned repositories: pick one to load, pin/unpin the current one."""
        wx = self._wx
        menu = wx.Menu()
        ids: dict[int, str] = {}
        for repo in self._saved.pinned:
            item_id = wx.NewIdRef()
            menu.Append(item_id, repo)
            ids[int(item_id)] = repo
        if self._saved.pinned:
            menu.AppendSeparator()
        current = self._repo_ctrl.GetValue().strip()
        action_id = wx.NewIdRef()
        if current and self._saved.is_pinned(current):
            menu.Append(action_id, f"Unpin {current}")
            action = "unpin"
        elif current and "/" in current:
            menu.Append(action_id, f"Pin {current}")
            action = "pin"
        else:
            menu.Append(action_id, "Pin the loaded repository (load one first)")
            menu.Enable(int(action_id), False)
            action = ""

        def _on_pick(event: object) -> None:
            picked_id = int(event.GetId())
            if picked_id == int(action_id):
                if action == "pin" and self._saved.pin_repo(current):
                    self._announce(f"Pinned {current}")
                elif action == "unpin" and self._saved.unpin_repo(current):
                    self._announce(f"Unpinned {current}")
                return
            repo = ids.get(picked_id)
            if repo:
                self._repo_ctrl.SetValue(repo)
                self._search_query = ""
                self._search_ctrl.SetValue("")
                self._on_load(None)

        menu.Bind(wx.EVT_MENU, _on_pick)
        try:
            self._pinned_btn.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _on_favorites_menu(self, _event: object) -> None:
        """Favorited items across every repo: pick one to open in the browser."""
        wx = self._wx
        if not self._saved.favorites:
            self._announce("No favorites yet. Press Ctrl+D on a selected item to favorite it.")
            return
        menu = wx.Menu()
        ids: dict[int, object] = {}
        for entry in self._saved.favorites:
            item_id = wx.NewIdRef()
            suffix = f" ({entry.subtitle})" if entry.subtitle else ""
            menu.Append(item_id, f"{entry.repo}: {entry.title}{suffix}")
            ids[int(item_id)] = entry

        def _on_pick(event: object) -> None:
            entry = ids.get(int(event.GetId()))
            if entry is not None and entry.url:
                webbrowser.open(entry.url)
                self._announce(f"Opened favorite {entry.title} in browser")

        menu.Bind(wx.EVT_MENU, _on_pick)
        try:
            self._favorites_btn.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _favorite_selected(self) -> None:
        """Ctrl+D: bookmark the selected row (GHManage favorites parity)."""
        from quill.core.github.saved_items import FavoriteItem

        idx = self._list.GetFirstSelected()
        if idx < 0 or idx >= len(self._rows):
            self._announce("Select an item to favorite first.")
            return
        model = self._rows[idx]
        url = model_url(model)
        if not url:
            self._announce("This item has no link to favorite.")
            return
        item_type = self._view.rstrip("s")
        if isinstance(model, GitHubItem):
            item_type = "pr" if model.is_pr else "issue"
        entry = FavoriteItem(
            repo=self._repo,
            item_type=item_type,
            url=url,
            title=model_label(model),
            subtitle=getattr(model, "state", "") or "",
        )
        if self._saved.add_favorite(entry):
            self._announce(f"Favorited {entry.title}")
        else:
            self._announce(f"{entry.title} is already a favorite")
