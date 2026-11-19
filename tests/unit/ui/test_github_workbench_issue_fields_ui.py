"""Issue types and fields on the Workbench's Issues list (complete.md 1.3).

The Issue type and Issue fields columns are offered by Columns... and shown
only once chosen; with the fields column on, each issue's typed fields are
read; ``type:`` and ``field.`` filters go to GitHub's search; Show Only on a
field value writes that qualifier; Group By Type groups by the issue type;
and the details name the type and every field in its state.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.github_api_fake import FakeGitHubApi  # noqa: E402

REPO = "acme/site"
_P = "github.workbench."


def _item(number: int, issue_type: str = "", *, pr: bool = False) -> GitHubItem:
    kind = "pull" if pr else "issues"
    url = f"https://github.com/{REPO}/{kind}/{number}"
    return GitHubItem(number, f"Item {number}", "open", url, pr, issue_type=issue_type)


class _Items:
    is_authenticated = True
    token = "test-token-not-real"

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def fetch_issues(self, _repo: str, *, state: str = "open", **_kw: Any) -> list[GitHubItem]:
        self.calls.append(("issues", state))
        return [_item(1, "Bug"), _item(2, "Task"), _item(3)]

    def fetch_pulls(self, _repo: str, *, state: str = "open", **_kw: Any) -> list[GitHubItem]:
        self.calls.append(("pulls", state))
        return [_item(4, pr=True)]

    def search_items(self, _repo: str, query: str, **_kw: Any) -> list[GitHubItem]:
        self.calls.append(("search", query))
        return [_item(1, "Bug")]

    def close(self) -> None:
        pass


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


def _api() -> FakeGitHubApi:
    api = FakeGitHubApi()
    api.answer(
        "GET",
        "/orgs/acme/issue-fields",
        [
            {"id": 1, "name": "Priority", "data_type": "single_select"},
            {"id": 2, "name": "Due", "data_type": "date"},
        ],
    )
    api.answer(
        "GET",
        f"/repos/{REPO}/issues/1/issue-field-values",
        [
            {"issue_field_id": 1, "single_select_option": {"name": "High"}},
            {"issue_field_id": 2, "value": "2026-12-31"},
        ],
    )
    api.answer("GET", f"/repos/{REPO}/issues/2/issue-field-values", [])
    return api


@pytest.fixture
def bench(wx_session_app, quill_data_dir):
    said: list[str] = []
    items = _Items()
    provider = GitHubWorkbenchProvider(items, REPO, announce=said.append)
    provider.api = _api()
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.items = items  # type: ignore[attr-defined]
    ref = NodeRef("repository", "issues_and_pulls", REPO)
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)
    yield frame
    frame.frame.Destroy()


def _choose(bench: Any, *columns: str) -> None:
    from quill.ui.github_workbench_loaders import saved_items_for

    saved_items_for(bench.items).set_columns("workbench:items:issues", list(columns))
    bench._set_columns(bench.node(bench.current))
    bench.reload()


def test_the_columns_are_offered_but_not_shown_until_chosen(bench) -> None:
    node = bench.node(bench.current)
    assert {"issue_type", "issue_fields"} <= set(bench.provider.all_columns(node))
    assert "issue_type" not in bench._columns and "issue_fields" not in bench._columns
    # Nothing was read for fields while the column is off.
    assert not any("issue-field" in path for _m, path, _b in bench.provider.api.calls)


def test_chosen_columns_show_the_type_and_typed_fields(bench) -> None:
    _choose(bench, "number", "issue_type", "issue_fields")
    assert bench.list.GetColumn(1).GetText() == "Issue type"
    cells = {row.number: bench.provider.cells(row, bench._columns) for row in bench.rows}
    assert cells[1] == ["1", "Bug", "Priority: High; Due: 2026-12-31"]
    assert cells[2] == ["2", "Task", "Priority: not set; Due: not set"]
    assert cells[3][1] == "no type"
    assert cells[4][1:] == ["", ""]  # a pull request has neither
    one = next(row for row in bench.rows if row.number == 1)
    detail = bench.provider.detail(one)
    assert "Issue type: Bug" in detail and "Field Due (date, field 2): 2026-12-31" in detail


def test_type_and_field_filters_go_to_github_search(bench) -> None:
    bench.filter.ChangeValue("type:Bug field.priority:high")
    bench.apply_filter()
    query = bench.items.calls[-1]
    assert query[0] == "search"
    assert "type:Bug" in query[1] and "field.priority:high" in query[1]


def test_show_only_on_a_field_and_group_by_type(bench) -> None:
    _choose(bench, "number", "issue_fields")
    index = next(i for i, row in enumerate(bench.rows) if row.number == 1)
    for other in range(bench.list.GetItemCount()):
        bench.list.Select(other, False)
    bench.list.Select(index)
    choices = bench.provider.cell_rows()
    assert ("type:Bug", "type Bug") in choices
    assert ("field.priority:High", "Priority High") in choices
    bench.provider.show_only_cell("field.priority:High")
    assert bench.filter.GetValue() == "field.priority:High"
    bench.filter.ChangeValue("")
    bench.apply_filter()
    bench.run(f"{_P}group_type")
    names = sorted(ref.name for ref in bench._groups)
    assert "Bug (1)" in names and "Task (1)" in names
