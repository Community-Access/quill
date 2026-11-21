"""Editing an issue's fields on its Properties sheet (complete.md 1.3).

The Issue Fields page edits a date, a number, a single choice and text, each
by its own kind of control, through the very request Issue Fields... on the
row sends (``issue_admin.field_request``); each save is checked by reading
the issue again, and several issues at once show Mixed where they differ.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.across_issue_fields import FieldValue
from quill.core.github.batch import BatchItem, run
from quill.core.github.issue_admin import IssueAdminError, clear_field_value, set_field_value
from quill.core.github.issue_fields_rows import (
    FIELD_PAGE,
    field_key,
    with_field_page,
    with_field_page_many,
)
from quill.core.github.permissions import ViewerContext
from quill.core.github.sheet_engine import load, locked_fields, save
from quill.core.github.sheets_items import ISSUE
from quill.core.workbench.properties import MIXED, FieldChange, FieldKind, merge_values
from tests.github_api_fake import FakeGitHubApi

REPO = "acme/site"
DEFS = [
    {
        "id": 1,
        "name": "Priority",
        "data_type": "single_select",
        "options": [{"name": "High"}, {"name": "Low"}],
    },
    {"id": 2, "name": "Due", "data_type": "date"},
    {"id": 3, "name": "Points", "data_type": "number"},
    {"id": 4, "name": "Notes", "data_type": "text"},
    {"id": 5, "name": "Areas", "data_type": "multi_select"},
]
PRIORITY, DUE, POINTS, NOTES = (
    field_key("1", "single_select"),
    field_key("2", "date"),
    field_key("3", "number"),
    field_key("4", "text"),
)


class _Issues:
    """GitHub's side: each issue's field values, changed by the writes the sheet sends."""

    def __init__(self, values: dict[int, dict[int, Any]], *, ignore: bool = False) -> None:
        self.values, self.ignore = values, ignore
        self.api = FakeGitHubApi()
        self.api.answer("GET", "/orgs/acme/issue-fields", DEFS)
        for number in values:
            self.api.answer("GET", f"/repos/{REPO}/issues/{number}", {"number": number})
            self.api.answer(
                "GET",
                f"/repos/{REPO}/issues/{number}/issue-field-values",
                lambda n=number: [
                    {"issue_field_id": k, "value": v} for k, v in self.values[n].items()
                ],
            )
        self.api.on_write = self._write

    def _write(self, method: str, path: str, body: Any) -> None:
        if self.ignore:
            return  # GitHub says 200 and keeps the old value
        number = int(path.split("/issues/")[1].split("/")[0])
        if method == "DELETE":
            self.values[number].pop(int(path.rsplit("/", 1)[1]), None)
        else:
            for entry in body["issue_field_values"]:
                self.values[number][entry["field_id"]] = entry["value"]


def _ident(number: int = 1) -> dict[str, str]:
    return {"repo": REPO, "number": str(number)}


def _page(values: dict[str, Any]) -> Any:
    sheet = with_field_page(ISSUE.sheet, values)
    return next(page for page in sheet.pages if page.key == FIELD_PAGE)


def test_each_field_is_edited_by_its_own_kind() -> None:
    issues = _Issues({1: {1: "High", 2: "2026-12-31", 3: 3}})
    page = _page(load(issues.api, ISSUE, _ident()).values)
    by_key = {spec.key: spec for spec in page.fields}
    assert by_key[PRIORITY].kind is FieldKind.CHOICE and not by_key[PRIORITY].readonly
    assert by_key[PRIORITY].choices == ("", "High", "Low")  # "" is (none): clears it
    assert by_key[DUE].kind is FieldKind.DATE and "year-month-day" in by_key[DUE].help
    assert by_key[POINTS].kind is FieldKind.NUMBER and not by_key[POINTS].readonly
    assert by_key[NOTES].kind is FieldKind.TEXT and not by_key[NOTES].readonly
    assert by_key[field_key("5", "multi_select")].readonly
    assert all("Issue Fields..." in by_key[k].help for k in (PRIORITY, DUE, POINTS, NOTES))


@pytest.mark.parametrize(
    ("key", "label", "typed", "sent"),
    [
        (DUE, "Due", "2027-01-15", "2027-01-15"),
        (POINTS, "Points", "5", 5),
        (POINTS, "Points", "2.5", 2.5),
        (PRIORITY, "Priority", "Low", "Low"),
        (NOTES, "Notes", "Ship it", "Ship it"),
    ],
)
def test_a_save_sends_issue_fields_own_request_and_is_checked(
    key: str, label: str, typed: str, sent: object
) -> None:
    issues = _Issues({1: {1: "High"}})
    loaded = load(issues.api, ISSUE, _ident()).values
    change = FieldChange(key, label, loaded.get(key), typed)
    outcome = save(issues.api, ISSUE, _ident(), [change], loaded=loaded)
    field_id = int(key.rsplit(":", 1)[1])
    body = {"issue_field_values": [{"field_id": field_id, "value": sent}]}
    assert issues.api.writes() == [("POST", f"/repos/{REPO}/issues/1/issue-field-values", body)]
    assert [c.key for c in outcome.done] == [key] and outcome.ok
    assert outcome.after[key] == typed


def test_the_sheet_and_issue_fields_send_the_same_request() -> None:
    by_row, by_sheet = _Issues({1: {}}), _Issues({1: {}})
    field = FieldValue("2", "Due", "date", "unset")
    set_field_value(by_row.api, REPO, 1, field, "2027-01-15")
    loaded = load(by_sheet.api, ISSUE, _ident()).values
    save(
        by_sheet.api, ISSUE, _ident(), [FieldChange(DUE, "Due", None, "2027-01-15")], loaded=loaded
    )
    assert by_row.api.writes() == by_sheet.api.writes()
    clear_field_value(by_row.api, REPO, 1, field)
    loaded = load(by_sheet.api, ISSUE, _ident()).values
    save(by_sheet.api, ISSUE, _ident(), [FieldChange(DUE, "Due", "2027-01-15", "")], loaded=loaded)
    assert by_row.api.writes()[-1] == by_sheet.api.writes()[-1]
    assert by_sheet.api.writes()[-1][:2] == (
        "DELETE",
        f"/repos/{REPO}/issues/1/issue-field-values/2",
    )


def test_emptying_a_field_clears_only_that_field() -> None:
    issues = _Issues({1: {1: "High", 4: "note"}})
    loaded = load(issues.api, ISSUE, _ident()).values
    change = FieldChange(NOTES, "Notes", "note", "")
    outcome = save(issues.api, ISSUE, _ident(), [change], loaded=loaded)
    assert issues.api.writes() == [("DELETE", f"/repos/{REPO}/issues/1/issue-field-values/4", None)]
    assert outcome.ok and issues.values[1] == {1: "High"}
    assert "Not set: " in str(outcome.after["issue_fields_state"])


def test_a_value_github_did_not_keep_is_reported_not_taken() -> None:
    issues = _Issues({1: {3: 1}}, ignore=True)
    loaded = load(issues.api, ISSUE, _ident()).values
    outcome = save(
        issues.api, ISSUE, _ident(), [FieldChange(POINTS, "Points", "1", "8")], loaded=loaded
    )
    assert [c.key for c in outcome.not_taken] == [POINTS] and not outcome.done


def test_a_wrong_date_is_refused_before_anything_is_sent() -> None:
    issues = _Issues({1: {}})
    loaded = load(issues.api, ISSUE, _ident()).values
    with pytest.raises(IssueAdminError, match="year-month-day"):
        save(issues.api, ISSUE, _ident(), [FieldChange(DUE, "Due", None, "soon")], loaded=loaded)
    assert issues.api.writes() == []


def test_without_triage_every_field_is_locked_with_the_reason() -> None:
    issues = _Issues({1: {}})
    values = load(issues.api, ISSUE, _ident()).values
    keys = [spec.key for spec in _page(values).fields]
    locked = locked_fields(ISSUE, ViewerContext(repo_role="read", where=REPO), keys)
    assert "triage access" in locked[DUE] and DUE in locked and PRIORITY in locked
    assert not set(keys) & set(locked_fields(ISSUE, ViewerContext(repo_role="triage"), keys))


def test_several_issues_show_mixed_and_each_is_saved_and_checked() -> None:
    issues = _Issues({1: {1: "High"}, 2: {1: "Low"}, 3: {1: "Low"}})
    loads = [load(issues.api, ISSUE, _ident(n)).values for n in (1, 2, 3)]
    sheet = with_field_page_many(ISSUE.sheet, loads)
    page = next(page for page in sheet.pages if page.key == FIELD_PAGE)
    assert PRIORITY in {spec.key for spec in page.fields}
    assert merge_values(loads)[PRIORITY] is MIXED
    items = [
        BatchItem(f"#{n}", _ident(n), values) for n, values in zip((1, 2, 3), loads, strict=True)
    ]
    change = FieldChange(PRIORITY, "Priority", MIXED, "Low")  # type: ignore[arg-type]
    results = run(issues.api, ISSUE, items, [change], pace=0)
    assert [r.status for r in results] == ["Done", "Skipped", "Skipped"]
    assert issues.values[1] == {1: "Low"}
    assert issues.api.writes() == [
        (
            "POST",
            f"/repos/{REPO}/issues/1/issue-field-values",
            {"issue_field_values": [{"field_id": 1, "value": "Low"}]},
        )
    ]


def test_several_issues_with_no_fields_keep_the_plain_sheet() -> None:
    assert with_field_page_many(ISSUE.sheet, [{"title": "a"}, {"title": "b"}]) is ISSUE.sheet
