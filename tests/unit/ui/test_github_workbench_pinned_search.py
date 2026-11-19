"""GH-R-053: a saved search can be pinned as a node of its own.

Pin as Node, on a row in Saved Searches, puts the search in the tree under
Saved Searches, named by the search; its list is the search's results, asked
of GitHub afresh. Unpin Node takes the node away and keeps the saved search,
and Remove Saved Search takes both.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.saved_items import GitHubSavedItems  # noqa: E402
from quill.core.github.workbench_tree import GITHUB_TREE  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.test_github_workbench_explore_nodes import _Explore  # noqa: E402
from tests.unit.ui.test_github_workbench_window import REPO, _go, _inline, _Items  # noqa: E402

QUERY = "is:open label:bug"
PINNED = NodeRef("pinned_search", "pinned_search", QUERY)


def test_the_store_pins_only_saved_searches_and_forgets_with_them(tmp_path) -> None:
    saved = GitHubSavedItems.load(tmp_path / "saved.json")
    assert saved.pin_search(QUERY) is False  # not saved yet
    saved.save_search(QUERY)
    assert saved.pin_search(QUERY) is True
    assert saved.pin_search(QUERY) is False  # already a node
    again = GitHubSavedItems.load(tmp_path / "saved.json")
    assert again.pinned_searches == [QUERY]
    again.remove_search(QUERY)
    assert GitHubSavedItems.load(tmp_path / "saved.json").pinned_searches == []


def test_the_pinned_node_sits_under_saved_searches() -> None:
    node = GITHUB_TREE.template_node("pinned_search", "pinned_search")
    assert dict(node.preset)["search"] == "instance"
    assert GITHUB_TREE.node("saved_searches").template == "pinned_search"
    assert GITHUB_TREE.depth("saved_searches") <= 4


@pytest.fixture
def bench(wx_session_app, quill_data_dir):
    said: list[str] = []
    provider = GitHubWorkbenchProvider(_Items(), REPO, announce=said.append)
    provider._explore = _Explore()
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()


def _saved(bench: WorkbenchFrame) -> Any:
    from quill.ui.github_workbench_loaders import saved_items_for

    return saved_items_for(bench.provider.items)


def test_pin_as_node_unpin_and_remove(bench) -> None:
    store = _saved(bench)
    store.save_search(QUERY)
    _go(bench, NodeRef("", "saved_searches"))
    bench.list.Select(0)
    assert bench.can_run("github.workbench.pin_search")
    assert not bench.can_run("github.workbench.unpin_search")
    bench.run("github.workbench.pin_search")
    assert bench.said[-1] == f"Pinned {QUERY} under Saved Searches."
    assert PINNED in bench._items
    assert bench.tree.GetItemText(bench._items[PINNED]) == QUERY
    # Its list is the search's results, with the search as the query.
    _go(bench, PINNED)
    assert bench.provider._explore.calls[-1] == ("search", "", "", QUERY)
    assert [row.label for row in bench.rows] == ["search row"]
    # Unpin keeps the saved search; Remove takes it away.
    _go(bench, NodeRef("", "saved_searches"))
    bench.list.Select(0)
    bench.run("github.workbench.unpin_search")
    assert PINNED not in bench._items
    assert QUERY in (_saved(bench).searches or [])
    bench.run("github.workbench.pin_search")
    bench.list.Select(0)
    bench.run("github.workbench.remove_search")
    assert PINNED not in bench._items
    assert _saved(bench).pinned_searches == []
