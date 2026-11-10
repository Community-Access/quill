"""GitHub Workbench Phase 2: Explore GitHub's views load as tree nodes."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.github.explore_models import ExploreRow  # noqa: E402
from quill.core.github.workbench_tree import GITHUB_TREE  # noqa: E402
from quill.core.workbench.filters import parse  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.test_github_workbench_window import REPO, _go, _inline, _Items  # noqa: E402


class _Explore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, str]] = []

    def account_login(self) -> str:
        return "me"

    def fetch_with_status(self, view: str, *, repo="", person="", query="", **_kw: Any):
        self.calls.append((view, repo, person, query))
        rows = {
            "my_work": [
                ExploreRow("o/r #1: A (issue)", "Assigned\nx", "u1", "o/r", "issue", "1"),
                ExploreRow(
                    "o/r #2: B (PR)", "Review requested; Mentioned\nx", "u2", "o/r", "pr", "2"
                ),
            ],
            "repo_search": [
                ExploreRow("other/repo", "d", "u3", "other/repo", "repo", "other/repo")
            ],
            "following": [ExploreRow("@octo", "d", "u4", "", "person", "octo")],
        }.get(view, [ExploreRow(f"{view} row", "detail", "u", repo, "", "k")])
        return SimpleNamespace(items=tuple(rows))


@pytest.fixture
def bench(wx_session_app):
    provider = GitHubWorkbenchProvider(_Items(), REPO, announce=lambda _text: None)
    provider._explore = _Explore()
    frame = WorkbenchFrame(provider, run_background=_inline)
    yield frame
    frame.frame.Destroy()


def test_every_explore_node_loads_in_the_window(bench) -> None:
    provider = bench.provider
    bench.query = parse("screen reader")
    for template, node in GITHUB_TREE.all_nodes():
        if not node.loader.startswith("explore:"):
            continue
        instance = {"repository": REPO, "person": "octo"}.get(template, "")
        reason = provider.unavailable(NodeRef(template, node.key, instance), node)
        assert reason == "", (node.key, reason)


def test_my_work_nodes_split_one_fetch_by_reason(bench) -> None:
    _go(bench, NodeRef("", "review_requests"))
    assert [row.key for row in bench.rows] == ["2"]
    _go(bench, NodeRef("", "assigned"))
    assert [row.key for row in bench.rows] == ["1"]
    _go(bench, NodeRef("", "mentions"))
    assert [row.key for row in bench.rows] == ["2"]


def test_a_search_node_waits_for_words_then_sends_them_to_github(bench) -> None:
    _go(bench, NodeRef("", "search_repositories"))
    assert "Type what to search for" in bench.details.GetValue()
    bench.filter.ChangeValue("screen reader")
    bench.apply_filter()
    assert bench.provider._explore.calls[-1] == ("repo_search", "", "", "screen reader")
    assert [row.repo for row in bench.rows] == ["other/repo"]


def test_enter_on_a_repository_or_person_selects_its_node(bench) -> None:
    _go(bench, NodeRef("", "search_repositories"))
    bench.filter.ChangeValue("x")
    bench.apply_filter()
    bench.list.Select(0)
    bench.default_action()
    assert NodeRef("repository", "repository", "other/repo") in bench._items
    _go(bench, NodeRef("", "following"))
    bench.list.Select(0)
    bench.default_action()
    assert NodeRef("person", "person", "octo") in bench._items
    _go(bench, NodeRef("person", "person_repositories", "octo"))
    assert bench.provider._explore.calls[-1][:3] == ("person_repos", "", "octo")


def test_a_repository_view_from_explore_is_scoped_to_its_repository(bench) -> None:
    _go(bench, NodeRef("repository", "labels", REPO))
    assert bench.provider._explore.calls[-1][:2] == ("labels", REPO)
    assert bench.list.GetItemCount() == 1
