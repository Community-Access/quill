"""Turn Workflow On or Off..., and Accept or Decline an invitation (GitHub PRD 14.1)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.repo_invitations import invitation_row
from quill.core.github.workflows import GitHubWorkflow
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from quill.ui.github_workbench_tier2 import GitHubWorkbenchTier2Mixin
from tests.unit.core.github_workbench.test_workflow_state_and_invitations import INVITE, FakeApi

REF = SimpleNamespace(instance="o/r")


class _Window(GitHubWorkbenchTier2Mixin):
    signed_in = True

    def __init__(self, yes: bool = True) -> None:
        self.api, self.yes = FakeApi(), yes
        self.said: list[str] = []
        self.asked: list[str] = []
        self.frame = SimpleNamespace(reload=lambda: self.said.append("(reloaded)"))

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _confirm(self, title: str, question: str) -> bool:
        self.asked.append(question)
        return self.yes

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


def test_registered() -> None:
    for verb in ("workflow_state", "accept_invitation", "decline_invitation"):
        assert verb in DEVELOPMENT_VERBS


def test_a_workflow_that_is_on_is_turned_off_after_asking() -> None:
    window = _Window()
    window._do_workflow_state(REF, GitHubWorkflow(12, "CI", ".github/workflows/ci.yml", "active"))
    assert "CI is on. Turn it off?" in window.asked[0]
    assert window.api.sent == [("PUT", "/repos/o/r/actions/workflows/12/disable")]
    assert window.said[0].startswith("Turned off CI.")


def test_a_workflow_github_turned_off_says_why_before_turning_it_on() -> None:
    window = _Window()
    flow = GitHubWorkflow(12, "CI", "ci.yml", "disabled_inactivity")
    window._do_workflow_state(REF, flow)
    assert "turned off by GitHub after 60 days without activity" in window.asked[0]
    assert window.api.sent == [("PUT", "/repos/o/r/actions/workflows/12/enable")]


def test_no_sends_nothing() -> None:
    window = _Window(yes=False)
    window._do_workflow_state(REF, GitHubWorkflow(12, "CI", "ci.yml", "active"))
    window._do_decline_invitation(REF, invitation_row(INVITE))
    assert window.api.sent == []


def test_invitations_are_answered_after_asking_and_expired_ones_cannot_be_accepted() -> None:
    window = _Window()
    row = invitation_row(INVITE)
    assert window._fits_accept_invitation(row)
    window._do_accept_invitation(REF, row)
    assert window.api.sent == [("PATCH", "/user/repository_invitations/77")]
    assert window.said[0] == "Accepted. You can now work in octo/app."
    expired = invitation_row({**INVITE, "expired": True})
    assert not window._fits_accept_invitation(expired)
    assert window._fits_decline_invitation(expired)
