"""GitHub Workbench leftovers of Phases 3 to 6, and Phase 9's filter menu, in the window.

View > Show, Open or Closed and Sort By; Quick Filters checked and in step
with the filter box; Show Only and Hide; Group By as tree nodes; local
filtering said honestly; Ctrl+Period for the next unread; Go's dynamic
submenus; and the editor's Repository Admin and Codespaces ids opening the
Workbench and running there.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.explore_models import ExploreRow  # noqa: E402
from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from quill.ui.workbench_frame_groups import GroupRef  # noqa: E402

REPO = "owner/repo"
_P = "github.workbench."


def _item(number: int, labels: tuple[str, ...] = (), *, pr: bool = False) -> GitHubItem:
    kind = "pull" if pr else "issues"
    url = f"https://github.com/owner/repo/{kind}/{number}"
    return GitHubItem(number, f"Item {number}", "open", url, pr, labels=labels)


class _Items:
    is_authenticated = True
    token = "test-token-not-real"

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def fetch_issues(self, _repo: str, *, state: str = "open", **_kw: Any) -> list[GitHubItem]:
        self.calls.append(("issues", state))
        return [_item(1, ("bug",)), _item(2, ("bug", "ui")), _item(3)]

    def fetch_pulls(self, _repo: str, *, state: str = "open", **_kw: Any) -> list[GitHubItem]:
        self.calls.append(("pulls", state))
        return [_item(4, pr=True)]

    def search_items(self, _repo: str, query: str, **_kw: Any) -> list[GitHubItem]:
        self.calls.append(("search", query))
        return [_item(1, ("bug",)), _item(4, pr=True)]

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
    items = _Items()
    provider = GitHubWorkbenchProvider(items, REPO, announce=said.append)
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.items = items  # type: ignore[attr-defined]
    ref = NodeRef("repository", "issues_and_pulls", REPO)
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)
    yield frame
    frame.frame.Destroy()


def test_show_and_state_choose_what_loads(bench) -> None:
    bench.items.calls.clear()
    bench.run(f"{_P}show_issues")
    bench.run(f"{_P}state_closed")
    assert ("issues", "closed") in bench.items.calls
    assert all(call[0] != "pulls" for call in bench.items.calls)
    assert bench.provider.is_checked(f"{_P}state_closed")
    assert bench.provider.is_checked(f"{_P}show_issues")
    assert not bench.provider.is_checked(f"{_P}show_both")


def test_sort_by_orders_the_list(bench) -> None:
    bench.run(f"{_P}sort_number_asc")
    assert [row.number for row in bench.rows] == [1, 2, 3, 4]
    bench.run(f"{_P}sort_number_desc")
    assert [row.number for row in bench.rows] == [4, 3, 2, 1]


def test_a_quick_filter_writes_the_query_is_checked_and_named_in_the_title(bench) -> None:
    bench.run(f"{_P}filter_no_milestone")
    assert bench.filter.GetValue() == "no:milestone"
    assert bench.provider.is_checked(f"{_P}filter_no_milestone")
    assert bench.items.calls[-1] == ("search", "no:milestone")
    assert "no milestone" in bench.frame.GetTitle()
    bench.run(f"{_P}filter_clear")
    assert bench.filter.GetValue() == ""
    assert not bench.provider.is_checked(f"{_P}filter_no_milestone")


def test_show_only_and_hide_on_a_cell(bench) -> None:
    index = next(i for i, row in enumerate(bench.rows) if row.number == 1)
    for other in range(bench.list.GetItemCount()):
        bench.list.Select(other, False)
    bench.list.Select(index)
    assert ("label:bug", "label bug") in bench.provider.cell_rows()
    bench.provider.show_only_cell("label:bug", hide=True)
    assert bench.filter.GetValue() == "-label:bug"


def test_group_by_puts_groups_in_the_tree(bench) -> None:
    bench.run(f"{_P}group_label")
    names = [ref.name for ref in bench._groups]
    assert names == ["bug (2)", "ui (1)", "None (2)"]
    bug = next(ref for ref in bench._groups if ref.name == "bug (2)")
    bench._show_group(bug)
    assert [row.number for row in bench.rows] == [2, 1]
    bench.run(f"{_P}group_none")
    assert bench._groups == {}
    assert isinstance(bug, GroupRef)


def test_has_conflicts_filters_locally_and_says_so(bench) -> None:
    from tests.github_api_fake import FakeGitHubApi

    api = FakeGitHubApi()
    api.answer("GET", "/repos/owner/repo/pulls/4", {"mergeable_state": "dirty"})
    bench.provider.api = api
    bench.run(f"{_P}filter_conflicts")
    assert bench.filter.GetValue() == "conflicts:true"
    assert [row.number for row in bench.rows] == [4]
    assert bench.provider.local_note == "Filtered locally: 1 of all 4."
    items = next(c for c in bench.status.visible_cells() if c.key == "items")
    assert "Filtered locally" in items.spoken()


def test_ctrl_period_moves_to_the_next_unread_row(bench) -> None:
    rows = [
        ExploreRow("Read, mentioned: a", "", kind="notification", key="1"),
        ExploreRow("Unread, assigned: b", "", kind="notification", key="2"),
        ExploreRow("Unread, mentioned: c", "", kind="notification", key="3"),
    ]
    bench._loaded = rows
    bench._fill_list()
    bench.run(f"{_P}next_unread")
    assert bench.selected_indices() == [1]
    bench.run(f"{_P}next_unread")
    assert bench.selected_indices() == [2]
    bench.run(f"{_P}next_unread")
    assert bench.said[-1] == "No more unread."
    bench.run(f"{_P}previous_unread")
    assert bench.selected_indices() == [1]


def test_go_lists_pins_favorites_and_saved_searches(bench) -> None:
    from quill.ui.github_workbench_loaders import saved_items_for

    saved = saved_items_for(bench.items)
    saved.pin_repo("octo/cat")
    saved.save_search("is:open label:bug")
    saved.save()
    assert [label for label, _a in bench.provider.dynamic_menu("pinned")] == ["octo/cat"]
    searches = bench.provider.dynamic_menu("saved_searches")
    assert [label for label, _a in searches] == ["is:open label:bug"]
    bench.fill_dynamic_menus()
    sub = bench._dynamic_menus["pinned"]
    assert [item.GetItemLabel() for item in sub.GetMenuItems()] == ["&1 octo/cat"]


def test_admin_ids_open_the_workbench_and_run_there(monkeypatch) -> None:
    from quill.ui import github_workbench_commands as commands
    from quill.ui.main_frame_github_doors import GitHubAdminDoorsMixin

    class _Base:
        def __init__(self) -> None:
            self.ran: list[str] = []

        def github_rename_repository(self) -> None:
            self.ran.append("classic rename")

    class _Host(GitHubAdminDoorsMixin, _Base):
        def open_github_items_viewer(self, node: str = "", then: str = "") -> None:
            self.ran.append(f"workbench {node} {then}")

    host = _Host()
    monkeypatch.setattr("quill.core.github.workbench_flag.workbench_window_enabled", lambda: True)
    host.github_rename_repository()
    assert host.ran == ["workbench repository sheet:general"]
    # The Workbench asking the editor for the same command gets the classic one.
    commands.editor_call(lambda _cid: host.github_rename_repository(), "github.rename_repository")
    assert host.ran[-1] == "classic rename"
    monkeypatch.setattr("quill.core.github.workbench_flag.workbench_window_enabled", lambda: False)
    host.github_rename_repository()
    assert host.ran[-1] == "classic rename"
