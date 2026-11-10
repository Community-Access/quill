"""GitHub Workbench Phase 7: Alt+Enter opens a real, editable, verified sheet (GH-R-030 to 035).

A real frame over fake GitHub Items rows, with the sheets' reads and writes
answered by a recorded API, background work run inline, and the sheet's own
modal loop replaced by a script that edits its controls the way a person
would.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.change_log import ChangeLog  # noqa: E402
from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from quill.ui.workbench_properties_sheet import PropertiesSheet  # noqa: E402
from tests.github_api_fake import FakeGitHubApi  # noqa: E402

REPO = "owner/repo"


def _issue(number: int, labels: list[str]) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"Issue {number}",
        "body": "",
        "state": "open",
        "user": {"login": "kellylford"},
        "updated_at": "2026-11-09T14:05:00Z",
        "labels": [{"name": n} for n in labels],
        "assignees": [],
        "milestone": None,
        "html_url": f"https://github.com/owner/repo/issues/{number}",
    }


class _Items:
    is_authenticated = True
    token = "test-token-not-real"

    def fetch_issues(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return [
            GitHubItem(1, "Issue 1", "open", "https://github.com/owner/repo/issues/1", False),
            GitHubItem(2, "Issue 2", "open", "https://github.com/owner/repo/issues/2", False),
        ]

    def fetch_pulls(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return []

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
    issues = {1: _issue(1, ["docs"]), 2: _issue(2, [])}

    def on_write(method: str, path: str, body: Any) -> None:
        number = int(path.rsplit("/", 1)[-1]) if path.rsplit("/", 1)[-1].isdigit() else 0
        if method == "PATCH" and number in issues and body:
            issue = dict(issues[number])
            if "labels" in body:
                issue["labels"] = [{"name": n} for n in body["labels"]]
            if "title" in body:
                issue["title"] = body["title"]
            issues[number] = issue

    api.on_write = on_write
    for number in issues:
        api.answer("GET", f"/repos/owner/repo/issues/{number}", lambda n=number: issues[n])
    api.answer_graphql(
        "issueOrPullRequest",
        {"repository": {"viewerPermission": "WRITE", "issueOrPullRequest": {"id": "I_1"}}},
    )
    api.answer("GET", "/repos/owner/repo/labels", [{"name": "bug"}, {"name": "docs"}])
    api.answer("GET", "/repos/owner/repo/milestones", [])
    api.answer("GET", "/repos/owner/repo/assignees", [])
    api.answer(
        "GET",
        "/repos/owner/repo",
        {"full_name": REPO, "name": "repo", "permissions": {"admin": True}},
    )
    return api


@pytest.fixture
def bench(wx_session_app, quill_data_dir, monkeypatch):
    said: list[str] = []
    provider = GitHubWorkbenchProvider(_Items(), REPO, announce=said.append)
    provider.api = _api()
    provider.batch_pace = 0
    monkeypatch.setattr(provider, "account_name", lambda: "me")
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    ref = NodeRef("repository", "issues_and_pulls", REPO)
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)
    yield frame
    frame.frame.Destroy()


def _script(monkeypatch, steps) -> list[PropertiesSheet]:
    seen: list[PropertiesSheet] = []

    def show(sheet: PropertiesSheet) -> int:
        seen.append(sheet)
        steps(sheet)
        sheet.dialog.Destroy()
        return wx.ID_OK

    monkeypatch.setattr(PropertiesSheet, "show", show)
    monkeypatch.setattr(
        "quill.ui.dialog_contract.show_modal_dialog", lambda dialog, title: wx.ID_OK
    )
    return seen


def _pick(bench: WorkbenchFrame, number: int, *, add: bool = False) -> None:
    if not add:
        for index in range(bench.list.GetItemCount()):
            bench.list.Select(index, False)
    index = next(i for i, row in enumerate(bench.rows) if row.number == number)
    bench.list.Select(index)


def _check(sheet: PropertiesSheet, key: str, name: str, on: bool = True) -> None:
    sheet.controls[key].set(name, on)


def test_alt_enter_opens_the_issue_sheet_fresh_from_github(bench, monkeypatch) -> None:
    seen = _script(monkeypatch, lambda sheet: None)
    _pick(bench, 1)
    bench.run("github.workbench.properties")
    (sheet,) = seen
    assert sheet.title == "Issue #1 Properties - owner/repo"
    assert sheet.sheet.pages[0].title == "General"
    assert sheet.controls["title"].GetValue() == "Issue 1"
    # Write access covers labels; read-only facts are read-only text boxes.
    assert sheet.editable(sheet.sheet.field("labels"))
    assert not sheet.editable(sheet.sheet.field("author"))
    assert sheet.controls["author"].IsEditable() is False


def test_saving_sends_only_the_change_verifies_it_and_says_one_sentence(bench, monkeypatch) -> None:
    def edit(sheet: PropertiesSheet) -> None:
        sheet.controls["title"].SetValue("Crash at start")
        _check(sheet, "labels", "bug")
        sheet.apply(close=False)

    _script(monkeypatch, edit)
    _pick(bench, 1)
    bench.run("github.workbench.properties")
    api = bench.provider.api
    assert api.writes() == [
        (
            "PATCH",
            "/repos/owner/repo/issues/1",
            {"title": "Crash at start", "labels": ["bug", "docs"]},
        )
    ]
    assert any(text.startswith("Issue #1: title Crash at start; added bug.") for text in bench.said)
    log = ChangeLog.load()
    assert [entry.target for entry in log.entries] == ["Issue #1"]


def test_ctrl_z_in_the_list_undoes_the_last_github_change(bench, monkeypatch) -> None:
    def edit(sheet: PropertiesSheet) -> None:
        _check(sheet, "labels", "bug")
        sheet.apply(close=True)

    _script(monkeypatch, edit)
    _pick(bench, 1)
    bench.run("github.workbench.properties")
    bench.list.SetFocus()
    bench.run("github.workbench.undo_change")
    api = bench.provider.api
    assert api.writes()[-1] == ("PATCH", "/repos/owner/repo/issues/1", {"labels": ["docs"]})
    assert any(text.startswith("Undone.") for text in bench.said)
    assert ChangeLog.load().entries[-1].undone


def test_several_rows_open_one_sheet_with_three_state_lists(bench, monkeypatch) -> None:
    results: list[str] = []
    monkeypatch.setattr(
        "quill.ui.github_workbench_results.show_results",
        lambda parent, title, text, **kw: results.append(text),
    )

    def edit(sheet: PropertiesSheet) -> None:
        rows = sheet.controls["labels"].labels()
        assert "docs, on 1 of 2" in rows
        _check(sheet, "labels", "bug")
        sheet.apply(close=True)

    seen = _script(monkeypatch, edit)
    _pick(bench, 1)
    _pick(bench, 2, add=True)
    bench.run("github.workbench.properties")
    assert seen[0].title == "Properties of 2 issues"
    writes = bench.provider.api.writes()
    assert ("PATCH", "/repos/owner/repo/issues/1", {"labels": ["docs", "bug"]}) in writes
    assert ("PATCH", "/repos/owner/repo/issues/2", {"labels": ["bug"]}) in writes
    assert results and results[0].endswith("2 done, 0 skipped, 0 failed")


def test_alt_enter_on_the_repository_node_opens_the_repository_sheet(bench, monkeypatch) -> None:
    seen = _script(monkeypatch, lambda sheet: None)
    bench.select(NodeRef("repository", "repository", REPO))
    bench.tree.SetFocus()
    bench.provider.open_properties(bench.current, [])
    assert seen[0].title == "owner/repo Properties"


def test_item_labels_opens_the_sheet_on_its_organize_page(bench, monkeypatch) -> None:
    pages: list[str] = []
    _script(monkeypatch, lambda sheet: pages.append(sheet.page_key()))
    _pick(bench, 1)
    bench.run("github.workbench.labels")
    assert pages == ["organize"]
