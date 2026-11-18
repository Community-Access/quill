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


# -- tags ------------------------------------------------------------------------


def test_new_tag_asks_name_and_target_then_makes_it(monkeypatch) -> None:
    from tests.unit.core.github_workbench.test_tags import FakeApi as TagApi

    window = _Window()
    window.api = TagApi()
    answers = ["v1.2.0", "main"]
    window._ask_text = lambda *_a, **_k: answers.pop(0)
    window.frame.current = SimpleNamespace(key="tags")
    assert window._fits_new_tag(None)
    window._do_new_tag(REF, None)
    assert window.said[0] == "Made tag v1.2.0 on main, commit abc1234."


def test_delete_tag_names_the_release_built_on_it_first() -> None:
    from quill.core.github.items_provider import GitHubTag
    from tests.unit.core.github_workbench.test_tags import FakeApi as TagApi

    window = _Window(yes=False)
    window.api = TagApi(release="Version 1")
    window._do_delete_tag(REF, GitHubTag("v1"))
    assert "The release Version 1 is built on it" in window.asked[0]
    assert not any(method == "DELETE" for method, _p, _b in window.api.sent)


# -- your status -------------------------------------------------------------------


def test_set_your_status_reads_it_then_asks_each_part() -> None:
    from tests.unit.core.github_workbench.test_user_status import FakeApi as StatusApi

    window = _Window(yes=True)
    window.api = StatusApi({"message": "Old", "emoji": "", "indicatesLimitedAvailability": False})
    picks = [0, 0]
    window._choose = lambda _t, prompt, _l: (window.asked.append(prompt), picks.pop(0))[1]
    texts = ["Back Monday", "palm_tree"]
    window._ask_text = lambda *_a, **_k: texts.pop(0)
    window._do_user_status(REF, None)
    assert window.asked[0].startswith("Your status: Old.")
    assert window.api.sent[0]["message"] == "Back Monday"
    assert window.api.sent[0]["emoji"] == ":palm_tree:" and window.api.sent[0]["busy"] is True
    assert window.said[-1].startswith("Your status is now: Back Monday")


def test_clear_status_from_the_same_window() -> None:
    from tests.unit.core.github_workbench.test_user_status import FakeApi as StatusApi

    window = _Window()
    window.api = StatusApi(None)
    window._choose = lambda *_a: 1
    window._do_user_status(REF, None)
    assert window.said == ["Your status is cleared."]
