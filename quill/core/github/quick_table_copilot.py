"""Quick commands for Copilot in an organization and a repository (complete.md 1.3).

Copilot Business is bought by an organization on any GitHub plan, so its seat
and settings routes are the organization's own (``/orgs/{org}/copilot/...``);
nothing here is an enterprise account's (those routes stay out of scope in
the API coverage table, with their reason).

* An organization: **Copilot Plan**, **Copilot Seats**, **A Member's Copilot
  Seat...**, **Give Copilot Seats...**, **Take Copilot Seats Away...**, **Give
  Teams Copilot...**, **Take Copilot from Teams...**, **Copilot Usage
  Report**, **Copilot Agent Access** and **Copilot Content Exclusions**.
* A repository: **Copilot Agent Configuration** and **Copilot Review
  Settings**.

Giving and taking seats change who the organization pays for, so each asks
first with the organization and the people named, and says GitHub's own
count afterwards. Settings GitHub documents only as a request shape the
Workbench has not seen are read here and changed on GitHub's site.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.quick_actions import Ask, Quick, QuickError, bulleted, call, plain

__all__ = ["COPILOT_QUICK"]

_ORG = frozenset({"org"})
_REPO = frozenset({"repo"})
_B = "/orgs/{org}/copilot/billing"
_LIVE = "needs Jeff: an organization with Copilot Business seats to give and take"


def _names(ctx: dict[str, str], key: str) -> list[str]:
    found = [n.strip().lstrip("@") for n in ctx.get(key, "").replace(";", ",").split(",")]
    names = [n for n in found if n]
    if not names:
        raise QuickError("Name at least one, separated by commas.")
    return names


def _plan(data: Any, ctx: dict[str, str]) -> str:
    data = data if isinstance(data, Mapping) else {}
    seats = data.get("seat_breakdown") if isinstance(data.get("seat_breakdown"), Mapping) else {}
    parts = [
        f"{ctx['org']} has {seats.get('total', 0)} Copilot seats: "
        f"{seats.get('active_this_cycle', 0)} used this cycle, "
        f"{seats.get('inactive_this_cycle', 0)} not used, "
        f"{seats.get('pending_invitation', 0)} waiting on an invitation, "
        f"{seats.get('pending_cancellation', 0)} ending."
    ]
    who = data.get("seat_management_setting")
    if who:
        parts.append(f"Who gets a seat: {str(who).replace('_', ' ')}.")
    for key, words in (
        ("public_code_suggestions", "Suggestions matching public code"),
        ("ide_chat", "Chat in the editor"),
        ("platform_chat", "Chat on GitHub"),
        ("cli", "Copilot in the command line"),
        ("plan_type", "Plan"),
    ):
        if data.get(key):
            parts.append(f"{words}: {data[key]}.")
    return " ".join(parts)


def _seat_line(seat: Mapping[str, Any]) -> str:
    found = seat.get("assignee")
    who: Mapping[str, Any] = found if isinstance(found, Mapping) else {}
    name = str(who.get("login") or who.get("slug") or "someone")
    via = seat.get("assigning_team")
    team = f", through the team {via.get('slug')}" if isinstance(via, Mapping) else ""
    last = str(seat.get("last_activity_at") or "")[:10]
    used = f", last used {last}" + (
        f" in {seat['last_activity_editor']}" if seat.get("last_activity_editor") else ""
    )
    ending = seat.get("pending_cancellation_date")
    end = f", ends {ending}" if ending else ""
    return f"{name}{team}{used if last else ', not used yet'}{end}"


def _seats(data: Any, _ctx: dict[str, str]) -> str:
    rows = data.get("seats") if isinstance(data, Mapping) else None
    seats = [s for s in rows or () if isinstance(s, Mapping)]
    total = data.get("total_seats") if isinstance(data, Mapping) else None
    head = (
        f"{total} seats; the first {len(seats)} are listed."
        if total and total != len(seats)
        else ""
    )
    lines = [_seat_line(s) for s in seats]
    return (head + "\n" if head else "") + bulleted(lines, "Nobody has a Copilot seat here.")


def _count(key: str, verb: str) -> Any:
    def said(data: Any, ctx: dict[str, str]) -> str:
        found = data.get(key) if isinstance(data, Mapping) else None
        return f"{verb} {found if found is not None else 'the'} Copilot seats in {ctx['org']}."

    return said


_AGREED = "It is billed to the organization from today."
COPILOT_QUICK: tuple[Quick, ...] = (
    Quick("copilot_plan", "Copilot Plan", ("organization",), _ORG,
          "The organization's Copilot seats, who may have one, and its settings.",
          ("GET /orgs/{org}/copilot/billing",),
          lambda api, ctx: call(api, "GET", _B, ctx), _plan, needs=("org",)),
    Quick("copilot_seats", "Copilot Seats", ("organization",), _ORG,
          "Who has a Copilot seat here, through which team, and when each last used it.",
          ("GET /orgs/{org}/copilot/billing/seats",),
          lambda api, ctx: call(api, "GET", _B + "/seats?per_page=100", ctx), _seats,
          report=True, needs=("org",)),
    Quick("copilot_member_seat", "A Member's Copilot Seat...", ("organization",), _ORG,
          "Whether one member has a Copilot seat here, and when they last used it.",
          ("GET /orgs/{org}/members/{username}/copilot",),
          lambda api, ctx: call(api, "GET", "/orgs/{org}/members/{login}/copilot", ctx),
          lambda data, _ctx: _seat_line(data if isinstance(data, Mapping) else {}),
          asks=(Ask("login", "Their login:"),), needs=("org",)),
    Quick("copilot_add_users", "Give Copilot Seats...", ("organization",), _ORG,
          "Give people Copilot seats in the organization; each is billed to it.",
          ("POST /orgs/{org}/copilot/billing/selected_users",),
          lambda api, ctx: call(api, "POST", _B + "/selected_users", ctx,
                                {"selected_usernames": _names(ctx, "logins")}),
          _count("seats_created", "Gave"), tier="A", need="org:owner",
          asks=(Ask("logins", "Their logins, separated by commas:"),),
          confirm="Give {logins} Copilot seats in {org}? " + _AGREED, needs=("org",), live=_LIVE),
    Quick("copilot_remove_users", "Take Copilot Seats Away...", ("organization",), _ORG,
          "Take people's Copilot seats away; each ends at the close of the billing cycle.",
          ("DELETE /orgs/{org}/copilot/billing/selected_users",),
          lambda api, ctx: call(api, "DELETE", _B + "/selected_users", ctx,
                                {"selected_usernames": _names(ctx, "logins")}),
          _count("seats_cancelled", "Ended"), tier="A", need="org:owner",
          asks=(Ask("logins", "Their logins, separated by commas:"),),
          confirm="Take the Copilot seats of {logins} in {org} away? They keep Copilot until "
                  "the billing cycle ends.", needs=("org",), live=_LIVE),
    Quick("copilot_add_teams", "Give Teams Copilot...", ("organization",), _ORG,
          "Give every member of some teams a Copilot seat; each is billed to the organization.",
          ("POST /orgs/{org}/copilot/billing/selected_teams",),
          lambda api, ctx: call(api, "POST", _B + "/selected_teams", ctx,
                                {"selected_teams": _names(ctx, "teams")}),
          _count("seats_created", "Gave"), tier="A", need="org:owner",
          asks=(Ask("teams", "The teams' names as in their links (slugs), by commas:"),),
          confirm="Give every member of {teams} a Copilot seat in {org}? " + _AGREED,
          needs=("org",), live=_LIVE),
    Quick("copilot_remove_teams", "Take Copilot from Teams...", ("organization",), _ORG,
          "End the Copilot seats that came through some teams.",
          ("DELETE /orgs/{org}/copilot/billing/selected_teams",),
          lambda api, ctx: call(api, "DELETE", _B + "/selected_teams", ctx,
                                {"selected_teams": _names(ctx, "teams")}),
          _count("seats_cancelled", "Ended"), tier="A", need="org:owner",
          asks=(Ask("teams", "The teams' names as in their links (slugs), by commas:"),),
          confirm="End the Copilot seats {teams} gave in {org}? People keep Copilot until the "
                  "billing cycle ends.", needs=("org",), live=_LIVE),
    Quick("copilot_usage", "Copilot Usage Report", ("organization",), _ORG,
          "GitHub's latest 28-day Copilot usage report for the organization, as download links.",
          ("GET /orgs/{org}/copilot/metrics/reports/organization-28-day/latest",),
          lambda api, ctx: call(api, "GET",
                                "/orgs/{org}/copilot/metrics/reports/organization-28-day/latest",
                                ctx),
          lambda data, _ctx: plain(data), report=True, needs=("org",)),
    Quick("copilot_agent_access", "Copilot Agent Access", ("organization",), _ORG,
          "Which of the organization's repositories Copilot's cloud agent may work in.",
          ("GET /orgs/{org}/copilot/coding-agent/permissions",),
          lambda api, ctx: call(api, "GET", "/orgs/{org}/copilot/coding-agent/permissions", ctx),
          lambda data, _ctx: plain(data), needs=("org",)),
    Quick("copilot_content_exclusion", "Copilot Content Exclusions", ("organization",), _ORG,
          "Files Copilot is kept away from in the organization's repositories.",
          ("GET /orgs/{org}/copilot/content_exclusion",),
          lambda api, ctx: call(api, "GET", "/orgs/{org}/copilot/content_exclusion", ctx),
          lambda data, _ctx: plain(data), report=True, needs=("org",)),
    Quick("copilot_agent_config", "Copilot Agent Configuration", ("repository",), _REPO,
          "How Copilot's cloud agent is set up in this repository.",
          ("GET /repos/{owner}/{repo}/copilot/cloud-agent/configuration",),
          lambda api, ctx: call(api, "GET", "/repos/{repo}/copilot/cloud-agent/configuration",
                                ctx),
          lambda data, _ctx: plain(data), report=True, needs=("repo",)),
    Quick("copilot_review_settings", "Copilot Review Settings", ("repository",), _REPO,
          "Whether Copilot reviews pull requests here on its own, and how.",
          ("GET /repos/{owner}/{repo}/copilot/code-review/settings",),
          lambda api, ctx: call(api, "GET", "/repos/{repo}/copilot/code-review/settings", ctx),
          lambda data, _ctx: plain(data), needs=("repo",)),
)  # fmt: skip
