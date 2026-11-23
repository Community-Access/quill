"""GH-R-151: the six writes once held back, each across repositories with a preview and a
result per repository, and the single-repository forms they stand on (New Ruleset and New
Environment). Against a recorded fake of the Workbench's GitHubApi: nothing reaches GitHub.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.across_alerts import (
    AlertNotFound,
    apply_dismiss,
    match_for,
    plan_dismiss,
)
from quill.core.github.across_branch_release import (
    apply_draft_releases,
    apply_merged_delete,
    plan_draft_releases,
    plan_merged_delete,
)
from quill.core.github.across_by_name import survey
from quill.core.github.across_changes import apply, plan_delete, plan_rename
from quill.core.github.across_more_changes import apply_more, plan_more_add
from quill.core.github.environments import EnvironmentRefused, create_environment
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.ruleset_new import RulesetRefused, create_ruleset, ruleset_request


class FakeApi:
    """GET answers by (method, path); a write is recorded and answered from the table too."""

    def __init__(self, answers: dict[tuple[str, str], Any]) -> None:
        self.answers = answers
        self.sent: list[tuple[str, str, Any]] = []
        self.queries: list[tuple[str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        if method != "GET":
            self.sent.append((method, path, body))
        else:
            self.queries.append((path, dict(query or {})))
        answer = self.answers.get((method, path))
        if callable(answer):
            answer = answer(query or {})
        if isinstance(answer, Exception):
            raise answer
        if answer is None:
            if method != "GET":
                return SimpleNamespace(status=200, data={}, headers={})
            raise GitHubRestError(f"404 Not Found: {path}", status=404)
        return SimpleNamespace(status=200, data=answer, headers={})


def _repo(push: bool = True, admin: bool = True, default: str = "main") -> dict[str, Any]:
    return {"default_branch": default, "permissions": {"push": push, "admin": admin}}


# -- milestones: rename and delete everywhere ------------------------------------------


def _milestone(number: int, title: str = "v1", open_: int = 2, closed: int = 3) -> dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "due_on": None,
        "description": "",
        "state": "open",
        "open_issues": open_,
        "closed_issues": closed,
    }


def _milestone_api() -> FakeApi:
    one, two = _milestone(1), _milestone(7)
    return FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(),
        ("GET", "/repos/a/three"): _repo(push=False, admin=False),
        ("GET", "/repos/a/one/milestones"): [one],
        ("GET", "/repos/a/two/milestones"): [two, _milestone(8, "v2")],
        ("GET", "/repos/a/three/milestones"): [_milestone(4)],
        ("GET", "/repos/a/one/milestones/1"): one,
        ("GET", "/repos/a/two/milestones/7"): two,
    })


def test_a_milestone_renamed_everywhere_is_undoable_and_a_clash_points_to_move_open_work() -> None:
    api = _milestone_api()
    found = survey(api, "milestones", ["a/one", "a/two", "a/three"])
    plan = plan_rename(found, found.row("v1"), "v2")
    one, two, three = plan.steps
    assert not one.blocked and one.preview() == "a/one: rename, v1 becomes v2"
    assert (
        "it already has v2; Move Open Work To... moves its open items into that one instead"
        in two.blocked
    )
    assert "needs write access" in three.blocked
    results = apply(api, plan)
    assert [r.ok for r in results] == [True, False, False]
    assert ("PATCH", "/repos/a/one/milestones/1", {"title": "v2"}) in api.sent
    log = results[0].log
    assert log is not None and log.kind == "milestone" and log.can_undo
    assert log.changes == (("title", "Title", "v1", "v2"),)
    assert dict(log.ident) == {"repo": "a/one", "number": "1"}


def test_a_milestone_renamed_on_github_meanwhile_is_left_alone() -> None:
    api = _milestone_api()
    found = survey(api, "milestones", ["a/one"])
    api.answers[("GET", "/repos/a/one/milestones/1")] = _milestone(1, "Version 1")
    (result,) = apply(api, plan_rename(found, found.row("v1"), "v9"))
    assert not result.ok and "renamed Version 1 on GitHub since you looked" in result.said
    assert api.sent == []


def test_a_milestone_deleted_everywhere_says_its_items_stay() -> None:
    api = _milestone_api()
    found = survey(api, "milestones", ["a/one", "a/two", "a/three"])
    plan = plan_delete(found, found.row("v1"))
    assert plan.steps[0].preview() == (
        "a/one: delete, v1; its 2 open items and 3 closed items stay, with no milestone"
    )
    one, two, three = apply(api, plan)
    assert one.ok and two.ok and not three.ok
    assert one.said == "deleted v1; its 2 open items and 3 closed items stay, with no milestone"
    assert [p for m, p, _b in api.sent if m == "DELETE"] == [
        "/repos/a/one/milestones/1",
        "/repos/a/two/milestones/7",
    ]
    assert one.log is not None and not one.log.can_undo


# -- environments: Add to Missing, and New Environment in one repository --------------


def test_an_environment_is_added_where_missing_as_the_winner() -> None:
    env = {
        "name": "production",
        "protection_rules": [{"type": "wait_timer", "wait_timer": 10}],
        "deployment_branch_policy": {"protected_branches": True, "custom_branch_policies": False},
    }
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(),
        ("GET", "/repos/a/one/environments"): {"environments": [env]},
        ("GET", "/repos/a/two/environments"): {"environments": []},
    })
    found = survey(api, "environments", ["a/one", "a/two"])
    row = found.row("production")
    plan = plan_more_add(found, row, row.copies[0].props)
    assert plan.steps[0].preview().startswith("a/two: create, gains production, wait_timer 10")
    (result,) = apply_more(api, plan)
    assert result.ok and result.said == "added"
    assert api.sent == [
        (
            "PUT",
            "/repos/a/two/environments/production",
            {
                "wait_timer": 10,
                "prevent_self_review": False,
                "reviewers": [],
                "deployment_branch_policy": {
                    "protected_branches": True,
                    "custom_branch_policies": False,
                },
            },
        )
    ]


def test_new_environment_never_replaces_one_and_says_what_github_made() -> None:
    made = {
        "name": "staging",
        "protection_rules": [{"type": "wait_timer", "wait_timer": 5}],
        "deployment_branch_policy": {"protected_branches": True, "custom_branch_policies": False},
    }
    api = FakeApi({("PUT", "/repos/o/r/environments/staging"): made})
    said = create_environment(api, "o/r", "staging", protected_only=True, wait_minutes=5)
    assert said == (
        "Made the environment staging in o/r: only protected branches may deploy to it, "
        "with a 5 minute wait."
    )
    (sent,) = api.sent
    assert sent[2] == {
        "deployment_branch_policy": {"protected_branches": True, "custom_branch_policies": False},
        "wait_timer": 5,
    }
    api = FakeApi({("GET", "/repos/o/r/environments/staging"): {"name": "staging"}})
    with pytest.raises(EnvironmentRefused, match="already has the environment staging"):
        create_environment(api, "o/r", "staging")
    assert api.sent == []
    with pytest.raises(EnvironmentRefused, match="0 to 43200"):
        create_environment(FakeApi({}), "o/r", "x", wait_minutes=50000)


# -- New Ruleset in one repository ------------------------------------------------------


def test_new_ruleset_builds_the_body_and_refuses_before_sending() -> None:
    body = ruleset_request(
        "Protect main", "branch", "~DEFAULT_BRANCH", ["pull_request", "deletion"], approvals=2
    )
    assert body["conditions"] == {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}}
    assert body["rules"][0]["parameters"]["required_approving_review_count"] == 2  # type: ignore[index]
    assert body["rules"][1] == {"type": "deletion"}  # type: ignore[index]
    pattern = ruleset_request("Tags", "tag", "v*", ["update"], enforcement="disabled")
    assert pattern["conditions"]["ref_name"]["include"] == ["refs/tags/v*"]  # type: ignore[index]
    for bad, words in (
        (("", "branch", "~ALL", ["deletion"]), "needs a name"),
        (("x", "branch", "~ALL", []), "at least one rule"),
        (("x", "tag", "~DEFAULT_BRANCH", ["deletion"]), "guards tags"),
        (("x", "branch", "~ALL", ["merge_queue"]), "does not offer merge_queue"),
    ):
        with pytest.raises(RulesetRefused, match=words):
            ruleset_request(*bad)  # type: ignore[arg-type]
    with pytest.raises(RulesetRefused, match="from 0 to 10"):
        ruleset_request("x", "branch", "~ALL", ["pull_request"], approvals=11)
    with pytest.raises(RulesetRefused, match="on or off"):
        ruleset_request("x", "branch", "~ALL", ["deletion"], enforcement="evaluate")


def test_new_ruleset_is_said_from_githubs_answer_and_never_doubled() -> None:
    body = ruleset_request("Protect main", "branch", "~DEFAULT_BRANCH", ["non_fast_forward"])
    api = FakeApi({
        ("GET", "/repos/o/r/rulesets"): [],
        ("POST", "/repos/o/r/rulesets"): {**body, "id": 5},
    })
    said = create_ruleset(api, "o/r", body)
    assert said == "Made the ruleset Protect main in o/r, as described."
    api.answers[("POST", "/repos/o/r/rulesets")] = {**body, "enforcement": "disabled"}
    assert create_ruleset(api, "o/r", body).endswith(
        "but GitHub has it as: On the default branch: force pushes are blocked. It is turned off."
    )
    api = FakeApi({("GET", "/repos/o/r/rulesets"): [{"name": "protect MAIN", "id": 1}]})
    with pytest.raises(RulesetRefused, match="already has a ruleset called protect MAIN"):
        create_ruleset(api, "o/r", body)
    assert api.sent == []


# -- branches: Delete Where Merged ------------------------------------------------------


def _branch_api() -> FakeApi:
    def branches(repo: str, extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"name": "main", "protected": True}, *extra]

    feature = {"name": "feature", "protected": False}
    return FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(),
        ("GET", "/repos/a/three"): _repo(),
        ("GET", "/repos/a/four"): _repo(),
        ("GET", "/repos/a/five"): _repo(),
        **{("GET", f"/repos/a/{n}/pulls"): [] for n in ("one", "two", "three", "four", "five")},
        ("GET", "/repos/a/one/branches"): branches("one", [feature]),
        ("GET", "/repos/a/two/branches"): branches("two", [feature]),
        ("GET", "/repos/a/three/branches"): branches("three", [feature]),
        ("GET", "/repos/a/four/branches"): branches("four", [{**feature, "protected": True}]),
        ("GET", "/repos/a/five/branches"): branches("five", [feature]),
        **{
            ("GET", f"/repos/a/{n}/branches/feature"): {"commit": {"sha": f"{n}sha0000"}}
            for n in ("one", "two", "three", "five")
        },
        ("GET", "/repos/a/one/compare/main...feature"): {"ahead_by": 0},
        ("GET", "/repos/a/two/compare/main...feature"): {"ahead_by": 3},
        ("GET", "/repos/a/three/compare/main...feature"): {"ahead_by": 2},
        ("GET", "/repos/a/five/compare/main...feature"): {"ahead_by": 1},
    })


def test_delete_where_merged_keeps_what_is_not_merged_and_says_why() -> None:
    api = _branch_api()
    squash = {"number": 12, "merged_at": "2026-11-01", "head": {"sha": "twosha0000"}}
    opened = {"number": 30, "head": {"sha": "fivesha000"}}

    def pulls(repo: str) -> Any:
        def answer(query: dict[str, str]) -> list[dict[str, Any]]:
            if query.get("head") != "a:feature":
                return []
            if repo == "two" and query.get("state") == "closed":
                return [squash]
            if repo == "five" and query.get("state") == "open":
                return [opened]
            return []

        return answer

    for name in ("one", "two", "three", "five"):
        api.answers[("GET", f"/repos/a/{name}/pulls")] = pulls(name)
    found = survey(api, "branches", ["a/one", "a/two", "a/three", "a/four", "a/five"])
    plan = plan_merged_delete(api, found, found.row("feature"))
    one, two, three, four, five = plan.steps
    assert one.after == "feature, because everything on it is in main"
    assert two.after == "feature, because pull request #12 merged its last commit"
    assert three.blocked == "2 commits on it are not in main and no merged pull request took them"
    assert four.blocked.startswith("it is protected")
    assert five.blocked == "pull request #30 is open from it"
    assert plan.preview().startswith(
        "Delete the merged copies of the branch feature: 2 of 5 repositories will change."
    )
    api.answers[("GET", "/repos/a/two/branches/feature")] = {"commit": {"sha": "newer000"}}
    results = apply_merged_delete(api, plan)
    assert [r.ok for r in results] == [True, False, False, False, False]
    assert results[0].said == "deleted; its last commit was onesha0, if it is ever wanted back"
    assert results[1].said == "it gained commits since you looked, so it is kept"
    assert [p for m, p, _b in api.sent] == ["/repos/a/one/git/refs/heads/feature"]


def test_the_default_branch_is_never_deleted_where_merged() -> None:
    api = _branch_api()
    found = survey(api, "branches", ["a/one"])
    plan = plan_merged_delete(api, found, found.row("main"))
    assert plan.steps[0].blocked == "it is the default branch" and not plan.runnable


# -- tags: Draft Releases Together ------------------------------------------------------


def test_draft_releases_together_fill_the_notes_and_skip_a_release_already_there() -> None:
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(default="trunk"),
        ("GET", "/repos/a/three"): _repo(),
        ("GET", "/repos/a/one/tags"): [{"name": "v2", "commit": {"sha": "abc"}}],
        ("GET", "/repos/a/two/tags"): [],
        ("GET", "/repos/a/three/tags"): [{"name": "v2", "commit": {"sha": "def"}}],
        ("GET", "/repos/a/one/releases"): [],
        ("GET", "/repos/a/two/releases"): [],
        ("GET", "/repos/a/three/releases"): [{"tag_name": "v2", "name": "Two", "draft": True}],
        ("POST", "/repos/a/one/releases"): {"draft": True},
    })
    found = survey(api, "tags", ["a/one", "a/two", "a/three"])
    plan = plan_draft_releases(
        api, found, "v2", ["a/one", "a/two", "a/three"], "{repository} {tag}", generated=True
    )
    one, two, three = plan.steps
    assert one.after == "a draft release v2 with the shared notes, then GitHub's generated notes"
    assert two.after.endswith("the tag is made on its default branch when it is published")
    assert three.blocked.startswith("it already has the draft release Two")
    results = apply_draft_releases(api, plan)
    assert [r.ok for r in results] == [True, True, False]
    assert results[0].said.startswith("drafted v2; only people who may push see it")
    first, second = (body for _m, _p, body in api.sent)
    assert first == {
        "tag_name": "v2",
        "name": "v2",
        "body": "a/one v2",
        "draft": True,
        "generate_release_notes": True,
    }
    assert second["body"] == "a/two v2" and second["target_commitish"] == "trunk"


def test_a_release_drafted_meanwhile_is_not_doubled() -> None:
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/one/tags"): [{"name": "v2", "commit": {"sha": "abc"}}],
        ("GET", "/repos/a/one/releases"): [],
    })
    found = survey(api, "tags", ["a/one"])
    plan = plan_draft_releases(api, found, "v2", ["a/one"], "notes")
    api.answers[("GET", "/repos/a/one/releases")] = [{"tag_name": "v2", "name": "v2"}]
    (result,) = apply_draft_releases(api, plan)
    assert not result.ok and result.said == "the release v2 was made there since you looked"
    assert api.sent == []


# -- alerts: Dismiss Everywhere ---------------------------------------------------------


def _dependabot(number: int, ghsa: str, manifest: str = "package.json") -> dict[str, Any]:
    return {
        "number": number,
        "state": "open",
        "security_advisory": {"ghsa_id": ghsa, "summary": "Prototype pollution"},
        "dependency": {"package": {"name": "lodash"}, "manifest_path": manifest},
    }


def _alert_api() -> FakeApi:
    return FakeApi({
        ("GET", "/repos/a/one/dependabot/alerts"): [_dependabot(3, "GHSA-1")],
        ("GET", "/repos/a/two/dependabot/alerts"): [
            _dependabot(5, "GHSA-1"),
            _dependabot(6, "GHSA-1", "web/package.json"),
            _dependabot(9, "GHSA-2"),
        ],
        ("GET", "/repos/a/three/dependabot/alerts"): [],
        ("GET", "/repos/a/four/dependabot/alerts"): GitHubRestError(
            "403 Dependabot alerts are disabled for this repository", status=403
        ),
        **{
            ("PATCH", f"/repos/a/{repo}/dependabot/alerts/{n}"): {"state": "dismissed"}
            for repo, n in (("one", 3), ("two", 5), ("two", 6))
        },
    })


def test_dismiss_everywhere_matches_the_advisory_and_says_each_repository() -> None:
    api = _alert_api()
    match = match_for(api, "a/one", "Dependabot", 3)
    assert match.key == "GHSA-1" and match.name == "GHSA-1 (Prototype pollution)"
    plan = plan_dismiss(api, match, ["a/one", "a/two", "a/three", "a/four"], "tolerable_risk")
    one, two, three, four = plan.steps
    assert one.after == (
        "alert #3 (lodash in package.json), reason: Risk is tolerable to this project"
    )
    assert two.after.startswith("alerts #5 (lodash in package.json) and #6 (lodash in web/")
    assert three.action == "skip" and three.after == "no open alert for it"
    assert four.blocked == "its alerts could not be read (Dependabot alerts are off)"
    results = apply_dismiss(api, match, plan)
    assert [r.ok for r in results] == [True, True, True, False]
    assert results[1].said == "dismissed alerts #5 and #6"
    body = {"state": "dismissed", "dismissed_reason": "tolerable_risk"}
    assert api.sent == [
        ("PATCH", "/repos/a/one/dependabot/alerts/3", body),
        ("PATCH", "/repos/a/two/dependabot/alerts/5", body),
        ("PATCH", "/repos/a/two/dependabot/alerts/6", body),
    ]
    two_logs = [results[1].log, *results[1].more]
    assert [dict(e.ident)["number"] for e in two_logs if e is not None] == ["5", "6"]
    for entry in two_logs:
        assert entry is not None and entry.kind == "security_alert" and entry.can_undo
        assert dict(entry.ident)["alert_path"] == "dependabot/alerts"


def test_a_dismissed_alert_is_undone_by_reopening_it_on_its_sheet() -> None:
    from quill.core.github.sheet_catalog import SHEETS
    from quill.core.github.sheet_engine import inverse
    from quill.core.github.sheet_replay import undo_refusal
    from quill.core.workbench.properties import FieldChange

    api = _alert_api()
    match = match_for(api, "a/one", "Dependabot", 3)
    plan = plan_dismiss(api, match, ["a/one"], "not_used", "Only in tests")
    (result,) = apply_dismiss(api, match, plan)
    assert result.log is not None
    changes = [FieldChange(k, n, b, a) for k, n, b, a in result.log.changes]
    sheet = SHEETS["security_alert"]
    assert undo_refusal(sheet, changes) == ""
    back, cannot = inverse(sheet, changes)
    assert not cannot and {c.key: c.after for c in back}["state"] == "open"
    assert api.sent[0][2]["dismissed_comment"] == "Only in tests"


def test_an_alert_closed_meanwhile_is_left_out_and_named() -> None:
    api = _alert_api()
    match = match_for(api, "a/one", "Dependabot", 3)
    plan = plan_dismiss(api, match, ["a/two"], "inaccurate")
    api.answers[("GET", "/repos/a/two/dependabot/alerts")] = [_dependabot(6, "GHSA-1")]
    (result,) = apply_dismiss(api, match, plan)
    assert result.ok and result.said == "dismissed alert #6; #5 closed on GitHub since you looked"


def test_code_scanning_matches_rule_and_tool_and_secrets_are_never_matched() -> None:
    def alert(number: int, rule: str, tool: str) -> dict[str, Any]:
        return {
            "number": number,
            "rule": {"id": rule, "description": "SQL injection"},
            "tool": {"name": tool},
            "most_recent_instance": {"location": {"path": "app.py"}},
        }

    api = FakeApi({
        ("GET", "/repos/a/one/code-scanning/alerts"): [alert(1, "py/sql", "CodeQL")],
        ("GET", "/repos/a/two/code-scanning/alerts"): [
            alert(4, "py/sql", "CodeQL"),
            alert(5, "py/sql", "Other"),
        ],
    })
    match = match_for(api, "a/one", "Code scanning", 1)
    plan = plan_dismiss(api, match, ["a/one", "a/two"], "false positive")
    assert plan.steps[1].after == "alert #4 (app.py), reason: False positive"
    with pytest.raises(AlertNotFound, match="one at a time"):
        match_for(api, "a/one", "Secret scanning", 1)
    with pytest.raises(AlertNotFound, match="not open now"):
        match_for(api, "a/one", "Code scanning", 99)
    with pytest.raises(ValueError, match="at most 280"):
        plan_dismiss(api, match, ["a/one"], "false positive", "x" * 281)
