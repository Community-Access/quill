"""Accessible pull-request review surface: threads, checks, and review actions."""

from __future__ import annotations

import threading
import webbrowser
from typing import TYPE_CHECKING

from quill.core.github.items_provider import GitHubItemsError, GitHubPullDiff
from quill.core.github.local_drafts import GitHubIssueDraftStore
from quill.core.github.pr_review import (
    GitHubCheckRun,
    GitHubPullReviewState,
    GitHubReviewError,
    GitHubReviewThread,
    PullReviewClient,
)
from quill.ui.dialog_contract import apply_modal_ids, dialog_alive, show_modal_dialog
from quill.ui.dpi import dip_size
from quill.ui.github_pr_review_menus import GitHubPullReviewMenusMixin
from quill.ui.github_pr_review_merge import GitHubPullReviewMergeMixin
from quill.ui.github_pr_review_policy import GitHubPullReviewPolicyMixin
from quill.ui.github_pr_review_render import GitHubPullReviewRenderMixin
from quill.ui.spoken_name import set_spoken_name

if TYPE_CHECKING:
    from collections.abc import Callable

    from quill.core.github.items_provider import GitHubItemsProvider


class GitHubPullReviewDialog(
    GitHubPullReviewPolicyMixin,
    GitHubPullReviewRenderMixin,
    GitHubPullReviewMenusMixin,
    GitHubPullReviewMergeMixin,
):
    """Three-pane reader for one PR's state, review threads, and check runs."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        repo: str,
        number: int,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._client = PullReviewClient(provider)
        self._review_draft_store = GitHubIssueDraftStore.load(getattr(provider, "token", None))
        self._repo = repo
        self._number = number
        self._announce = announce_cb or (lambda _message: None)
        self._state: GitHubPullReviewState | None = None
        self._threads: tuple[GitHubReviewThread, ...] = ()
        self._checks: tuple[GitHubCheckRun, ...] = ()
        self._diff: GitHubPullDiff | None = None
        self._nodes: dict[int, tuple[str, int]] = {}
        self._thread_items: dict[int, object] = {}
        self._visited_thread_ids: set[str] = set()
        self._loading = False
        self._policy_loading = False
        # Bumped by every refresh; a reply carrying an older number is dropped, so a
        # slow refresh can never overwrite the one that started after it.
        self._refresh_generation = 0

        self.dialog = wx.Dialog(
            parent,
            title=f"Review pull request #{number}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 960, 600))
        self.dialog.SetSize(dip_size(self.dialog, 1180, 740))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        self._header = wx.StaticText(panel, label="Loading review state…")
        self._header.SetName("Pull request review status")
        self._header.SetHelpText(
            "Draft, merge readiness, review approvals, checks, and thread counts."
        )
        root.Add(self._header, 0, wx.EXPAND | wx.ALL, 8)

        outer_splitter = wx.SplitterWindow(panel, style=wx.SP_3D)
        outer_splitter.SetName("Review threads and details")
        thread_panel = wx.Panel(outer_splitter)
        thread_sizer = wx.BoxSizer(wx.VERTICAL)
        thread_label = wx.StaticText(thread_panel, label="Pull request outline")
        thread_label.SetName("Pull request outline")
        thread_label.SetHelpText("Expand the pull request, files, and checks.")
        self._outline = wx.TreeCtrl(
            thread_panel, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE
        )
        self._outline.SetName("Pull request outline; files, review threads, and checks")
        self._outline.SetHelpText(
            "Up and Down select; Right expands; Left collapses; Tab reads details. "
            "Ctrl+R replies to a selected thread. Shift+F10 opens actions."
        )
        set_spoken_name(self._outline, "Pull request outline")
        thread_sizer.Add(thread_label, 0, wx.ALL, 6)
        thread_sizer.Add(self._outline, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        thread_panel.SetSizer(thread_sizer)

        detail_splitter = wx.SplitterWindow(outer_splitter, style=wx.SP_3D)
        detail_splitter.SetName("Thread detail and review summary")
        self._thread_detail = wx.TextCtrl(
            detail_splitter,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        set_spoken_name(self._thread_detail, "Selected review thread, including all replies")
        self._thread_detail.SetHelpText(
            "The selected review conversation, including file and line context."
        )

        side_panel = wx.Panel(detail_splitter)
        side_sizer = wx.BoxSizer(wx.VERTICAL)
        summary_label = wx.StaticText(side_panel, label="Review summary")
        summary_label.SetName("Review summary")
        summary_label.SetHelpText("Plain-language pull request status and reviewer summary.")
        side_sizer.Add(summary_label, 0, wx.ALL, 6)
        self._policy_btn = wx.Button(side_panel, label="Check Merge Policy")
        self._policy_btn.SetName("Read merge policy for the pull request base branch")
        self._policy_btn.SetHelpText(
            "Read branch protection, applicable rulesets, CODEOWNERS location, "
            "merge-queue status, and the pull request head revision."
        )
        side_sizer.Add(self._policy_btn, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        self._summary = wx.TextCtrl(
            side_panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        self._summary.SetName("Pull request review summary and merge readiness")
        self._summary.SetHelpText("Copyable summary of the pull request's review and merge status.")
        side_sizer.Add(self._summary, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        checks_label = wx.StaticText(side_panel, label="Checks")
        checks_label.SetName("Checks")
        checks_label.SetHelpText(
            "Continuous-integration checks on the pull request's latest commit."
        )
        side_sizer.Add(checks_label, 0, wx.LEFT | wx.TOP, 6)
        self._check_list = wx.ListBox(side_panel, choices=[])
        self._check_list.SetName("Check runs; activate one to open its job")
        self._check_list.SetHelpText("Double-click a check to open its details on GitHub.")
        set_spoken_name(self._check_list, "Check runs; activate one to open its job")
        side_sizer.Add(self._check_list, 1, wx.EXPAND | wx.ALL, 6)
        side_panel.SetSizer(side_sizer)

        detail_splitter.SplitVertically(self._thread_detail, side_panel, 590)
        outer_splitter.SplitVertically(thread_panel, detail_splitter, 300)
        root.Add(outer_splitter, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self._status = wx.StaticText(panel, label="")
        self._status.SetName("Review action status")
        self._status.SetHelpText("Reports loading progress and the outcome of review actions.")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._next_unresolved_btn = wx.Button(panel, label="Next &Unresolved")
        self._next_unresolved_btn.SetName("Move to the next known unresolved review thread")
        self._next_unvisited_btn = wx.Button(panel, label="Next Un&visited")
        self._next_unvisited_btn.SetName(
            "Move to the next review thread not yet visited in this session"
        )
        self._browser_btn = wx.Button(panel, label="Open on &GitHub")
        self._browser_btn.SetName("Open this pull request on GitHub in a browser")
        self._browser_btn.SetHelpText("Open the pull request page in your default browser.")
        self._copy_btn = wx.Button(panel, label="Copy Review &Summary")
        self._copy_btn.SetName("Copy the pull request review summary")
        self._copy_btn.SetHelpText("Copy the loaded review summary to the clipboard.")
        self._submit_btn = wx.Button(panel, label="&Compose Review…")
        self._submit_btn.SetName("Compose, save locally, or submit a review for this pull request")
        self._submit_btn.SetHelpText(
            "Review drafts save locally. Submitting is a separate explicit action in the composer."
        )
        self._reply_btn = wx.Button(panel, label="&Reply to Thread…")
        self._reply_btn.SetName("Reply to the selected pull request review thread")
        self._reply_btn.SetHelpText("Post a reply to the selected review conversation.")
        self._reviewers_btn = wx.Button(panel, label="Request Revie&wers…")
        self._reviewers_btn.SetName("Request reviewers for this pull request")
        self._reviewers_btn.SetHelpText("Request reviews from one or more GitHub usernames.")
        self._draft_btn = wx.Button(panel, label="&Mark Ready")
        self._draft_btn.SetName("Change this pull request between draft and ready for review")
        self._draft_btn.SetHelpText(
            "Toggle whether the pull request is a draft or ready for review."
        )
        self._update_btn = wx.Button(panel, label="Update &Branch…")
        self._update_btn.SetName("Update the pull request branch from its base branch")
        self._update_btn.SetHelpText("Merge the base branch into this pull request's branch.")
        self._merge_btn = wx.Button(panel, label="&Auto-Merge and Queue…")
        self._merge_btn.SetName("Auto-merge, merge queue and combined check status")
        self._merge_btn.SetHelpText(
            "Turn auto-merge on with a merge method or off, add the pull request to the "
            "merge queue or take it out, or hear how many required checks pass."
        )
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close pull request review")
        close_btn.SetHelpText("Close the review window.")
        self._write_buttons = (
            self._submit_btn,
            self._reply_btn,
            self._reviewers_btn,
            self._draft_btn,
            self._update_btn,
            self._merge_btn,
        )
        for button in (
            self._next_unresolved_btn,
            self._next_unvisited_btn,
            self._browser_btn,
            self._copy_btn,
            *self._write_buttons,
        ):
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        self._browser_btn.Bind(wx.EVT_BUTTON, self._open_pr)
        self._copy_btn.Bind(wx.EVT_BUTTON, self._copy_summary)
        self._policy_btn.Bind(wx.EVT_BUTTON, self._load_merge_policy)
        self._next_unresolved_btn.Bind(
            wx.EVT_BUTTON, lambda _event: self._next_thread(unresolved_only=True)
        )
        self._next_unvisited_btn.Bind(
            wx.EVT_BUTTON, lambda _event: self._next_thread(unresolved_only=False)
        )
        self._submit_btn.Bind(wx.EVT_BUTTON, self._submit_review)
        self._reply_btn.Bind(wx.EVT_BUTTON, self._reply_to_thread)
        self._reviewers_btn.Bind(wx.EVT_BUTTON, self._request_reviewers)
        self._draft_btn.Bind(wx.EVT_BUTTON, self._toggle_draft)
        self._update_btn.Bind(wx.EVT_BUTTON, self._update_branch)
        self._merge_btn.Bind(wx.EVT_BUTTON, self._show_merge_menu)
        self._outline.Bind(wx.EVT_TREE_SEL_CHANGED, self._select_node)
        self._outline.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._activate_node)
        self._outline.Bind(wx.EVT_CONTEXT_MENU, self._show_node_menu)
        self._outline.Bind(wx.EVT_CHAR_HOOK, self._on_review_key)
        self._thread_detail.Bind(wx.EVT_CHAR_HOOK, self._on_review_key)
        self._thread_detail.Bind(wx.EVT_CONTEXT_MENU, self._show_node_menu)
        self._check_list.Bind(wx.EVT_LISTBOX_DCLICK, self._open_check)
        for button in self._write_buttons:
            button.Enable(False)

    def show(self) -> None:
        wx = self._wx
        self._refresh()
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
            show_modal_dialog(self.dialog, "Pull Request Review", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _refresh(self) -> None:
        if self._loading:
            return
        self._loading = True
        self._refresh_generation += 1
        generation = self._refresh_generation
        self._status.SetLabel("Loading review threads, checks, and status…")

        def worker() -> None:
            wx = self._wx
            try:
                thread_result = self._client.fetch_review_threads(self._repo, self._number)
                threads = thread_result.items
                state = self._client.fetch_review_state(
                    self._repo,
                    self._number,
                    threads=threads,
                    thread_result=thread_result,
                )
                diff_error = ""
                try:
                    diff = self._client._provider.fetch_pull_diff(self._repo, self._number)
                except GitHubItemsError as exc:
                    diff, diff_error = None, str(exc.args[0]) if exc.args else str(exc)
            except GitHubReviewError as exc:
                wx.CallAfter(self._refresh_failed, str(exc), generation)
                return
            wx.CallAfter(self._refresh_landed, generation, state, threads, diff, diff_error)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: review data fetch.

    def _refresh_landed(
        self,
        generation: int,
        state: object,
        threads: tuple[GitHubReviewThread, ...],
        diff: GitHubPullDiff | None,
        diff_error: str,
    ) -> None:
        if generation != self._refresh_generation or not dialog_alive(self.dialog):
            return
        self._refresh_ready(state, threads, diff)
        if diff_error:
            # The threads and checks loaded; say plainly that the changed files did not.
            message = f"Could not load the diff: {diff_error}"
            self._status.SetLabel(f"Review loaded. {message}")
            self._announce(message)

    def _refresh_failed(self, message: str, generation: int | None = None) -> None:
        if not dialog_alive(self.dialog):
            return
        if generation is not None and generation != self._refresh_generation:
            return
        self._loading = False
        self._status.SetLabel(f"Could not load review: {message}")
        self._announce(f"Could not load pull request review: {message}")

    def _node_kind(self) -> tuple[str, int]:
        item = self._outline.GetSelection()
        return self._nodes.get(int(item.GetID()), ("", -1)) if item.IsOk() else ("", -1)

    def _select_node(self, _event: object) -> None:
        kind, index = self._node_kind()
        self._reply_btn.Enable(False)
        if kind == "pr" and self._state is not None:
            self._thread_detail.SetValue(self._state.summary_text())
            return
        if kind == "files":
            self._thread_detail.SetValue(
                "Expand to explore changed files and their review threads."
            )
            return
        if kind == "file":
            path = self._outline.GetItemText(self._outline.GetSelection())
            file = (
                next((f for f in self._diff.files if f.filename == path), None)
                if self._diff
                else None
            )
            self._thread_detail.SetValue(
                f"{path}\n{file.status}; +{file.additions} -{file.deletions} lines."
                if file
                else f"{path}\nReview comments are available; file diff unavailable."
            )
            return
        if kind == "checks":
            self._thread_detail.SetValue(self._state.checks_summary if self._state else "")
            return
        if kind == "check" and 0 <= index < len(self._checks):
            check = self._checks[index]
            self._thread_detail.SetValue(
                f"{check.name}: {check.state_display}\n{check.summary}\n{check.url}".strip()
            )
            return
        if kind != "thread" or not 0 <= index < len(self._threads):
            self._thread_detail.SetValue("No review threads." if not self._threads else "")
            return
        thread = self._threads[index]
        self._visited_thread_ids.add(self._thread_visit_key(index))
        self._reply_btn.Enable(
            self._client.can_write
            and self._state is not None
            and self._state.state == "open"
            and not self._state.merged
            and thread.root.id > 0
        )
        lines = [thread.header, ""]
        if thread.resolution_error:
            lines.extend([f"Resolution status could not be loaded: {thread.resolution_error}", ""])
        for comment in thread.comments:
            when = f" — {comment.created_at}" if comment.created_at else ""
            lines.extend([
                f"{comment.author}{when}",
                comment.body,
                "",
            ])
        self._thread_detail.SetValue("\n".join(lines).rstrip())

    def _thread_visit_key(self, index: int) -> str:
        thread = self._threads[index]
        return (
            thread.root.id or f"{thread.root.path}:{thread.root.line}:{thread.root.author}:{index}"
        )

    def _next_thread(self, *, unresolved_only: bool) -> None:
        if not self._threads:
            self._announce("No review threads are loaded.")
            return
        kind, current = self._node_kind()
        start = current if kind == "thread" else -1
        order = [*range(start + 1, len(self._threads)), *range(0, start + 1)]
        if unresolved_only:
            candidates = [index for index in order if self._threads[index].resolved is False]
            if not candidates:
                unknown = any(thread.resolved is None for thread in self._threads)
                self._announce(
                    "No known unresolved threads; resolution data is unavailable for some threads."
                    if unknown
                    else "No unresolved review threads."
                )
                return
            if len(candidates) == 1 and candidates[0] == current:
                self._announce("This is the only unresolved review thread.")
                return
        else:
            candidates = [
                index
                for index in order
                if self._thread_visit_key(index) not in self._visited_thread_ids
            ]
            if not candidates:
                self._announce("You have visited every loaded review thread in this session.")
                return
        index = candidates[0]
        self._visited_thread_ids.add(self._thread_visit_key(index))
        self._outline.SelectItem(self._thread_items[index])
        self._outline.SetFocus()
        thread = self._threads[index]
        label = "unresolved" if unresolved_only else "unvisited"
        self._announce(
            f"Moved to {label} thread by {thread.root.author}, "
            f"line {thread.root.line or 'unknown'}."
        )

    def _open_pr(self, _event: object) -> None:
        if self._state is not None and self._state.url:
            if webbrowser.open(self._state.url):
                self._announce("Opened pull request in browser.")
            else:
                self._announce("Could not open the pull request in a browser.")

    def _copy_summary(self, _event: object) -> None:
        if self._state is None:
            self._announce("The review summary is not loaded yet.")
            return
        wx = self._wx
        if not wx.TheClipboard.Open():
            self._status.SetLabel("Could not open the clipboard.")
            self._announce("Could not copy the review summary.")
            return
        try:
            copied = wx.TheClipboard.SetData(wx.TextDataObject(self._state.summary_text()))
        finally:
            wx.TheClipboard.Close()
        if copied:
            self._announce(f"Copied the review summary for pull request #{self._number}.")
        else:
            self._status.SetLabel("Could not copy the review summary.")
            self._announce("Could not copy the review summary.")

    def _show_native(self, dialog: object, title: str) -> int:
        return show_modal_dialog(dialog, title, announce=self._announce)

    def _confirm(self, message: str, title: str) -> bool:
        wx = self._wx
        dialog = wx.MessageDialog(
            self.dialog,
            message,
            title,
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        try:
            return self._show_native(dialog, title) == wx.ID_YES
        finally:
            dialog.Destroy()

    def _text_entry(self, message: str, title: str) -> str | None:
        wx = self._wx
        dialog = wx.TextEntryDialog(self.dialog, message, title)
        try:
            if self._show_native(dialog, title) != wx.ID_OK:
                return None
            value = dialog.GetValue().strip()
            return value or None
        finally:
            dialog.Destroy()

    def _request_reviewers(self, _event: object) -> None:
        value = self._text_entry("GitHub usernames, separated by commas:", "Request Reviewers")
        if value is None:
            return
        reviewers = [name.strip() for name in value.split(",") if name.strip()]
        self._run_action(
            lambda: self._client.request_reviewers(self._repo, self._number, reviewers),
            f"Review requested from {', '.join(reviewers)}.",
        )

    def _reply_to_thread(self, _event: object) -> None:
        kind, index = self._node_kind()
        if kind != "thread" or not 0 <= index < len(self._threads):
            self._announce("Select a review thread first.")
            return
        if not self._reply_btn.IsEnabled():
            self._announce("Sign in and select an open pull request to reply.")
            return
        body = self._text_entry("Reply to this review thread:", "Reply to Review Thread")
        if body is None:
            return
        comment_id = self._threads[index].root.id
        self._run_action(
            lambda: self._client.reply_to_thread(self._repo, self._number, comment_id, body),
            "Reply posted to the review thread.",
        )

    def _on_review_key(self, event: object) -> None:
        if event.ControlDown() and event.GetKeyCode() in (ord("R"), ord("r")):
            if getattr(event, "ShiftDown", lambda: False)():
                self._change_thread_resolution(None)
            else:
                self._reply_to_thread(None)
            return
        event.Skip()

    def _activate_node(self, _event: object) -> None:
        kind, index = self._node_kind()
        if kind == "file":
            self._open_file_diff(None)
        elif kind == "check":
            self._open_selected_check(None)
        elif kind == "thread":
            self._thread_detail.SetFocus()
        else:
            item = self._outline.GetSelection()
            if self._outline.IsExpanded(item):
                self._outline.Collapse(item)
            else:
                self._outline.Expand(item)


__all__ = ["GitHubPullReviewDialog"]
