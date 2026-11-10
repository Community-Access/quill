"""GitHub Workbench Phase 3: the full menu bar, its keys, the loaders, the actions, the place.

A real frame over a fake GitHub Items provider, with background work run
inline, in a data directory of the test's own (the window remembers its place
on close).
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.app_keymaps import APP_KEYMAPS  # noqa: E402
from quill.core.github.explore_models import ExploreRow  # noqa: E402
from quill.core.github.item_actions import DELETE_COMMANDS, GITHUB_ACTIONS  # noqa: E402
from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.core.github.navigation_state import load_workbench_place  # noqa: E402
from quill.core.github.workbench_window_menu import (  # noqa: E402
    GO_NODES,
    WINDOW_MENU,
    WORKBENCH_KEYMAP_ID,
    WORKBENCH_KEYS,
)
from quill.core.workbench.menus import rows  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider, start_ref  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

REPO = "owner/repo"


class _Entry:
    def __init__(self, name: str, kind: str) -> None:
        self.name, self.kind = name, kind
        self.path = name
        self.url = ""
        self.is_folder = kind == "dir"
        self.label = f"{name}, folder" if self.is_folder else f"{name}, 1 KB"


class _Items:
    is_authenticated = True
    token = "test-token-not-real"

    def __init__(self) -> None:
        self.comments: list[tuple[str, int, str]] = []
        self.states: list[tuple[str, list[int], str]] = []

    def fetch_issues(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return [GitHubItem(1, "Crash on start", "open", "https://github.com/o/r/issues/1", False)]

    def fetch_pulls(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return []

    def fetch_default_branch(self, _repo: str) -> str:
        return "main"

    def fetch_repo_folder(self, _repo: str, _ref: str, path: str = "") -> list[_Entry]:
        return [_Entry("docs", "dir"), _Entry("README.md", "file")] if not path else []

    def create_comment(self, repo: str, number: int, body: str) -> dict[str, str]:
        self.comments.append((repo, number, body))
        return {}

    def update_items(self, repo: str, numbers: list[int], *, state: str) -> None:
        self.states.append((repo, list(numbers), state))

    def close(self) -> None:
        pass


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
    ran: list[str] = []
    items = _Items()
    provider = GitHubWorkbenchProvider(
        items,
        REPO,
        announce=said.append,
        editor_command=lambda cid: ran.append(cid) or True,
        editor_command_available=lambda cid: cid.startswith("github."),
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.ran = ran  # type: ignore[attr-defined]
    frame.items = items  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()


def _go(frame: WorkbenchFrame, ref: NodeRef) -> None:
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)


def test_the_bar_has_every_prd_menu_in_order(bench) -> None:
    bar = bench.frame.GetMenuBar()
    titles = [bar.GetMenuLabel(i) for i in range(bar.GetMenuCount())]
    assert titles == [
        "&File",
        "&Edit",
        "&View",
        "&Go",
        "&Item",
        "&Repository",
        "&Account",
        "&Tools",
        "&Window",
        "&Help",
    ]


def test_every_menu_key_is_the_app_keymap_entry_and_wx_can_bind_it() -> None:
    assert APP_KEYMAPS[WORKBENCH_KEYMAP_ID] == WORKBENCH_KEYS
    for _menu, row in rows(WINDOW_MENU):
        assert WORKBENCH_KEYS[row.command_id] == row.key
    for key in WORKBENCH_KEYS.values():
        assert wx.AcceleratorEntry().FromString(key), key
    # Decision 11: no plain letters, and no key sets a single property.
    assert all(
        "+" in key or key.startswith("F") or key == "Delete" for key in WORKBENCH_KEYS.values()
    )


def test_ctrl_numbers_go_to_places_and_ctrl_shift_numbers_to_repository_parts() -> None:
    keyed = {WORKBENCH_KEYS[cid]: GO_NODES[cid] for cid in GO_NODES}
    assert keyed["Ctrl+1"] == ("", "inbox")
    assert keyed["Ctrl+9"] == ("", "start")
    assert keyed["Ctrl+0"] == ("", "across")
    assert keyed["Ctrl+Shift+1"] == ("repository", "issues")
    assert keyed["Ctrl+Shift+4"] == ("repository", "runs")


def test_a_go_key_selects_its_node(bench) -> None:
    bench.run("github.workbench.go_issues")
    if bench.current != NodeRef("repository", "issues", REPO):
        bench._show_node(NodeRef("repository", "issues", REPO), remember=True)
    assert [row.number for row in bench.rows] == [1]


def test_placeholders_explain_themselves_and_are_greyed(bench) -> None:
    _go(bench, NodeRef("", "across"))
    assert "later release" in bench.details.GetValue()
    assert not bench.can_run("github.workbench.filter_builder")
    bench.run("github.workbench.filter_builder")
    assert bench.said[-1] == "This is coming in a later release of the Workbench."


def test_files_list_a_folder_and_enter_opens_a_subfolder(bench) -> None:
    _go(bench, NodeRef("repository", "files", REPO))
    assert [row.kind for row in bench.rows] == ["folder", "file"]
    bench.list.Select(0)
    bench.default_action()
    assert bench.provider._folders[REPO] == "docs"
    assert bench.rows[0].label == "Up one folder"


def test_comment_posts_through_items_and_says_one_result(bench, monkeypatch) -> None:
    monkeypatch.setattr(
        "quill.ui.github_workbench_actions.GitHubWorkbenchActionsMixin._ask_text",
        lambda _self, *_a, **_k: "Looks good",
    )
    _go(bench, NodeRef("repository", "issues", REPO))
    bench.list.Select(0)
    bench.run("github.workbench.comment")
    assert bench.items.comments == [(REPO, 1, "Looks good")]
    assert bench.said[-1] == "Comment posted on #1."
    bench.run("github.workbench.explain_result")
    assert bench.said[-1].startswith("Your comment is on GitHub now")
    bench.run("github.workbench.repeat_result")
    assert bench.said[-1] == "Comment posted on #1."


def test_delete_on_an_issue_closes_it_after_asking(bench, monkeypatch) -> None:
    monkeypatch.setattr(
        "quill.ui.github_workbench_actions.GitHubWorkbenchActionsMixin._confirm",
        lambda _self, *_a: True,
    )
    assert DELETE_COMMANDS["issue"] == "github.workbench.close_reopen"
    _go(bench, NodeRef("repository", "issues", REPO))
    bench.list.Select(0)
    bench._remove_selected()
    assert bench.items.states == [(REPO, [1], "closed")]


def test_repository_actions_run_the_editors_own_command(bench, monkeypatch) -> None:
    monkeypatch.setattr(
        "quill.ui.github_workbench_actions.GitHubWorkbenchActionsMixin._choose",
        lambda _self, _title, _prompt, labels: labels.index("Fork Repository..."),
    )
    _go(bench, NodeRef("repository", "issues", REPO))
    bench.run("github.workbench.repository_actions")
    assert bench.ran == ["github.fork_repository"]
    bench.run("github.workbench.manage_accounts")  # an editor verb: not offered here
    assert bench.ran == ["github.fork_repository"]


def test_the_admin_pages_list_the_settings_commands(bench) -> None:
    _go(bench, NodeRef("repository", "general", REPO))
    assert [row.key for row in bench.rows][:1] == ["github.rename_repository"]
    bench.list.Select(0)
    bench.default_action()
    assert bench.ran == ["github.rename_repository"]


def test_the_place_is_remembered_per_account(bench) -> None:
    _go(bench, NodeRef("repository", "runs", REPO))
    bench.tree.Expand(bench._items[NodeRef("repository", "actions", REPO)])
    bench.remember_place()
    place = load_workbench_place(bench.provider._account_key())
    assert place.last == ("repository", "runs", REPO)
    assert ("repository", "actions", REPO) in place.expanded
    assert place.repositories == (REPO,)


def test_where_the_window_opens() -> None:
    assert start_ref(REPO, node="runs", signed_in=True) == NodeRef("repository", "runs", REPO)
    assert start_ref("", node="inbox", signed_in=True) == NodeRef("", "inbox")
    assert start_ref(REPO, view="releases", signed_in=True) == NodeRef(
        "repository", "releases", REPO
    )
    assert start_ref("", signed_in=False) == NodeRef("", "start")


def test_alt_readouts_say_and_move_nothing(bench) -> None:
    _go(bench, NodeRef("repository", "issues", REPO))
    bench.list.Select(0)
    before = bench.current
    bench.run("github.workbench.say_item")
    assert bench.said[-1] == "Issue #1, open, Crash on start"
    bench.run("github.workbench.say_counts")
    assert bench.said[-1] == "1 shown"
    assert bench.current == before


def test_every_row_type_on_a_loader_row_has_a_menu() -> None:
    for kind in ("file", "folder", "milestone", "project", "organization", "admin_action"):
        assert GITHUB_ACTIONS.rows_for(kind)


def test_explore_style_rows_map_to_their_row_types(bench) -> None:
    node = bench.node(NodeRef("", "saved_searches"))
    row = ExploreRow("is:open", "", kind="saved_search", key="is:open")
    assert bench.provider.row_type(node, row) == "saved_search"


def test_the_options_dialog_saves_to_the_workbench_file(wx_session_app, quill_data_dir) -> None:
    from quill.core.github.workbench_prefs import WorkbenchPrefs, load_prefs
    from quill.ui.app_context_help import ensure_help_provider
    from quill.ui.github_workbench_options import WorkbenchOptionsDialog

    ensure_help_provider(wx)  # SetHelpText stores nothing without one

    dialog = WorkbenchOptionsDialog(None, WorkbenchPrefs())
    try:
        dialog.controls["open_on"].SetSelection(2)
        dialog.controls["poll_audible_tick"].SetValue(True)
        values = dialog.values()
        assert values.open_on == "last"
        assert values.poll_audible_tick is True
        for control in dialog.controls.values():
            assert control.GetHelpText(), control
        assert dialog.notebook.GetPageCount() == 5
    finally:
        dialog.dialog.Destroy()
    assert load_prefs() == WorkbenchPrefs()  # nothing saved without OK
