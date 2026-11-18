"""Unlink Branch... and Not a Duplicate... (GitHub PRD 14.1)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import issue_links as il


class FakeApi:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    def rest(self, *_a: Any, **_k: Any) -> Any:
        raise AssertionError

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        self.sent.append(variables)
        if "linkedBranches" in query:
            nodes = [{"id": "LB_1", "ref": {"name": "42-fix"}}, {"id": "LB_2", "ref": None}]
            return {"repository": {"issue": {"linkedBranches": {"nodes": nodes}}}}
        if "issue(number" in query:
            if variables["i"] == 404:
                return {"repository": {"issue": None}}
            return {"repository": {"issue": {"id": f"I_{variables['i']}", "title": "Crash"}}}
        return {}


def test_linked_branches_are_listed_and_one_is_unlinked() -> None:
    api = FakeApi()
    found = il.linked_branch_ids(api, "o/r", 42)
    assert found == [il.LinkedBranch("LB_1", "42-fix")]
    assert (
        il.unlink_branch(api, 42, found[0])
        == "Unlinked 42-fix from #42. The branch is still there."
    )
    assert api.sent[-1] == {"id": "LB_1"}


def test_not_a_duplicate_sends_both_issues() -> None:
    api = FakeApi()
    said = il.not_a_duplicate(api, "o/r", 7, 3)
    assert said == "#7 is no longer marked a duplicate of #3, Crash."
    assert api.sent[-1] == {"dup": "I_7", "canon": "I_3"}
    with pytest.raises(il.IssueLinkError, match="itself"):
        il.not_a_duplicate(api, "o/r", 7, 7)
    with pytest.raises(il.IssueLinkError, match="no issue #404"):
        il.not_a_duplicate(api, "o/r", 7, 404)
    assert il.IssueLinkError.code == "QUILL-GITHUB-ISSUE-LINKS"
