"""Copilot seats and settings for an organization and a repository (complete.md 1.3)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.api_coverage import load_coverage
from quill.core.github.item_actions import GITHUB_ACTIONS
from quill.core.github.permissions import WriteTier
from quill.core.github.quick_actions import QuickError
from quill.core.github.quick_table_copilot import COPILOT_QUICK
from quill.core.github.rest_transport import RestResponse
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS

BY_VERB = {q.verb: q for q in COPILOT_QUICK}


class FakeApi:
    def __init__(self, answer: Any) -> None:
        self.answer, self.sent = answer, []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body, query))
        return RestResponse(200, {}, self.answer)


def test_no_enterprise_route_is_used() -> None:
    for q in COPILOT_QUICK:
        assert all("/enterprises/" not in e for e in q.endpoints), q.verb


def test_every_route_is_covered_by_its_own_command() -> None:
    rest = load_coverage()["rest"]
    for q in COPILOT_QUICK:
        for endpoint in q.endpoints:
            entry = rest[endpoint]
            assert entry.status == "covered" and entry.home == f"command:github.workbench.{q.verb}"


def test_seat_changes_are_access_writes_for_an_owner_and_ask_first() -> None:
    for verb in ("copilot_add_users", "copilot_remove_users", "copilot_add_teams",
                 "copilot_remove_teams"):  # fmt: skip
        assert COMMAND_REQUIREMENTS[f"github.workbench.{verb}"] == ("org:owner", WriteTier.ACCESS)
        assert BY_VERB[verb].confirm and "{org}" in BY_VERB[verb].confirm
    org_rows = {r.command_id for r in GITHUB_ACTIONS.rows_for("organization")}
    assert "github.workbench.copilot_seats" in org_rows


def test_giving_seats_sends_the_logins_and_says_githubs_count() -> None:
    q = BY_VERB["copilot_add_users"]
    api = FakeApi({"seats_created": 2})
    ctx = {"org": "acme", "logins": "@ann, bob ,"}
    said = q.said(q.run(api, ctx), ctx)
    assert api.sent == [
        ("POST", "/orgs/acme/copilot/billing/selected_users",
         {"selected_usernames": ["ann", "bob"]}, None),
    ]  # fmt: skip
    assert said == "Gave 2 Copilot seats in acme."
    with pytest.raises(QuickError):
        q.run(api, {"org": "acme", "logins": " , "})


def test_taking_seats_away_uses_delete_with_the_logins() -> None:
    q = BY_VERB["copilot_remove_users"]
    api = FakeApi({"seats_cancelled": 1})
    ctx = {"org": "acme", "logins": "ann"}
    assert q.said(q.run(api, ctx), ctx) == "Ended 1 Copilot seats in acme."
    assert api.sent[0][:3] == (
        "DELETE",
        "/orgs/acme/copilot/billing/selected_users",
        {"selected_usernames": ["ann"]},
    )


def test_the_plan_and_seats_read_as_sentences() -> None:
    plan = BY_VERB["copilot_plan"]
    data = {
        "seat_breakdown": {"total": 5, "active_this_cycle": 3, "inactive_this_cycle": 2},
        "seat_management_setting": "assign_selected",
        "public_code_suggestions": "block",
    }
    said = plan.said(data, {"org": "acme"})
    assert said.startswith("acme has 5 Copilot seats: 3 used this cycle, 2 not used,")
    assert "Who gets a seat: assign selected." in said
    seats = BY_VERB["copilot_seats"]
    rows = {
        "total_seats": 2,
        "seats": [
            {"assignee": {"login": "ann"}, "last_activity_at": "2026-11-01T00:00:00Z",
             "last_activity_editor": "vscode", "assigning_team": {"slug": "devs"}},
            {"assignee": {"login": "bob"}, "pending_cancellation_date": "2026-12-01"},
        ],
    }  # fmt: skip
    assert seats.said(rows, {}) == (
        "ann, through the team devs, last used 2026-11-01 in vscode\n"
        "bob, not used yet, ends 2026-12-01"
    )
    assert seats.said({"seats": []}, {}) == "Nobody has a Copilot seat here."
