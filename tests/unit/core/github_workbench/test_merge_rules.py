"""The rules that block a pull request, each by name (GX09, complete.md 1.3)."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from typing import Any

from quill.core.github import merge_readiness as mr
from quill.core.github.merge_rules import name_blockers
from quill.core.github.rest_transport import GitHubRestError, RestResponse

RULES = "/repos/o/r/rules/branches/main"
PROTECTION = "/repos/o/r/branches/main/protection"


def _pull(**changes: Any) -> dict[str, Any]:
    pull: dict[str, Any] = {
        "state": "OPEN",
        "isDraft": False,
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "BLOCKED",
        "reviewDecision": "REVIEW_REQUIRED",
        "headRefOid": "abc1234def",
        "baseRefName": "main",
        "commits": {"nodes": [{"commit": {"statusCheckRollup": {"contexts": {"nodes": []}}}}]},
    }
    pull.update(changes)
    return pull


def _run(name: str, conclusion: str | None, *, done: bool = True) -> dict[str, Any]:
    return {
        "__typename": "CheckRun",
        "name": name,
        "status": "COMPLETED" if done else "IN_PROGRESS",
        "conclusion": conclusion,
        "isRequired": True,
    }


def _checks(*nodes: dict[str, Any]) -> dict[str, Any]:
    return {"nodes": [{"commit": {"statusCheckRollup": {"contexts": {"nodes": list(nodes)}}}}]}


def _rule(kind: str, ruleset: int = 7, source: str = "Repository", **params: Any) -> dict:
    return {
        "type": kind,
        "ruleset_id": ruleset,
        "ruleset_source_type": source,
        "ruleset_source": "o/r",
        "parameters": params,
    }


def _file(text: str) -> dict[str, Any]:
    return {"type": "file", "content": base64.b64encode(text.encode()).decode()}


class FakeApi:
    """Recorded answers by path; a status number answers as that HTTP error."""

    def __init__(self, pull: dict[str, Any], answers: Mapping[str, Any]) -> None:
        self.pull = pull
        self.answers = dict(answers)
        self.calls: list[str] = []

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        return {"repository": {"pullRequest": self.pull}}

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        page = (query or {}).get("page", "1")
        self.calls.append(path if page == "1" else f"{path}?page={page}")
        assert method == "GET", "naming rules never writes"
        answer = self.answers.get(path, 404)
        if isinstance(answer, int):
            raise GitHubRestError("GitHub said no.", status=answer)
        if isinstance(answer, list) and page != "1":
            answer = []
        return RestResponse(200, {}, answer)


BASE_ANSWERS: dict[str, Any] = {
    "/repos/o/r/rulesets": [{"id": 7, "name": "Protect main"}, {"id": 9, "name": "Org rules"}],
}


def _named(pull: dict[str, Any], **answers: Any) -> tuple[mr.Readiness, FakeApi]:
    api = FakeApi(pull, {**BASE_ANSWERS, **answers})
    return mr.load_readiness(api, "o/r", 4, named=True), api


def test_a_required_check_is_named_with_the_ruleset_that_wants_it() -> None:
    rules = [
        _rule(
            "required_status_checks",
            required_status_checks=[{"context": "build"}, {"context": "lint"}, {"context": "ok"}],
        )
    ]
    pull = _pull(
        reviewDecision="APPROVED",
        commits=_checks(_run("build", "FAILURE"), _run("ok", "SUCCESS")),
    )
    ready, _api = _named(pull, **{RULES: rules})
    assert ready.reasons == (
        'Check build, which the ruleset "Protect main" requires, failed. Re-run or fix it.',
        'Check lint, which the ruleset "Protect main" requires, has not reported on commit '
        "abc1234.",
    )
    assert not ready.can_merge
    # The generic "Required check build failed" is not said twice.
    assert "Required check" not in ready.sentence


def test_approving_reviews_are_counted_against_the_rule_that_wants_them() -> None:
    rules = [
        _rule("pull_request", ruleset=9, source="Organization", required_approving_review_count=2)
    ]
    reviews = [
        {"user": {"login": "ann"}, "state": "APPROVED"},
        {"user": {"login": "bob"}, "state": "APPROVED"},
        {"user": {"login": "bob"}, "state": "CHANGES_REQUESTED"},  # bob's latest counts
        {"user": {"login": "cy"}, "state": "COMMENTED"},
    ]
    ready, _api = _named(_pull(), **{RULES: rules, "/repos/o/r/pulls/4/reviews": reviews})
    assert ready.reasons == (
        'The ruleset "Org rules" from the organization wants 2 approving reviews; it has 1.',
    )
    assert "It needs an approving review." not in ready.reasons


CODEOWNERS = """# Owners
*           @o/everyone
/docs/      @ann
/src/ui/    @o/ui-team @carol
"""


def _owners_case(**more: Any) -> tuple[mr.Readiness, FakeApi]:
    rules = [
        _rule("pull_request", required_approving_review_count=1, require_code_owner_review=True)
    ]
    files = [{"filename": "docs/guide.md"}, {"filename": "src/ui/window.py"}]
    answers = {
        RULES: rules,
        "/repos/o/r/pulls/4/reviews": [{"user": {"login": "dave"}, "state": "APPROVED"}],
        "/repos/o/r/contents/.github/CODEOWNERS": _file(CODEOWNERS),
        "/repos/o/r/pulls/4/files": files,
        "/orgs/o/teams/ui-team/memberships/dave": 404,
        **more,
    }
    return _named(_pull(), **answers)


def test_the_codeowners_line_whose_owner_has_not_approved_is_named() -> None:
    ready, api = _owners_case()
    assert ready.reasons == (
        'The ruleset "Protect main" wants a code owner\'s review, and none from @ann has '
        "approved: .github/CODEOWNERS line 3, /docs/, owns 1 changed file, such as docs/guide.md.",
        'The ruleset "Protect main" wants a code owner\'s review, and none from @o/ui-team or '
        "@carol has approved: .github/CODEOWNERS line 4, /src/ui/, owns 1 changed file, such as "
        "src/ui/window.py.",
    )
    assert "/repos/o/r/contents/.github/CODEOWNERS" in api.calls


def test_a_team_member_approving_satisfies_the_teams_line() -> None:
    ready, _api = _owners_case(**{"/orgs/o/teams/ui-team/memberships/dave": {"state": "active"}})
    assert len(ready.reasons) == 1 and "line 3, /docs/" in ready.reasons[0]


def test_an_unreadable_team_is_said_as_unknown_never_as_missing() -> None:
    ready, _api = _owners_case(**{"/orgs/o/teams/ui-team/memberships/dave": 403})
    assert "QUILL could not tell whether @o/ui-team or @carol approved." in ready.reasons[1]


def test_the_merge_queue_rule_is_named_when_it_can_join_the_queue() -> None:
    pull = _pull(mergeStateStatus="CLEAN", reviewDecision="APPROVED", isMergeQueueEnabled=True)
    ready, _api = _named(pull, **{RULES: [_rule("merge_queue")]})
    assert ready.can_merge and ready.queue_required
    assert ready.sentence == (
        "#4 can join the merge queue for main, as of commit abc1234; main merges only "
        'through its queue, by the ruleset "Protect main".'
    )


def test_a_pull_that_can_merge_reads_no_rules_and_naming_never_blocks_it() -> None:
    api = FakeApi(_pull(mergeStateStatus="CLEAN", reviewDecision="APPROVED"), BASE_ANSWERS)
    ready = mr.load_readiness(api, "o/r", 4, named=True)
    assert ready.can_merge and ready.rules is None and api.calls == []
    # Even a rule that names a check never turns GitHub's "can merge" into "cannot".
    clean = mr.Readiness(number=4, head="abc1234def", base="main", merge_state="CLEAN")
    rules = [_rule("required_status_checks", required_status_checks=[{"context": "build"}])]
    found = name_blockers(FakeApi(_pull(), {**BASE_ANSWERS, RULES: rules}), "o/r", clean)
    assert found.blockers == ()


def test_classic_protection_names_checks_and_reviews() -> None:
    protection = {
        "required_status_checks": {"contexts": ["ci/legacy"], "checks": []},
        "required_pull_request_reviews": {"required_approving_review_count": 1},
    }
    ready, _api = _named(
        _pull(), **{RULES: [], PROTECTION: protection, "/repos/o/r/pulls/4/reviews": []}
    )
    assert ready.reasons == (
        "Check ci/legacy, which the branch protection on main requires, has not reported on "
        "commit abc1234.",
        "The branch protection on main wants 1 approving review; it has 0.",
    )


def test_without_admin_the_branch_still_names_its_checks_and_says_what_it_could_not_read() -> None:
    branch = {"protection": {"enabled": True, "required_status_checks": {"contexts": ["ci"]}}}
    ready, _api = _named(
        _pull(reviewDecision="APPROVED"),
        **{RULES: [], PROTECTION: 403, "/repos/o/r/branches/main": branch},
    )
    assert ready.reasons == (
        "Check ci, which the branch protection on main requires, has not reported on commit "
        "abc1234.",
    )
    assert ready.sentence.endswith(
        "QUILL could not read which reviews the branch protection on main wants (that needs "
        "admin access), so a rule there may not be named."
    )


def test_a_blocked_pull_with_no_named_rule_says_so_and_points_at_github() -> None:
    ready, _api = _named(_pull(reviewDecision="APPROVED"), **{RULES: []})
    assert ready.reasons == (
        "A rule on main blocks it, and GitHub's list of the branch's rules does not say which. "
        "The pull request's page on GitHub does.",
    )


def test_other_rules_are_offered_only_when_nothing_else_explains_the_block() -> None:
    rules = [_rule("required_signatures"), _rule("required_linear_history")]
    ready, _api = _named(_pull(reviewDecision="APPROVED"), **{RULES: rules})
    assert ready.reasons == (
        'The ruleset "Protect main" requires signed commits; that may be what blocks it.',
        'The ruleset "Protect main" requires a straight history, with no merge commits; '
        "that may be what blocks it.",
    )


def test_unreadable_rules_leave_github_s_answer_and_say_what_was_unread() -> None:
    ready, _api = _named(_pull(reviewDecision="APPROVED"), **{RULES: 403})
    assert not ready.can_merge
    assert "QUILL could not read the rulesets on main" in ready.sentence


def test_unexpected_failures_never_lose_github_s_answer(monkeypatch: Any) -> None:
    import quill.core.github.merge_rules as rules_module

    def boom(*_a: Any) -> Any:
        raise RuntimeError("broken")

    monkeypatch.setattr(rules_module, "name_blockers", boom)
    ready, _api = _named(_pull())
    assert ready.reasons == ("It needs an approving review.",)
    assert "QUILL could not read the rules on main" in ready.sentence
