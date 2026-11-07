"""On-demand repository merge-policy diagnostics in the review surface."""

from __future__ import annotations

import threading
from dataclasses import replace

from quill.core.github.merge_policy import GitHubMergePolicy, GitHubPullQueueState
from quill.ui.dialog_contract import dialog_alive


class GitHubPullReviewPolicyMixin:
    """Fetch branch policy only when the reviewer asks to inspect it."""

    def _load_merge_policy(self, _event: object) -> None:
        if self._policy_loading:
            return
        state = self._state
        if state is None or not state.base_ref:
            self._announce("Load the pull request before checking its merge policy.")
            return
        self._policy_loading = True
        self._policy_btn.Enable(False)
        self._status.SetLabel("Reading base-branch policy and merge-queue status…")
        expected_sha = state.head_sha

        def worker() -> None:
            try:
                policy, queue_state = self._client.fetch_merge_policy_context(
                    self._repo,
                    self._number,
                    state.base_ref,
                    expected_head_sha=expected_sha,
                )
            except Exception as exc:  # noqa: BLE001 - keep the review dialog usable
                self._wx.CallAfter(self._merge_policy_failed, expected_sha, str(exc))
                return
            self._wx.CallAfter(
                self._merge_policy_loaded,
                expected_sha,
                policy,
                queue_state,
            )

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: explicit policy read.

    def _merge_policy_failed(self, expected_sha: str, error: str) -> None:
        if not dialog_alive(self.dialog):
            return
        self._policy_loading = False
        state = self._state
        if state is not None and state.head_sha == expected_sha:
            self._policy_btn.Enable(bool(state.base_ref) and state.state == "open")
        self._status.SetLabel(f"Could not check merge policy: {error}")
        self._announce(f"Could not check merge policy: {error}")

    def _merge_policy_loaded(
        self,
        expected_sha: str,
        policy: GitHubMergePolicy,
        queue_state: GitHubPullQueueState | None,
    ) -> None:
        if not dialog_alive(self.dialog):
            return
        self._policy_loading = False
        state = self._state
        if state is None or state.head_sha != expected_sha:
            self._status.SetLabel(
                "The pull request changed during the policy check. Refresh and try again."
            )
            self._announce(
                "The pull request changed during the policy check. Refresh and try again."
            )
            return
        updated = replace(state, merge_policy=policy, merge_queue_state=queue_state)
        self._refresh_ready(updated, self._threads, self._diff)
        self._status.SetLabel(
            f"Merge policy checked for pull request head {expected_sha[:12] or 'unknown'}; "
            "refresh the review to recheck after new commits."
        )
        self._announce(
            "Merge policy and merge-queue status loaded for the current pull request head."
        )


__all__ = ["GitHubPullReviewPolicyMixin"]
