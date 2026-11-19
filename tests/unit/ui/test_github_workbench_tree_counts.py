"""GH-R-010: counts after node names, never announced (GitHub PRD 3.3 and 9).

A node's count goes after its name once its list has loaded: "Issues (1)".
It is written as you leave the node, never while it has focus, so nothing
changes under the screen reader; the app never speaks it. A list that
stopped at a page says "or more". A search has no count of its own, because
its rows depend on what was typed.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.test_github_workbench_help import REPO, _go, _inline, _Items  # noqa: E402

ISSUES = NodeRef("repository", "issues", REPO)


@pytest.fixture
def bench(wx_session_app, quill_data_dir):
    said: list[str] = []
    rows = [
        GitHubItem(n, f"Issue {n}", "open", f"https://github.com/o/r/issues/{n}", False)
        for n in (1, 2, 3)
    ]
    provider = GitHubWorkbenchProvider(_Items(rows), REPO, announce=said.append)
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()


def _text(frame: WorkbenchFrame, ref: NodeRef) -> str:
    return frame.tree.GetItemText(frame._items[ref])


def test_the_count_arrives_when_you_leave_and_is_never_said(bench) -> None:
    _go(bench, ISSUES)
    assert len(bench.rows) == 3
    assert _text(bench, ISSUES) == "Issues"  # not while it has focus
    said_before = list(bench.said)
    _go(bench, NodeRef("", "help_words"))
    assert _text(bench, ISSUES) == "Issues (3)"
    assert not any("(3)" in text for text in bench.said[len(said_before) :])


def test_a_rebuilt_tree_keeps_the_counts(bench) -> None:
    _go(bench, ISSUES)
    _go(bench, NodeRef("", "help_words"))
    bench._build_tree()
    assert _text(bench, ISSUES) == "Issues (3)"


def test_a_list_that_stopped_at_a_page_says_or_more(bench) -> None:
    assert bench.provider.count_words(ISSUES, 30) == "30 or more"
    assert bench.provider.count_words(ISSUES, 12) == "12"
    assert bench.provider.count_words(ISSUES, 0) == "0"


def test_a_search_has_no_count_of_its_own(bench) -> None:
    search = NodeRef("", "search_issues")
    _go(bench, search)
    _go(bench, NodeRef("", "help_words"))
    assert "(" not in _text(bench, search)
