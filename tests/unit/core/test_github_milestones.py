"""Milestones read as words, change only when GitHub confirms, and batch-assign."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest

from quill.core.github import milestones
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.milestones import (
    GitHubMilestone,
    GitHubMilestonesMixin,
    due_date_to_iso,
    parse_milestones,
    spoken_date,
)
from quill.core.github.rest_transport import GitHubRestError, RestResponse

TODAY = dt.date(2026, 11, 7)


class _Provider(GitHubMilestonesMixin):
    def __init__(self, token: str | None = "tok") -> None:
        self._token = token

    def _require_write_access(self, action: str) -> None:
        if not self._token:
            raise GitHubItemsError(f"To {action} you need a signed-in GitHub account.")


class _Api:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any, Any]] = []
        self.replies: dict[tuple[str, str], Any] = {}

    def __call__(self, token, method, path, *, body=None, query=None, **_kw):
        self.calls.append((method, path, query, body))
        reply = self.replies.get((method, path), RestResponse(200, {}, None))
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> _Api:
    fake = _Api()
    monkeypatch.setattr(milestones, "request_json", fake)
    return fake


def _row(**extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "number": 3,
        "title": "Release 2.0",
        "state": "open",
        "open_issues": 5,
        "closed_issues": 8,
        "due_on": "2026-12-12T08:00:00Z",
        "html_url": "https://github.com/o/r/milestone/3",
    }
    row.update(extra)
    return row


def test_a_milestone_reads_as_words() -> None:
    milestone = parse_milestones([_row()])[0]
    assert milestone.label(TODAY) == (
        "Release 2.0: 61 percent done, 5 open, 8 closed, due 12 December"
    )
    empty = GitHubMilestone(1, "Later", state="closed")
    assert empty.summary(TODAY) == (
        "nothing in it yet, 0 open, 0 closed, no due date, closed milestone"
    )


def test_spoken_dates_add_the_year_only_when_it_differs() -> None:
    assert spoken_date("2026-12-12T08:00:00Z", today=TODAY) == "12 December"
    assert spoken_date("2027-01-02", today=TODAY) == "2 January 2027"
    assert spoken_date("", today=TODAY) == ""
    assert spoken_date("garbage!!!", today=TODAY) == ""


def test_due_dates_typed_by_a_person() -> None:
    assert due_date_to_iso(" 2026-12-12 ") == "2026-12-12T08:00:00Z"
    assert due_date_to_iso("") is None
    with pytest.raises(GitHubItemsError, match="2026-12-12"):
        due_date_to_iso("12/12/2026")


def test_list_asks_for_the_state_and_orders_by_due_date(api: _Api) -> None:
    api.replies[("GET", "/repos/o/r/milestones")] = RestResponse(200, {}, [_row()])
    assert _Provider().fetch_milestones("o/r", state="all")[0].number == 3
    assert api.calls[0][2]["state"] == "all"
    assert api.calls[0][2]["sort"] == "due_on"
    with pytest.raises(GitHubItemsError):
        _Provider().fetch_milestones("o/r", state="nope")


def test_create_needs_github_to_send_the_milestone_back(api: _Api) -> None:
    api.replies[("POST", "/repos/o/r/milestones")] = RestResponse(201, {}, _row())
    made = _Provider().create_milestone("o/r", " Release 2.0 ", due_on="2026-12-12T08:00:00Z")
    assert made.title == "Release 2.0"
    assert api.calls[0][3] == {
        "title": "Release 2.0",
        "description": "",
        "due_on": "2026-12-12T08:00:00Z",
    }
    api.replies[("POST", "/repos/o/r/milestones")] = RestResponse(200, {}, None)
    with pytest.raises(GitHubItemsError, match="without confirming"):
        _Provider().create_milestone("o/r", "x")


def test_close_is_only_reported_when_github_shows_it_closed(api: _Api) -> None:
    path = "/repos/o/r/milestones/3"
    api.replies[("PATCH", path)] = RestResponse(200, {}, _row(state="closed"))
    assert _Provider().update_milestone("o/r", 3, state="closed").state == "closed"
    assert api.calls[-1][3] == {"state": "closed"}
    api.replies[("PATCH", path)] = RestResponse(200, {}, _row(state="open"))
    with pytest.raises(GitHubItemsError, match="still shows the milestone open"):
        _Provider().update_milestone("o/r", 3, state="closed")


def test_edit_can_clear_the_due_date(api: _Api) -> None:
    api.replies[("PATCH", "/repos/o/r/milestones/3")] = RestResponse(200, {}, _row(due_on=None))
    _Provider().update_milestone("o/r", 3, title="New", description="d", clear_due=True)
    assert api.calls[-1][3] == {"title": "New", "description": "d", "due_on": None}


def test_writes_need_a_signed_in_account(api: _Api) -> None:
    with pytest.raises(GitHubItemsError, match="signed-in"):
        _Provider(token=None).create_milestone("o/r", "x")
    with pytest.raises(GitHubItemsError, match="signed-in"):
        _Provider(token=None).assign_milestone("o/r", [1], 3)
    assert api.calls == []


def test_batch_milestone_checks_each_reply(api: _Api) -> None:
    api.replies[("PATCH", "/repos/o/r/issues/1")] = RestResponse(200, {}, {"milestone": _row()})
    api.replies[("PATCH", "/repos/o/r/issues/2")] = RestResponse(200, {}, {"milestone": None})
    api.replies[("PATCH", "/repos/o/r/issues/4")] = GitHubRestError("Not Found", status=404)
    errors = _Provider().assign_milestone("o/r", [1, 2, 4], 3)
    assert len(errors) == 2
    assert errors[0].startswith("#2: GitHub did not confirm")
    assert errors[1].startswith("#4: Could not set the milestone")
    assert api.calls[0][3] == {"milestone": 3}


def test_clearing_the_milestone_sends_null(api: _Api) -> None:
    api.replies[("PATCH", "/repos/o/r/issues/1")] = RestResponse(200, {}, {"milestone": None})
    assert _Provider().assign_milestone("o/r", [1], None) == []
    assert api.calls[0][3] == {"milestone": None}


def test_batch_assignees_names_anyone_github_skipped(api: _Api) -> None:
    api.replies[("POST", "/repos/o/r/issues/1/assignees")] = RestResponse(
        201, {}, {"assignees": [{"login": "Jeff"}]}
    )
    errors = _Provider().add_assignees("o/r", [1], ["@jeff", "kelly"])
    assert errors == [
        "#1: GitHub did not assign kelly; they may not have access to this repository."
    ]
    assert api.calls[0][3] == {"assignees": ["jeff", "kelly"]}
    with pytest.raises(GitHubItemsError, match="not a GitHub username"):
        _Provider().add_assignees("o/r", [1], ["bad name!"])
