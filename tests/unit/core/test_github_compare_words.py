"""The comparison's words and the two extra halves of a fetch: behind and the open PR.

Wx-free: :mod:`quill.core.github.compare_words` and
:func:`quill.core.github.branch_compare.fetch_branch_comparison` against fakes.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github import compare_words
from quill.core.github.branch_compare import (
    GitHubBranchComparison,
    fetch_branch_comparison,
    split_compare_ref,
)
from quill.core.github.items_provider import GitHubCommit, GitHubPullFile


def _commit(sha: str, message: str = "Change") -> GitHubCommit:
    return GitHubCommit(sha=sha, short_sha=sha[:7], message=message)


def _comparison(**overrides: Any) -> GitHubBranchComparison:
    values: dict[str, Any] = {"base": "main", "head": "feature"}
    values.update(overrides)
    return GitHubBranchComparison(**values)


# -- words ---------------------------------------------------------------------


def test_relation_says_how_the_two_stand() -> None:
    assert compare_words.relation(_comparison(ahead_by=1)) == ("feature is 1 commit ahead of main.")
    assert compare_words.relation(_comparison(behind_by=3)) == ("feature is 3 commits behind main.")
    assert compare_words.relation(_comparison(ahead_by=2, behind_by=1205)) == (
        "feature and main have diverged: feature is 2 commits ahead and 1,205 behind."
    )
    assert compare_words.relation(_comparison(status="identical")) == (
        "feature and main are identical."
    )
    assert "compared with itself" in compare_words.relation(_comparison(head="main"))


def test_a_whole_sha_is_said_short() -> None:
    sha = "0123456789abcdef0123456789abcdef01234567"
    assert compare_words.relation(_comparison(base=sha, ahead_by=1)).endswith("of 0123456.")
    assert compare_words.naming(_comparison(base=sha)) == "feature compared with 0123456"


def test_pull_note_and_summary() -> None:
    plain = _comparison(ahead_by=1)
    assert compare_words.pull_note(plain) == ""
    with_pull = _comparison(
        ahead_by=1,
        pull_number=12,
        pull_title="Fix the crash",
        files=(GitHubPullFile(filename="a.py", status="modified", additions=3, deletions=1),),
    )
    assert compare_words.pull_note(with_pull) == "Pull request #12 is open: Fix the crash."
    assert compare_words.summary(with_pull) == (
        "feature is 1 commit ahead of main. 1 file changed, 3 lines added and 1 removed. "
        "Pull request #12 is open: Fix the crash."
    )


def test_tab_titles_and_lists_say_when_cut_short() -> None:
    c = _comparison(
        ahead_by=2,
        behind_by=300,
        total_commits=2,
        commits=(_commit("a" * 40), _commit("b" * 40)),
        behind_commits=tuple(_commit(f"{i:040x}") for i in range(250)),
    )
    assert compare_words.ahead_tab_title(c) == "Commits Ahead (2)"
    assert compare_words.behind_tab_title(c) == "Commits Behind (250 of 300, newest)"
    assert compare_words.list_said(c, behind=False) == "Commits ahead: 2."
    assert compare_words.list_said(c, behind=True) == "Commits behind: the newest 250 of 300."


def test_split_compare_ref() -> None:
    assert split_compare_ref("main...feature") == ("main", "feature")
    assert split_compare_ref("v1.0..v1.1") == ("v1.0", "v1.1")
    assert split_compare_ref("feat/x?expand=1") == ("", "feat/x")
    assert split_compare_ref("main...owner:feat") == ("main", "owner:feat")


# -- fetching --------------------------------------------------------------------


class _Repo:
    full_name = "owner/repo"
    default_branch = "trunk"

    def __init__(self, *, behind: int = 0, pulls: list[Any] | None = None) -> None:
        self.compared: list[tuple[str, str]] = []
        self.pull_queries: list[dict[str, str]] = []
        self._behind = behind
        self._pulls = pulls or []

    def compare(self, base: str, head: str) -> Any:
        self.compared.append((base, head))
        forward = len(self.compared) == 1
        rows = [SimpleNamespace(sha=f"{base}-{head}-{i}") for i in range(2)]
        return SimpleNamespace(
            ahead_by=2 if forward else self._behind,
            behind_by=self._behind if forward else 2,
            status="diverged",
            total_commits=2,
            commits=rows,
            files=[],
            html_url=f"https://github.com/owner/repo/compare/{base}...{head}",
        )

    def get_pulls(self, **kw: str) -> list[Any]:
        self.pull_queries.append(kw)
        return list(self._pulls)

    def get_commit(self, sha: str) -> Any:
        return SimpleNamespace(parents=[SimpleNamespace(sha=f"parent-of-{sha}")])


def _fetch(repo: _Repo, base: str, head: str) -> GitHubBranchComparison:
    return fetch_branch_comparison(
        repo,
        base,
        head,
        map_commit=lambda row: _commit(row.sha),
        take=lambda rows, limit: list(rows or [])[:limit],
        limit=30,
    )


def test_behind_commits_come_from_the_comparison_turned_round_newest_first() -> None:
    repo = _Repo(behind=2)
    result = _fetch(repo, "main", "feature")
    assert repo.compared == [("main", "feature"), ("feature", "main")]
    assert [c.sha for c in result.behind_commits] == ["feature-main-1", "feature-main-0"]


def test_nothing_behind_asks_github_once() -> None:
    repo = _Repo(behind=0)
    result = _fetch(repo, "main", "feature")
    assert repo.compared == [("main", "feature")]
    assert result.behind_commits == ()


def test_the_open_pull_request_is_found_by_owner_and_branch() -> None:
    pull = SimpleNamespace(number=7, title="Add it", html_url="https://github.com/o/r/pull/7")
    repo = _Repo(pulls=[pull])
    result = _fetch(repo, "main", "feature")
    assert repo.pull_queries == [{"state": "open", "base": "main", "head": "owner:feature"}]
    assert (result.pull_number, result.pull_title) == (7, "Add it")
    assert result.pull_url.endswith("/pull/7")


def test_a_failed_pull_lookup_never_costs_the_comparison() -> None:
    repo = _Repo()

    def _boom(**_kw: str) -> list[Any]:
        raise RuntimeError("rate limited")

    repo.get_pulls = _boom  # type: ignore[method-assign]
    result = _fetch(repo, "main", "feature")
    assert result.pull_number == 0 and result.ahead_by == 2


def test_an_empty_side_is_the_default_branch_and_a_caret_is_the_parent() -> None:
    repo = _Repo()
    result = _fetch(repo, "", "feature")
    assert result.base == "trunk"
    repo = _Repo()
    result = _fetch(repo, "abc123^", "abc123")
    assert repo.compared[0] == ("parent-of-abc123", "abc123")
    assert result.base == "parent-of-abc123"
