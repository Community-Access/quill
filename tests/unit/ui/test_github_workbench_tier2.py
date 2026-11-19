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
    for verb in (
        "workflow_state",
        "accept_invitation",
        "decline_invitation",
        "tag_message",
        "transfer_repository",
    ):
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
    window._ask_optional = lambda *_a, **_k: ""
    window.frame.current = SimpleNamespace(key="tags")
    assert window._fits_new_tag(None)
    window._do_new_tag(REF, None)
    assert window.said[0] == "Made tag v1.2.0 on main, commit abc1234."


def test_new_tag_with_a_message_is_annotated_and_cancel_at_the_message_sends_nothing() -> None:
    from tests.unit.core.github_workbench.test_tags import FakeApi as TagApi

    window = _Window()
    window.api = TagApi()
    answers = ["v2", "main", "v3", "main"]
    window._ask_text = lambda *_a, **_k: answers.pop(0)
    window._ask_optional = lambda *_a, **_k: "Second beta"
    window._do_new_tag(REF, None)
    assert window.said[0] == "Made annotated tag v2 on main, commit abc1234."
    window.api = TagApi()
    window._ask_optional = lambda *_a, **_k: None
    window._do_new_tag(REF, None)
    assert not any(method == "POST" for method, _p, _b in window.api.sent)


def test_read_tag_message_says_who_when_and_what() -> None:
    from quill.core.github.items_provider import GitHubTag
    from tests.unit.core.github_workbench.test_tags import FakeApi as TagApi

    window = _Window()
    window.api = TagApi()
    assert window._fits_tag_message(GitHubTag("v9"))
    window._do_tag_message(REF, GitHubTag("v9"))
    assert window.said == ["v9, tagged by Jeff Bishop on 2026-11-18: First beta"]


# -- transferring a repository -------------------------------------------------------


def _typed(monkeypatch, answer: bool) -> list[str]:
    seen: list[str] = []

    class Typed:
        def __init__(self, _parent: Any, **kw: Any) -> None:
            seen.append(kw["expected"])

        def show(self) -> bool:
            return answer

    monkeypatch.setattr("quill.ui.github_repo_admin_dialogs.TypedConfirmDialog", Typed)
    return seen


def test_transfer_asks_the_owner_then_the_typed_name(monkeypatch) -> None:
    from tests.unit.core.github_workbench.test_repo_transfer import FakeApi as TransferApi

    seen = _typed(monkeypatch, True)
    window = _Window()
    window.api = TransferApi({"full_name": "team/r"})
    window._ask_text = lambda *_a, **_k: "@team"
    window.frame.frame = None
    window.frame.current = SimpleNamespace(template="repository")
    assert window._fits_transfer_repository(None)
    window._do_transfer_repository(REF, None)
    assert seen == ["o/r"]
    assert window.api.sent == [("POST", "/repos/o/r/transfer", {"new_owner": "team"})]
    assert window.said == ["Transferred o/r; it is now team/r. The old address redirects."]


def test_transfer_cancelled_at_the_typed_name_sends_nothing(monkeypatch) -> None:
    from tests.unit.core.github_workbench.test_repo_transfer import FakeApi as TransferApi

    _typed(monkeypatch, False)
    window = _Window()
    window.api = TransferApi()
    window._ask_text = lambda *_a, **_k: "team"
    window.frame.frame = None
    window._do_transfer_repository(REF, None)
    assert window.api.sent == []
    assert window.said == ["Cancelled; the repository was not transferred."]


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


def test_set_status_on_a_commit_asks_and_posts() -> None:
    from quill.core.github.items_provider import GitHubCommit
    from tests.unit.core.github_workbench.test_commit_status import FakeApi as StatusApi

    window = _Window()
    window.api = StatusApi()
    window._choose = lambda *_a: 1
    texts = ["lab", "2 failed", ""]
    window._ask_text = lambda *_a, **_k: texts.pop(0)
    window._do_commit_status(REF, GitHubCommit("abc1234def", "abc1234", "Fix it"))
    assert window.api.sent[0][2]["state"] == "failure"
    assert window.said == ["Set lab to failed on commit abc1234."]


# -- links an issue carries ---------------------------------------------------------


def _issue(number: int = 42) -> Any:
    from quill.core.github.items_provider import GitHubItem

    return GitHubItem(number, "Crash", "open", "", False)


def test_unlink_branch_chooses_then_asks(monkeypatch) -> None:
    from tests.unit.core.github_workbench.test_issue_links import FakeApi as LinkApi

    window = _Window()
    window.api = LinkApi()
    window._choose = lambda *_a: 0
    assert window._fits_unlink_branch(_issue())
    window._do_unlink_branch(REF, _issue())
    assert "Unlink branch 42-fix from #42?" in window.asked[0]
    assert "The branch itself is kept" in window.asked[0]
    assert "only its link to the issue is removed" in window.asked[0]
    assert window.said == ["Unlinked 42-fix from #42. The branch is still there."]


class _TwoLinks:
    """An issue with two linked branches; every GraphQL call is kept."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        self.sent.append(variables)
        if "linkedBranches" in query:
            nodes = [
                {"id": "LB_1", "ref": {"name": "42-fix"}},
                {"id": "LB_2", "ref": {"name": "b"}},
            ]
            return {"repository": {"issue": {"linkedBranches": {"nodes": nodes}}}}
        return {}


def _link_window(api: Any = None, *, yes: bool = True, pick: int = 0) -> _Window:
    window = _Window(yes=yes)
    window.api = api or _TwoLinks()
    window.chosen = []  # type: ignore[attr-defined]
    window._choose = lambda _t, _p, labels: window.chosen.append(labels) or pick  # type: ignore[attr-defined,method-assign]
    return window


def test_unlink_branch_with_several_asks_which_and_says_the_outcome_once() -> None:
    window = _link_window(pick=1)
    window._do_unlink_branch(REF, _issue())
    assert window.chosen == [["42-fix", "b"]]  # type: ignore[attr-defined]
    assert window.asked == [
        "Unlink branch b from #42? The branch itself is kept, with its commits; only its "
        "link to the issue is removed."
    ]
    assert window.api.sent[-1] == {"id": "LB_2"}
    assert window.said == ["Unlinked b from #42. The branch is still there."]


def test_unlink_branch_with_one_skips_the_chooser() -> None:
    from tests.unit.core.github_workbench.test_issue_links import FakeApi as LinkApi

    window = _link_window(LinkApi())
    window._do_unlink_branch(REF, _issue())
    assert window.chosen == []  # type: ignore[attr-defined]
    assert window.api.sent[-1] == {"id": "LB_1"}


def test_unlink_branch_declined_sends_nothing() -> None:
    window = _link_window(yes=False)
    window._do_unlink_branch(REF, _issue())
    assert [v for v in window.api.sent if "id" in v] == []
    assert window.said == []


def test_unlink_branch_on_an_issue_with_none_says_so() -> None:
    class _None(_TwoLinks):
        def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
            self.sent.append(variables)
            return {"repository": {"issue": {"linkedBranches": {"nodes": []}}}}

    window = _link_window(_None())
    window._do_unlink_branch(REF, _issue())
    assert window.said == ["#42 has no linked branches."]
    assert window.asked == []


# Read Only, Organize and Safe Mode for Unlink Branch are the dispatcher's one level
# check now: tests/unit/ui/test_github_workbench_level_gate.py.


# -- the issue sheet's Linked branches list ---------------------------------------------


class _Sheet:
    def __init__(self, rows: tuple[str, ...]) -> None:
        self.state = SimpleNamespace(loaded={"branches": rows})
        self.shown: list[tuple[str, tuple[str, ...]]] = []

    def set_table(self, key: str, rows: tuple[str, ...]) -> None:
        self.shown.append((key, rows))
        self.state.loaded[key] = rows


def _sheet_state(rows: tuple[str, ...] = ("42-fix", "b")) -> dict[str, Any]:
    loaded = SimpleNamespace(values={"title": "Crash", "branches": rows})
    return {"ident": {"repo": "o/r", "number": "42"}, "loaded": loaded, "sheet": _Sheet(rows)}


def test_remove_on_the_sheet_unlinks_that_branch_and_takes_it_off_the_list() -> None:
    window = _link_window()
    state = _sheet_state()
    window.act_on_linked_branch(state, "remove", "b")
    assert window.chosen == []  # type: ignore[attr-defined]
    assert "Unlink branch b from #42?" in window.asked[0]
    assert window.api.sent[-1] == {"id": "LB_2"}
    assert state["sheet"].shown == [("branches", ("42-fix",))]
    assert window.said == ["Unlinked b from #42. The branch is still there."]


def test_remove_on_the_sheet_of_a_branch_unlinked_meanwhile_sends_nothing() -> None:
    window = _link_window()
    state = _sheet_state(("gone",))
    window.act_on_linked_branch(state, "remove", "gone")
    assert window.asked == [] and state["sheet"].shown == []
    assert window.said == ["gone is no longer linked to #42. F5 reads the issue again."]


def test_change_on_the_sheet_explains_what_a_link_offers() -> None:
    window = _link_window()
    window.act_on_linked_branch(_sheet_state(), "change", "b")
    assert window.api.sent == []
    assert window.said == [
        "A linked branch has nothing to change: Remove unlinks it, and Add makes a new one."
    ]


def test_the_issue_sheet_shows_linked_branches_as_a_list_with_add_and_remove() -> None:
    from quill.core.github.sheets_items import ISSUE
    from quill.core.workbench.properties import FieldKind

    spec = ISSUE.sheet.field("branches")
    assert spec.kind is FieldKind.TABLE
    assert "the branch itself is kept" in spec.help


def test_the_sheet_list_routes_to_the_linked_branch_commands() -> None:
    from quill.ui.github_workbench_tools import GitHubWorkbenchToolsMixin

    seen: list[tuple[Any, ...]] = []
    checked: list[str] = []
    host = SimpleNamespace(
        act_on_linked_branch=lambda *args: seen.append(args),
        refused=lambda command_id: checked.append(command_id) or False,
    )
    state = _sheet_state()
    act = GitHubWorkbenchToolsMixin.table_action(host, SimpleNamespace(kind="issue"), state)  # type: ignore[arg-type]
    act(SimpleNamespace(key="branches"), "remove", "b")
    assert seen == [(state, "remove", "b")]
    assert checked == ["github.workbench.unlink_branch"]


def test_not_a_duplicate_asks_the_original() -> None:
    from tests.unit.core.github_workbench.test_issue_links import FakeApi as LinkApi

    window = _Window()
    window.api = LinkApi()
    window._ask_text = lambda *_a, **_k: "#3"
    window._do_not_duplicate(REF, _issue(7))
    assert window.said == ["#7 is no longer marked a duplicate of #3, Crash."]
