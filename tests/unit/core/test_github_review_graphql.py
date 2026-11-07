"""Authenticated review-thread resolution mapping and pagination."""

from __future__ import annotations

from urllib.error import HTTPError

import pytest

from quill.core.github import review_graphql


def test_review_thread_state_pages_by_root_comment(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_request(_token: str, _query: str, variables: dict[str, object]):
        calls.append(variables)
        root_id = 11 if variables["after"] is None else 22
        return {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "nodes": [
                            {
                                "id": f"THREAD_{root_id}",
                                "isResolved": root_id == 11,
                                "isOutdated": False,
                                "viewerCanResolve": root_id == 22,
                                "viewerCanUnresolve": root_id == 11,
                                "line": 10,
                                "originalLine": 9,
                                "comments": {"nodes": [{"databaseId": root_id}]},
                            }
                        ],
                        "pageInfo": {
                            "hasNextPage": root_id == 11,
                            "endCursor": "next" if root_id == 11 else None,
                        },
                    }
                }
            }
        }

    monkeypatch.setattr(review_graphql, "_request", fake_request)
    states = review_graphql.fetch_thread_states("token", "owner/repo", 7)
    assert set(states) == {11, 22}
    assert states[11].resolved and states[11].can_unresolve
    assert not states[22].resolved and states[22].can_resolve
    assert [call["after"] for call in calls] == [None, "next"]


def test_mutation_requires_confirmed_state(monkeypatch) -> None:
    monkeypatch.setattr(
        review_graphql,
        "_request",
        lambda *_args: {"resolveReviewThread": {"thread": {"id": "T", "isResolved": True}}},
    )
    review_graphql.set_thread_resolved("token", "T", True)
    with pytest.raises(review_graphql.ReviewGraphQLError, match="did not confirm"):
        review_graphql.set_thread_resolved("token", "T", False)


def test_missing_resolution_field_is_not_mapped_to_unresolved(monkeypatch) -> None:
    monkeypatch.setattr(
        review_graphql,
        "_request",
        lambda *_args: {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "nodes": [
                            {
                                "id": "T",
                                "viewerCanResolve": False,
                                "viewerCanUnresolve": False,
                                "isOutdated": False,
                                "comments": {"nodes": [{"databaseId": 11}]},
                            }
                        ],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            }
        },
    )

    with pytest.raises(review_graphql.ReviewGraphQLError, match="incomplete review-thread state"):
        review_graphql.fetch_thread_states("token", "owner/repo", 7)


def test_pull_queue_state_maps_queue_auto_merge_and_head(monkeypatch) -> None:
    monkeypatch.setattr(
        review_graphql,
        "_request",
        lambda *_args: {
            "repository": {
                "pullRequest": {
                    "headRefOid": "abc123",
                    "isMergeQueueEnabled": True,
                    "isInMergeQueue": False,
                    "autoMergeRequest": {"mergeMethod": "SQUASH"},
                }
            }
        },
    )

    state = review_graphql.fetch_pull_queue_state("token", "owner/repo", 7)

    assert state.merge_queue_enabled
    assert not state.in_merge_queue
    assert state.auto_merge_enabled
    assert state.head_sha == "abc123"


def test_pull_queue_state_rejects_missing_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        review_graphql,
        "_request",
        lambda *_args: {
            "repository": {
                "pullRequest": {
                    "headRefOid": "abc123",
                    "isMergeQueueEnabled": True,
                }
            }
        },
    )

    with pytest.raises(review_graphql.ReviewGraphQLError, match="incomplete merge-queue state"):
        review_graphql.fetch_pull_queue_state("token", "owner/repo", 7)


def test_later_page_failure_is_reported(monkeypatch) -> None:
    calls = 0

    def fake_request(*_args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise review_graphql.ReviewGraphQLError("rate limit exceeded")
        return {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "nodes": [],
                        "pageInfo": {"hasNextPage": True, "endCursor": "next"},
                    }
                }
            }
        }

    monkeypatch.setattr(review_graphql, "_request", fake_request)
    with pytest.raises(review_graphql.ReviewGraphQLError, match="rate limit exceeded"):
        review_graphql.fetch_thread_states("token", "owner/repo", 7)


def test_invalid_page_cursor_is_reported(monkeypatch) -> None:
    monkeypatch.setattr(
        review_graphql,
        "_request",
        lambda *_args: {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "nodes": [],
                        "pageInfo": {"hasNextPage": True, "endCursor": ""},
                    }
                }
            }
        },
    )

    with pytest.raises(
        review_graphql.ReviewGraphQLError, match="invalid review-thread page cursor"
    ):
        review_graphql.fetch_thread_states("token", "owner/repo", 7)


def test_graphql_redirect_is_refused_without_following(monkeypatch) -> None:
    requests = []

    class Opener:
        def open(self, request, *, timeout):
            requests.append(request)
            raise HTTPError(
                request.full_url,
                302,
                "Moved",
                {"Location": "https://other.example/graphql"},
                None,
            )

    monkeypatch.setattr(review_graphql, "build_opener", lambda *_args: Opener())
    with pytest.raises(review_graphql.ReviewGraphQLError, match="credentials were not forwarded"):
        review_graphql._request("secret", "query {}", {})

    assert len(requests) == 1
    assert requests[0].full_url == "https://api.github.com/graphql"
    assert requests[0].get_header("Authorization") == "Bearer secret"


def test_malformed_mutation_response_is_a_coded_error(monkeypatch) -> None:
    monkeypatch.setattr(review_graphql, "_request", lambda *_args: {"resolveReviewThread": None})

    with pytest.raises(review_graphql.ReviewGraphQLError, match="did not confirm"):
        review_graphql.set_thread_resolved("token", "T", True)
