"""Unit tests for the wx-free PR review client (github.md plan 4.2.1).

PyGithub is mocked with lightweight stubs, mirroring
``test_github_items_provider.py``: model mapping, thread grouping, the
plain-language header summaries, write-access refusal, and each review
action's argument passing are all testable without wx or network.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.pr_review import (
    GitHubCheckRun,
    GitHubPullReviewState,
    GitHubReview,
    GitHubReviewComment,
    GitHubReviewError,
    PullReviewClient,
    group_review_threads,
)

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakePull:
    def __init__(self, **attrs: Any) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self._reviews: list[Any] = attrs.pop("reviews", [])
        self._review_comments: list[Any] = attrs.pop("review_comments", [])
        self.__dict__.update(attrs)

    def get_reviews(self) -> list[Any]:
        return self._reviews

    def get_review_comments(self) -> list[Any]:
        return self._review_comments

    def create_review(self, **kwargs: Any) -> None:
        self.calls.append(("create_review", (), kwargs))

    def create_review_comment_reply(self, comment_id: int, body: str) -> None:
        self.calls.append(("create_review_comment_reply", (comment_id, body), {}))

    def create_review_request(self, **kwargs: Any) -> None:
        self.calls.append(("create_review_request", (), kwargs))

    def convert_to_draft(self) -> None:
        self.calls.append(("convert_to_draft", (), {}))

    def mark_ready_for_review(self) -> None:
        self.calls.append(("mark_ready_for_review", (), {}))

    def update_branch(self) -> None:
        self.calls.append(("update_branch", (), {}))


class _FakeCommit:
    def __init__(self, check_runs: list[Any]) -> None:
        self._check_runs = check_runs

    def get_check_runs(self) -> list[Any]:
        return self._check_runs


class _FakeRepo:
    def __init__(self, pull: _FakePull, check_runs: list[Any] | None = None) -> None:
        self._pull = pull
        self._check_runs = check_runs or []
        self.commit_shas: list[str] = []

    def get_pull(self, number: int) -> _FakePull:
        return self._pull

    def get_commit(self, sha: str) -> _FakeCommit:
        self.commit_shas.append(sha)
        return _FakeCommit(self._check_runs)


class _FakeProvider:
    """Stands in for GitHubItemsProvider: _repo + is_authenticated."""

    def __init__(self, repo: _FakeRepo, *, authenticated: bool = True) -> None:
        self._repo_obj = repo
        self._authenticated = authenticated

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    def _repo(self, full_name: str) -> _FakeRepo:
        return self._repo_obj


def _user(login: str) -> SimpleNamespace:
    return SimpleNamespace(login=login)


def _review_comment_row(
    comment_id: int,
    *,
    author: str = "alice",
    body: str = "Looks off",
    path: str = "quill/core/x.py",
    line: int | None = 10,
    position: int | None = 5,
    in_reply_to_id: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=comment_id,
        user=_user(author),
        body=body,
        path=path,
        line=line,
        original_line=line,
        position=position,
        in_reply_to_id=in_reply_to_id,
        created_at=None,
        html_url=f"https://github.com/o/r/pull/1#discussion_r{comment_id}",
    )


def _full_pull(**overrides: Any) -> _FakePull:
    attrs: dict[str, Any] = {
        "title": "Add thing",
        "state": "open",
        "draft": False,
        "merged": False,
        "mergeable": True,
        "mergeable_state": "clean",
        "base": SimpleNamespace(ref="main", sha="b" * 40),
        "head": SimpleNamespace(ref="feature", sha="a" * 40),
        "user": _user("author"),
        "html_url": "https://github.com/o/r/pull/7",
        "requested_reviewers": [_user("carol")],
    }
    attrs.update(overrides)
    return _FakePull(**attrs)


def _client(
    pull: _FakePull, *, check_runs: list[Any] | None = None, authenticated: bool = True
) -> tuple[PullReviewClient, _FakeRepo]:
    repo = _FakeRepo(pull, check_runs)
    provider = _FakeProvider(repo, authenticated=authenticated)
    return PullReviewClient(provider), repo  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Thread grouping
# ---------------------------------------------------------------------------


def test_group_review_threads_groups_replies_under_roots() -> None:
    comments = [
        GitHubReviewComment(id=1, author="alice", body="root"),
        GitHubReviewComment(id=2, author="bob", body="reply", in_reply_to=1),
        GitHubReviewComment(id=3, author="carol", body="other root"),
    ]
    threads = group_review_threads(comments)
    assert len(threads) == 2
    assert threads[0].root.id == 1
    assert threads[0].reply_count == 1
    assert threads[1].root.id == 3


def test_group_review_threads_promotes_orphan_reply_to_root() -> None:
    comments = [GitHubReviewComment(id=5, author="bob", body="orphan", in_reply_to=999)]
    threads = group_review_threads(comments)
    assert len(threads) == 1
    assert threads[0].root.id == 5


def test_thread_header_carries_place_author_replies_and_outdated() -> None:
    thread = group_review_threads([
        GitHubReviewComment(id=1, author="alice", body="x", path="a.py", line=12, outdated=True),
        GitHubReviewComment(id=2, author="bob", body="y", in_reply_to=1),
    ])[0]
    assert thread.header == "a.py:12 — alice — 1 reply — outdated"


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def test_fetch_review_state_maps_everything() -> None:
    reviews = [
        SimpleNamespace(user=_user("bob"), state="APPROVED", body="", submitted_at=None),
    ]
    check = SimpleNamespace(
        name="CI",
        status="completed",
        conclusion="success",
        html_url="https://ci",
        output=SimpleNamespace(title="All green"),
    )
    pull = _full_pull(
        reviews=reviews,
        review_comments=[_review_comment_row(1), _review_comment_row(2, position=None)],
    )
    client, repo = _client(pull, check_runs=[check])
    state = client.fetch_review_state("o/r", 7)
    assert state.title == "Add thing"
    assert state.head_ref == "feature" and state.base_ref == "main"
    assert state.requested_reviewers == ("carol",)
    assert state.reviews == (GitHubReview(reviewer="bob", state="APPROVED"),)
    assert state.checks == (
        GitHubCheckRun(
            name="CI",
            status="completed",
            conclusion="success",
            url="https://ci",
            summary="All green",
        ),
    )
    assert state.thread_count == 2
    assert state.outdated_thread_count == 1
    assert repo.commit_shas == ["a" * 40]


def test_fetch_review_threads_maps_outdated_from_missing_position() -> None:
    pull = _full_pull(
        review_comments=[
            _review_comment_row(1, position=None),
            _review_comment_row(2, in_reply_to_id=1),
        ]
    )
    client, _repo = _client(pull)
    threads = client.fetch_review_threads("o/r", 7)
    assert len(threads) == 1
    assert threads[0].outdated is True
    assert threads[0].comments[1].in_reply_to == 1


def test_fetch_check_runs_returns_empty_without_head_sha() -> None:
    pull = _full_pull(head=SimpleNamespace(ref="feature", sha=""))
    client, _repo = _client(pull)
    assert client.fetch_check_runs("o/r", 7) == ()


# ---------------------------------------------------------------------------
# Header language
# ---------------------------------------------------------------------------


def _state(**overrides: Any) -> GitHubPullReviewState:
    base: dict[str, Any] = {
        "number": 7,
        "title": "Add thing",
        "state": "open",
        "draft": False,
        "merged": False,
        "mergeable": True,
        "mergeable_state": "clean",
        "base_ref": "main",
        "head_ref": "feature",
        "head_sha": "a" * 40,
        "author": "author",
        "url": "https://github.com/o/r/pull/7",
    }
    base.update(overrides)
    return GitHubPullReviewState(**base)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"merged": True}, "Merged."),
        ({"state": "closed"}, "Closed without merging."),
        ({"draft": True}, "Draft — not ready for review."),
        (
            {"mergeable_state": "behind"},
            "Branch is behind the base branch; update it before merging.",
        ),
        ({"mergeable": False, "mergeable_state": "dirty"}, "Merge conflicts with the base branch."),
        ({"mergeable_state": "blocked"}, "Blocked — required reviews or checks are not satisfied."),
        ({"mergeable": None, "mergeable_state": ""}, "GitHub is still computing mergeability."),
        ({}, "Ready to merge."),
    ],
)
def test_merge_readiness_phrases(overrides: dict[str, Any], expected: str) -> None:
    assert _state(**overrides).merge_readiness == expected


def test_review_decision_latest_review_per_reviewer_wins() -> None:
    state = _state(
        reviews=(
            GitHubReview(reviewer="bob", state="CHANGES_REQUESTED"),
            GitHubReview(reviewer="bob", state="APPROVED"),
            GitHubReview(reviewer="dan", state="COMMENTED"),
        )
    )
    assert state.review_decision == "approved by 1"


def test_review_decision_changes_requested_blocks() -> None:
    state = _state(
        reviews=(
            GitHubReview(reviewer="amy", state="APPROVED"),
            GitHubReview(reviewer="bob", state="CHANGES_REQUESTED"),
        )
    )
    assert state.review_decision == "changes requested by 1"


def test_review_decision_dismissal_clears_a_standing_review() -> None:
    state = _state(
        reviews=(
            GitHubReview(reviewer="bob", state="CHANGES_REQUESTED"),
            GitHubReview(reviewer="bob", state="DISMISSED"),
        )
    )
    assert state.review_decision == "review pending"


def test_checks_summary_counts() -> None:
    state = _state(
        checks=(
            GitHubCheckRun(name="a", status="completed", conclusion="success"),
            GitHubCheckRun(name="b", status="completed", conclusion="failure"),
            GitHubCheckRun(name="c", status="in_progress", conclusion=""),
        )
    )
    assert state.checks_summary == "1 passed, 1 failed, 1 running"
    assert _state().checks_summary == "no checks"


def test_summary_text_is_the_copyable_brief() -> None:
    text = _state(thread_count=3, outdated_thread_count=1).summary_text()
    assert "PR #7: Add thing" in text
    assert "feature into main, by author" in text
    assert "Review threads: 3 (1 outdated)" in text
    assert "https://github.com/o/r/pull/7" in text


def test_check_run_state_display() -> None:
    assert GitHubCheckRun(name="a", status="in_progress", conclusion="").state_display == (
        "in progress"
    )
    assert GitHubCheckRun(name="a", status="completed", conclusion="failure").state_display == (
        "failure"
    )


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def test_submit_review_approve_passes_event() -> None:
    pull = _full_pull()
    client, _repo = _client(pull)
    client.submit_review("o/r", 7, "approve")
    assert pull.calls == [("create_review", (), {"body": "", "event": "APPROVE"})]


def test_submit_review_request_changes_requires_body() -> None:
    pull = _full_pull()
    client, _repo = _client(pull)
    with pytest.raises(GitHubReviewError, match="requires a message"):
        client.submit_review("o/r", 7, "request changes", "")
    client.submit_review("o/r", 7, "request changes", "Please fix")
    assert pull.calls[-1] == (
        "create_review",
        (),
        {"body": "Please fix", "event": "REQUEST_CHANGES"},
    )


def test_submit_review_unknown_event_is_refused_before_network() -> None:
    pull = _full_pull()
    client, _repo = _client(pull, authenticated=False)
    with pytest.raises(GitHubReviewError, match="Unknown review action"):
        client.submit_review("o/r", 7, "merge")
    assert pull.calls == []


def test_actions_refuse_anonymous_sessions() -> None:
    pull = _full_pull()
    client, _repo = _client(pull, authenticated=False)
    with pytest.raises(GitHubReviewError, match="Sign in"):
        client.submit_review("o/r", 7, "approve")
    with pytest.raises(GitHubReviewError, match="Sign in"):
        client.reply_to_thread("o/r", 7, 1, "hi")
    with pytest.raises(GitHubReviewError, match="Sign in"):
        client.request_reviewers("o/r", 7, ["bob"])
    with pytest.raises(GitHubReviewError, match="Sign in"):
        client.set_draft("o/r", 7, True)
    with pytest.raises(GitHubReviewError, match="Sign in"):
        client.update_branch("o/r", 7)
    assert pull.calls == []


def test_reply_to_thread_posts_reply() -> None:
    pull = _full_pull()
    client, _repo = _client(pull)
    client.reply_to_thread("o/r", 7, 42, "Agreed, fixing.")
    assert pull.calls == [("create_review_comment_reply", (42, "Agreed, fixing."), {})]


def test_reply_to_thread_requires_text() -> None:
    pull = _full_pull()
    client, _repo = _client(pull)
    with pytest.raises(GitHubReviewError, match="needs a message"):
        client.reply_to_thread("o/r", 7, 42, "   ")


def test_request_reviewers_strips_handles_and_requires_one() -> None:
    pull = _full_pull()
    client, _repo = _client(pull)
    client.request_reviewers("o/r", 7, ["@bob ", " carol"])
    assert pull.calls == [("create_review_request", (), {"reviewers": ["bob", "carol"]})]
    with pytest.raises(GitHubReviewError, match="at least one reviewer"):
        client.request_reviewers("o/r", 7, ["  "])


def test_set_draft_toggles_both_ways() -> None:
    pull = _full_pull()
    client, _repo = _client(pull)
    client.set_draft("o/r", 7, True)
    client.set_draft("o/r", 7, False)
    assert [name for name, _a, _k in pull.calls] == [
        "convert_to_draft",
        "mark_ready_for_review",
    ]


def test_update_branch_calls_through() -> None:
    pull = _full_pull()
    client, _repo = _client(pull)
    client.update_branch("o/r", 7)
    assert pull.calls == [("update_branch", (), {})]


def test_action_errors_become_coded_errors() -> None:
    class _ExplodingPull(_FakePull):
        def create_review(self, **kwargs: Any) -> None:
            raise RuntimeError("boom")

    pull = _ExplodingPull(
        title="t",
        state="open",
        draft=False,
        merged=False,
        mergeable=True,
        mergeable_state="clean",
        base=None,
        head=None,
        user=None,
        html_url="",
        requested_reviewers=[],
    )
    client, _repo = _client(pull)
    with pytest.raises(GitHubReviewError, match="Could not submit the review: boom") as excinfo:
        client.submit_review("o/r", 7, "approve")
    assert excinfo.value.code == "QUILL-GITHUB-REVIEW-ERROR"
