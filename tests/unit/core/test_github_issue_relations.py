"""An issue's parent, sub-issues and blocked-by links (GitHub REST)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.issue_relations import GitHubIssueRelations, IssueRef, parse_issue_ref
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import GitHubRestError, RestResponse

BASE = "/repos/o/r/issues/5"


def _issue(number: int, ident: int, repo: str = "o/r") -> dict[str, Any]:
    return {
        "id": ident,
        "number": number,
        "title": f"Issue {number}",
        "state": "open",
        "repository_url": f"https://api.github.com/repos/{repo}",
    }


class _GitHub:
    def __init__(self, answers: dict[tuple[str, str], Any]) -> None:
        self.answers = answers
        self.calls: list[tuple[str, str, Any]] = []

    def __call__(self, _token: Any, method: str, path: str, **kw: Any) -> RestResponse:
        self.calls.append((method, path, kw.get("body")))
        answer = self.answers.get((method, path))
        if isinstance(answer, Exception):
            raise answer
        if answer is None and method == "GET":
            raise GitHubRestError("Not Found", status=404)
        status = {"GET": 200, "DELETE": 204}.get(method, 201)
        return RestResponse(status=status, data=answer)


def test_parse_an_issue_typed_any_of_three_ways() -> None:
    assert parse_issue_ref("#12", "o/r") == ("o/r", 12)
    assert parse_issue_ref("other/thing#3", "o/r") == ("other/thing", 3)
    assert parse_issue_ref("https://github.com/a/b/issues/9", "o/r") == ("a/b", 9)
    with pytest.raises(GitHubItemsError):
        parse_issue_ref("the parser bug", "o/r")


def test_relations_read_all_four_and_no_parent_is_not_a_failure() -> None:
    github = _GitHub({
        ("GET", f"{BASE}/sub_issues"): [_issue(6, 106)],
        ("GET", f"{BASE}/dependencies/blocked_by"): [_issue(2, 102, "x/y")],
        ("GET", f"{BASE}/dependencies/blocking"): [],
    })
    relations = GitHubIssueRelations("t", github).relations("o/r", 5)
    assert relations.parent is None and relations.unread == ()
    assert relations.lines("o/r") == [
        "Sub-issue: #6 Issue 6 (open)",
        "Blocked by: x/y#2 Issue 2 (open)",
    ]
    assert relations.summary() == "1 sub-issue, 1 issue blocking it"


def test_a_part_github_refuses_is_named_not_shown_as_empty() -> None:
    github = _GitHub({
        ("GET", f"{BASE}/parent"): _issue(1, 101),
        ("GET", f"{BASE}/sub_issues"): GitHubRestError("Forbidden", status=403),
        ("GET", f"{BASE}/dependencies/blocked_by"): [],
        ("GET", f"{BASE}/dependencies/blocking"): [],
    })
    relations = GitHubIssueRelations("t", github).relations("o/r", 5)
    assert relations.parent is not None and relations.parent.number == 1
    assert relations.unread and relations.unread[0].startswith("the sub-issues")


def test_writes_send_the_issue_id_not_its_number() -> None:
    github = _GitHub({})
    api = GitHubIssueRelations("t", github)
    child = IssueRef(id=106, number=6, title="Six", repo="o/r")
    api.add_sub_issue("o/r", 5, child)
    api.add_sub_issue("o/r", 5, child, move=True)
    api.remove_sub_issue("o/r", 5, child)
    api.add_blocked_by("o/r", 5, child)
    api.remove_blocked_by("o/r", 5, child)
    assert github.calls == [
        ("POST", f"{BASE}/sub_issues", {"sub_issue_id": 106}),
        ("POST", f"{BASE}/sub_issues", {"sub_issue_id": 106, "replace_parent": True}),
        ("DELETE", f"{BASE}/sub_issue", {"sub_issue_id": 106}),
        ("POST", f"{BASE}/dependencies/blocked_by", {"issue_id": 106}),
        ("DELETE", f"{BASE}/dependencies/blocked_by/106", None),
    ]


def test_writes_need_a_signed_in_account() -> None:
    api = GitHubIssueRelations(None, _GitHub({}))
    with pytest.raises(GitHubItemsError, match="signed-in"):
        api.add_blocked_by("o/r", 5, IssueRef(id=1, number=1, title="", repo="o/r"))
