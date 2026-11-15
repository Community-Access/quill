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

    def fetch_milestones(self, _repo: str, **_kw: Any) -> list[Any]:
        from quill.core.github.milestones import GitHubMilestone

        return [GitHubMilestone(1, "1.0", open_issues=2, closed_issues=3)]

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
def bench(wx_session_app, quill_data_dir):
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


def test_milestones_load_through_the_existing_fetch(bench) -> None:
    _go(bench, NodeRef("repository", "milestones", REPO))
    assert [row.key for row in bench.rows] == ["1.0"]
    assert bench.provider.row_type(bench.node(bench.current), bench.rows[0]) == "milestone"


def test_the_pull_request_menu_starts_with_review_and_ends_with_properties(bench) -> None:
    _go(bench, NodeRef("repository", "pulls", REPO))
    top, more = bench.row_actions(bench.rows[0])
    assert top[0].label == "Review..."
    assert top[-1].label == "Properties..."
    assert more
    assert bench.can_run("github.workbench.open_on_github")
    bench.list.Select(0)
    # Merge is the Workbench's own now (github_workbench_items.py).
    assert bench.can_run("github.workbench.merge")
    assert bench.can_run("github.workbench.filter_builder")


def test_alt_enter_opens_the_sheet_for_the_selected_row(bench, monkeypatch) -> None:
    from tests.github_api_fake import FakeGitHubApi

    api = FakeGitHubApi()
    api.answer("GET", "/repos/owner/repo/pulls/2", {"number": 2, "title": "Fix it"})
    bench.provider.api = api  # never GitHub itself
    shown: list[Any] = []
    monkeypatch.setattr(
        "quill.ui.workbench_properties_sheet.show_modal_dialog",
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


def test_every_github_door_opens_the_workbench(monkeypatch, quill_data_dir) -> None:
    """The retired Items and Explore dialogs are no longer an alternate route."""
    from quill.core.github.workbench_flag import workbench_window_enabled
    from quill.core.github.workbench_prefs import WorkbenchPrefs, save_prefs
    from quill.ui import github_workbench_commands

    assert workbench_window_enabled()
    save_prefs(WorkbenchPrefs())
    assert workbench_window_enabled()
    opened: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.ui.github_workbench_window.open_github_workbench",
        lambda _editor, _items, *, repository, view, announce, **_kw: opened.append((
            repository,
            view,
        )),
    )
    assert github_workbench_commands.open_in_workbench_window(
        None, _Items(), repository=REPO, view="runs"
    )
    assert opened == [(REPO, "runs")]


def test_the_retired_dialogs_are_unreachable() -> None:
    """No app entry point imports the retired GitHub Items or Explore GitHub windows.

    The snapshot calls them ``parked`` -- the audit's reviewed word for "kept on
    purpose, reached by nothing" -- and this asserts the second half from the
    import graph itself, so a door that quietly imported one again would fail.
    """
    from quill.tools.surface_reachability_audit import (
        PARKED,
        PARKED_FALLBACKS,
        load_snapshot,
        reachable_modules,
    )

    snapshot = load_snapshot()
    reached = reachable_modules()
    assert not PARKED_FALLBACKS
    for module in ("quill.ui.github_items_dialog", "quill.ui.github_explore_dialog"):
        assert snapshot[module] == PARKED
        assert module not in reached


def test_both_editors_reach_the_window_through_the_one_shared_call() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    for name in ("quill/ui/main_frame_github_items.py", "quill/apps/lite_github_workbench.py"):
        source = (root / name).read_text(encoding="utf-8")
        assert "open_in_workbench_window(" in source, name
        assert "WorkbenchFrame(" not in source, name


def test_the_opener_accepts_every_keyword_the_editors_pass() -> None:
    """QUILL Lite once passed ``guide_product``, which the opener did not take.

    The door test above replaces the opener with a ``**kwargs`` lambda, so a
    TypeError there could never show; this reads the real signature instead.
    """
    import ast
    import inspect
    from pathlib import Path

    from quill.ui.github_workbench_window import open_github_workbench

    accepted = set(inspect.signature(open_github_workbench).parameters)
    root = Path(__file__).resolve().parents[3]
    for name in ("quill/ui/main_frame_github_items.py", "quill/apps/lite_github_workbench.py"):
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and getattr(node.func, "id", getattr(node.func, "attr", ""))
            == "open_in_workbench_window"
        ]
        assert calls, name
        for call in calls:
            passed = {kw.arg for kw in call.keywords if kw.arg}
            assert passed <= accepted, (name, passed - accepted)
            assert "gist_source" in passed, name


class _GistClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.starred = False

    def create_gist(self, draft: Any, *, public: bool) -> Any:
        self.calls.append(("create", (draft.names(), public)))
        return object()

    def fetch_gist(self, gist_id: str) -> Any:
        from quill.core.github.gists import Gist, GistFile

        self.calls.append(("fetch", gist_id))
        return Gist(
            id=gist_id,
            description="notes",
            public=False,
            url="https://gist.github.com/x",
            files=(GistFile("a.md", "hello"),),
        )

    def update_gist(self, gist_id: str, draft: Any) -> Any:
        self.calls.append(("update", gist_id))
        return None

    def is_gist_starred(self, gist_id: str) -> bool:
        return self.starred

    def set_gist_starred(self, gist_id: str, starred: bool) -> None:
        self.calls.append(("star", starred))
        self.starred = starred

    def delete_gist(self, gist_id: str) -> None:
        self.calls.append(("delete", gist_id))


def _gist_row() -> Any:
    from quill.core.github.explore_models import ExploreRow

    return ExploreRow(label="a.md", detail="", kind="gist", key="abc123", title="notes")


def test_gist_commands_answer_in_the_workbench(bench, monkeypatch) -> None:
    """Explore's New, Edit, Star and Delete Gist, now native rows (github_workbench_gists.py)."""
    client = _GistClient()
    provider = bench.provider
    provider._explore = client
    provider._gist_source = lambda: ("draft.md", "from the editor")
    row = _gist_row()
    for verb in ("edit_gist", "star_gist", "delete_gist", "new_gist"):
        assert provider._native_applies(verb, row), verb

    shown: list[Any] = []

    class _Editor:
        def __init__(self, _parent: Any, draft: Any, *, creating: bool, announce_cb: Any) -> None:
            shown.append((draft.names(), creating))
            self.draft, self.public = draft, False
            if not creating:
                draft.set_content("a.md", "changed")

        def show(self) -> bool:
            return True

    monkeypatch.setattr("quill.ui.github_gist_editor_dialog.GitHubGistEditorDialog", _Editor)
    monkeypatch.setattr(provider, "_confirm", lambda _title, _question: True)
    ref = NodeRef("", "my_gists")
    provider._do_new_gist(ref, None)
    assert shown[0] == (["draft.md"], True)
    assert client.calls[0][0] == "create"
    provider._do_edit_gist(ref, row)
    assert ("fetch", "abc123") in client.calls and ("update", "abc123") in client.calls
    provider._do_star_gist(ref, row)
    assert ("star", True) in client.calls
    provider._do_delete_gist(ref, row)
    assert ("delete", "abc123") in client.calls
    assert any("Created the secret gist" in s for s in bench.said)
    assert any("Starred the gist notes" in s for s in bench.said)
    assert any("Deleted the gist a.md" in s for s in bench.said)


def test_ctrl_n_on_pull_requests_opens_new_pull_request(bench, monkeypatch) -> None:
    """Ctrl+N on Pull Requests used to run new_pull with nothing answering it."""
    from quill.core.github import pull_compose
    from quill.core.github.branch_compare import GitHubBranchComparison
    from quill.core.github.items_provider import GitHubBranch, GitHubCommit

    pull_compose._KEPT.clear()
    items = bench.items
    sent: list[tuple[Any, ...]] = []
    items.fetch_branches = lambda _repo, **_kw: [
        GitHubBranch("main", "a", default_branch="main"),
        GitHubBranch("fix/crash", "b", default_branch="main"),
    ]
    items.compare_branches = lambda _repo, base, head: GitHubBranchComparison(
        base, head, ahead_by=1, commits=(GitHubCommit("c", "c", message="Fix the crash\n\nWhy."),)
    )
    items.create_pull_request = lambda *a, draft=False: (
        sent.append((*a, draft)) or GitHubItem(9, a[1], "open", "u", True)
    )
    monkeypatch.setattr(pull_compose, "open_pull_item", lambda *_a: None)
    shown: list[Any] = []

    class _Form:
        def __init__(self, _parent, start, names, **_kw) -> None:
            shown.append((start, names))
            self.draft = pull_compose.PullDraft(
                start.repository, start.base, start.head, start.title, start.body, draft=True
            )

        def show(self) -> bool:
            return True

    monkeypatch.setattr("quill.ui.github_new_pull_dialog.NewPullRequestDialog", _Form)
    _go(bench, NodeRef("repository", "pulls", REPO))
    assert bench.provider._native_applies("new_pull", None)
    bench.provider._do_new_pull(NodeRef("repository", "pulls", REPO), None)
    start, names = shown[0]
    assert (start.base, start.head, start.title, start.body) == (
        "main",
        "fix/crash",
        "Fix the crash",
        "Why.",
    )
    assert names == ["main", "fix/crash"]
    assert sent == [(REPO, "Fix the crash", "Why.", "fix/crash", "main", True)]
    assert any("Opened draft pull request #9" in s for s in bench.said)


def test_across_repositories_lists_one_kind_from_every_chosen_repository(
    bench, monkeypatch, quill_data_dir
) -> None:
    """Ctrl+0: choose repositories with Ctrl+N, then read Issues from all of them."""
    from types import SimpleNamespace

    from quill.core.github import across

    provider = bench.provider
    listed = [{"full_name": "o/one"}, {"full_name": "o/two"}, {"full_name": "o/other"}]
    api = SimpleNamespace(rest=lambda *_a, **_kw: SimpleNamespace(data=listed))
    monkeypatch.setattr(provider, "github_api", lambda: api)
    offered: list[list[str]] = []
    monkeypatch.setattr(
        provider, "_checklist", lambda _t, names, _c, _n: offered.append(names) or names[:2]
    )
    provider._do_choose_repositories(NodeRef("", "across"), None)
    assert offered == [["o/one", "o/two", "o/other"]]
    assert "2 repositories in My Repositories." in bench.said
    chosen = provider.load_across("across:chosen")
    assert [r.repo for r in chosen] == ["o/one", "o/two"]

    def fake(_provider, kind, repos, **_kw):
        assert (kind, list(repos)) == ("issues", ["o/one", "o/two"])
        item = GitHubItem(4, "Crash", "open", "https://github.com/o/one/issues/4", False)
        return across.AcrossResult(
            "issues",
            (("o/one", item),),
            (across.RepoOutcome("o/one", 1), across.RepoOutcome("o/two", error="no access")),
        )

    monkeypatch.setattr(across, "fetch_across", fake)
    row, status = provider.load_across("across:issues")
    assert row.repo == "o/one" and row.kind == "across_item" and row.label.startswith("o/one: ")
    # A repository that could not be read keeps a row of its own (GX16).
    assert status.repo == "o/two" and status.label == "o/two: could not be read, no access"
    assert "o/two: could not be read, no access" in provider.local_note


def _held(code: str, *, alt: bool = False, shift: bool = False) -> Any:
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(ord(code))
    event.SetControlDown(True)
    event.SetAltDown(alt)
    event.SetShiftDown(shift)
    return event


def test_the_second_keys_answer_only_on_their_own_modifiers(bench, monkeypatch) -> None:
    """Ctrl+Shift+F and Ctrl+R keep working here, and no longer swallow the chords
    with Alt added (the WordPress Workbench's Forget a Saved Request and Roles)."""
    done: list[str] = []
    monkeypatch.setattr(bench.filter, "SetFocus", lambda: done.append("filter"))
    monkeypatch.setattr(bench, "reload", lambda: done.append("reload"))
    bench._on_char_hook(_held("F", shift=True))
    bench._on_char_hook(_held("R"))
    assert done == ["filter", "reload"]
    for event in (_held("F", alt=True, shift=True), _held("R", alt=True)):
        bench._on_char_hook(event)
        assert event.GetSkipped()
    assert done == ["filter", "reload"]
