"""Branch ahead/behind against the default (branch_divergence.py) and the compare order fix."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from quill.core.github import branch_divergence as bd
from quill.core.github.branch_compare import (
    MAX_COMPARE_COMMITS,
    GitHubBranchComparison,
    fetch_branch_comparison,
)
from quill.core.github.items_provider import GitHubBranch


def _page(nodes: list[dict[str, Any]], *, more: bool = False) -> dict[str, Any]:
    return {
        "repository": {
            "refs": {
                "pageInfo": {"hasNextPage": more, "endCursor": "c1" if more else None},
                "nodes": nodes,
            }
        }
    }


def test_the_compare_direction_is_swapped_into_ahead_and_behind() -> None:
    """compare(headRef: default) on X: aheadBy is what the default has -- X's behind."""
    found, cursor = bd.parse_divergence_page(
        _page([{"name": "feature", "compare": {"aheadBy": 2, "behindBy": 5}}])
    )
    assert found == {"feature": bd.Divergence(ahead=5, behind=2)}
    assert cursor == ""


def test_pages_follow_the_cursor_and_skip_unanswered_rows(monkeypatch) -> None:
    pages = [
        _page([{"name": "a", "compare": {"aheadBy": 0, "behindBy": 1}}], more=True),
        _page([
            {"name": "b", "compare": None},
            {"name": "c", "compare": {"aheadBy": 3, "behindBy": 0}},
        ]),
    ]
    seen: list[Any] = []

    def fake(_token, _query, variables, *, action):
        seen.append(variables["after"])
        return pages[len(seen) - 1]

    monkeypatch.setattr(bd, "graphql_data", fake)
    found = bd.fetch_divergence("tok", "o/r", "main")
    assert seen == [None, "c1"]
    assert found == {"a": bd.Divergence(1, 0), "c": bd.Divergence(0, 3)}


def test_unknown_stays_unknown_and_the_default_says_so(monkeypatch) -> None:
    monkeypatch.setattr(
        bd, "fetch_divergence", lambda *_a: {"feature": bd.Divergence(ahead=3, behind=1)}
    )
    rows = [GitHubBranch("main", "a"), GitHubBranch("feature", "b"), GitHubBranch("gone", "c")]
    main, feature, gone = bd.with_divergence(rows, "tok", "o/r", "main")
    assert (feature.ahead, feature.behind) == (3, 1)
    assert gone.ahead is None and gone.behind is None
    say = bd.describe_divergence
    assert say(3, 1, default_branch="main") == "3 ahead, 1 behind main"
    assert say(0, 0, default_branch="main") == "even with main"
    assert say(None, None, default_branch="main") == ""
    assert say(None, None, default_branch="main", is_default=True) == "the default branch"
    assert main.default_branch == "main"


def test_a_failed_request_costs_the_counts_not_the_list(monkeypatch) -> None:
    def boom(*_a):
        raise RuntimeError("rate limited")

    monkeypatch.setattr(bd, "fetch_divergence", boom)
    rows = bd.with_divergence([GitHubBranch("feature", "b")], "tok", "o/r", "main")
    assert rows[0].ahead is None
    assert bd.with_divergence([GitHubBranch("x", "b")], None, "o/r", "main")[0].ahead is None


def _commit(n: int) -> Any:
    return SimpleNamespace(sha=f"{n:040d}", number=n)


def test_compare_shows_the_newest_commits_first_and_says_when_cut_short() -> None:
    """GitHub lists comparison commits oldest first; the dialog promises newest first."""
    oldest_first = [_commit(n) for n in range(1, 301)]
    comparison = SimpleNamespace(
        ahead_by=300,
        behind_by=0,
        status="ahead",
        total_commits=1204,
        commits=oldest_first,
        files=[],
    )
    repo = SimpleNamespace(compare=lambda _b, _h: comparison)
    result = fetch_branch_comparison(
        repo,
        "main",
        "feature",
        map_commit=lambda row: row.number,
        take=lambda rows, limit: list(rows or [])[:limit],
        limit=30,
    )
    assert len(result.commits) == MAX_COMPARE_COMMITS
    assert result.commits[0] == 250 and result.commits[-1] == 1
    assert result.commits_cut_short
    assert result.commits_tab_title() == "Commits (250 of 1,204, newest)"
    whole = GitHubBranchComparison("main", "f", total_commits=2, commits=(1, 2))  # type: ignore[arg-type]
    assert whole.commits_tab_title() == "Commits (2)"


def test_a_branch_reads_against_the_default_in_its_cells_and_detail() -> None:
    from quill.ui.github_items_view import model_detail, row_cells

    branch = GitHubBranch(
        name="feature",
        commit_sha="abc",
        commit_date=datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        ahead=2,
        behind=0,
        default_branch="main",
    )
    assert row_cells(branch, ("name", "against_default"), full=False) == ["feature", "2 ahead main"]
    assert "Against the default branch: 2 ahead main" in model_detail(branch)
    unknown = GitHubBranch(name="x", commit_sha="a", default_branch="main")
    assert "Against the default branch: not known" in model_detail(unknown)
