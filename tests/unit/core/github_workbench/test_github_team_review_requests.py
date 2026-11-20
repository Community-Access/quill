"""Review requests made to a team you belong to, in Needs My Attention (GH-R-143)."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.github.explore import GitHubExploreClient
from quill.core.github.explore_models import ExploreRow
from quill.core.github.review_requests import TEAM_MARK, as_team_request, is_direct_request
from quill.core.workbench.filters import Query


def _pull(number: int) -> SimpleNamespace:
    return SimpleNamespace(
        number=number,
        title=f"Change {number}",
        html_url=f"https://github.com/o/r/pull/{number}",
        repository=SimpleNamespace(full_name="o/r"),
        state="open",
        pull_request=SimpleNamespace(),
        updated_at=f"2026-11-1{number}",
    )


class _Provider:
    """GitHub search as it answers: review-requested includes your teams' requests."""

    is_authenticated = True
    token = "secret"

    def __init__(self, *, direct=(1,), broad=(1, 2), assigned=()) -> None:
        self.searches: list[str] = []
        self._answers = {
            "user-review-requested:me": direct,
            "review-requested:me": broad,
            "assignee:me": assigned,
        }
        user = SimpleNamespace(login="me")
        self._gh = SimpleNamespace(get_user=lambda *_a: user, search_issues=self._search)

    def _search(self, query: str):
        self.searches.append(query)
        for needle, numbers in self._answers.items():  # the most specific first
            if needle in query:
                return [_pull(n) for n in numbers]
        return []


def _by_key(rows) -> dict[str, ExploreRow]:
    return {row.key: row for row in rows}


def test_my_work_marks_a_team_request_and_keeps_yours_unmarked() -> None:
    provider = _Provider()
    rows = _by_key(GitHubExploreClient(provider).fetch("my_work"))  # type: ignore[arg-type]

    assert "is:open is:pr user-review-requested:me" in provider.searches
    assert "is:open is:pr review-requested:me" in provider.searches
    assert TEAM_MARK not in rows["1"].label
    assert rows["1"].detail.startswith("Review requested")
    assert rows["2"].label == f"o/r #2: Change 2 (PR, {TEAM_MARK})"
    assert rows["2"].detail.startswith("Team review requested")
    assert "a team you belong to" in rows["2"].detail


def test_review_requests_node_lists_both_and_the_team_row_says_so() -> None:
    from quill.core.github.workbench_tree import GITHUB_TREE
    from quill.ui.github_workbench_explore import load_explore

    node = GITHUB_TREE.node("review_requests")
    client = GitHubExploreClient(_Provider(assigned=(3,)))  # type: ignore[arg-type]
    rows = load_explore(client, node, instance="", query=Query())

    assert sorted(row.key for row in rows) == ["1", "2"]
    assert [row.key for row in rows if TEAM_MARK in row.label] == ["2"]


def test_a_team_request_that_is_also_assigned_to_you_keeps_both_reasons() -> None:
    rows = _by_key(
        GitHubExploreClient(_Provider(assigned=(2,))).fetch("my_work")  # type: ignore[arg-type]
    )

    first = rows["2"].detail.split("\n", 1)[0]
    assert first.split("; ") == ["Assigned", "Team review requested"]
    assert TEAM_MARK in rows["2"].label


def test_the_inbox_marks_team_requests_once_and_never_a_direct_one() -> None:
    provider = _Provider(assigned=(2,))
    result = GitHubExploreClient(provider).fetch_attention(  # type: ignore[arg-type]
        categories=["assigned", "review_requested"]
    )
    rows = _by_key(result.items)

    assert result.complete
    assert TEAM_MARK not in rows["1"].label
    assert rows["2"].label.count(TEAM_MARK) == 1
    assert rows["2"].detail.startswith("Also: Assigned, Team review requested")


def test_marking_is_idempotent_and_direct_is_read_from_either_separator() -> None:
    row = ExploreRow("o/r #2: Change 2 (PR)", "Team review requested\no/r #2: Change 2 (PR)")
    marked = as_team_request(row)
    assert as_team_request(marked) is marked
    assert marked.detail.split("\n")[2] == marked.label
    assert is_direct_request("Also: Assigned, Review requested")
    assert is_direct_request("Mentioned; Review requested")
    assert not is_direct_request("Team review requested")
