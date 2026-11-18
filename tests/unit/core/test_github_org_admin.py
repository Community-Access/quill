"""An organization's roles and rulesets: what is sent, and what is read back."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.org_admin import GitHubOrgAdmin, Holder, Role, RulesetRow
from quill.core.github.rest_transport import RestResponse

ROLE = Role(8, "all_repo_write", "Write to every repository", "write")
RULES = RulesetRow(5, "Protect main", "branch", "active")


class _GitHub:
    def __init__(self, replies: dict[tuple[str, str], RestResponse] | None = None) -> None:
        self.sent: list[tuple[str, str, dict[str, Any]]] = []
        self.replies = replies or {}

    def __call__(self, _token: Any, method: str, path: str, **kw: Any) -> RestResponse:
        self.sent.append((method, path, kw))
        if (method, path) in self.replies:
            return self.replies[(method, path)]
        return RestResponse(204 if method in ("PUT", "DELETE") else 200, data=[])


def test_roles_and_their_holders_read_as_sentences() -> None:
    github = _GitHub({
        ("GET", "/orgs/acme/organization-roles"): RestResponse(
            200,
            data={
                "total_count": 1,
                "roles": [{"id": 8, "name": "all_repo_write", "base_role": "write"}],
            },
        ),
        ("GET", "/orgs/acme/organization-roles/8/users"): RestResponse(
            200,
            data=[
                {"login": "jeff", "assignment": "direct"},
                {"login": "kim", "assignment": "indirect", "inherited_from": [{"slug": "docs"}]},
            ],
        ),
        ("GET", "/orgs/acme/organization-roles/8/teams"): RestResponse(
            200, data=[{"slug": "docs"}]
        ),
    })
    api = GitHubOrgAdmin("t", github)
    assert api.roles("acme")[0].label() == "all_repo_write, based on write"
    labels = [h.label() for h in api.holders("acme", ROLE)]
    assert labels == ["Person: jeff", "Person: kim, through docs", "Team: docs"]


@pytest.mark.parametrize(
    ("call", "method", "path"),
    [
        (
            lambda a: a.assign("acme", "person", "@jeff", ROLE),
            "PUT",
            "/orgs/acme/organization-roles/users/jeff/8",
        ),
        (
            lambda a: a.unassign("acme", "team", "docs", ROLE),
            "DELETE",
            "/orgs/acme/organization-roles/teams/docs/8",
        ),
        (
            lambda a: a.unassign_all("acme", "person", "jeff"),
            "DELETE",
            "/orgs/acme/organization-roles/users/jeff",
        ),
        (lambda a: a.delete_ruleset("acme", RULES), "DELETE", "/orgs/acme/rulesets/5"),
    ],
)
def test_each_write_goes_to_its_route(call: Any, method: str, path: str) -> None:
    github = _GitHub()
    call(GitHubOrgAdmin("t", github))
    assert github.sent[-1][:2] == (method, path)


def test_enforcement_sends_only_the_new_value_and_refuses_a_wrong_one() -> None:
    github = _GitHub({("PUT", "/orgs/acme/rulesets/5"): RestResponse(200, data={})})
    api = GitHubOrgAdmin("t", github)
    api.set_enforcement("acme", RULES, "evaluate")
    assert github.sent[-1][2]["body"] == {"enforcement": "evaluate"}
    with pytest.raises(GitHubItemsError):
        api.set_enforcement("acme", RULES, "loud")


def test_a_ruleset_reads_in_words_with_its_history_and_insights() -> None:
    github = _GitHub({
        ("GET", "/orgs/acme/rulesets"): RestResponse(
            200,
            data=[{"id": 5, "name": "Protect main", "target": "branch", "enforcement": "evaluate"}],
        ),
        ("GET", "/orgs/acme/rulesets/5"): RestResponse(
            200,
            data={
                "target": "branch",
                "conditions": {
                    "ref_name": {"include": ["~DEFAULT_BRANCH"]},
                    "repository_name": {"include": ["~ALL"]},
                },
                "rules": [{"type": "deletion"}],
            },
        ),
        ("GET", "/orgs/acme/rulesets/5/history"): RestResponse(
            200,
            data=[
                {"version_id": 3, "actor": {"type": "User", "id": 9}, "updated_at": "2026-11-18"}
            ],
        ),
        ("GET", "/orgs/acme/rulesets/rule-suites"): RestResponse(
            200,
            data=[
                {
                    "result": "fail",
                    "actor_name": "kim",
                    "repository_name": "site",
                    "ref": "refs/heads/main",
                    "pushed_at": "today",
                }
            ],
        ),
    })
    api = GitHubOrgAdmin("t", github)
    row = api.rulesets("acme")[0]
    assert row.label() == "Protect main: Evaluate, on branches"
    assert api.ruleset_summary("acme", row).startswith("On the default branch")
    assert api.history("acme", row) == ["Version 3: changed 2026-11-18 by User 9"]
    assert api.insights("acme", "week") == ["Blocked: kim pushed to site main, today"]
    assert github.sent[-1][2]["query"]["time_period"] == "week"


def test_writes_need_a_sign_in_and_names_are_checked_before_sending() -> None:
    github = _GitHub()
    with pytest.raises(GitHubItemsError, match="signed-in"):
        GitHubOrgAdmin(None, github).assign("acme", "person", "jeff", ROLE)
    with pytest.raises(GitHubItemsError):
        GitHubOrgAdmin("t", github).assign("acme", "person", "../x", ROLE)
    assert github.sent == []
    assert Holder("team", "docs").label() == "Team: docs"
