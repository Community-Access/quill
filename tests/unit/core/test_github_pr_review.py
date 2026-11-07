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

from quill.core.github.merge_policy import (
    GitHubMergePolicy,
    GitHubPullQueueState,
    GitHubRuleSetPolicy,
)
from quill.core.github.pr_review import (
    GitHubCheckRun,
    GitHubPullReviewState,
    GitHubReview,
    GitHubReviewComment,
    GitHubReviewError,
    PullReviewClient,
    _rows,
    group_review_threads,
)
from quill.core.github.review_graphql import ReviewThreadState

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
    def __init__(self, check_runs: list[Any], statuses: list[Any]) -> None:
        self._check_runs = check_runs
        self._statuses = statuses

    def get_check_runs(self) -> list[Any]:
        return self._check_runs

    def get_statuses(self) -> list[Any]:
        return self._statuses


class _FakeRepo:
    def __init__(
        self,
        pull: _FakePull,
        check_runs: list[Any] | None = None,
        statuses: list[Any] | None = None,
    ) -> None:
        self._pull = pull
        self._check_runs = check_runs or []
        self._statuses = statuses or []
        self.commit_shas: list[str] = []

    def get_pull(self, number: int) -> _FakePull:
        return self._pull

    def get_commit(self, sha: str) -> _FakeCommit:
        self.commit_shas.append(sha)
        return _FakeCommit(self._check_runs, self._statuses)


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
    pull: _FakePull,
    *,
    check_runs: list[Any] | None = None,
    statuses: list[Any] | None = None,
    authenticated: bool = True,
) -> tuple[PullReviewClient, _FakeRepo]:
    repo = _FakeRepo(pull, check_runs, statuses)
    provider = _FakeProvider(repo, authenticated=authenticated)
    return PullReviewClient(provider), repo  # type: ignore[arg-type]


def _failing_page(rows: list[Any], message: str = "rate limited") -> Any:
    yield from rows
    raise RuntimeError(message)


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
    assert thread.header == "a.py:12 — alice — 1 reply — outdated — resolution unavailable"


def test_rows_reports_later_page_failure_and_preserves_loaded_rows() -> None:
    result = _rows(_failing_page(["first", "second"], "later page failed"), 5)

    assert result.items == ("first", "second")
    assert not result.complete
    assert not result.truncated
    assert "later page failed" in result.warning


def test_rows_distinguishes_exact_limit_from_truncation() -> None:
    exact = _rows(["first", "second"], 2)
    truncated = _rows(["first", "second", "third"], 2)

    assert exact.items == ("first", "second")
    assert exact.complete
    assert not exact.truncated
    assert truncated.items == ("first", "second")
    assert not truncated.complete
    assert truncated.truncated


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


def test_fetch_head_sha_reads_latest_pull_request_commit() -> None:
    client, _repo = _client(_full_pull())

    assert client.fetch_head_sha("o/r", 7) == "a" * 40

    pull = _full_pull(head=SimpleNamespace(ref="feature", sha=""))
    client, _repo = _client(pull)
    with pytest.raises(GitHubReviewError, match="current head SHA"):
        client.fetch_head_sha("o/r", 7)


def test_fetch_review_state_marks_partial_reviews_and_withholds_readiness() -> None:
    pull = _full_pull(
        reviews=_failing_page([
            SimpleNamespace(user=_user("bob"), state="APPROVED", body="", submitted_at=None)
        ])
    )
    client, _repo = _client(pull)

    state = client.fetch_review_state("o/r", 7)

    assert not state.reviews_complete
    assert state.review_decision == "unknown (review data incomplete)"
    assert any(
        "Reviews" in warning and "rate limited" in warning for warning in state.data_warnings
    )
    assert state.merge_readiness.startswith("Merge readiness unknown:")


def test_fetch_review_threads_maps_outdated_from_missing_position() -> None:
    pull = _full_pull(
        review_comments=[
            _review_comment_row(1, position=None),
            _review_comment_row(2, in_reply_to_id=1),
        ]
    )
    client, _repo = _client(pull)
    result = client.fetch_review_threads("o/r", 7)
    assert len(result.items) == 1
    assert result.items[0].outdated is True
    assert result.items[0].comments[1].in_reply_to == 1


def test_fetch_review_threads_keeps_rows_and_reports_failed_later_page() -> None:
    pull = _full_pull(review_comments=_failing_page([_review_comment_row(1)]))
    client, _repo = _client(pull)

    result = client.fetch_review_threads("o/r", 7)

    assert len(result.items) == 1
    assert not result.complete
    assert "rate limited" in result.warning


def test_fetch_review_threads_joins_graphql_resolution_by_root_id(monkeypatch) -> None:
    from quill.core.github import pr_review

    pull = _full_pull(review_comments=[_review_comment_row(11)])
    client, _repo = _client(pull)
    client._provider.token = "secret"  # type: ignore[attr-defined]
    monkeypatch.setattr(
        pr_review,
        "fetch_thread_states",
        lambda *_args: {11: ReviewThreadState("THREAD_11", True, False, True, False, 10, 10)},
    )
    thread = client.fetch_review_threads("o/r", 7).items[0]
    assert thread.node_id == "THREAD_11"
    assert thread.resolved and thread.can_unresolve
    assert "resolved" in thread.header


def test_fetch_check_runs_returns_empty_without_head_sha() -> None:
    pull = _full_pull(head=SimpleNamespace(ref="feature", sha=""))
    client, _repo = _client(pull)
    result = client.fetch_check_runs("o/r", 7)
    assert result.items == ()
    assert not result.complete


def test_fetch_review_state_includes_legacy_commit_status_contexts() -> None:
    status = SimpleNamespace(
        context="legacy-ci",
        state="success",
        target_url="https://ci.example/run/12",
        description="All legacy checks passed",
    )
    pending = SimpleNamespace(
        context="release-build",
        state="pending",
        target_url="",
        description="Waiting for a runner",
    )
    client, _repo = _client(_full_pull(), statuses=[status, pending])

    state = client.fetch_review_state("o/r", 7)

    assert [(check.name, check.status, check.conclusion) for check in state.checks] == [
        ("legacy-ci", "completed", "success"),
        ("release-build", "in_progress", ""),
    ]
    assert "All legacy checks passed" in state.checks[0].summary


def test_policy_readiness_checks_legacy_status_contexts() -> None:
    status = SimpleNamespace(
        context="legacy-ci",
        state="success",
        target_url="",
        description="passed",
    )
    client, _repo = _client(_full_pull(), statuses=[status])
    state = client.fetch_review_state("o/r", 7)
    policy = GitHubMergePolicy(
        base_branch="main",
        branch_protection_available=True,
        branch_protection_enabled=True,
        required_checks=("legacy-ci",),
    )

    assert _state(merge_policy=policy, checks=state.checks).merge_readiness.startswith(
        "GitHub reports no merge conflict;"
    )
    pending = SimpleNamespace(
        context="legacy-ci",
        state="pending",
        target_url="",
        description="still running",
    )
    client, _repo = _client(_full_pull(), statuses=[pending])
    pending_state = client.fetch_review_state("o/r", 7)
    assert _state(merge_policy=policy, checks=pending_state.checks).merge_readiness == (
        "Required checks need attention: legacy-ci."
    )


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
        ({"merged": True}, "Merged (reported by GitHub)."),
        ({"state": "closed"}, "Closed without merging (reported by GitHub)."),
        ({"draft": True}, "Draft — not ready for review (reported by GitHub)."),
        (
            {"mergeable_state": "behind"},
            "GitHub reports that this branch is behind its base branch.",
        ),
        (
            {"mergeable": False, "mergeable_state": "dirty"},
            "GitHub reports merge conflicts with the base branch.",
        ),
        (
            {"mergeable_state": "blocked"},
            "GitHub reports this pull request is blocked by repository policy.",
        ),
        (
            {"mergeable": None, "mergeable_state": ""},
            "Merge readiness unknown: GitHub has not reported a stable clean state.",
        ),
        (
            {},
            "GitHub reports no merge conflict; required reviews and branch protection rules "
            "are not verified here.",
        ),
    ],
)
def test_merge_readiness_phrases(overrides: dict[str, Any], expected: str) -> None:
    assert _state(**overrides).merge_readiness == expected


def test_unknown_merge_state_is_never_reported_as_ready() -> None:
    state = _state(mergeable=True, mergeable_state="unexpected")

    assert (
        state.merge_readiness
        == "Merge readiness unknown: GitHub has not reported a stable clean state."
    )


def test_unstable_merge_state_is_not_reported_as_ready() -> None:
    state = _state(mergeable=True, mergeable_state="unstable")

    assert state.merge_readiness == (
        "GitHub reports an unstable merge state; check results need attention."
    )


@pytest.mark.parametrize("conclusion", ["failure", "timed_out", "cancelled", "action_required"])
def test_non_success_check_cannot_be_reported_as_ready(conclusion: str) -> None:
    state = _state(checks=(GitHubCheckRun("CI", "completed", conclusion),))

    assert state.merge_readiness == (
        "One or more check runs are pending or not successful; "
        "GitHub determines which checks are required."
    )


def test_pending_check_cannot_be_reported_as_ready() -> None:
    state = _state(checks=(GitHubCheckRun("CI", "in_progress", ""),))

    assert state.merge_readiness == (
        "One or more check runs are pending or not successful; "
        "GitHub determines which checks are required."
    )


def test_partial_thread_data_is_visible_and_withholds_readiness() -> None:
    state = _state(
        threads_complete=False,
        data_warnings=("Review threads: results may be incomplete.",),
    )

    assert state.merge_readiness.startswith("Merge readiness unknown:")
    assert "Data status: incomplete" in state.summary_text()
    assert "Data note: Review threads: results may be incomplete." in state.summary_text()


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


def test_policy_readiness_requires_the_observed_approval_count() -> None:
    state = _state(
        merge_policy=GitHubMergePolicy(
            base_branch="main",
            branch_protection_available=True,
            branch_protection_enabled=True,
            required_approvals=2,
        ),
        reviews=(GitHubReview(reviewer="alice", state="APPROVED"),),
    )

    assert state.merge_readiness == "Repository policy requires 1 more approval(s)."


def test_policy_readiness_ignores_nonrequired_failed_checks() -> None:
    state = _state(
        merge_policy=GitHubMergePolicy(
            base_branch="main",
            branch_protection_available=True,
            branch_protection_enabled=True,
        ),
        checks=(GitHubCheckRun("Optional preview", "completed", "failure"),),
    )

    assert state.merge_readiness.startswith("GitHub reports no merge conflict;")


def test_policy_readiness_only_requires_configured_check_names() -> None:
    policy = GitHubMergePolicy(
        base_branch="main",
        branch_protection_available=True,
        branch_protection_enabled=True,
        required_checks=("build",),
    )
    state = _state(
        merge_policy=policy,
        checks=(
            GitHubCheckRun("build", "completed", "success"),
            GitHubCheckRun("lint", "completed", "failure"),
        ),
    )

    assert state.merge_readiness.startswith("GitHub reports no merge conflict;")


def test_policy_readiness_does_not_assume_codeowner_approval() -> None:
    state = _state(
        merge_policy=GitHubMergePolicy(
            base_branch="main",
            branch_protection_available=True,
            branch_protection_enabled=True,
            codeowners_review_required=True,
            codeowners_path=".github/CODEOWNERS",
        )
    )

    assert state.merge_readiness == (
        "Merge readiness unknown: CODEOWNERS approval is required, but "
        "the required owners' review has not been verified."
    )


def test_policy_readiness_requires_the_merge_queue_when_configured() -> None:
    policy = GitHubMergePolicy(
        base_branch="main",
        branch_protection_available=True,
        branch_protection_enabled=True,
        rulesets=(
            GitHubRuleSetPolicy(
                ruleset_id=1,
                name="Queue main",
                enforcement="active",
                merge_queue_required=True,
            ),
        ),
    )
    state = _state(
        merge_policy=policy,
        merge_queue_state=GitHubPullQueueState(
            merge_queue_enabled=True,
            in_merge_queue=False,
            auto_merge_enabled=False,
            head_sha="a" * 40,
        ),
    )

    assert state.merge_readiness == (
        "Repository policy requires this pull request to enter the merge queue."
    )


def test_policy_readiness_rejects_stale_merge_queue_evidence() -> None:
    state = _state(
        merge_policy=GitHubMergePolicy(
            base_branch="main",
            branch_protection_available=True,
            branch_protection_enabled=True,
        ),
        merge_queue_state=GitHubPullQueueState(
            merge_queue_enabled=False,
            in_merge_queue=False,
            auto_merge_enabled=False,
            head_sha="b" * 40,
        ),
    )

    assert state.merge_readiness == (
        "Merge readiness unknown: the pull request head changed; refresh the review."
    )


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
