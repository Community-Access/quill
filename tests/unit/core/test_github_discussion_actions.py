"""Discussion threads, replies, answers, new discussions and polls as text."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import github_graphql
from quill.core.github.discussion_actions import (
    DiscussionPoll,
    GitHubDiscussionActionsMixin,
    parse_discussion_thread,
    poll_lines,
)
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import RestResponse


class _Provider(GitHubDiscussionActionsMixin):
    def __init__(self, token: str | None = "tok") -> None:
        self._token = token

    def _require_write_access(self, action: str) -> None:
        if not self._token:
            raise GitHubItemsError(f"To {action} you need a signed-in GitHub account.")


class _GraphQL:
    def __init__(self) -> None:
        self.bodies: list[dict[str, Any]] = []
        self.reply: Any = {"data": {}}

    def __call__(self, token, method, path, *, body=None, **_kw):
        assert (method, path) == ("POST", "/graphql")
        self.bodies.append(body)
        return RestResponse(200, {}, self.reply)


@pytest.fixture
def gql(monkeypatch: pytest.MonkeyPatch) -> _GraphQL:
    fake = _GraphQL()
    monkeypatch.setattr(github_graphql, "request_json", fake)
    return fake


THREAD = {
    "repository": {
        "discussion": {
            "id": "D_1",
            "number": 4,
            "title": "Which theme?",
            "bodyText": "Pick one.",
            "url": "https://github.com/o/r/discussions/4",
            "closed": False,
            "author": {"login": "jeff"},
            "category": {"name": "Q&A", "isAnswerable": True},
            "answer": {"id": "C_2", "author": {"login": "kelly"}},
            "poll": {
                "question": "Theme",
                "totalVoteCount": 30,
                "options": {
                    "nodes": [
                        {"option": "Option A", "totalVoteCount": 12},
                        {"option": "Option B", "totalVoteCount": 18},
                    ]
                },
            },
            "comments": {
                "totalCount": 2,
                "nodes": [
                    {
                        "id": "C_1",
                        "bodyText": "Dark, please.",
                        "author": {"login": "ann"},
                        "viewerCanMarkAsAnswer": True,
                        "replies": {
                            "nodes": [
                                {"id": "R_1", "bodyText": "Agreed", "author": {"login": "bo"}}
                            ]
                        },
                    },
                    {
                        "id": "C_2",
                        "bodyText": "Light.",
                        "isAnswer": True,
                        "viewerCanUnmarkAsAnswer": True,
                        "author": {"login": "kelly"},
                        "replies": {"nodes": []},
                    },
                ],
            },
        }
    }
}


def test_thread_reads_answer_poll_and_replies_in_order() -> None:
    thread = parse_discussion_thread(THREAD, 4)
    assert thread.answer_line == "Answered by kelly."
    text = thread.text()
    assert "Option A: 12 votes, 40 percent" in text
    assert "Option B: 18 votes, 60 percent" in text
    entries = thread.entries()
    assert [entry.id for entry in entries] == ["C_1", "R_1", "C_2"]
    assert entries[0].label == "Comment by ann, 1 reply: Dark, please."
    assert entries[1].is_reply and entries[1].parent_id == "C_1"
    assert entries[2].label == "Comment by kelly, the answer: Light."


def test_poll_lines_handle_no_votes() -> None:
    assert poll_lines(DiscussionPoll("Q", 0, (("Yes", 0), ("Single", 1)))) == [
        "Poll: Q, 0 votes in all",
        "Yes: 0 votes, 0 percent",
        "Single: 1 vote, 0 percent",
    ]


def test_missing_discussion_is_a_clear_error() -> None:
    with pytest.raises(GitHubItemsError, match="#9 was not found"):
        parse_discussion_thread({"repository": {"discussion": None}}, 9)


def test_reply_to_a_comment_sends_reply_to_and_needs_confirmation(gql: _GraphQL) -> None:
    gql.reply = {"data": {"addDiscussionComment": {"comment": {"id": "C_9", "url": "u"}}}}
    assert _Provider().reply_to_discussion("D_1", "Thanks", reply_to="C_1") == "u"
    assert gql.bodies[0]["variables"] == {"discussion": "D_1", "body": "Thanks", "replyTo": "C_1"}
    gql.reply = {"data": {"addDiscussionComment": None}}
    with pytest.raises(GitHubItemsError, match="did not confirm"):
        _Provider().reply_to_discussion("D_1", "Thanks")
    assert gql.bodies[1]["variables"]["replyTo"] is None


def test_mark_and_unmark_answer_check_githubs_reply(gql: _GraphQL) -> None:
    gql.reply = {
        "data": {
            "markDiscussionCommentAsAnswer": {
                "discussion": {"isAnswered": True, "answer": {"id": "C_1"}}
            }
        }
    }
    _Provider().set_discussion_answer("C_1", answer=True)
    assert "markDiscussionCommentAsAnswer" in gql.bodies[0]["query"]
    with pytest.raises(GitHubItemsError, match="did not confirm"):
        _Provider().set_discussion_answer("C_2", answer=True)
    gql.reply = {
        "data": {
            "unmarkDiscussionCommentAsAnswer": {"discussion": {"isAnswered": False, "answer": None}}
        }
    }
    _Provider().set_discussion_answer("C_1", answer=False)
    assert "unmarkDiscussionCommentAsAnswer" in gql.bodies[-1]["query"]


def test_create_discussion_in_a_category(gql: _GraphQL) -> None:
    gql.reply = {
        "data": {
            "repository": {
                "id": "R_1",
                "discussionCategories": {
                    "nodes": [{"id": "CAT_1", "name": "Ideas", "isAnswerable": False}]
                },
            }
        }
    }
    repo_id, categories = _Provider().fetch_discussion_categories("o/r")
    assert repo_id == "R_1" and categories[0].name == "Ideas"
    gql.reply = {"data": {"createDiscussion": {"discussion": {"number": 12, "url": "u"}}}}
    assert _Provider().create_discussion("R_1", "CAT_1", "Title", "Body") == (12, "u")
    assert gql.bodies[-1]["variables"]["category"] == "CAT_1"


def test_graphql_errors_and_rate_limits_become_messages(gql: _GraphQL) -> None:
    gql.reply = {"errors": [{"type": "FORBIDDEN", "message": "Resource not accessible"}]}
    with pytest.raises(GitHubItemsError, match="GitHub said: Resource not accessible"):
        _Provider().fetch_discussion_thread("o/r", 4)
    gql.reply = {"errors": [{"type": "RATE_LIMITED", "message": "API rate limit exceeded"}]}
    with pytest.raises(GitHubItemsError, match="rate-limited"):
        _Provider().fetch_discussion_thread("o/r", 4)


def test_writes_need_sign_in(gql: _GraphQL) -> None:
    with pytest.raises(GitHubItemsError, match="signed-in"):
        _Provider(token=None).reply_to_discussion("D_1", "x")
    with pytest.raises(GitHubItemsError, match="signed-in"):
        _Provider(token=None).set_discussion_answer("C_1", answer=True)
    assert gql.bodies == []
