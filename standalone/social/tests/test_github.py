"""Tests for the GitHub adapter (PRD 24.1, 24.2)."""

import pytest

from quill_social.adapters.base import AdapterError
from quill_social.adapters.github import (
    GitHubAdapter,
    GitHubIssue,
    GitHubNotification,
    GitHubPullRequest,
    GitHubRelease,
    MockGitHub,
)


def test_mock_returns_deterministic_content():
    a = MockGitHub()
    b = MockGitHub()
    assert [i.number for i in a.issues()] == [i.number for i in b.issues()]
    assert [p.number for p in a.pull_requests()] == [p.number for p in b.pull_requests()]
    assert a.releases()[0].tag == "v0.1.0"
    assert any(n.reason == "review_requested" for n in a.notifications())
    assert [p.merged for p in a.pull_requests()] == [True, True, False]


def test_mock_create_issue_and_comment_round_trip():
    gh = MockGitHub()
    before = len(gh.issues())
    issue = gh.create_issue("quill/quill-social", "New bug", body="details",
                            labels=["bug"])
    assert issue.number > 0
    assert len(gh.issues()) == before + 1
    updated = gh.comment("quill/quill-social", issue.number, "thanks")
    assert "thanks" in updated.body


def test_mock_comment_on_missing_issue_raises_validation():
    gh = MockGitHub()
    with pytest.raises(AdapterError) as exc:
        gh.comment("quill/quill-social", 99999, "hi")
    assert exc.value.kind == "validation"


def test_live_boundary_raises_clearly():
    gh = GitHubAdapter()
    for call in (
        gh.notifications,
        lambda: gh.issues("o/r"),
        lambda: gh.pull_requests("o/r"),
        lambda: gh.discussions("o/r"),
        lambda: gh.releases("o/r"),
        lambda: gh.create_issue("o/r", "t"),
        lambda: gh.comment("o/r", 1, "b"),
    ):
        with pytest.raises(AdapterError) as exc:
            call()
        assert exc.value.kind == "permission"
        assert "live GitHub not enabled" in str(exc.value)


def test_available_reflects_client_presence():
    # No assertion on the boolean itself (env-dependent); it must not raise.
    assert isinstance(GitHubAdapter.available(), bool)


def test_dataclass_roundtrips():
    samples = [
        GitHubIssue(id="i1", repo="o/r", number=3, title="t", body="b",
                    state="open", labels=["a", "b"], author="@x",
                    url="http://x", updated=5),
        GitHubPullRequest(id="p1", repo="o/r", number=4, state="merged",
                          labels=["c"], updated=6),
        GitHubRelease(id="r1", repo="o/r", title="1.0", tag="v1.0", updated=7),
        GitHubNotification(id="n1", repo="o/r", reason="mention", updated=8),
    ]
    for obj in samples:
        clone = type(obj).from_dict(obj.to_dict())
        assert clone == obj


def test_pull_request_merged_property():
    assert GitHubPullRequest(state="merged").merged
    assert not GitHubPullRequest(state="open").merged
