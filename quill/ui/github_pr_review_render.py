"""Render loaded pull-request state into the accessible review outline."""

from __future__ import annotations

from quill.core.github.items_provider import GitHubPullDiff
from quill.core.github.pr_review import GitHubPullReviewState, GitHubReviewThread
from quill.ui.dialog_contract import dialog_alive


class GitHubPullReviewRenderMixin:
    """Build the PR, file, thread, and check outline while preserving selection."""

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
        self._policy_btn.Enable(bool(state.base_ref) and state.state == "open")
        self._header.SetLabel(
            f"PR #{state.number}: {state.merge_readiness} "
            f"Reviews: {state.review_decision}. Checks: {state.checks_summary}. "
            f"{state.thread_count} review thread(s), "
            f"{state.unresolved_thread_count} unresolved, "
            f"{state.outdated_thread_count} outdated."
            + (" Review data is incomplete." if state.data_warnings else "")
        )
        self._summary.SetValue(state.summary_text())
        self._outline.DeleteAllItems()
        self._nodes.clear()
        self._thread_items.clear()
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
                    f"{thread.reply_count} replies"
                    + (", outdated" if thread.outdated else "")
                    + (
                        ", resolution unavailable"
                        if thread.resolved is None
                        else ", resolved"
                        if thread.resolved
                        else ", unresolved"
                    )
                )
                node = self._outline.AppendItem(file_node, label)
                self._nodes[int(node.GetID())] = ("thread", index)
                self._thread_items[index] = node
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
                self._thread_items[index] = node
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
        self._draft_btn.SetLabel("&Mark Ready" if state.draft else "Convert to &Draft")
        can_change = self._client.can_write and state.state == "open" and not state.merged
        self._submit_btn.Enable(can_change)
        self._reviewers_btn.Enable(can_change)
        self._draft_btn.Enable(can_change)
        self._update_btn.Enable(can_change and not state.draft)
        self._merge_btn.Enable(can_change)
        self._next_unresolved_btn.Enable(bool(threads))
        self._next_unvisited_btn.Enable(bool(threads))
        self._select_node(None)
        if state.data_warnings:
            self._status.SetLabel("Review data is incomplete. See the summary for details.")
            self._announce(
                f"Review loaded for pull request #{state.number} with incomplete data. "
                f"{state.merge_readiness}"
            )
        else:
            self._status.SetLabel("Review loaded.")
            self._announce(
                f"Review loaded for pull request #{state.number}. {state.merge_readiness}"
            )


__all__ = ["GitHubPullReviewRenderMixin"]
