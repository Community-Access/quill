"""The GitHub Workbench window spike (GitHub PRD Phase 1): panes, keys, menus, sheet.

Built on a real frame with a fake GitHub Items provider and a background
runner that runs work inline, so loading is deterministic without a network.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.items_provider import GitHubItem, GitHubWorkflowRun  # noqa: E402
from quill.core.github.workbench_window_menu import WINDOW_MENU  # noqa: E402
from quill.core.workbench.menus import problems, rows  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

REPO = "owner/repo"


class _Items:
    is_authenticated = True

    def __init__(self) -> None:
        self.closed = False
        self.searched: list[str] = []

    def fetch_issues(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return [GitHubItem(1, "Crash on start", "open", "https://github.com/o/r/issues/1", False)]

    def fetch_pulls(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return [
            GitHubItem(
                2,
                "Fix the crash",
                "open",
                "https://github.com/o/r/pull/2",
                True,
                labels=("bug",),
                head_branch="fix",
                base_branch="main",
            )
        ]

    def search_items(self, _repo: str, query: str, **_kw: Any) -> list[GitHubItem]:
        self.searched.append(query)
        return self.fetch_pulls(_repo)

    def fetch_workflow_runs(self, _repo: str, **_kw: Any) -> list[GitHubWorkflowRun]:
        return [GitHubWorkflowRun(id=9, name="CI", status="completed", conclusion="success")]

    def close(self) -> None:
        self.closed = True


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app):
    said: list[str] = []
    items = _Items()
    provider = GitHubWorkbenchProvider(items, REPO, announce=said.append)
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.items = items  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()


def _go(frame: WorkbenchFrame, ref: NodeRef) -> None:
    assert frame.select(ref)
    if frame.current != ref:  # no event loop: deliver the selection ourselves
        frame._show_node(ref, remember=True)


def test_the_tree_shows_the_prd_top_level_and_the_repository_first(bench) -> None:
    tree = bench.tree
    root = tree.GetRootItem()
    labels, (child, cookie) = [], tree.GetFirstChild(root)
    while child.IsOk():
        labels.append(tree.GetItemText(child))
        child, cookie = tree.GetNextChild(root, cookie)
    assert labels[:3] == ["Start Here", "Needs My Attention", "Repositories"]
    repositories = bench._items[NodeRef("", "repositories")]
    first, _cookie = tree.GetFirstChild(repositories)
    assert tree.GetItemText(first) == REPO


def test_a_node_loads_its_rows_and_says_nothing(bench) -> None:
    _go(bench, NodeRef("repository", "runs", REPO))
    assert [row.name for row in bench.rows] == ["CI"]
    assert bench.list.GetItemCount() == 1
    assert bench.list.GetColumnCount() == 6
    assert bench.said == []  # GATE-13: the list and the tree say it


def test_issues_and_pull_requests_are_separate_presets(bench) -> None:
    _go(bench, NodeRef("repository", "issues", REPO))
    assert [row.number for row in bench.rows] == [1]
    _go(bench, NodeRef("repository", "pulls", REPO))
    assert [row.number for row in bench.rows] == [2]
    _go(bench, NodeRef("repository", "issues_and_pulls", REPO))
    assert [row.number for row in bench.rows] == [2, 1]


def test_words_filter_here_and_qualifiers_ask_github(bench) -> None:
    _go(bench, NodeRef("repository", "issues_and_pulls", REPO))
    bench.filter.ChangeValue("fix")
    bench.apply_filter()
    assert [row.number for row in bench.rows] == [2]
    bench.filter.ChangeValue("label:bug")
    bench.apply_filter()
    assert bench.items.searched == ["label:bug"]
    bench.clear_filter()
    assert len(bench.rows) == 2


def test_escape_clears_the_filter_then_goes_back(bench) -> None:
    _go(bench, NodeRef("repository", "runs", REPO))
    _go(bench, NodeRef("repository", "pulls", REPO))
    bench.filter.ChangeValue("fix")
    bench.apply_filter()
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(wx.WXK_ESCAPE)
    bench._on_char_hook(event)
    assert bench.filter.GetValue() == ""
    assert bench.current == NodeRef("repository", "pulls", REPO)
    bench._on_char_hook(event)
    if bench.current != NodeRef("repository", "runs", REPO):
        bench._show_node(NodeRef("repository", "runs", REPO), remember=False)
    assert bench.forward == [NodeRef("repository", "pulls", REPO)]


def test_a_node_that_is_not_in_the_preview_explains_itself(bench) -> None:
    _go(bench, NodeRef("repository", "milestones", REPO))
    assert "not in this preview yet" in bench.details.GetValue()
    assert bench.rows == []


def test_the_pull_request_menu_starts_with_review_and_ends_with_properties(bench) -> None:
    _go(bench, NodeRef("repository", "pulls", REPO))
    top, more = bench.row_actions(bench.rows[0])
    assert top[0].label == "Review..."
    assert top[-1].label == "Properties..."
    assert more
    assert bench.can_run("github.workbench.open_on_github")
    assert not bench.can_run("github.workbench.merge")


def test_alt_enter_opens_a_read_only_sheet_for_the_selected_row(bench, monkeypatch) -> None:
    shown: list[Any] = []
    monkeypatch.setattr(
        "quill.ui.workbench_properties_dialog.show_modal_dialog",
        lambda dialog, title: shown.append((dialog.GetTitle(), title)) or wx.ID_CANCEL,
    )
    _go(bench, NodeRef("repository", "pulls", REPO))
    bench.list.Select(0)
    bench.run("github.workbench.properties")
    assert shown == [("Pull Request #2 Properties - owner/repo",) * 2]


def test_the_status_bar_reads_name_and_value_and_mirrors_them(bench) -> None:
    _go(bench, NodeRef("repository", "runs", REPO))
    cells = {cell.key: cell for cell in bench.status.visible_cells()}
    assert cells["repository"].spoken() == f"Repository, {REPO}"
    assert cells["items"].spoken() == "Items, 1 shown"
    assert cells["filter"].spoken() == "Filter, No filter"
    labels = [label for label, _action in bench.status.menu_rows(cells["filter"])]
    assert labels[-2:] == ["Copy", "Help for This Cell"]
    assert f"Repository, {REPO}" in bench.frame.GetStatusBar().GetStatusText()


def test_f6_cycles_the_panes_in_order(bench) -> None:
    order = [bench.tree, bench.filter, bench.list, bench.details]
    assert bench.panes() == order


def test_the_menu_bar_keeps_the_accelerator_and_access_key_rules() -> None:
    assert problems(WINDOW_MENU) == []
    for _menu, row in rows(WINDOW_MENU):
        entry = wx.AcceleratorEntry()
        assert entry.FromString(row.key), row.key


def test_closing_the_window_closes_the_provider(bench) -> None:
    event = wx.CloseEvent(wx.wxEVT_CLOSE_WINDOW)
    bench._on_close(event)
    assert bench.items.closed


def test_the_window_is_off_unless_the_developer_flag_is_set(monkeypatch) -> None:
    from quill.core.github.workbench_flag import ENV_VAR, workbench_window_enabled
    from quill.ui import github_workbench_commands

    monkeypatch.delenv(ENV_VAR, raising=False)
    assert not workbench_window_enabled()
    assert not github_workbench_commands.open_in_workbench_window(None, _Items())
    opened: list[tuple[str, str]] = []
    monkeypatch.setenv(ENV_VAR, "1")
    monkeypatch.setattr(
        "quill.ui.github_workbench_window.open_github_workbench",
        lambda _editor, _items, *, repository, view, announce: opened.append((repository, view)),
    )
    assert github_workbench_commands.open_in_workbench_window(
        None, _Items(), repository=REPO, view="runs"
    )
    assert opened == [(REPO, "runs")]


def test_both_editors_reach_the_window_through_the_one_shared_call() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    for name in ("quill/ui/main_frame_github_items.py", "quill/apps/lite_github_workbench.py"):
        source = (root / name).read_text(encoding="utf-8")
        assert "open_in_workbench_window(" in source, name
        assert "WorkbenchFrame(" not in source, name
