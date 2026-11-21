"""Discussion to issue to pull request, and Related (GX12), over recorded answers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import pytest

from quill.core.github import collab_links as cl
from quill.core.github.rest_transport import GitHubRestError, RestResponse


class FakeApi:
    """REST by (method, path); GraphQL by a function of the query. Every call is recorded."""

    def __init__(
        self,
        rest: Mapping[tuple[str, str], Any] | None = None,
        graphql: Callable[[str, Mapping[str, object]], dict[str, Any]] | None = None,
    ) -> None:
        self.routes = dict(rest or {})
        self.answer = graphql
        self.sent: list[tuple[str, str, Any]] = []
        self.queries: list[str] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body))
        found = self.routes.get((method, path), GitHubRestError("Not Found", status=404))
        if callable(found):
            found = found(body)
        if isinstance(found, Exception):
            raise found
        return RestResponse(200, {}, found)

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        self.queries.append(query)
        assert self.answer is not None, "no GraphQL expected"
        return self.answer(query, variables)


def test_the_issue_body_links_back_and_quotes_the_discussion() -> None:
    body = cl.discussion_issue_body("https://github.com/o/r/discussions/5", "ann", "Line\n\nTwo")
    assert body.startswith("From the discussion https://github.com/o/r/discussions/5 by @ann.")
    assert "> Line\n>\n> Two" in body


def test_issue_from_discussion_opens_the_issue_only_when_not_asked_to_comment() -> None:
    api = FakeApi({("POST", "/repos/o/r/issues"): {"number": 9, "html_url": "u9"}})
    number, said = cl.issue_from_discussion(api, "o/r", 5, " Title ", "Body")
    assert number == 9 and said == "Opened issue #9 from discussion #5."
    assert api.sent == [("POST", "/repos/o/r/issues", {"title": "Title", "body": "Body"})]
    assert api.queries == []


def test_the_comment_back_links_the_new_issue_from_the_discussion() -> None:
    def answer(query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        if "addDiscussionComment" in query:
            assert variables == {"d": "D1", "b": "Opened as issue u9."}
            return {"addDiscussionComment": {"comment": {"url": "c"}}}
        return {"repository": {"discussion": {"id": "D1", "url": "x"}}}

    api = FakeApi({("POST", "/repos/o/r/issues"): {"number": 9, "html_url": "u9"}}, answer)
    _number, said = cl.issue_from_discussion(api, "o/r", 5, "T", "B", comment_back=True)
    assert said.endswith("The discussion links to it in a new comment.")


def test_a_refused_comment_never_undoes_the_issue() -> None:
    def answer(query: str, _v: Mapping[str, object]) -> dict[str, Any]:
        raise RuntimeError("refused")

    api = FakeApi({("POST", "/repos/o/r/issues"): {"number": 9}}, answer)
    number, said = cl.issue_from_discussion(api, "o/r", 5, "T", "B", comment_back=True)
    assert number == 9 and "was not posted" in said


def test_an_issue_needs_a_title() -> None:
    with pytest.raises(cl.CollabError):
        cl.issue_from_discussion(FakeApi(), "o/r", 5, "  ", "B")


def _pull_routes(ahead: int, *, refuse_draft: bool = False) -> dict[tuple[str, str], Any]:
    def pulls(body: Any) -> Any:
        if refuse_draft and body.get("draft"):
            return GitHubRestError("Draft pull requests are not supported", status=422)
        return {"number": 21}

    return {
        ("GET", "/repos/o/r"): {"default_branch": "main"},
        ("GET", "/repos/o/r/git/ref/heads/main"): {"object": {"sha": "base"}},
        ("GET", "/repos/o/r/git/ref/heads/7-fix"): {"object": {"sha": "base"}},
        ("GET", "/repos/o/r/compare/main...7-fix"): {"ahead_by": ahead},
        ("GET", "/repos/o/r/git/commits/base"): {"tree": {"sha": "tree1"}},
        ("POST", "/repos/o/r/git/commits"): {"sha": "new1"},
        ("PATCH", "/repos/o/r/git/refs/heads/7-fix"): {"ref": "refs/heads/7-fix"},
        ("POST", "/repos/o/r/pulls"): pulls,
    }


def _linking(query: str, _v: Mapping[str, object]) -> dict[str, Any]:
    if "createLinkedBranch" in query:
        return {"createLinkedBranch": {"linkedBranch": {"ref": {"name": "7-fix"}}}}
    return {"repository": {"id": "R", "issue": {"id": "I", "title": "Fix", "state": "OPEN"}}}


def test_pull_for_issue_links_a_branch_adds_one_empty_commit_and_opens_a_draft() -> None:
    api = FakeApi(_pull_routes(0), _linking)
    number, said = cl.pull_for_issue(api, "o/r", 7, "Fix", "7-fix")
    assert number == 21
    assert said == (
        "Made branch 7-fix, linked to #7, and opened draft pull request #21 into main. "
        "Merging it closes #7."
    )
    sent = {(m, p): b for m, p, b in api.sent if m != "GET"}
    assert sent[("POST", "/repos/o/r/git/commits")] == {
        "message": "Start work on #7",
        "tree": "tree1",
        "parents": ["base"],
    }
    assert sent[("PATCH", "/repos/o/r/git/refs/heads/7-fix")] == {"sha": "new1", "force": False}
    pull = sent[("POST", "/repos/o/r/pulls")]
    assert pull["draft"] is True and pull["head"] == "7-fix" and pull["base"] == "main"
    assert pull["body"].startswith("Closes #7.")


def test_a_branch_with_its_own_commits_gets_no_empty_one() -> None:
    api = FakeApi(_pull_routes(2), _linking)
    cl.pull_for_issue(api, "o/r", 7, "Fix", "7-fix")
    assert ("POST", "/repos/o/r/git/commits") not in {(m, p) for m, p, _b in api.sent}


def test_a_repository_without_drafts_gets_an_ordinary_pull_request_said_so() -> None:
    api = FakeApi(_pull_routes(1, refuse_draft=True), _linking)
    _number, said = cl.pull_for_issue(api, "o/r", 7, "Fix", "7-fix")
    assert "no drafts" in said
    posts = [b for m, p, b in api.sent if (m, p) == ("POST", "/repos/o/r/pulls")]
    assert posts[-1].get("draft") is None


def test_a_bad_branch_name_sends_nothing() -> None:
    api = FakeApi()
    with pytest.raises(cl.CollabError):
        cl.pull_for_issue(api, "o/r", 7, "Fix", "bad name")
    assert api.sent == []


def test_references_are_found_once_each_outside_code() -> None:
    text = (
        "See #3 and o/other#4, https://github.com/o/r/pull/8 and "
        "https://github.com/o/r/discussions/2.\n`#99` and\n```\n#98\n```\n#3 again"
    )
    assert cl.find_references(text, "o/r") == [
        ("pull_request", "o/r", 8),
        ("discussion", "o/r", 2),
        ("ref", "o/r", 3),
        ("ref", "o/other", 4),
    ]


def _subject(typename: str, number: int, **more: Any) -> dict[str, Any]:
    return {
        "__typename": typename,
        "number": number,
        "title": f"T{number}",
        "state": "OPEN",
        "url": f"https://github.com/o/r/x/{number}",
        "repository": {"nameWithOwner": "o/r"},
        **more,
    }


def test_related_for_an_issue_lists_closing_pulls_cross_references_and_its_links() -> None:
    def answer(query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        if "closedByPullRequestsReferences" in query and "r0:" not in query:
            return {
                "repository": {
                    "issueOrPullRequest": {
                        "__typename": "Issue",
                        "title": "Bug",
                        "body": "From https://github.com/o/r/discussions/2",
                        "comments": {"totalCount": 1, "nodes": [{"body": "dup of #7"}]},
                        "closedByPullRequestsReferences": {
                            "nodes": [_subject("PullRequest", 8)]
                        },
                        "timelineItems": {
                            "pageInfo": {"hasNextPage": True},
                            "nodes": [
                                {"__typename": "CrossReferencedEvent", "willCloseTarget": True,
                                 "source": _subject("PullRequest", 8)},
                                {"__typename": "CrossReferencedEvent", "willCloseTarget": False,
                                 "source": _subject("Issue", 6)},
                            ],
                        },
                    }
                }
            }  # fmt: skip
        assert "r0:repository" in query and "discussion(number:$i0)" in query
        assert "issueOrPullRequest(number:$i1)" in query
        return {
            "r0": {"discussion": {**_subject("Discussion", 2, closed=True), "state": None}},
            "r1": {"issueOrPullRequest": None},  # #7 is gone or hidden: left out
        }

    found = cl.related(FakeApi(graphql=answer), "o/r", "issue", 5)
    lines = found.lines()
    assert lines[0] == (
        "Pull request o/r#8, T8 (open): merging it closes this issue."
    )  # the closing link wins over the cross-reference
    assert "Issue o/r#6, T6 (open): mentions it." in lines
    assert "Discussion o/r#2, T2 (closed): its text links to it." in lines
    assert len(lines) == 3
    assert found.sentence.startswith("Issue #5: 3 linked items.")
    assert "first 100 cross-references" in found.sentence


def test_related_for_a_discussion_says_github_keeps_no_backlinks() -> None:
    def answer(query: str, _v: Mapping[str, object]) -> dict[str, Any]:
        if "r0:" in query:
            return {"r0": {"issueOrPullRequest": _subject("Issue", 9)}}
        return {
            "repository": {
                "discussion": {
                    "title": "Idea",
                    "body": "",
                    "comments": {
                        "totalCount": 1,
                        "nodes": [{"body": "x", "replies": {"nodes": [{"body": "Opened #9"}]}}],
                    },
                }
            }
        }

    found = cl.related(FakeApi(graphql=answer), "o/r", "discussion", 2)
    assert found.lines() == ["Issue o/r#9, T9 (open): its text links to it."]
    assert "no record of what links to a discussion" in found.sentence


def test_unreadable_links_are_said_as_unread_never_as_none() -> None:
    def answer(query: str, _v: Mapping[str, object]) -> dict[str, Any]:
        if "r0:" in query:
            raise RuntimeError("rate limited")
        return {"repository": {"issueOrPullRequest": {"__typename": "PullRequest",
                                                      "body": "#4", "comments": {}}}}  # fmt: skip

    found = cl.related(FakeApi(graphql=answer), "o/r", "pull_request", 3)
    assert "they are unread" in found.sentence


def test_a_missing_item_is_one_sentence() -> None:
    api = FakeApi(graphql=lambda _q, _v: {"repository": {"issueOrPullRequest": None}})
    with pytest.raises(cl.CollabError, match="no issue #5"):
        cl.related(api, "o/r", "issue", 5)
