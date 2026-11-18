"""Closing an issue with its reason, and branches linked to an issue (GH-D)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from quill.core.github import issue_development as dev
from quill.core.github.rest_transport import GitHubRestError, RestResponse

COMPLETED, NOT_PLANNED, DUPLICATE = dev.CLOSE_REASONS


class FakeApi:
    """Recorded answers; every call is kept so a test can say what was sent."""

    def __init__(self, *, branches: tuple[str, ...] = ("main",), linked: tuple[str, ...] = ()):
        self.calls: list[tuple[str, str, Any]] = []
        self.branches = set(branches)
        self.linked = linked

    def rest(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, object] | None = None,
        query: Mapping[str, str] | None = None,
    ) -> RestResponse:
        self.calls.append((method, path, body))
        if path == "/repos/o/r":
            return RestResponse(200, {}, {"default_branch": "main"})
        if path.startswith("/repos/o/r/git/ref/heads/"):
            name = path.rsplit("/", 1)[1]
            if name in self.branches:
                return RestResponse(200, {}, {"object": {"sha": "abc123"}})
            raise GitHubRestError("404 not found")
        if path.startswith("/repos/o/r/branches/"):
            if path.rsplit("/", 1)[1] in self.branches:
                return RestResponse(200, {}, {"name": path.rsplit("/", 1)[1]})
            raise GitHubRestError("404 not found")
        return RestResponse(200, {}, {})

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        self.calls.append(("GRAPHQL", query.split("(", 1)[0].split()[-1], dict(variables)))
        if "issue(number:$i){id" in query:
            number = int(str(variables["i"]))
            if number == 404:
                return {"repository": {"id": "R", "issue": None}}
            return {"repository": {"id": "R", "issue": {"id": f"I{number}", "title": "Original"}}}
        if "linkedBranches" in query:
            nodes = [{"ref": {"name": name}} for name in self.linked]
            return {"repository": {"issue": {"linkedBranches": {"nodes": nodes}}}}
        return {}


def test_completed_and_not_planned_close_through_rest_with_their_reason() -> None:
    api = FakeApi()
    assert dev.close_issue(api, "o/r", 7, NOT_PLANNED) == "Closed #7 as not planned."
    assert api.calls == [
        ("PATCH", "/repos/o/r/issues/7", {"state": "closed", "state_reason": "not_planned"})
    ]
    assert dev.close_issue(FakeApi(), "o/r", 7, COMPLETED) == "Closed #7 as completed."


def test_a_duplicate_names_its_original_through_graphql() -> None:
    api = FakeApi()
    said = dev.close_issue(api, "o/r", 7, DUPLICATE, duplicate_of=3)
    assert said == "Closed #7 as a duplicate of #3, Original."
    sent = [call for call in api.calls if call[0] == "GRAPHQL" and "dup" in call[2]]
    assert sent and sent[0][2] == {"id": "I7", "dup": "I3"}


@pytest.mark.parametrize(
    ("duplicate_of", "said"),
    [
        (0, "Name the issue it duplicates"),
        (7, "cannot be a duplicate of itself"),
        (404, "no issue #404"),
    ],
)
def test_a_duplicate_without_a_real_other_issue_is_refused(duplicate_of: int, said: str) -> None:
    with pytest.raises(dev.IssueDevelopmentError, match=said):
        dev.close_issue(FakeApi(), "o/r", 7, DUPLICATE, duplicate_of=duplicate_of)


def test_linked_branches_are_listed_by_name() -> None:
    assert dev.linked_branches(FakeApi(linked=("7-fix", "7-docs")), "o/r", 7) == ["7-fix", "7-docs"]
    assert dev.linked_branches(FakeApi(), "o/r", 7) == []


@pytest.mark.parametrize(
    ("title", "name"),
    [
        ("Fix the parser", "7-fix-the-parser"),
        ("  Crash: when * saving?  ", "7-crash-when-saving"),
        ("", "7"),
        ("x" * 100, "7-" + "x" * 58),
    ],
)
def test_the_suggested_name_is_githubs_own_shape(title: str, name: str) -> None:
    assert dev.branch_name_for(7, title) == name


@pytest.mark.parametrize(
    "bad", ["", "has space", "a..b", "-start", "end/", "end.", "x.lock", "a:b"]
)
def test_names_git_refuses_are_refused_before_anything_is_sent(bad: str) -> None:
    assert dev.valid_branch_name(bad)
    api = FakeApi()
    with pytest.raises(dev.IssueDevelopmentError):
        dev.create_linked_branch(api, "o/r", 7, bad)
    assert api.calls == []


def test_a_branch_is_made_from_the_default_branch_and_linked() -> None:
    api = FakeApi()
    assert dev.create_linked_branch(api, "o/r", 7, "7-fix") == (
        "Made branch 7-fix from main, linked to #7."
    )
    created = [call for call in api.calls if call[0] == "GRAPHQL" and "oid" in call[2]]
    assert created[0][2] == {"issue": "I7", "oid": "abc123", "name": "7-fix", "repo": "R"}


def test_an_existing_branch_or_a_missing_base_is_refused() -> None:
    with pytest.raises(dev.IssueDevelopmentError, match="already has a branch"):
        dev.create_linked_branch(FakeApi(branches=("main", "7-fix")), "o/r", 7, "7-fix")
    with pytest.raises(dev.IssueDevelopmentError, match="has no branch nope"):
        dev.create_linked_branch(FakeApi(), "o/r", 7, "7-fix", base="nope")
