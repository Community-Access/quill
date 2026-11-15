"""GitHub Workbench Phase 7: Alt+Enter opens a real, editable, verified sheet (GH-R-030 to 035).

A real frame over fake GitHub Items rows, with the sheets' reads and writes
answered by a recorded API, background work run inline, and the sheet's own
modal loop replaced by a script that edits its controls the way a person
would.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote

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
        parts = path.split("/")  # "", repos, owner, repo, issues, n, labels, name
        if len(parts) >= 7 and parts[6] == "labels" and parts[5].isdigit():
            issue = dict(issues[int(parts[5])])
            names = [label["name"] for label in issue["labels"]]
            if method == "POST":
                names += [n for n in body["labels"] if n not in names]
            elif method == "DELETE":
                names = [n for n in names if n != unquote(parts[7])]
            issue["labels"] = [{"name": n} for n in names]
            issues[int(parts[5])] = issue
            return
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
        ("PATCH", "/repos/owner/repo/issues/1", {"title": "Crash at start"}),
        ("POST", "/repos/owner/repo/issues/1/labels", {"labels": ["bug"]}),
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
    assert api.writes()[-1] == ("DELETE", "/repos/owner/repo/issues/1/labels/bug", None)
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
    assert ("POST", "/repos/owner/repo/issues/1/labels", {"labels": ["bug"]}) in writes
    assert ("POST", "/repos/owner/repo/issues/2/labels", {"labels": ["bug"]}) in writes
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


# -- one command per field (complete.md 10B.1) ----------------------------------------


@pytest.mark.parametrize(
    ("command", "page", "field"),
    [
        ("github.workbench.edit_title", "general", "title"),
        ("github.workbench.labels", "organize", "labels"),
        ("github.workbench.assignees", "organize", "assignees"),
        ("github.workbench.milestone", "organize", "milestone"),
        ("github.workbench.projects", "projects", "projects"),
    ],
)
def test_each_field_row_is_enabled_and_opens_the_sheet_on_its_field(
    bench, monkeypatch, command: str, page: str, field: str
) -> None:
    landed: list[tuple[str, str, bool]] = []

    def look(sheet: PropertiesSheet) -> None:
        moved = sheet.focus_start_field()
        landed.append((sheet.page_key(), sheet.start_field, moved))

    _script(monkeypatch, look)
    _pick(bench, 1)
    # Greyed before 2026-11-13: the context menu offered these rows disabled.
    assert bench.can_run(command)
    bench.run(command)
    assert landed == [(page, field, True)]


def test_edit_title_puts_focus_in_the_title_and_saves_it(bench, monkeypatch) -> None:
    def edit(sheet: PropertiesSheet) -> None:
        assert sheet.focus_start_field()
        title = sheet.controls["title"]
        assert title.GetStringSelection() == "Issue 1"  # typing replaces it
        title.SetValue("Renamed")
        sheet.apply(close=True)

    _script(monkeypatch, edit)
    _pick(bench, 1)
    bench.run("github.workbench.edit_title")
    assert bench.provider.api.writes() == [
        ("PATCH", "/repos/owner/repo/issues/1", {"title": "Renamed"})
    ]


def test_pull_request_rows_have_milestone_projects_and_edit_title() -> None:
    from quill.core.github.item_actions import GITHUB_ACTIONS

    for kind in ("issue", "pull_request"):
        commands = {row.command_id for row in GITHUB_ACTIONS.rows_for(kind)}
        for verb in ("edit_title", "labels", "assignees", "milestone", "projects"):
            assert f"github.workbench.{verb}" in commands, (kind, verb)


def test_a_label_somebody_added_while_the_sheet_was_open_survives(bench, monkeypatch) -> None:
    api = bench.provider.api

    def edit(sheet: PropertiesSheet) -> None:
        # Somebody else labels it on GitHub while this sheet is open.
        issue = dict(api.answers[("GET", "/repos/owner/repo/issues/1")]())
        issue["labels"] = [*issue["labels"], {"name": "urgent"}]
        api.answer("GET", "/repos/owner/repo/issues/1", issue)
        api.on_write = _keep(api, issue)
        _check(sheet, "labels", "bug")
        _check(sheet, "labels", "docs", on=False)
        sheet.apply(close=True)

    _script(monkeypatch, edit)
    _pick(bench, 1)
    bench.run("github.workbench.labels")
    assert api.writes() == [
        ("POST", "/repos/owner/repo/issues/1/labels", {"labels": ["bug"]}),
        ("DELETE", "/repos/owner/repo/issues/1/labels/docs", None),
    ]
    final = api.answers[("GET", "/repos/owner/repo/issues/1")]
    assert sorted(label["name"] for label in final["labels"]) == ["bug", "urgent"]
    assert any(text.startswith("Issue #1: added bug, removed docs.") for text in bench.said)


def _keep(api: FakeGitHubApi, issue: dict[str, Any]) -> Any:
    """GitHub's label endpoints over one issue answer that is replaced on each write."""

    def on_write(method: str, path: str, body: Any) -> None:
        current = api.answers[("GET", "/repos/owner/repo/issues/1")]
        names = [label["name"] for label in current["labels"]]
        if method == "POST":
            names += [n for n in body["labels"] if n not in names]
        elif method == "DELETE":
            names = [n for n in names if n != unquote(path.rsplit("/", 1)[-1])]
        api.answer(
            "GET", "/repos/owner/repo/issues/1", {**current, "labels": [{"name": n} for n in names]}
        )

    return on_write


def _projects_api(api: FakeGitHubApi, member: list[str]) -> None:
    """Projects on GitHub: Roadmap and Triage, the issue in those named in *member*."""
    ids = {"Roadmap": "PVT_road", "Triage": "PVT_tri", "Q1": "PVT_new"}

    def viewer() -> dict[str, Any]:
        nodes = [{"id": f"PVTI_{t}", "project": {"id": ids[t], "title": t}} for t in member]
        return {
            "repository": {
                "viewerPermission": "WRITE",
                "issueOrPullRequest": {"id": "I_1", "projectItems": {"nodes": nodes}},
            }
        }

    api.graphql_answers.clear()
    api.answer_graphql("issueOrPullRequest", viewer)
    api.answer_graphql(
        "projectsV2(first:50)",
        {
            "repository": {
                "projectsV2": {"nodes": [{"id": "PVT_road", "title": "Roadmap"}]},
                "owner": {"projectsV2": {"nodes": [{"id": "PVT_tri", "title": "Triage"}]}},
            },
            "viewer": {"projectsV2": {"nodes": []}},
        },
    )
    real = api.graphql

    def graphql(query: str, variables: Any) -> dict[str, Any]:
        found = real(query, variables)
        if "addProjectV2ItemById" in query:
            member.append(next(t for t, i in ids.items() if i == variables["project"]))
        if "deleteProjectV2Item" in query:
            member.remove(variables["item"].removeprefix("PVTI_"))
        return found

    api.graphql = graphql  # type: ignore[method-assign]


def test_projects_on_the_sheet_add_and_remove_with_the_graphql_mutations(
    bench, monkeypatch
) -> None:
    api = bench.provider.api
    member = ["Roadmap"]
    _projects_api(api, member)

    def edit(sheet: PropertiesSheet) -> None:
        assert sheet.editable(sheet.sheet.field("projects"))
        assert sheet.controls["projects"].labels() == ["Roadmap", "Triage"]
        _check(sheet, "projects", "Triage")
        _check(sheet, "projects", "Roadmap", on=False)
        sheet.apply(close=True)

    _script(monkeypatch, edit)
    _pick(bench, 1)
    bench.run("github.workbench.projects")
    sent = [
        ("addProjectV2ItemById" if "addProjectV2ItemById" in q else "deleteProjectV2Item", v)
        for q, v in api.graphql_calls
        if q.startswith("mutation")
    ]
    assert sent == [
        ("addProjectV2ItemById", {"project": "PVT_tri", "content": "I_1"}),
        ("deleteProjectV2Item", {"project": "PVT_road", "item": "PVTI_Roadmap"}),
    ]
    assert member == ["Triage"]
    assert any(text.startswith("Issue #1: added Triage, removed Roadmap.") for text in bench.said)


def test_new_project_creates_one_on_github_and_puts_the_issue_in_it(bench, monkeypatch) -> None:
    api = bench.provider.api
    member: list[str] = []
    _projects_api(api, member)
    api.answer_graphql(
        "repository(owner:$owner,name:$name){id owner{id}}",
        {"repository": {"id": "R_1", "owner": {"id": "O_1"}}},
    )
    api.answer_graphql(
        "createProjectV2", {"createProjectV2": {"projectV2": {"id": "PVT_new", "title": "Q1"}}}
    )
    monkeypatch.setattr(bench.provider, "_ask_text", lambda *_a: "Q1", raising=False)

    def edit(sheet: PropertiesSheet) -> None:
        sheet._create(sheet.sheet.field("projects"))
        assert sheet.controls["projects"].state("Q1") == "on"
        sheet.apply(close=True)

    _script(monkeypatch, edit)
    _pick(bench, 1)
    bench.run("github.workbench.projects")
    created = [v for q, v in api.graphql_calls if "createProjectV2" in q]
    assert created == [{"owner": "O_1", "title": "Q1", "repository": "R_1"}]
    added = [v for q, v in api.graphql_calls if "addProjectV2ItemById" in q]
    assert added == [{"project": "PVT_new", "content": "I_1"}]
    assert "Created Q1." in bench.said
