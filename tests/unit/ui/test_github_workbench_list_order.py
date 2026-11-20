"""Sort and Group By Column on every list, and the row kept on return (complete.md 1.3).

A real Workbench frame over a fake GitHub Items provider, background work
inline, as in ``test_github_workbench_compare.py``. The chooser is answered by
replacing the provider's ``_choose`` with the index a person would pick.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.items_provider import GitHubTag  # noqa: E402
from quill.core.github.list_order import (  # noqa: E402
    ONE_COLUMN_FIELDS,
    ColumnOrder,
    fields_for,
    group_by_field,
    order_rows,
)
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from quill.ui.workbench_frame_groups import GroupRef  # noqa: E402

REPO = "owner/repo"
_P = "github.workbench."
TAGS = NodeRef("repository", "tags", REPO)
RELEASES = NodeRef("repository", "releases", REPO)


class _Items:
    is_authenticated = True
    token = "test-token-not-real"

    def __init__(self) -> None:
        self.tags = [
            GitHubTag("v2.0", "bbb"),
            GitHubTag("v10.0", "aaa"),
            GitHubTag("v1.0", "aaa"),
        ]

    def fetch_tags(self, _repo: str, **_kw: Any) -> list[GitHubTag]:
        return list(self.tags)

    def fetch_releases(self, _repo: str, **_kw: Any) -> list[object]:
        return []

    def fetch_default_branch(self, _repo: str) -> str:
        return "main"

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
    yield frame
    frame.frame.Destroy()


def _open(bench, ref: NodeRef, *, remember: bool = True) -> None:
    bench._show_node(ref, remember=remember)


def _names(bench) -> list[str]:
    return [row.name for row in bench.rows]


def _answer(bench, monkeypatch, label: str) -> list[list[str]]:
    asked: list[list[str]] = []

    def choose(_title: str, _prompt: str, labels: list[str]) -> int:
        asked.append(list(labels))
        return labels.index(label)

    monkeypatch.setattr(bench.provider, "_choose", choose)
    return asked


# -- the core ----------------------------------------------------------------------


def test_numbers_sort_as_numbers_and_empty_values_go_last() -> None:
    rows = ["10", "", "9", "apple", "Banana"]
    ordered = order_rows(rows, ColumnOrder("x"), lambda r: r)
    assert ordered == ["9", "10", "apple", "Banana", ""]
    backwards = order_rows(rows, ColumnOrder("x", descending=True), lambda r: r)
    assert backwards == ["Banana", "apple", "10", "9", ""]
    assert order_rows(rows, ColumnOrder(), lambda r: r) == rows  # GitHub's own order


def test_a_one_column_list_offers_its_rows_own_fields() -> None:
    assert fields_for(("result",)) == ONE_COLUMN_FIELDS
    assert fields_for(("name", "commit_sha")) == ("name", "commit_sha")


def test_groups_put_none_last_and_a_date_by_its_day() -> None:
    rows = ["2026-11-01T10:00:00Z", "2026-11-01T12:00:00Z", "", "2026-10-30T09:00:00Z"]
    groups = group_by_field(rows, lambda r: r)
    assert [(name, len(found)) for name, found in groups] == [
        ("2026-10-30", 1),
        ("2026-11-01", 2),
        ("None", 1),
    ]


def test_the_stored_choice_round_trips() -> None:
    order = ColumnOrder("name", descending=True)
    assert ColumnOrder.from_stored(order.stored()) == order
    assert ColumnOrder.from_stored([]) == ColumnOrder()


# -- the window ----------------------------------------------------------------------


def test_sort_by_column_orders_a_non_issue_list_and_is_remembered(bench, monkeypatch) -> None:
    _open(bench, TAGS)
    assert bench.provider.supports(f"{_P}column_sort")
    assert not bench.provider.supports(f"{_P}sort_title_asc")  # GitHub's orders: Issues only
    asked = _answer(bench, monkeypatch, "Name, last to first")
    bench.provider.run_view(f"{_P}column_sort")
    assert asked[0][0] == "As GitHub sends it"
    assert _names(bench) == ["v2.0", "v10.0", "v1.0"]  # words, Z to A
    assert bench.said[-1] == "Sorted by name, last to first."
    # Remembered for this list: a fresh load comes back in the same order.
    bench.reload()
    assert _names(bench) == ["v2.0", "v10.0", "v1.0"]
    _answer(bench, monkeypatch, "As GitHub sends it")
    bench.provider.run_view(f"{_P}column_sort")
    assert _names(bench) == ["v2.0", "v10.0", "v1.0"]  # the fake's own order
    assert bench.said[-1] == "Sorted as GitHub sends it."


def test_sorting_keeps_the_selected_item(bench, monkeypatch) -> None:
    _open(bench, TAGS)
    bench.focus_row(2)  # v1.0
    _answer(bench, monkeypatch, "Commit sha, first to last")
    bench.provider.run_view(f"{_P}column_sort")
    assert bench.selected_row().name == "v1.0"


def test_group_by_column_puts_groups_in_the_tree(bench, monkeypatch) -> None:
    _open(bench, TAGS)
    assert bench.provider.supports(f"{_P}column_group")
    assert not bench.provider.supports(f"{_P}group_label")  # an issue's field: Issues only
    _answer(bench, monkeypatch, "Commit sha")
    bench.provider.run_view(f"{_P}column_group")
    names = sorted(ref.name for ref in bench._groups)
    assert names == ["aaa (2)", "bbb (1)"]
    assert bench.said[-1] == "2 groups by commit sha, in the tree."
    # No Grouping takes them away and forgets the choice for this list.
    bench.provider.run_view(f"{_P}group_none")
    assert bench._groups == {}
    assert not bench.provider.column_grouped()


def test_columns_and_order_rows_are_offered_on_every_kind_of_list(bench) -> None:
    from quill.core.github.workbench_tree import GITHUB_TREE

    for ref in (TAGS, RELEASES):
        _open(bench, ref)
        node = bench.node(ref)
        assert len(bench.provider.order_fields(node)) > 1, node.key
    # An Explore list of one column still sorts and groups by its rows' fields.
    one = next(n for n in GITHUB_TREE._nodes.values() if n.loader.startswith("explore:"))
    assert bench.provider.order_fields(one) == ONE_COLUMN_FIELDS


# -- the selected row on return ---------------------------------------------------------


def test_coming_back_to_a_list_lands_on_the_row_you_left(bench) -> None:
    """Would catch a list losing its selected row on return (Back, Forward, Alt+Left)."""
    _open(bench, TAGS)
    bench.focus_row(1)  # v10.0
    _open(bench, RELEASES)
    _open(bench, TAGS, remember=False)  # what Back does
    assert bench.selected_row().name == "v10.0"
    assert bench.list.GetFocusedItem() == 1
    # The item moved while you were away: you land on it where it is now.
    bench.items.tags.insert(0, GitHubTag("v11.0", "ccc"))
    _open(bench, RELEASES)
    _open(bench, TAGS, remember=False)
    assert bench.selected_row().name == "v10.0"


def test_a_reload_inside_a_group_keeps_the_group_and_the_row(bench, monkeypatch) -> None:
    _open(bench, TAGS)
    _answer(bench, monkeypatch, "Commit sha")
    bench.provider.run_view(f"{_P}column_group")
    group = next(ref for ref in bench._groups if ref.name.startswith("aaa"))
    bench._show_group(group)
    bench.tree.SelectItem(bench._groups[group][0])
    bench.focus_row(1)  # v1.0 within the group
    assert bench.selected_row().name == "v1.0"
    bench.reload()
    chosen = bench.tree.GetItemData(bench.tree.GetSelection())
    assert isinstance(chosen, GroupRef) and chosen.name.startswith("aaa")
    assert bench.selected_row().name == "v1.0"
