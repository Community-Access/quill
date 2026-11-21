"""Projects (version 2) end to end over recorded answers (complete.md 1.3, the verification row).

The whole life the Workbench offers a Project, its fields, its items and its
status updates: list, open, Properties, create, change, archive or delete,
with every field type, and the refusals: GitHub's own (no permission, not
found) and the Workbench level (Read Only). Views and workflows are read
only on the sheet, each with GitHub's reason said.

Already covered elsewhere, and not repeated here: the board's paging and
blockers (tests/unit/core/test_github_projects.py), the draft, field, status,
link, template, copy and delete mutations' bodies
(tests/unit/core/test_github_project_admin.py), a single select's and a
date's plan on the item sheet (tests/unit/core/workbench/test_github_phase8_sheets.py),
and Delete Project needing the title typed
(tests/unit/ui/test_github_workbench_project_admin.py).
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import projects
from quill.core.github.permissions import AccessLevel, ViewerContext
from quill.core.github.project_admin import FIELD_TYPES, create_field, post_status_update
from quill.core.github.project_models import OWN_FIELD_TYPES, GitHubProjectsError
from quill.core.github.project_transport import refusal_words
from quill.core.github.projects import fetch_project, list_projects, update_project_field
from quill.core.github.quick_actions import QuickError
from quill.core.github.quick_tables import QUICK, QUICK_REQUIREMENTS
from quill.core.github.sheet_catalog import SHEETS
from quill.core.github.sheet_engine import SheetSaveError, load, locked_fields, plan, save
from quill.core.github.sheets_projects import PROJECT, parse_fields, project_item_sheet
from quill.core.github.write_gate import command_refusal
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS
from quill.core.workbench.properties import FieldChange
from tests.github_api_fake import FakeGitHubApi

_P = "github.workbench."
PROJECT_ID = "PVT_1"
ITEM_ID = "PVTI_1"


# -- recorded answers ------------------------------------------------------------------


def _project_node(**changes: Any) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": PROJECT_ID,
        "title": "Roadmap",
        "shortDescription": "What ships when",
        "readme": "# Roadmap",
        "public": False,
        "closed": False,
        "template": False,
        "url": "https://github.com/orgs/acme/projects/3",
        "number": 3,
        "viewerCanUpdate": True,
        "owner": {"login": "acme"},
        "fields": {"nodes": [{"name": "Status", "dataType": "SINGLE_SELECT"}]},
        "views": {"nodes": [{"name": "Board", "layout": "BOARD_LAYOUT", "filter": "is:open"}]},
        "items": {
            "totalCount": 1,
            "nodes": [{"content": {"__typename": "DraftIssue", "title": "Plan"}}],
        },  # fmt: skip
        "workflows": {"nodes": [{"name": "Item closed", "enabled": True}]},
        "statusUpdates": {"nodes": [{"status": "AT_RISK", "body": "Late"}]},
        "repositories": {"nodes": [{"nameWithOwner": "acme/app"}]},
    }
    node.update(changes)
    return node


_FIELDS = {
    "node": {
        "fields": {
            "nodes": [
                {"id": "F_text", "name": "Notes", "dataType": "TEXT"},
                {"id": "F_num", "name": "Points", "dataType": "NUMBER"},
                {"id": "F_date", "name": "Due", "dataType": "DATE"},
                {
                    "id": "F_sel",
                    "name": "Status",
                    "dataType": "SINGLE_SELECT",
                    "options": [{"id": "o1", "name": "Todo"}, {"id": "o2", "name": "Done"}],
                },
                {
                    "id": "F_it",
                    "name": "Sprint",
                    "dataType": "ITERATION",
                    "configuration": {
                        "iterations": [
                            {
                                "id": "i5",
                                "title": "Iteration 5",
                                "startDate": "2026-11-18",
                                "duration": 14,
                            },
                        ],
                        "completedIterations": [
                            {
                                "id": "i4",
                                "title": "Iteration 4",
                                "startDate": "2026-11-04",
                                "duration": 14,
                            },
                        ],
                    },
                },  # fmt: skip
                {"id": "F_title", "name": "Title", "dataType": "TITLE"},
            ]
        }
    }
}
_ITEM_SHEET = project_item_sheet(parse_fields(_FIELDS))
_IDENT = {"project_id": PROJECT_ID, "item_id": ITEM_ID}


def _item_answer(values: list[dict[str, Any]], *, can: bool = True) -> dict[str, Any]:
    return {
        "node": {
            "id": ITEM_ID,
            "isArchived": False,
            "type": "ISSUE",
            "project": {"viewerCanUpdate": can},
            "content": {"number": 7, "title": "Crash on start", "url": "u"},
            "fieldValues": {"nodes": values},
        }
    }


def _value(field: str, **raw: Any) -> dict[str, Any]:
    return {**raw, "field": {"id": field}}


# -- the Project: open, Properties, views and workflows ---------------------------------


def test_the_project_opens_with_every_page_and_says_views_and_workflows_are_github_s() -> None:
    api = FakeGitHubApi()
    api.answer_graphql("... on ProjectV2{id title", {"node": _project_node()})
    loaded = load(api, PROJECT, {"node_id": PROJECT_ID})
    assert loaded.values["title"] == "Roadmap"
    assert loaded.values["views"] == ("Board, board, filter is:open",)
    assert loaded.values["workflows"] == ("Item closed, on",)
    assert loaded.values["status_updates"] == ("at risk: Late",)
    assert loaded.values["repositories"] == ("acme/app",)
    assert loaded.viewer == {"viewerCanUpdate": True}
    assert SHEETS["project"] is PROJECT
    # Views and workflows have no write, and each says why in plain words.
    for key in ("views", "workflows", "fields", "status_updates", "items"):
        assert key not in PROJECT.writes
    views = PROJECT.sheet.field("views").help
    flows = PROJECT.sheet.field("workflows").help
    assert "GitHub has no API to change a view's layout, filter" in views
    assert "New View..." in views and "Delete a View..." in views
    assert "no API to turn one on or off" in flows and "Delete a Workflow..." in flows


def test_a_project_github_will_not_show_is_said_never_opened_empty() -> None:
    api = FakeGitHubApi()
    api.answer_graphql("... on ProjectV2{id title", {"node": None})
    with pytest.raises(GitHubProjectsError, match="no such Project"):
        load(api, PROJECT, {"node_id": "PVT_gone"})


def test_renaming_and_closing_the_project_send_one_mutation_each_and_are_read_back() -> None:
    api = FakeGitHubApi()
    state = {"node": _project_node()}
    api.answer_graphql("... on ProjectV2{id title", lambda: {"node": state["node"]})

    def on_mutation(query: str, variables: dict[str, Any]) -> None:
        if "updateProjectV2(" in query and "title:$value" in query:
            state["node"] = {**state["node"], "title": variables["value"]}
        if "updateProjectV2(" in query and "closed:$value" in query:
            state["node"] = {**state["node"], "closed": variables["value"]}

    original = api.graphql

    def graphql(query: str, variables: Any) -> dict[str, Any]:
        if query.lstrip().startswith("mutation"):
            on_mutation(query, dict(variables))
        return original(query, variables)

    api.graphql = graphql  # type: ignore[method-assign]
    loaded = load(api, PROJECT, {"node_id": PROJECT_ID})
    changes = [
        FieldChange("title", "Title", "Roadmap", "Roadmap 2027"),
        FieldChange("closed", "Closed", False, True),
    ]
    outcome = save(api, PROJECT, {"node_id": PROJECT_ID}, changes, loaded=loaded.values)
    sent = [(q, v) for q, v in api.graphql_calls if q.startswith("mutation")]
    assert len(sent) == 2
    assert {v["value"] for _q, v in sent} == {"Roadmap 2027", True}
    assert all(v["id"] == PROJECT_ID for _q, v in sent)
    assert [c.key for c in outcome.done] == ["title", "closed"] and not outcome.not_taken


def test_read_only_and_a_project_you_cannot_update_lock_every_field_with_a_reason() -> None:
    read_only = ViewerContext(level=AccessLevel.READ_ONLY)
    locked = locked_fields(PROJECT, read_only)
    assert set(locked) == set(PROJECT.writes)
    assert all("Read Only" in reason or "read only" in reason for reason in locked.values())
    cannot = ViewerContext(viewer={"viewerCanUpdate": False})
    assert set(locked_fields(PROJECT, cannot)) == set(PROJECT.writes)
    # Organize may rename, but public and closed change who sees it: Full.
    organize = locked_fields(PROJECT, ViewerContext(level=AccessLevel.ORGANIZE))
    assert "title" not in organize and {"public", "closed"} <= set(organize)


# -- every field type on an item's sheet ------------------------------------------------


def test_an_item_sheet_has_a_control_for_every_editable_type_and_none_for_title() -> None:
    keys = {f.key for f in _ITEM_SHEET.sheet.fields()}
    assert {"f_F_text", "f_F_num", "f_F_date", "f_F_sel", "f_F_it", "archived"} <= keys
    assert "f_F_title" not in keys
    sprint = _ITEM_SHEET.sheet.field("f_F_it").choices
    assert sprint == (
        "Iteration 5, from 2026-11-18 for 14 days",
        "Iteration 4, from 2026-11-04 for 14 days",
    )


@pytest.mark.parametrize(
    ("key", "after", "sent"),
    [
        ("f_F_text", "Needs a repro", {"text": "Needs a repro"}),
        ("f_F_num", "3", {"number": 3.0}),
        ("f_F_num", "2.5", {"number": 2.5}),
        ("f_F_date", "2026-12-01", {"date": "2026-12-01"}),
        ("f_F_sel", "Done", {"singleSelectOptionId": "o2"}),
        ("f_F_it", "Iteration 5, from 2026-11-18 for 14 days", {"iterationId": "i5"}),
    ],
)
def test_each_field_type_is_set_with_the_value_github_wants(
    key: str, after: str, sent: dict[str, object]
) -> None:
    (request,) = plan(_ITEM_SHEET, _IDENT, [FieldChange(key, key, "", after)])
    assert "updateProjectV2ItemFieldValue" in request.graphql
    assert request.body == {
        "project": PROJECT_ID,
        "item": ITEM_ID,
        "field": key.removeprefix("f_"),
        "value": sent,
    }


@pytest.mark.parametrize("key", ["f_F_text", "f_F_num", "f_F_sel", "f_F_it"])
def test_emptying_any_field_clears_it(key: str) -> None:
    (request,) = plan(_ITEM_SHEET, _IDENT, [FieldChange(key, key, "x", "")])
    assert "clearProjectV2ItemFieldValue" in request.graphql
    assert "value" not in (request.body or {})


def test_a_number_that_is_not_one_is_refused_before_anything_is_sent() -> None:
    with pytest.raises(SheetSaveError, match="Points needs a number"):
        plan(_ITEM_SHEET, _IDENT, [FieldChange("f_F_num", "Points", "", "three")])


def test_an_item_reads_every_value_including_zero_and_a_finished_iteration() -> None:
    api = FakeGitHubApi()
    api.answer_graphql(
        "... on ProjectV2Item{id isArchived",
        _item_answer([
            _value("F_text", text="Needs a repro"),
            _value("F_num", number=0.0),
            _value("F_date", date="2026-12-01"),
            _value("F_sel", optionId="o1"),
            _value("F_it", iterationId="i4"),
        ]),
    )  # fmt: skip
    loaded = load(api, _ITEM_SHEET, _IDENT)
    assert loaded.values["content"] == "#7 Crash on start"
    assert loaded.values["f_F_text"] == "Needs a repro"
    assert loaded.values["f_F_num"] == "0"
    assert loaded.values["f_F_date"] == "2026-12-01"
    assert loaded.values["f_F_sel"] == "Todo"
    assert loaded.values["f_F_it"] == "Iteration 4, from 2026-11-04 for 14 days"
    assert loaded.viewer == {"viewerCanUpdate": True}


def test_a_saved_number_reads_back_as_typed_so_it_is_reported_done() -> None:
    api = FakeGitHubApi()
    state = {"values": [_value("F_num", number=1.0)]}
    api.answer_graphql("... on ProjectV2Item{id isArchived", lambda: _item_answer(state["values"]))
    api.answer_graphql(
        "updateProjectV2ItemFieldValue",
        lambda: state.update(values=[_value("F_num", number=3.0)]) or {},
    )
    loaded = load(api, _ITEM_SHEET, _IDENT)
    assert loaded.values["f_F_num"] == "1"
    outcome = save(
        api,
        _ITEM_SHEET,
        _IDENT,
        [FieldChange("f_F_num", "Points", "1", "3")],
        loaded=loaded.values,
    )
    assert [c.key for c in outcome.done] == ["f_F_num"]
    assert outcome.not_taken == [] and outcome.failed == []


def test_a_field_github_ignored_is_reported_not_taken() -> None:
    api = FakeGitHubApi()
    api.answer_graphql(
        "... on ProjectV2Item{id isArchived", _item_answer([_value("F_sel", optionId="o1")])
    )
    loaded = load(api, _ITEM_SHEET, _IDENT)
    outcome = save(
        api, _ITEM_SHEET, _IDENT, [FieldChange("f_F_sel", "Status", "Todo", "Done")],
        loaded=loaded.values,
    )  # fmt: skip
    assert [c.key for c in outcome.not_taken] == ["f_F_sel"]


def test_archiving_an_item_from_its_sheet_and_back() -> None:
    (archive,) = plan(_ITEM_SHEET, _IDENT, [FieldChange("archived", "Archived", False, True)])
    (restore,) = plan(_ITEM_SHEET, _IDENT, [FieldChange("archived", "Archived", True, False)])
    assert "archiveProjectV2Item" in archive.graphql
    assert "unarchiveProjectV2Item" in restore.graphql
    assert archive.body == restore.body == {"project": PROJECT_ID, "id": ITEM_ID}


def test_an_item_on_a_project_you_cannot_update_locks_every_field() -> None:
    api = FakeGitHubApi()
    api.answer_graphql("... on ProjectV2Item{id isArchived", _item_answer([], can=False))
    loaded = load(api, _ITEM_SHEET, _IDENT)
    ctx = ViewerContext(viewer=loaded.viewer)
    assert set(locked_fields(_ITEM_SHEET, ctx)) == set(_ITEM_SHEET.writes)
    read_only = ViewerContext(level=AccessLevel.READ_ONLY)
    assert set(locked_fields(_ITEM_SHEET, read_only)) == set(_ITEM_SHEET.writes)


def test_an_item_that_is_gone_is_said() -> None:
    api = FakeGitHubApi()
    api.answer_graphql("... on ProjectV2Item{id isArchived", {"node": None})
    with pytest.raises(GitHubProjectsError, match="no such Project item"):
        load(api, _ITEM_SHEET, _IDENT)


# -- the board the Projects window reads, and its field edits ----------------------------


def _board(fields: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "node": {
            "id": PROJECT_ID,
            "title": "Roadmap",
            "number": 3,
            "url": "u",
            "fields": {"nodes": fields, "pageInfo": {"hasNextPage": False}},
            "items": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}},
        }
    }


def test_the_board_names_each_plain_field_by_its_type_and_reads_iterations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fields = [
        {"__typename": "ProjectV2Field", "id": "F_title", "name": "Title", "dataType": "TITLE"},
        {"__typename": "ProjectV2Field", "id": "F_text", "name": "Notes", "dataType": "TEXT"},
        {"__typename": "ProjectV2Field", "id": "F_num", "name": "Points", "dataType": "NUMBER"},
        {"__typename": "ProjectV2Field", "id": "F_date", "name": "Due", "dataType": "DATE"},
        {
            "__typename": "ProjectV2IterationField",
            "id": "F_it",
            "name": "Sprint",
            "dataType": "ITERATION",
            # GitHub answers a list here, not a connection.
            "configuration": {"iterations": [{"id": "i5", "title": "Iteration 5"}]},
        },
    ]
    seen: list[str] = []
    monkeypatch.setattr(
        projects, "_request", lambda _t, query, _v: seen.append(query) or _board(fields)
    )
    board = fetch_project("token", PROJECT_ID)
    kinds = {f.name: (f.kind, f.data_type) for f in board.fields}
    assert kinds == {
        "Title": ("field", "TITLE"),
        "Notes": ("text", "TEXT"),
        "Points": ("number", "NUMBER"),
        "Due": ("date", "DATE"),
        "Sprint": ("iteration", "ITERATION"),
    }
    assert board.fields[-1].iterations == (("i5", "Iteration 5"),)
    # The field union is read through its common interface, never selected bare.
    assert "... on ProjectV2FieldCommon { id name dataType }" in seen[0]
    assert "field { id name }" not in seen[0]
    assert [f.name for f in board.fields if f.data_type in OWN_FIELD_TYPES] == [
        "Notes",
        "Points",
        "Due",
        "Sprint",
    ]


@pytest.mark.parametrize(
    ("kind", "typed", "sent"),
    [
        ("text", "Hello", {"text": "Hello"}),
        ("number", "4", {"number": 4.0}),
        ("date", "2026-12-01", {"date": "2026-12-01"}),
        ("iteration", "i5", {"iterationId": "i5"}),
    ],
)
def test_the_projects_window_sets_text_number_date_and_iteration(
    monkeypatch: pytest.MonkeyPatch, kind: str, typed: str, sent: dict[str, object]
) -> None:
    from quill.core.github.projects import GitHubProjectField

    variables: list[dict[str, Any]] = []
    monkeypatch.setattr(
        projects,
        "_request",
        lambda _t, _q, v: (
            variables.append(v)
            or {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": ITEM_ID}}}
        ),
    )
    field = GitHubProjectField("F", "Field", kind, iterations=(("i5", "Iteration 5"),))
    update_project_field("token", PROJECT_ID, ITEM_ID, field, typed)
    assert variables[0]["value"] == sent


def test_a_built_in_field_is_refused_as_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.github.projects import GitHubProjectField

    monkeypatch.setattr(projects, "_request", lambda *_a: pytest.fail("sent"))
    with pytest.raises(GitHubProjectsError, match="read-only in QUILL"):
        update_project_field(
            "token", PROJECT_ID, ITEM_ID, GitHubProjectField("F", "Title", "field"), "x"
        )


def test_a_repository_github_cannot_find_lists_no_projects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(projects, "_request", lambda *_a: {"repository": None})
    with pytest.raises(GitHubProjectsError, match="unavailable"):
        list_projects("token", "acme/gone")


# -- creating fields and status updates ----------------------------------------------


@pytest.mark.parametrize("code", [code for code, _w in FIELD_TYPES])
def test_every_field_type_the_workbench_offers_can_be_made(code: str) -> None:
    sent: list[dict[str, Any]] = []

    def request(_t: str, _q: str, variables: dict[str, object]) -> dict[str, Any]:
        sent.append(dict(variables["input"]))  # type: ignore[call-overload]
        return {"createProjectV2Field": {"projectV2Field": {"name": "Size"}}}

    assert create_field("token", PROJECT_ID, "Size", code, ("S", "M"), request=request) == "Size"
    assert sent[0]["dataType"] == code


def test_an_iteration_field_is_not_offered_to_make() -> None:
    # Made on GitHub (the API's iteration setup is not built here); edited once it exists.
    assert "ITERATION" not in {code for code, _w in FIELD_TYPES}
    with pytest.raises(GitHubProjectsError, match="Choose Text, Number, Date or Single select"):
        create_field("token", PROJECT_ID, "Sprint", "ITERATION", request=lambda *_a: {})


def test_a_status_update_with_a_date_github_would_refuse_sends_nothing() -> None:
    def request(*_a: object) -> dict[str, Any]:
        raise AssertionError("sent")

    for bad in ("12/01/2026", "2026-13-01", "2026-1-1"):
        with pytest.raises(GitHubProjectsError, match="year-month-day"):
            post_status_update("t", PROJECT_ID, "ON_TRACK", "", target_date=bad, request=request)
    seen: list[Any] = []
    post_status_update(
        "t",
        PROJECT_ID,
        "ON_TRACK",
        "Fine",
        start_date="2026-11-01",
        target_date="2026-12-01",
        request=lambda _t, _q, v: (
            seen.append(v) or {"createProjectV2StatusUpdate": {"statusUpdate": {"id": "S"}}}
        ),
    )
    assert seen[0]["input"]["targetDate"] == "2026-12-01"


# -- items and status updates from the Project's row (quick commands) ------------------


def _quick(verb: str) -> Any:
    return next(q for q in QUICK if q.verb == verb)


def _items_answer() -> dict[str, Any]:
    return {
        "node": {
            "items": {
                "nodes": [
                    {"id": "I1", "isArchived": False,
                     "content": {"__typename": "Issue", "number": 7, "title": "Crash"}},
                    {"id": "I2", "isArchived": True,
                     "content": {"__typename": "DraftIssue", "title": "Old idea"}},
                ]
            }
        }
    }  # fmt: skip


@pytest.mark.parametrize(
    ("verb", "offered", "mutation"),
    [
        ("project_archive_item", [("#7 Crash", "I1")], "archiveProjectV2Item"),
        ("project_restore_item", [("Old idea", "I2")], "unarchiveProjectV2Item"),
        ("project_remove_item", [("#7 Crash", "I1"), ("Old idea", "I2")], "deleteProjectV2Item"),
    ],
)
def test_archive_restore_and_remove_an_item_pick_the_right_items_and_send(
    verb: str, offered: list[tuple[str, str]], mutation: str
) -> None:
    api = FakeGitHubApi()
    api.answer_graphql("items(first: 100)", _items_answer())
    quick = _quick(verb)
    ctx = {"key": PROJECT_ID}
    assert quick.pick is not None and quick.pick(api, ctx) == offered
    ctx.update(item=offered[0][1], item_label=offered[0][0])
    quick.run(api, ctx)
    query, variables = api.graphql_calls[-1]
    assert mutation in query
    assert variables == {"input": {"projectId": PROJECT_ID, "itemId": offered[0][1]}}
    assert quick.said(None, ctx).endswith(".")


def test_removing_an_item_asks_first_and_archive_is_organizing() -> None:
    assert "cannot be put back" in _quick("project_remove_item").confirm
    assert QUICK_REQUIREMENTS[f"{_P}project_remove_item"][1].name == "DESTRUCTIVE"
    assert QUICK_REQUIREMENTS[f"{_P}project_archive_item"][1].name == "ORGANIZING"


def test_restore_with_nothing_archived_says_so() -> None:
    api = FakeGitHubApi()
    api.answer_graphql("items(first: 100)", {"node": {"items": {"nodes": []}}})
    pick = _quick("project_restore_item").pick
    assert pick is not None
    with pytest.raises(QuickError, match="no archived items"):
        pick(api, {"key": PROJECT_ID})


def test_a_status_update_is_edited_and_deleted_by_its_id() -> None:
    api = FakeGitHubApi()
    api.answer_graphql(
        "statusUpdates(first: 20)",
        {"node": {"statusUpdates": {"nodes": [
            {"id": "SU1", "status": "AT_RISK", "body": "Late", "createdAt": "2026-11-10T00:00Z"}
        ]}}},
    )  # fmt: skip
    edit, delete = _quick("project_edit_status"), _quick("project_delete_status")
    assert edit.pick is not None
    assert edit.pick(api, {"key": PROJECT_ID}) == [("2026-11-10, at_risk: Late", "SU1")]
    edit.run(api, {"key": PROJECT_ID, "update": "SU1", "status": "ON_TRACK", "body": ""})
    assert api.graphql_calls[-1][1] == {"input": {"statusUpdateId": "SU1", "status": "ON_TRACK"}}
    delete.run(api, {"key": PROJECT_ID, "update": "SU1"})
    assert "deleteProjectV2StatusUpdate" in api.graphql_calls[-1][0]


# -- refusals ---------------------------------------------------------------------------

_PROJECT_WRITES = sorted(
    command
    for command in {*COMMAND_REQUIREMENTS, *QUICK_REQUIREMENTS}
    if command.startswith(f"{_P}project_")
)


@pytest.mark.parametrize("command_id", _PROJECT_WRITES)
def test_every_project_write_is_refused_at_read_only(command_id: str) -> None:
    said = command_refusal(command_id, lambda: AccessLevel.READ_ONLY)
    assert said.startswith("Cannot run ") and "this account is Read Only" in said


def test_deleting_a_project_or_a_field_needs_full_and_editing_only_organize() -> None:
    organize = lambda: AccessLevel.ORGANIZE  # noqa: E731
    for verb in ("project_delete", "project_field_delete", "project_remove_item"):
        assert "it needs Full" in command_refusal(f"{_P}{verb}", organize), verb
    for verb in ("project_archive_item", "project_restore_item", "project_move_item"):
        assert command_refusal(f"{_P}{verb}", organize) == "", verb


@pytest.mark.parametrize(
    ("errors", "said"),
    [
        ([{"type": "FORBIDDEN", "message": "Resource not accessible"}], "may not change this"),
        ([{"type": "NOT_FOUND", "message": "Could not resolve"}], "no such Project or item"),
        ([{"type": "INSUFFICIENT_SCOPES", "message": "needs project"}], "lacks the project scope"),
        ([{"message": "Something else"}], "Something else"),
    ],
)
def test_github_s_refusals_are_said_in_plain_words_then_its_own(
    errors: list[dict[str, str]], said: str
) -> None:
    words = refusal_words(errors)
    assert said in words
    if errors[0].get("type"):
        assert words.endswith(f"GitHub said: {errors[0]['message']}")


def test_a_refused_mutation_is_never_reported_as_done() -> None:
    def refused(*_a: object) -> dict[str, Any]:
        raise GitHubProjectsError(refusal_words([{"type": "FORBIDDEN", "message": "no"}]))

    with pytest.raises(GitHubProjectsError, match="may not change this Project"):
        create_field("t", PROJECT_ID, "Size", "TEXT", request=refused)
