"""Unit tests for the wx-free GitHub items provider (#924).

PyGithub is mocked with lightweight stubs so the core mapping logic (model
construction, pagination/limit, error mapping, Safe Mode refusal) is testable
without wx or network.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import items_provider
from quill.core.github.items_provider import (
    GitHubItemsError,
    GitHubItemsProvider,
    refuse_in_safe_mode,
)

# ---------------------------------------------------------------------------
# Fake PyGithub plumbing
# ---------------------------------------------------------------------------


class _FakeGithubException(Exception):
    """Mimics github.GithubException: carries ``status`` and ``data``."""

    def __init__(self, status: int, message: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.data = {"message": message}


class _FakeRepo:
    """Records the calls and returns canned paginated results."""

    def __init__(
        self, *, full_name: str = "owner/repo", html_url: str = "https://github.com/owner/repo"
    ) -> None:
        self.full_name = full_name
        self.html_url = html_url
        self.calls: list[tuple[str, dict[str, Any]]] = []
        # Canned iterables per method.
        self._issues: list[Any] = []
        self._pulls: list[Any] = []
        self._branches: list[Any] = []
        self._commits: list[Any] = []
        self._tags: list[Any] = []
        self._releases: list[Any] = []
        self._runs: list[Any] = []
        self._issue_comments: dict[int, list[Any]] = {}

    def get_issues(self, state: str = "open") -> list[Any]:
        self.calls.append(("get_issues", {"state": state}))
        return self._issues

    def get_pulls(self, state: str = "open") -> list[Any]:
        self.calls.append(("get_pulls", {"state": state}))
        return self._pulls

    def get_branches(self) -> list[Any]:
        self.calls.append(("get_branches", {}))
        return self._branches

    def get_commits(self, **kwargs: Any) -> list[Any]:
        self.calls.append(("get_commits", dict(kwargs)))
        return self._commits

    def get_tags(self) -> list[Any]:
        self.calls.append(("get_tags", {}))
        return self._tags

    def get_releases(self) -> list[Any]:
        self.calls.append(("get_releases", {}))
        return self._releases

    def get_workflow_runs(self) -> list[Any]:
        self.calls.append(("get_workflow_runs", {}))
        return self._runs

    def get_issue(self, number: int) -> Any:
        self.calls.append(("get_issue", {"number": number}))
        return SimpleNamespace(
            get_comments=lambda: self._issue_comments.get(number, []),
        )


class _FakeGithubClient:
    def __init__(self, repo: _FakeRepo) -> None:
        self._repo = repo

    def get_repo(self, full_name: str) -> _FakeRepo:
        return self._repo

    def close(self) -> None:
        pass


def _install_fake_github(monkeypatch: pytest.MonkeyPatch, repo: _FakeRepo) -> None:
    """Make items_provider._get_gh_module return a fake github module."""
    fake_module = SimpleNamespace(
        Github=lambda auth=None: _FakeGithubClient(repo),
        Auth=SimpleNamespace(Token=lambda token: ("token", token)),
        GithubException=_FakeGithubException,
    )
    monkeypatch.setitem(sys.modules, "github", fake_module)
    # _get_gh_module imports github by name; once sys.modules has it, the import
    # resolves to our fake. Also patch the provider's helper for robustness.
    monkeypatch.setattr(items_provider, "_get_gh_module", lambda: fake_module)


@pytest.fixture
def repo() -> _FakeRepo:
    return _FakeRepo()


@pytest.fixture
def provider(repo: _FakeRepo, monkeypatch: pytest.MonkeyPatch) -> GitHubItemsProvider:
    _install_fake_github(monkeypatch, repo)
    return GitHubItemsProvider(token="tok")


# ---------------------------------------------------------------------------
# Safe Mode refusal (core-level, no wx needed)
# ---------------------------------------------------------------------------


def test_refuse_in_safe_mode_raises_when_active() -> None:
    with pytest.raises(GitHubItemsError, match="Safe Mode"):
        refuse_in_safe_mode(True)


def test_refuse_in_safe_mode_allows_when_inactive() -> None:
    refuse_in_safe_mode(False)  # must not raise


def test_github_items_error_carries_a_coded_code() -> None:
    # GATE-EC: the error must carry a greppable QUILL-* code in its str.
    err = GitHubItemsError("boom")
    assert "[QUILL-GITHUB-ITEMS-ERROR]" in str(err)


# ---------------------------------------------------------------------------
# Issue / PR mapping
# ---------------------------------------------------------------------------


def _issue_row(number: int, *, title: str = "T", state: str = "open", is_pr: bool = False) -> Any:
    row = SimpleNamespace(
        number=number,
        title=title,
        state=state,
        html_url=f"https://github.com/owner/repo/issues/{number}",
        user=SimpleNamespace(login="alice"),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
        body="body text",
        labels=[SimpleNamespace(name="bug"), SimpleNamespace(name="ui")],
        assignees=[SimpleNamespace(login="bob"), SimpleNamespace(login="carol")],
        comments=3,
        draft=False,
    )
    if is_pr:
        row.pull_request = SimpleNamespace(url="pr-url")
        row.merged = False
        row.additions = 10
        row.deletions = 2
        row.changed_files = 4
        row.base = SimpleNamespace(ref="main")
        row.head = SimpleNamespace(ref="feature-x")
    return row


def test_fetch_issues_maps_issue_fields(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    repo._issues = [_issue_row(208), _issue_row(209, title="Second")]
    items = provider.fetch_issues("owner/repo", state="open", limit=30)

    assert len(items) == 2
    first = items[0]
    assert first.number == 208
    assert first.title == "T"
    assert first.is_pr is False
    assert first.author == "alice"
    assert first.labels == ("bug", "ui")
    assert first.assignees == ("bob", "carol")
    assert first.comments == 3
    assert first.created_at.startswith("2026-01-01")
    # The state filter is forwarded to PyGithub.
    assert repo.calls[0] == ("get_issues", {"state": "open"})


def test_fetch_pulls_marks_is_pr_and_carries_diff(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    repo._pulls = [_issue_row(300, is_pr=True, title="PR")]
    items = provider.fetch_pulls("owner/repo", state="closed", limit=10)

    assert len(items) == 1
    pr = items[0]
    assert pr.is_pr is True
    assert pr.additions == 10
    assert pr.deletions == 2
    assert pr.changed_files == 4
    assert pr.base_branch == "main"
    assert pr.head_branch == "feature-x"
    # reviewDecision is not exposed by PyGithub's list endpoint -> empty in rows.
    assert pr.review_status == ""
    assert pr.is_merged is False
    assert pr.kind == "PR"
    assert pr.state_display == "OPEN"
    assert repo.calls[0] == ("get_pulls", {"state": "closed"})


def test_fetch_respects_limit(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    # 50 issues available; limit=5 must yield exactly 5 (pagination cap, #924).
    repo._issues = [_issue_row(n) for n in range(50)]
    items = provider.fetch_issues("owner/repo", limit=5)
    assert len(items) == 5
    assert [i.number for i in items] == [0, 1, 2, 3, 4]


def test_fetch_issues_empty_repo_returns_empty(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    repo._issues = []
    assert provider.fetch_issues("owner/repo") == []


# ---------------------------------------------------------------------------
# Branches / commits
# ---------------------------------------------------------------------------


def test_fetch_branches_maps_commit_metadata(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    repo._branches = [
        SimpleNamespace(
            name="main",
            commit=SimpleNamespace(
                sha="abc1234567",
                commit=SimpleNamespace(
                    message="Fix thing",
                    author=SimpleNamespace(name="Alice", date=datetime(2026, 1, 3, tzinfo=UTC)),
                ),
            ),
            protected=True,
        ),
    ]
    branches = provider.fetch_branches("owner/repo", limit=30)

    assert len(branches) == 1
    b = branches[0]
    assert b.name == "main"
    assert b.commit_sha == "abc1234567"
    assert b.commit_message == "Fix thing"
    assert b.commit_author == "Alice"
    assert b.commit_date.startswith("2026-01-03")
    assert b.protected is True
    assert b.url == "https://github.com/owner/repo/tree/main"


def test_fetch_commits_short_sha_and_stats(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    repo._commits = [
        SimpleNamespace(
            sha="0123456789abcdef",
            commit=SimpleNamespace(
                message="Commit one",
                author=SimpleNamespace(name="Bob", date=datetime(2026, 1, 4, tzinfo=UTC)),
            ),
            stats=SimpleNamespace(additions=7, deletions=1),
            files=[SimpleNamespace(filename="a.py"), SimpleNamespace(filename="b.py")],
            html_url="https://github.com/owner/repo/commit/0123456789abcdef",
        ),
    ]
    commits = provider.fetch_commits("owner/repo", branch="main", limit=30)

    assert len(commits) == 1
    c = commits[0]
    assert c.short_sha == "0123456"
    assert c.additions == 7
    assert c.deletions == 1
    assert c.files_changed == 2
    assert c.url.endswith("0123456789abcdef")
    # The branch is forwarded as sha= for get_commits.
    assert repo.calls[0] == ("get_commits", {"sha": "main"})


def test_fetch_commits_without_branch_passes_no_sha(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    repo._commits = []
    provider.fetch_commits("owner/repo")
    assert repo.calls[0] == ("get_commits", {})


# ---------------------------------------------------------------------------
# Tags / releases / workflow runs
# ---------------------------------------------------------------------------


def test_fetch_tags_maps_name_and_commit(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    repo._tags = [
        SimpleNamespace(name="v1.0", commit=SimpleNamespace(sha="tagsha1")),
    ]
    tags = provider.fetch_tags("owner/repo")
    assert tags[0].name == "v1.0"
    assert tags[0].commit_sha == "tagsha1"
    assert "v1.0" in tags[0].url


def test_fetch_releases_flags_draft_and_prerelease(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    repo._releases = [
        SimpleNamespace(
            tag_name="v2.0",
            title="Release 2.0",
            draft=True,
            prerelease=False,
            created_at=datetime(2026, 2, 1, tzinfo=UTC),
            html_url="https://github.com/owner/repo/releases/tag/v2.0",
            body="release notes",
        ),
    ]
    releases = provider.fetch_releases("owner/repo")
    r = releases[0]
    assert r.tag == "v2.0"
    assert r.draft is True
    assert r.prerelease is False
    assert r.created_at.startswith("2026-02-01")
    assert r.body == "release notes"


def test_fetch_workflow_runs_maps_status_and_conclusion(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    repo._runs = [
        SimpleNamespace(
            name="CI",
            status="completed",
            conclusion="success",
            head_branch="main",
            event="push",
            created_at=datetime(2026, 3, 1, tzinfo=UTC),
            html_url="https://github.com/owner/repo/actions/runs/1",
            run_number=42,
        ),
    ]
    runs = provider.fetch_workflow_runs("owner/repo")
    run = runs[0]
    assert run.name == "CI"
    assert run.status == "completed"
    assert run.conclusion == "success"
    assert run.branch == "main"
    assert run.event == "push"
    assert run.run_number == 42


# ---------------------------------------------------------------------------
# Comments (detail pane)
# ---------------------------------------------------------------------------


def test_fetch_issue_comments_returns_thread(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    repo._issue_comments[208] = [
        SimpleNamespace(
            user=SimpleNamespace(login="reviewer"),
            created_at=datetime(2026, 1, 5, tzinfo=UTC),
            body="looks good",
        ),
    ]
    comments = provider.fetch_issue_comments("owner/repo", 208)
    assert len(comments) == 1
    assert comments[0]["author"] == "reviewer"
    assert comments[0]["body"] == "looks good"
    assert comments[0]["created_at"].startswith("2026-01-05")


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


def test_fetch_raises_coded_error_for_missing_repo(
    repo: _FakeRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _MissingClient:
        def get_repo(self, full_name: str) -> Any:
            raise _FakeGithubException(404, "Not Found")

        def close(self) -> None:
            pass

    fake_module = SimpleNamespace(
        Github=lambda auth=None: _MissingClient(),
        Auth=SimpleNamespace(Token=lambda token: token),
        GithubException=_FakeGithubException,
    )
    monkeypatch.setattr(items_provider, "_get_gh_module", lambda: fake_module)
    provider = GitHubItemsProvider(token="tok")

    with pytest.raises(GitHubItemsError, match="not found"):
        provider.fetch_issues("missing/repo")


def test_fetch_raises_coded_error_on_403(repo: _FakeRepo, monkeypatch: pytest.MonkeyPatch) -> None:
    class _ForbiddenClient:
        def get_repo(self, full_name: str) -> Any:
            raise _FakeGithubException(403, "Forbidden")

        def close(self) -> None:
            pass

    fake_module = SimpleNamespace(
        Github=lambda auth=None: _ForbiddenClient(),
        Auth=SimpleNamespace(Token=lambda token: token),
        GithubException=_FakeGithubException,
    )
    monkeypatch.setattr(items_provider, "_get_gh_module", lambda: fake_module)
    provider = GitHubItemsProvider(token="tok")

    with pytest.raises(GitHubItemsError, match="Access denied"):
        provider.fetch_branches("owner/repo")


def test_fetch_surfaces_api_failure_as_coded_error(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    def _boom() -> list[Any]:
        raise RuntimeError("network down")

    repo.get_issues = _boom  # type: ignore[method-assign]
    with pytest.raises(GitHubItemsError, match="Could not list issues"):
        provider.fetch_issues("owner/repo")
