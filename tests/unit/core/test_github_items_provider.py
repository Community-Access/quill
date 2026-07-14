"""Unit tests for the wx-free GitHub items provider (#924).

PyGithub is mocked with lightweight stubs so the core mapping logic (model
construction, pagination/limit, error mapping, Safe Mode refusal) is testable
without wx or network.
"""

from __future__ import annotations

import io
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import items_provider
from quill.core.github.items_provider import (
    GitHubArtifact,
    GitHubItemsError,
    GitHubItemsProvider,
    GitHubRepoForkInfo,
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
        self,
        *,
        full_name: str = "owner/repo",
        html_url: str = "https://github.com/owner/repo",
        fork: bool = False,
        parent: Any = None,
    ) -> None:
        self.full_name = full_name
        self.html_url = html_url
        self.fork = fork
        self.parent = parent
        self.calls: list[tuple[str, dict[str, Any]]] = []
        # Canned iterables per method.
        self._issues: list[Any] = []
        self._pulls: list[Any] = []
        self._branches: list[Any] = []
        self._commits: list[Any] = []
        self._tags: list[Any] = []
        self._releases: list[Any] = []
        self._runs: list[Any] = []
        self._workflows: list[Any] = []
        self._issue_comments: dict[int, list[Any]] = {}
        self._reruns: list[int] = []
        self._jobs: list[Any] = []
        self._dispatches: list[tuple[str, str, dict]] = []
        self._dispatch_ok = True
        self._alerts: list[Any] = []
        self._artifacts: list[Any] = []

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

    def get_workflows(self) -> list[Any]:
        self.calls.append(("get_workflows", {}))
        return self._workflows

    def get_issue(self, number: int) -> Any:
        self.calls.append(("get_issue", {"number": number}))
        return SimpleNamespace(
            get_comments=lambda: self._issue_comments.get(number, []),
            create_comment=lambda body: self._make_comment(number, body),
        )

    def _make_comment(self, number: int, body: str) -> Any:
        comment = SimpleNamespace(
            id=len(self._issue_comments.get(number, [])) + 1,
            user=SimpleNamespace(login="me"),
            created_at=datetime(2026, 1, 6, tzinfo=UTC),
            body=body,
        )
        self._issue_comments.setdefault(number, []).append(comment)
        return comment

    def create_issue(self, *, title: str, body: str = "") -> Any:
        self.calls.append(("create_issue", {"title": title, "body": body}))
        return SimpleNamespace(
            number=1,
            title=title,
            body=body,
            state="open",
            html_url="https://github.com/owner/repo/issues/1",
            user=SimpleNamespace(login="me"),
            created_at=datetime(2026, 1, 6, tzinfo=UTC),
            updated_at=datetime(2026, 1, 6, tzinfo=UTC),
            labels=[],
            assignees=[],
            comments=0,
            draft=False,
        )

    def create_pull(self, *, title: str, body: str, head: str, base: str) -> Any:
        self.calls.append((
            "create_pull",
            {"title": title, "body": body, "head": head, "base": base},
        ))
        return SimpleNamespace(
            number=2,
            title=title,
            body=body,
            state="open",
            html_url="https://github.com/owner/repo/pull/2",
            user=SimpleNamespace(login="me"),
            created_at=datetime(2026, 1, 6, tzinfo=UTC),
            updated_at=datetime(2026, 1, 6, tzinfo=UTC),
            labels=[],
            assignees=[],
            comments=0,
            draft=False,
            pull_request=SimpleNamespace(url="pr-url"),
            merged=False,
            additions=0,
            deletions=0,
            changed_files=0,
            base=SimpleNamespace(ref=base),
            head=SimpleNamespace(ref=head),
        )

    def get_pull(self, number: int) -> Any:
        self.calls.append(("get_pull", {"number": number}))
        return SimpleNamespace(
            merge=lambda **kwargs: SimpleNamespace(merged=True, sha="merged-sha", message="")
        )

    def get_workflow_run(self, run_id: int) -> Any:
        self.calls.append(("get_workflow_run", {"run_id": run_id}))
        reruns: list[int] = self._reruns
        return SimpleNamespace(
            rerun=lambda: reruns.append(run_id),
            jobs=lambda: self._jobs,
            get_artifacts=lambda: self._artifacts,
        )

    def get_workflow(self, workflow_id: str) -> Any:
        self.calls.append(("get_workflow", {"workflow_id": workflow_id}))
        dispatches: list[tuple[str, str, dict]] = self._dispatches

        def create_dispatch(ref: str, inputs: dict | None = None) -> bool:
            dispatches.append((workflow_id, ref, inputs or {}))
            return self._dispatch_ok

        return SimpleNamespace(create_dispatch=create_dispatch)

    def get_dependabot_alerts(self, state: str = "open") -> list[Any]:
        self.calls.append(("get_dependabot_alerts", {"state": state}))
        return self._alerts

    def get_issue_comment(self, comment_id: int) -> Any:
        self.calls.append(("get_issue_comment", {"comment_id": comment_id}))
        store = self._issue_comments
        found: Any = None
        for comments in store.values():
            for comment in comments:
                if comment.id == comment_id:
                    found = comment
                    break
        if found is None:
            found = SimpleNamespace(
                id=comment_id,
                user=SimpleNamespace(login="me"),
                created_at=datetime(2026, 1, 6, tzinfo=UTC),
                body="",
            )

        def edit(body: str) -> None:
            found.body = body

        def delete() -> None:
            for comments in store.values():
                comments[:] = [c for c in comments if c.id != comment_id]

        found.edit = edit
        found.delete = delete
        return found


class _FakeAuthenticatedUser:
    def __init__(self) -> None:
        self.notifications: list[Any] = []
        self.read_ids: list[str] = []

    def get_notifications(self) -> list[Any]:
        return self.notifications

    def get_notification(self, notification_id: str) -> Any:
        read_ids = self.read_ids

        def mark_as_read() -> None:
            read_ids.append(notification_id)

        return SimpleNamespace(mark_as_read=mark_as_read)


class _FakeGithubClient:
    def __init__(self, repo: _FakeRepo) -> None:
        self._repo = repo
        self.searches: list[str] = []
        self.search_results: list[Any] = []
        self._user = _FakeAuthenticatedUser()

    def get_repo(self, full_name: str) -> _FakeRepo:
        return self._repo

    def get_user(self) -> _FakeAuthenticatedUser:
        return self._user

    def search_issues(self, query: str) -> list[Any]:
        self.searches.append(query)
        return self.search_results

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
# Compare Branches (GHManage parity, Ctrl+Shift+B)
# ---------------------------------------------------------------------------


def test_compare_branches_maps_counts_commits_and_files(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    commit_row = SimpleNamespace(
        sha="0123456789abcdef",
        commit=SimpleNamespace(
            message="Fix thing",
            author=SimpleNamespace(name="Bob", date=datetime(2026, 1, 4, tzinfo=UTC)),
        ),
        stats=SimpleNamespace(additions=3, deletions=1),
        files=[SimpleNamespace(filename="a.py")],
        html_url="https://github.com/owner/repo/commit/0123456789abcdef",
    )
    file_row = SimpleNamespace(
        filename="quill/core/x.py",
        status="modified",
        additions=4,
        deletions=1,
        changes=5,
        previous_filename=None,
        patch="@@ -1 +1 @@",
    )
    captured: list[tuple[str, str]] = []

    def _compare(base: str, head: str) -> Any:
        captured.append((base, head))
        return SimpleNamespace(
            ahead_by=3,
            behind_by=1,
            status="diverged",
            total_commits=3,
            commits=[commit_row],
            files=[file_row],
            html_url="https://github.com/owner/repo/compare/main...feature",
        )

    repo.compare = _compare  # type: ignore[attr-defined]
    result = provider.compare_branches("owner/repo", "main", "feature")

    assert captured == [("main", "feature")]
    assert result.base == "main" and result.head == "feature"
    assert result.ahead_by == 3 and result.behind_by == 1
    assert result.status == "diverged" and result.total_commits == 3
    assert result.commits[0].short_sha == "0123456"
    assert result.files[0].filename == "quill/core/x.py"
    assert result.permalink_url.endswith("main...feature")


def test_compare_branches_wraps_failures_as_coded_errors(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    def _boom(base: str, head: str) -> Any:
        raise RuntimeError("no common ancestor")

    repo.compare = _boom  # type: ignore[attr-defined]
    with pytest.raises(GitHubItemsError, match="Could not compare"):
        provider.compare_branches("owner/repo", "main", "feature")


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


def test_fetch_workflows_maps_id_name_path_state(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    repo._workflows = [
        SimpleNamespace(
            id=12345,
            name="CI",
            path=".github/workflows/ci.yml",
            state="active",
            html_url="https://github.com/owner/repo/actions/workflows/ci.yml",
            badge_url="https://github.com/owner/repo/workflows/CI/badge.svg",
        ),
    ]
    workflows = provider.fetch_workflows("owner/repo")
    wf = workflows[0]
    assert wf.id == 12345
    assert wf.name == "CI"
    assert wf.path == ".github/workflows/ci.yml"
    assert wf.state == "active"
    assert wf.url.endswith("ci.yml")


def test_fetch_workflows_wraps_failures_as_coded_errors(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    def _boom() -> list[Any]:
        raise RuntimeError("rate limited")

    repo.get_workflows = _boom  # type: ignore[attr-defined,method-assign]
    with pytest.raises(GitHubItemsError, match="Could not list workflows"):
        provider.fetch_workflows("owner/repo")


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


# ---------------------------------------------------------------------------
# Advanced search (Unified GitHub Management: full GitHub search syntax)
# ---------------------------------------------------------------------------


def test_search_items_pins_the_repo_qualifier(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    client = provider._gh
    client.search_results = [_issue_row(42, title="Found")]
    items = provider.search_items("owner/repo", "label:bug is:open crash")
    assert client.searches == ["repo:owner/repo label:bug is:open crash"]
    assert [item.number for item in items] == [42]
    # A PR-shaped search row (pull_request link present) maps as a PR.
    client.search_results = [_issue_row(7, is_pr=True)]
    assert provider.search_items("owner/repo", "is:pr")[0].is_pr is True


def test_search_items_with_a_blank_query_is_a_no_op(
    provider: GitHubItemsProvider,
) -> None:
    assert provider.search_items("owner/repo", "   ") == []


def test_search_items_maps_failures_to_coded_errors(
    provider: GitHubItemsProvider,
) -> None:
    def _boom(_query: str):
        raise RuntimeError("rate limited")

    provider._gh.search_issues = _boom
    with pytest.raises(GitHubItemsError, match="Search failed"):
        provider.search_items("owner/repo", "label:bug")


# ---------------------------------------------------------------------------
# PR diff inventory + file content + batch updates (Unified GitHub Management)
# ---------------------------------------------------------------------------


def test_fetch_pull_diff_maps_files_and_refs(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    file_row = SimpleNamespace(
        filename="quill/core/x.py",
        status="modified",
        additions=4,
        deletions=1,
        changes=5,
        previous_filename=None,
        patch="@@ -1 +1 @@",
    )
    repo.get_pull = lambda number: SimpleNamespace(  # type: ignore[attr-defined]
        title="Fix x",
        base=SimpleNamespace(ref="main", sha="b" * 40),
        head=SimpleNamespace(ref="fix-x", sha="h" * 40),
        get_files=lambda: [file_row],
    )
    diff = provider.fetch_pull_diff("owner/repo", 42)
    assert diff.number == 42 and diff.title == "Fix x"
    assert diff.base_ref == "main" and diff.head_ref == "fix-x"
    assert diff.base_sha.startswith("b") and diff.head_sha.startswith("h")
    assert diff.files[0].filename == "quill/core/x.py"
    assert diff.files[0].additions == 4 and diff.files[0].deletions == 1


def test_fetch_file_text_decodes_and_maps_missing_to_empty(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    repo.get_contents = lambda path, ref: SimpleNamespace(  # type: ignore[attr-defined]
        decoded_content=b"hello\nworld\n"
    )
    assert provider.fetch_file_text("owner/repo", "a.md", "sha") == "hello\nworld\n"

    def _missing(path, ref):
        raise _FakeGithubException(404, "not found")

    repo.get_contents = _missing  # type: ignore[attr-defined]
    assert provider.fetch_file_text("owner/repo", "gone.md", "sha") == ""


def test_fetch_file_text_rejects_binary_clearly(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    repo.get_contents = lambda path, ref: SimpleNamespace(  # type: ignore[attr-defined]
        decoded_content=b"\x00\xff\xfe binary"
    )
    with pytest.raises(GitHubItemsError, match="not a text file"):
        provider.fetch_file_text("owner/repo", "img.png", "sha")


def test_update_items_requires_a_token() -> None:
    anonymous_repo = _FakeRepo()
    fake_module = SimpleNamespace(
        Github=lambda auth=None: _FakeGithubClient(anonymous_repo),
        Auth=SimpleNamespace(Token=lambda token: ("token", token)),
        GithubException=_FakeGithubException,
    )
    import sys as _sys

    _sys.modules["github"] = fake_module
    try:
        import quill.core.github.items_provider as ip

        original = ip._get_gh_module
        ip._get_gh_module = lambda: fake_module
        try:
            anonymous = GitHubItemsProvider(token=None)
            assert anonymous.is_authenticated is False
            with pytest.raises(GitHubItemsError, match="read-only"):
                anonymous.update_items("owner/repo", [1], state="closed")
        finally:
            ip._get_gh_module = original
    finally:
        _sys.modules.pop("github", None)


def test_update_items_applies_state_and_labels_collecting_errors(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    edited: list[tuple[int, str]] = []
    labeled: list[tuple[int, tuple]] = []

    def get_issue(number: int):
        if number == 13:
            raise RuntimeError("no such issue")
        return SimpleNamespace(
            edit=lambda state: edited.append((number, state)),
            add_to_labels=lambda *labels: labeled.append((number, labels)),
        )

    repo.get_issue = get_issue  # type: ignore[attr-defined]
    assert provider.is_authenticated is True
    errors = provider.update_items(
        "owner/repo", [7, 13, 9], state="closed", add_labels=("wontfix",)
    )
    assert edited == [(7, "closed"), (9, "closed")]
    assert labeled == [(7, ("wontfix",)), (9, ("wontfix",))]
    assert len(errors) == 1 and errors[0].startswith("#13:")


def test_update_items_rejects_unknown_state(provider: GitHubItemsProvider) -> None:
    with pytest.raises(GitHubItemsError, match="Unknown state"):
        provider.update_items("owner/repo", [1], state="merged")


# ---------------------------------------------------------------------------
# Creating issues, pull requests, comments; merging; re-running workflows
# ---------------------------------------------------------------------------


def test_create_issue(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    item = provider.create_issue("owner/repo", "Bug found", "steps to repro")
    assert item.title == "Bug found"
    assert item.body == "steps to repro"
    assert item.is_pr is False
    assert repo.calls[0] == ("create_issue", {"title": "Bug found", "body": "steps to repro"})


def test_create_issue_requires_a_token() -> None:
    anon_repo = _FakeRepo()
    fake_module = SimpleNamespace(
        Github=lambda auth=None: _FakeGithubClient(anon_repo),
        Auth=SimpleNamespace(Token=lambda token: ("token", token)),
        GithubException=_FakeGithubException,
    )
    import sys as _sys

    _sys.modules["github"] = fake_module
    try:
        import quill.core.github.items_provider as ip

        original = ip._get_gh_module
        ip._get_gh_module = lambda: fake_module
        try:
            anonymous = GitHubItemsProvider(token=None)
            with pytest.raises(GitHubItemsError, match="signed-in"):
                anonymous.create_issue("owner/repo", "T")
        finally:
            ip._get_gh_module = original
    finally:
        _sys.modules.pop("github", None)


def test_create_pull_request(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    item = provider.create_pull_request("owner/repo", "Fix it", "body", "feature", "main")
    assert item.is_pr is True
    assert item.base_branch == "main"
    assert item.head_branch == "feature"
    assert repo.calls[0] == (
        "create_pull",
        {"title": "Fix it", "body": "body", "head": "feature", "base": "main"},
    )


def test_merge_pull_request_returns_sha(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    sha = provider.merge_pull_request("owner/repo", 42, merge_method="squash")
    assert sha == "merged-sha"
    assert repo.calls[0] == ("get_pull", {"number": 42})


def test_merge_pull_request_rejects_unknown_method(provider: GitHubItemsProvider) -> None:
    with pytest.raises(GitHubItemsError, match="Unknown merge method"):
        provider.merge_pull_request("owner/repo", 42, merge_method="octopus")


def test_merge_pull_request_surfaces_github_refusal(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    repo.get_pull = lambda number: SimpleNamespace(  # type: ignore[attr-defined]
        merge=lambda **kwargs: SimpleNamespace(merged=False, sha="", message="not mergeable")
    )
    with pytest.raises(GitHubItemsError, match="not mergeable"):
        provider.merge_pull_request("owner/repo", 42)


def test_rerun_workflow_run(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    provider.rerun_workflow_run("owner/repo", 999)
    assert repo._reruns == [999]


def test_create_comment_posts_to_the_thread(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    result = provider.create_comment("owner/repo", 208, "thanks, LGTM")
    assert result["body"] == "thanks, LGTM"
    assert result["author"] == "me"
    assert result["id"]
    assert len(repo._issue_comments[208]) == 1


def test_edit_comment_updates_body(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    posted = provider.create_comment("owner/repo", 208, "typo hree")
    result = provider.edit_comment("owner/repo", int(posted["id"]), "typo here")
    assert result["body"] == "typo here"


def test_delete_comment_removes_it(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    posted = provider.create_comment("owner/repo", 208, "oops, wrong thread")
    provider.delete_comment("owner/repo", int(posted["id"]))
    assert repo._issue_comments[208] == []


def test_fetch_issue_comments_includes_id(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    repo._issue_comments[208] = [
        SimpleNamespace(
            id=555,
            user=SimpleNamespace(login="reviewer"),
            created_at=datetime(2026, 1, 5, tzinfo=UTC),
            body="looks good",
        ),
    ]
    comments = provider.fetch_issue_comments("owner/repo", 208)
    assert comments[0]["id"] == "555"


# ---------------------------------------------------------------------------
# Workflow jobs, dispatch, notifications, security alerts (Tier 2)
# ---------------------------------------------------------------------------


def test_fetch_workflow_jobs(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    repo._jobs = [
        SimpleNamespace(
            name="build",
            status="completed",
            conclusion="success",
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
            completed_at=datetime(2026, 1, 1, 0, 5, tzinfo=UTC),
            html_url="https://github.com/owner/repo/actions/runs/1/jobs/1",
        ),
    ]
    jobs = provider.fetch_workflow_jobs("owner/repo", 1)
    assert len(jobs) == 1
    assert jobs[0].name == "build"
    assert jobs[0].conclusion == "success"


def test_dispatch_workflow(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    provider.dispatch_workflow("owner/repo", "ci.yml", "main", inputs={"env": "prod"})
    assert repo._dispatches == [("ci.yml", "main", {"env": "prod"})]


def test_dispatch_workflow_requires_a_token() -> None:
    anonymous_repo = _FakeRepo()
    fake_module = SimpleNamespace(
        Github=lambda auth=None: _FakeGithubClient(anonymous_repo),
        Auth=SimpleNamespace(Token=lambda token: ("token", token)),
        GithubException=_FakeGithubException,
    )
    import sys as _sys

    _sys.modules["github"] = fake_module
    try:
        import quill.core.github.items_provider as ip

        original = ip._get_gh_module
        ip._get_gh_module = lambda: fake_module
        try:
            anonymous = GitHubItemsProvider(token=None)
            with pytest.raises(GitHubItemsError, match="signed-in"):
                anonymous.dispatch_workflow("owner/repo", "ci.yml", "main")
        finally:
            ip._get_gh_module = original
    finally:
        _sys.modules.pop("github", None)


def test_dispatch_workflow_surfaces_a_declined_dispatch(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    repo._dispatch_ok = False
    with pytest.raises(GitHubItemsError, match="declined to dispatch"):
        provider.dispatch_workflow("owner/repo", "ci.yml", "main")


def test_fetch_notifications(provider: GitHubItemsProvider) -> None:
    provider._gh._user.notifications = [
        SimpleNamespace(
            id="1",
            repository=SimpleNamespace(full_name="owner/repo"),
            reason="mention",
            subject=SimpleNamespace(title="Fix the bug", type="Issue"),
            unread=True,
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
            url="https://api.github.com/notifications/threads/1",
        ),
    ]
    notifications = provider.fetch_notifications()
    assert len(notifications) == 1
    assert notifications[0].repository == "owner/repo"
    assert notifications[0].subject_title == "Fix the bug"
    assert notifications[0].unread is True


def test_mark_notification_read(provider: GitHubItemsProvider) -> None:
    provider.mark_notification_read("42")
    assert provider._gh._user.read_ids == ["42"]


def test_fetch_security_alerts(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    repo._alerts = [
        SimpleNamespace(
            number=1,
            state="open",
            security_advisory=SimpleNamespace(severity="high", summary="Bad dep"),
            dependency=SimpleNamespace(package=SimpleNamespace(name="left-pad")),
            html_url="https://github.com/owner/repo/security/dependabot/1",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    ]
    alerts = provider.fetch_security_alerts("owner/repo")
    assert len(alerts) == 1
    assert alerts[0].severity == "high"
    assert alerts[0].package == "left-pad"
    assert repo.calls[-1] == ("get_dependabot_alerts", {"state": "open"})


# ---------------------------------------------------------------------------
# Fork/upstream info (View Upstream)
# ---------------------------------------------------------------------------


def test_fetch_fork_info_for_a_non_fork(provider: GitHubItemsProvider, repo: _FakeRepo) -> None:
    assert repo.fork is False
    info = provider.fetch_fork_info("owner/repo")
    assert info == GitHubRepoForkInfo(is_fork=False, parent_full_name="")


def test_fetch_fork_info_for_a_fork(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _FakeRepo(
        full_name="me/repo", fork=True, parent=SimpleNamespace(full_name="upstream/repo")
    )
    _install_fake_github(monkeypatch, repo)
    provider = GitHubItemsProvider(token="tok")

    info = provider.fetch_fork_info("me/repo")
    assert info == GitHubRepoForkInfo(is_fork=True, parent_full_name="upstream/repo")


def test_fetch_fork_info_fork_with_no_resolvable_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fork whose parent PyGithub could not resolve (deleted, private, or a
    transient API gap) must still report is_fork=True with an empty parent
    name, not raise -- the dialog's View Upstream button simply stays
    disabled rather than crashing the repo load."""
    repo = _FakeRepo(full_name="me/repo", fork=True, parent=None)
    _install_fake_github(monkeypatch, repo)
    provider = GitHubItemsProvider(token="tok")

    info = provider.fetch_fork_info("me/repo")
    assert info == GitHubRepoForkInfo(is_fork=True, parent_full_name="")


# ---------------------------------------------------------------------------
# Workflow run artifacts (list + download)
# ---------------------------------------------------------------------------


class _FakeHTTPResponse:
    """A minimal context-manager response: headers.get() + chunked read()."""

    def __init__(self, data: bytes, headers: dict[str, str]) -> None:
        self._buf = io.BytesIO(data)
        self.headers = SimpleNamespace(get=lambda key, default=None: headers.get(key, default))

    def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def test_fetch_workflow_run_artifacts_maps_rows(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    repo._artifacts = [
        SimpleNamespace(
            id=1,
            name="build-output",
            size_in_bytes=2048,
            expired=False,
            archive_download_url="https://api.github.com/artifacts/1/zip",
        )
    ]
    artifacts = provider.fetch_workflow_run_artifacts("owner/repo", 42)
    assert artifacts == [
        GitHubArtifact(
            id=1,
            name="build-output",
            size_bytes=2048,
            expired=False,
            archive_download_url="https://api.github.com/artifacts/1/zip",
        )
    ]
    assert repo.calls[-1] == ("get_workflow_run", {"run_id": 42})


def test_fetch_workflow_run_artifacts_wraps_errors(
    provider: GitHubItemsProvider, repo: _FakeRepo
) -> None:
    def _boom(_run_id: int) -> Any:
        raise RuntimeError("network gone")

    repo.get_workflow_run = _boom  # type: ignore[method-assign]
    with pytest.raises(GitHubItemsError, match="Could not list artifacts"):
        provider.fetch_workflow_run_artifacts("owner/repo", 42)


def test_download_artifact_rejects_an_expired_artifact(
    provider: GitHubItemsProvider, tmp_path: Any
) -> None:
    artifact = GitHubArtifact(
        id=1,
        name="build-output",
        size_bytes=10,
        expired=True,
        archive_download_url="https://api.github.com/artifacts/1/zip",
    )
    with pytest.raises(GitHubItemsError, match="expired"):
        provider.download_artifact_to_file(artifact, tmp_path / "out.zip")


def test_download_artifact_needs_a_signed_in_account(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _FakeRepo()
    _install_fake_github(monkeypatch, repo)
    anonymous_provider = GitHubItemsProvider(token=None)
    artifact = GitHubArtifact(
        id=1,
        name="build-output",
        size_bytes=10,
        expired=False,
        archive_download_url="https://api.github.com/artifacts/1/zip",
    )
    with pytest.raises(GitHubItemsError, match="signed-in"):
        anonymous_provider.download_artifact_to_file(artifact, tmp_path / "out.zip")


def test_download_artifact_rejects_a_non_https_url(
    provider: GitHubItemsProvider, tmp_path: Any
) -> None:
    artifact = GitHubArtifact(
        id=1,
        name="build-output",
        size_bytes=10,
        expired=False,
        archive_download_url="http://api.github.com/artifacts/1/zip",
    )
    with pytest.raises(GitHubItemsError, match="HTTPS"):
        provider.download_artifact_to_file(artifact, tmp_path / "out.zip")


def test_download_artifact_follows_redirect_and_drops_auth_header(
    provider: GitHubItemsProvider, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The core security property: GitHub's artifact endpoint 302s to a
    signed URL on a different host (Azure Blob Storage in production), and
    the Authorization header must not be forwarded to that second request."""
    artifact = GitHubArtifact(
        id=1,
        name="build-output",
        size_bytes=4,
        expired=False,
        archive_download_url="https://api.github.com/artifacts/1/zip",
    )
    redirect_target = "https://blob.example.com/signed/1/zip?sig=abc"

    class _FakeOpener:
        def open(self, request: urllib.request.Request, timeout: int = 60) -> Any:
            assert request.get_full_url() == artifact.archive_download_url
            assert request.headers.get("Authorization") == "Bearer tok"
            raise urllib.error.HTTPError(
                artifact.archive_download_url, 302, "Found", {"Location": redirect_target}, None
            )

    captured_final_request: list[urllib.request.Request] = []

    def _fake_urlopen(request: urllib.request.Request, timeout: int = 60) -> _FakeHTTPResponse:
        captured_final_request.append(request)
        return _FakeHTTPResponse(b"zipdata", {"Content-Length": "7"})

    monkeypatch.setattr(items_provider.urllib.request, "build_opener", lambda *_h: _FakeOpener())
    monkeypatch.setattr(items_provider.urllib.request, "urlopen", _fake_urlopen)

    dest = tmp_path / "out.zip"
    progress_calls: list[tuple[int, int]] = []
    result = provider.download_artifact_to_file(
        artifact, dest, progress=lambda done, total: progress_calls.append((done, total))
    )

    assert result == dest
    assert dest.read_bytes() == b"zipdata"
    assert len(captured_final_request) == 1
    final_request = captured_final_request[0]
    assert final_request.get_full_url() == redirect_target
    assert "Authorization" not in final_request.headers
    assert progress_calls[-1] == (7, 7)


def test_download_artifact_rejects_a_non_https_redirect(
    provider: GitHubItemsProvider, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = GitHubArtifact(
        id=1,
        name="build-output",
        size_bytes=4,
        expired=False,
        archive_download_url="https://api.github.com/artifacts/1/zip",
    )

    class _FakeOpener:
        def open(self, request: urllib.request.Request, timeout: int = 60) -> Any:
            raise urllib.error.HTTPError(
                artifact.archive_download_url,
                302,
                "Found",
                {"Location": "http://blob.example.com/signed/1/zip"},
                None,
            )

    monkeypatch.setattr(items_provider.urllib.request, "build_opener", lambda *_h: _FakeOpener())
    with pytest.raises(GitHubItemsError, match="HTTPS"):
        provider.download_artifact_to_file(artifact, tmp_path / "out.zip")


def test_download_artifact_honors_should_cancel(
    provider: GitHubItemsProvider, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = GitHubArtifact(
        id=1,
        name="build-output",
        size_bytes=4,
        expired=False,
        archive_download_url="https://api.github.com/artifacts/1/zip",
    )

    class _FakeOpener:
        def open(self, request: urllib.request.Request, timeout: int = 60) -> Any:
            return _FakeHTTPResponse(b"zipdata", {"Content-Length": "7"})

    monkeypatch.setattr(items_provider.urllib.request, "build_opener", lambda *_h: _FakeOpener())

    with pytest.raises(GitHubItemsError, match="cancelled"):
        provider.download_artifact_to_file(
            artifact, tmp_path / "out.zip", should_cancel=lambda: True
        )
