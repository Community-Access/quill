"""Auto-merge and merge-queue mutations say only what GitHub confirmed."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import merge_automation
from quill.core.github.merge_automation import (
    dequeue_pull_request,
    disable_auto_merge,
    enable_auto_merge,
    enqueue_pull_request,
)
from quill.core.github.review_errors import GitHubReviewError
from quill.core.github.review_graphql import ReviewGraphQLError


class _Provider:
    is_authenticated = True
    token = "tok"


class _GraphQL:
    def __init__(self, reply: dict[str, Any] | Exception) -> None:
        self.reply = reply
        self.calls: list[dict[str, object]] = []

    def __call__(self, token: str, query: str, variables: dict[str, object]) -> dict[str, Any]:
        self.calls.append(variables)
        if "pullRequest(number" in query:
            return {"repository": {"pullRequest": {"id": "PR_1", "headRefOid": "abc"}}}
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def _install(monkeypatch: pytest.MonkeyPatch, reply: dict[str, Any] | Exception) -> _GraphQL:
    fake = _GraphQL(reply)
    monkeypatch.setattr(merge_automation, "_request", fake)
    return fake


def test_enable_auto_merge_sends_the_chosen_method(monkeypatch) -> None:
    fake = _install(
        monkeypatch,
        {
            "enablePullRequestAutoMerge": {
                "pullRequest": {"autoMergeRequest": {"enabledAt": "now", "mergeMethod": "SQUASH"}}
            }
        },
    )
    message = enable_auto_merge(_Provider(), "o/r", 5, "Squash and merge")
    assert fake.calls[-1] == {"id": "PR_1", "method": "SQUASH"}
    assert message.startswith("Auto-merge is on for pull request #5; GitHub will squash it")


def test_enable_auto_merge_unconfirmed_is_an_error(monkeypatch) -> None:
    _install(
        monkeypatch, {"enablePullRequestAutoMerge": {"pullRequest": {"autoMergeRequest": None}}}
    )
    with pytest.raises(GitHubReviewError, match="did not confirm"):
        enable_auto_merge(_Provider(), "o/r", 5, "Create a merge commit")


def test_disable_auto_merge(monkeypatch) -> None:
    _install(
        monkeypatch, {"disablePullRequestAutoMerge": {"pullRequest": {"autoMergeRequest": None}}}
    )
    assert disable_auto_merge(_Provider(), "o/r", 5) == "Auto-merge is off for pull request #5."


def test_enqueue_sends_expected_head_and_reports_position(monkeypatch) -> None:
    fake = _install(
        monkeypatch,
        {
            "enqueuePullRequest": {
                "mergeQueueEntry": {"id": "MQE", "position": 3, "state": "QUEUED"}
            }
        },
    )
    assert enqueue_pull_request(_Provider(), "o/r", 5) == (
        "Pull request #5 is in the merge queue at position 3."
    )
    assert fake.calls[-1] == {"id": "PR_1", "head": "abc"}


def test_dequeue(monkeypatch) -> None:
    _install(monkeypatch, {"dequeuePullRequest": {"mergeQueueEntry": {"id": "MQE", "state": "x"}}})
    assert (
        dequeue_pull_request(_Provider(), "o/r", 5) == "Pull request #5 is out of the merge queue."
    )


def test_known_refusals_are_rephrased(monkeypatch) -> None:
    _install(monkeypatch, ReviewGraphQLError("Auto merge is not allowed for this repository"))
    with pytest.raises(GitHubReviewError, match="Auto-merge is turned off for this repository"):
        enable_auto_merge(_Provider(), "o/r", 5, "Rebase and merge")
    _install(monkeypatch, ReviewGraphQLError("Something odd"))
    with pytest.raises(GitHubReviewError, match="GitHub said: Something odd"):
        dequeue_pull_request(_Provider(), "o/r", 5)


def test_signed_out_and_unknown_method_are_refused(monkeypatch) -> None:
    fake = _install(monkeypatch, {})
    anonymous = _Provider()
    anonymous.is_authenticated = False
    with pytest.raises(GitHubReviewError, match="Sign in"):
        disable_auto_merge(anonymous, "o/r", 5)
    with pytest.raises(GitHubReviewError, match="merge method"):
        enable_auto_merge(_Provider(), "o/r", 5, "Octopus")
    assert fake.calls == []
