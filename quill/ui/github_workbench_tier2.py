"""Turn a workflow on or off, and answer an invitation to a repository (GitHub PRD 14.1).

* **Turn Workflow On or Off...** on a workflow's row says its state in words
  (on, turned off, turned off by GitHub after 60 days without activity) and
  asks before changing it. The work is :mod:`quill.core.github.workflow_state`.
* **Accept Invitation...** and **Decline Invitation...** on a row of Needs My
  Attention > Invitations answer it, each after asking. The work is
  :mod:`quill.core.github.repo_invitations`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.workflows import GitHubWorkflow

__all__ = ["TIER2_REASONS", "TIER2_VERBS", "GitHubWorkbenchTier2Mixin"]

TIER2_VERBS: dict[str, frozenset[str]] = {
    "workflow_state": frozenset({"workflow"}),
    "accept_invitation": frozenset({"invitation"}),
    "decline_invitation": frozenset({"invitation"}),
}

TIER2_REASONS: dict[str, str] = {
    "workflow_state": "Turning a workflow on or off is for a workflow, while you are signed in.",
    "accept_invitation": "Accept is for an invitation that has not expired.",
    "decline_invitation": "Decline is for an invitation, while you are signed in.",
}


class GitHubWorkbenchTier2Mixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _confirm: Callable[[str, str], bool]

    def github_api(self) -> Any:
        raise NotImplementedError

    # -- workflows -----------------------------------------------------------------

    def _fits_workflow_state(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubWorkflow) and row.id > 0

    def _do_workflow_state(self, ref: Any, row: object) -> None:
        from quill.core.github.workflow_state import is_enabled, set_enabled, state_words

        assert isinstance(row, GitHubWorkflow)
        on = not is_enabled(row.state)
        now = state_words(row.state)
        question = (
            f"{row.name} is {now}. Turn it on, so it runs on its triggers again?"
            if on
            else f"{row.name} is on. Turn it off? Nothing starts it, not even Run Workflow, "
            "until it is turned on again."
        )
        if not self._confirm("Turn Workflow On or Off", question):
            return
        api, repository = self.github_api(), ref.instance
        self._background(
            "turn the workflow on" if on else "turn the workflow off",
            lambda: set_enabled(api, repository, row.id, row.name, on),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    # -- invitations ---------------------------------------------------------------

    @staticmethod
    def _invitation(row: object) -> ExploreRow | None:
        return row if isinstance(row, ExploreRow) and row.kind == "invitation" else None

    def _fits_accept_invitation(self, row: object) -> bool:
        found = self._invitation(row)
        return self.signed_in and found is not None and "expired" not in found.label

    def _fits_decline_invitation(self, row: object) -> bool:
        return self.signed_in and self._invitation(row) is not None

    def _answer(self, row: object, *, accept: bool) -> None:
        from quill.core.github.repo_invitations import accept as accept_it
        from quill.core.github.repo_invitations import decline

        found = self._invitation(row)
        if found is None:
            return
        repository, key = found.repo, found.key
        question = (
            f"Accept the invitation to {repository}? {found.detail.split('.')[0]}."
            if accept
            else f"Decline the invitation to {repository}? To join later, you would need a "
            "new invitation."
        )
        if not self._confirm("Invitation", question):
            return
        api = self.github_api()
        call = accept_it if accept else decline
        self._background(
            "answer the invitation",
            lambda: call(api, key, repository),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    def _do_accept_invitation(self, _ref: Any, row: object) -> None:
        self._answer(row, accept=True)

    def _do_decline_invitation(self, _ref: Any, row: object) -> None:
        self._answer(row, accept=False)
