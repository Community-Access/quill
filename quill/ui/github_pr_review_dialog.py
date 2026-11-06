"""Accessible pull-request review surface: threads, checks, and review actions."""

from __future__ import annotations

import threading
import webbrowser
from typing import TYPE_CHECKING

from quill.core.github.items_provider import GitHubItemsError, GitHubPullDiff
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
from quill.ui.spoken_name import set_spoken_name

if TYPE_CHECKING:
    from collections.abc import Callable

    from quill.core.github.items_provider import GitHubItemsProvider


class GitHubPullReviewDialog(GitHubPullReviewMenusMixin):
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
        self._repo = repo
        self._number = number
        self._announce = announce_cb or (lambda _message: None)
        self._state: GitHubPullReviewState | None = None
        self._threads: tuple[GitHubReviewThread, ...] = ()
        self._checks: tuple[GitHubCheckRun, ...] = ()
        self._diff: GitHubPullDiff | None = None
        self._nodes: dict[int, tuple[str, int]] = {}
        self._loading = False

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
        self._thread_detail.SetName("Selected review thread, including all replies")
        self._thread_detail.SetHelpText(
            "The selected review conversation, including file and line context."
        )

        side_panel = wx.Panel(detail_splitter)
        side_sizer = wx.BoxSizer(wx.VERTICAL)
        summary_label = wx.StaticText(side_panel, label="Review summary")
        summary_label.SetName("Review summary")
        summary_label.SetHelpText("Plain-language pull request status and reviewer summary.")
        side_sizer.Add(summary_label, 0, wx.ALL, 6)
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
        self._browser_btn = wx.Button(panel, label="Open on &GitHub")
        self._browser_btn.SetName("Open this pull request on GitHub in a browser")
        self._browser_btn.SetHelpText("Open the pull request page in your default browser.")
        self._copy_btn = wx.Button(panel, label="Copy Review &Summary")
        self._copy_btn.SetName("Copy the pull request review summary")
        self._copy_btn.SetHelpText("Copy the loaded review summary to the clipboard.")
        self._submit_btn = wx.Button(panel, label="Submit Re&view…")
        self._submit_btn.SetName("Approve, request changes, or comment on this pull request")
        self._submit_btn.SetHelpText("Submit one of GitHub's three review decisions.")
        self._reply_btn = wx.Button(panel, label="&Reply to Thread…")
        self._reply_btn.SetName("Reply to the selected pull request review thread")
        self._reply_btn.SetHelpText("Post a reply to the selected review conversation.")
        self._reviewers_btn = wx.Button(panel, label="Request Revie&wers…")
        self._reviewers_btn.SetName("Request reviewers for this pull request")
        self._reviewers_btn.SetHelpText("Request reviews from one or more GitHub usernames.")
        self._draft_btn = wx.Button(panel, label="Mark &Ready")
        self._draft_btn.SetName("Change this pull request between draft and ready for review")
        self._draft_btn.SetHelpText(
            "Toggle whether the pull request is a draft or ready for review."
        )
        self._update_btn = wx.Button(panel, label="&Update Branch…")
        self._update_btn.SetName("Update the pull request branch from its base branch")
        self._update_btn.SetHelpText("Merge the base branch into this pull request's branch.")
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close pull request review")
        close_btn.SetHelpText("Close the review window.")
        self._write_buttons = (
            self._submit_btn,
            self._reply_btn,
            self._reviewers_btn,
            self._draft_btn,
            self._update_btn,
        )
        for button in (
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
        self._submit_btn.Bind(wx.EVT_BUTTON, self._submit_review)
        self._reply_btn.Bind(wx.EVT_BUTTON, self._reply_to_thread)
        self._reviewers_btn.Bind(wx.EVT_BUTTON, self._request_reviewers)
        self._draft_btn.Bind(wx.EVT_BUTTON, self._toggle_draft)
        self._update_btn.Bind(wx.EVT_BUTTON, self._update_branch)
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
        self._status.SetLabel("Loading review threads, checks, and status…")

        def worker() -> None:
            wx = self._wx
            try:
                threads = self._client.fetch_review_threads(self._repo, self._number)
                state = self._client.fetch_review_state(self._repo, self._number, threads=threads)
                try:
                    diff = self._client._provider.fetch_pull_diff(self._repo, self._number)
                except GitHubItemsError:
                    diff = None
            except GitHubReviewError as exc:
                wx.CallAfter(self._refresh_failed, str(exc))
                return
            wx.CallAfter(self._refresh_ready, state, threads, diff)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: review data fetch.

    def _refresh_failed(self, message: str) -> None:
        if not dialog_alive(self.dialog):
            return
        self._loading = False
        self._status.SetLabel(f"Could not load review: {message}")
        self._announce(f"Could not load pull request review: {message}")

    def _refresh_ready(
        self,
        state: GitHubPullReviewState,
        threads: tuple[GitHubReviewThread, ...],
        diff: GitHubPullDiff | None = None,
    ) -> None:
        if not dialog_alive(self.dialog):
            return
        previous = self._node_kind()
        previous_id = (
            self._threads[previous[1]].root.id
            if previous[0] == "thread" and 0 <= previous[1] < len(self._threads)
            else None
        )
        self._loading = False
        self._state = state
        self._threads = threads
        self._checks = state.checks
        self._diff = diff
        self._header.SetLabel(
            f"PR #{state.number}: {state.merge_readiness} "
            f"Reviews: {state.review_decision}. Checks: {state.checks_summary}. "
            f"{state.thread_count} review thread(s), "
            f"{state.outdated_thread_count} outdated."
        )
        self._summary.SetValue(state.summary_text())
        self._outline.DeleteAllItems()
        self._nodes.clear()
        root = self._outline.AddRoot(f"PR #{state.number}: {state.title}")
        self._nodes[int(root.GetID())] = ("pr", 0)
        files_root = self._outline.AppendItem(root, "Changed files")
        self._nodes[int(files_root.GetID())] = ("files", 0)
        file_names = list(dict.fromkeys([file.filename for file in diff.files] if diff else []))
        file_names.extend(
            path
            for path in dict.fromkeys(thread.root.path for thread in threads)
            if path and path not in file_names
        )
        selected = None
        for file_index, path in enumerate(file_names):
            file_node = self._outline.AppendItem(files_root, path)
            self._nodes[int(file_node.GetID())] = ("file", file_index)
            for index, thread in enumerate(threads):
                if thread.root.path != path:
                    continue
                label = (
                    f"Line {thread.root.line or 'unknown'}, {thread.root.author}, "
                    f"{thread.reply_count} replies" + (", outdated" if thread.outdated else "")
                )
                node = self._outline.AppendItem(file_node, label)
                self._nodes[int(node.GetID())] = ("thread", index)
                if thread.root.id == previous_id:
                    selected = node
            if self._outline.ItemHasChildren(file_node):
                self._outline.Expand(file_node)
        general = [(index, thread) for index, thread in enumerate(threads) if not thread.root.path]
        if general:
            general_node = self._outline.AppendItem(root, "General conversations")
            self._nodes[int(general_node.GetID())] = ("threads", 0)
            for index, thread in general:
                node = self._outline.AppendItem(
                    general_node, f"{thread.root.author}, {thread.reply_count} replies"
                )
                self._nodes[int(node.GetID())] = ("thread", index)
                if thread.root.id == previous_id:
                    selected = node
            self._outline.Expand(general_node)
        checks_root = self._outline.AppendItem(root, f"Checks ({len(self._checks)})")
        self._nodes[int(checks_root.GetID())] = ("checks", 0)
        for index, check in enumerate(self._checks):
            node = self._outline.AppendItem(checks_root, f"{check.state_display}: {check.name}")
            self._nodes[int(node.GetID())] = ("check", index)
        self._outline.Expand(root)
        self._outline.Expand(files_root)
        self._outline.Expand(checks_root)
        self._outline.SelectItem(selected or root)
        self._check_list.Set([
            f"{check.state_display}: {check.name}"
            + (f" — {check.summary}" if check.summary else "")
            for check in self._checks
        ])
        self._draft_btn.SetLabel("Mark &Ready" if state.draft else "Convert to &Draft")
        can_change = self._client.can_write and state.state == "open" and not state.merged
        self._submit_btn.Enable(can_change)
        self._reviewers_btn.Enable(can_change)
        self._draft_btn.Enable(can_change)
        self._update_btn.Enable(can_change and not state.draft)
        self._select_node(None)
        self._status.SetLabel("Review loaded.")
        self._announce(f"Review loaded for pull request #{state.number}. {state.merge_readiness}")

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
        self._reply_btn.Enable(
            self._client.can_write
            and self._state is not None
            and self._state.state == "open"
            and not self._state.merged
            and thread.root.id > 0
        )
        lines = [thread.header, ""]
        for comment in thread.comments:
            when = f" — {comment.created_at}" if comment.created_at else ""
            lines.extend([
                f"{comment.author}{when}",
                comment.body,
                "",
            ])
        self._thread_detail.SetValue("\n".join(lines).rstrip())

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

    def _submit_review(self, _event: object) -> None:
        if not self._client.can_write:
            self._announce("Sign in to GitHub to submit a review.")
            return
        wx = self._wx
        choices = ["Approve", "Request changes", "Comment"]
        dialog = wx.SingleChoiceDialog(
            self.dialog, "Choose a review action:", "Submit Review", choices
        )
        try:
            if self._show_native(dialog, "Submit Review") != wx.ID_OK:
                return
            choice = dialog.GetSelection()
        finally:
            dialog.Destroy()
        if choice not in (0, 1, 2):
            self._announce("Choose a review action first.")
            return
        event = ("approve", "request changes", "comment")[choice]
        body = ""
        if event != "approve":
            body = self._text_entry("Review message:", "Submit Review") or ""
            if not body:
                self._announce("Review cancelled; a message is required.")
                return
        if event == "request changes" and not self._confirm(
            "Submit a changes-requested review for this pull request?",
            "Request Changes",
        ):
            return
        self._run_action(
            lambda: self._client.submit_review(self._repo, self._number, event, body),
            f"Review submitted on pull request #{self._number}.",
        )

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
