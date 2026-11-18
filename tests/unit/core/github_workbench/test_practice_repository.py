"""The practice repository: made, found and deleted (GitHub PRD 22.8)."""

from __future__ import annotations

import base64
from typing import Any

import pytest

from quill.core.github import practice_repository as pr
from quill.core.github.rest_transport import GitHubRestError, RestResponse


class FakeApi:
    def __init__(self, *, exists: bool = False, refuse_delete: bool = False) -> None:
        self.exists, self.refuse_delete = exists, refuse_delete
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body))
        if method == "GET" and path == "/repos/me/quill-practice":
            if not self.exists:
                raise GitHubRestError("Not Found", status=404)
            return RestResponse(200, {}, {"full_name": "me/quill-practice"})
        if method == "GET" and "/contents/" in path:
            if "fix-greeting" in str(query):
                return RestResponse(200, {}, {"sha": "readme-sha"})
            raise GitHubRestError("Not Found", status=404)
        if method == "GET" and "/git/ref/heads/" in path:
            return RestResponse(200, {}, {"object": {"sha": "base-sha"}})
        if method == "POST" and path == "/user/repos":
            return RestResponse(
                201, {}, {"full_name": "me/quill-practice", "default_branch": "main"}
            )
        if method == "DELETE" and self.refuse_delete:
            raise GitHubRestError("Forbidden", status=403)
        if method == "DELETE":
            self.exists = False
        return RestResponse(201, {}, {})

    def graphql(self, query: str, variables: Any) -> Any:
        raise AssertionError("no GraphQL here")


def test_it_is_made_private_and_filled() -> None:
    api = FakeApi()
    told: list[str] = []
    practice = pr.create_practice(api, "me", progress=told.append)
    made = api.sent[1]
    assert made[:2] == ("POST", "/user/repos") and made[2]["private"] is True
    paths = [(m, p) for m, p, _b in api.sent]
    assert ("PUT", "/repos/me/quill-practice/contents/.github/workflows/practice.yml") in paths
    assert sum(1 for m, p in paths if m == "POST" and p.endswith("/issues")) == 3
    assert sum(1 for m, p in paths if m == "POST" and p.endswith("/labels")) == 2
    ref = next(b for m, p, b in api.sent if p.endswith("/git/refs"))
    assert ref == {"ref": "refs/heads/fix-greeting", "sha": "base-sha"}
    fix = [b for m, p, b in api.sent if m == "PUT" and b.get("branch") == "fix-greeting"][0]
    assert fix["sha"] == "readme-sha"
    assert base64.b64decode(fix["content"]).decode().startswith("# Hello")
    assert ("POST", "/repos/me/quill-practice/pulls") in paths
    assert practice.sentence == (
        "Made me/quill-practice, private, with a workflow that fails on purpose, 3 issues, "
        "a branch with a pull request."
    )
    assert len(told) == 3


def test_it_is_not_made_twice() -> None:
    with pytest.raises(pr.PracticeError, match="already there"):
        pr.create_practice(FakeApi(exists=True), "me")
    assert pr.find_practice(FakeApi(exists=True), "me") == "me/quill-practice"
    assert pr.find_practice(FakeApi(), "me") == ""


def test_deleting_and_when_github_refuses() -> None:
    api = FakeApi(exists=True)
    assert pr.delete_practice(api, "me") == "Deleted me/quill-practice."
    assert api.sent[-1][:2] == ("DELETE", "/repos/me/quill-practice")
    assert "no quill-practice" in pr.delete_practice(FakeApi(), "me")
    with pytest.raises(pr.PracticeError, match="delete_repo permission"):
        pr.delete_practice(FakeApi(exists=True, refuse_delete=True), "me")
    assert pr.PracticeError.code == "QUILL-GITHUB-PRACTICE"
