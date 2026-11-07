"""Repository milestones, and the batch milestone and assignee changes (Wave 3).

A milestone reads as one sentence a listener can take in without columns:
"Release 2.0: 62 percent done, 5 open, 8 closed, due 12 December". Creating,
editing and closing a milestone, setting the milestone on several issues, and
adding assignees to several issues all go through
:func:`~quill.core.github.rest_transport.request_json`, and each one is only
reported done when GitHub's reply shows the change.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import (
    GitHubRestError,
    RestResponse,
    request_json,
    rest_failure_message,
)
from quill.core.github.run_actions import repo_path

__all__ = [
    "GitHubMilestone",
    "GitHubMilestonesMixin",
    "due_date_to_iso",
    "parse_milestones",
    "spoken_date",
]

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")


def spoken_date(value: str, *, today: date | None = None) -> str:
    """``2026-12-12T08:00:00Z`` as "12 December", with the year when it is not this year."""
    text = (value or "").strip()
    if len(text) < 10:
        return ""
    try:
        when = date.fromisoformat(text[:10])
    except ValueError:
        return ""
    current = today or datetime.now().date()
    words = f"{when.day} {_MONTHS[when.month - 1]}"
    return words if when.year == current.year else f"{words} {when.year}"


def due_date_to_iso(value: str) -> str | None:
    """``YYYY-MM-DD`` typed by a person as GitHub's due-on timestamp; ``""`` clears it.

    Returns ``None`` for an empty field, meaning no due date.
    """
    text = value.strip()
    if not text:
        return None
    try:
        when = date.fromisoformat(text)
    except ValueError as exc:
        raise GitHubItemsError(
            "Type the due date as year, month and day, like 2026-12-12, or leave it empty."
        ) from exc
    return f"{when.isoformat()}T08:00:00Z"


@dataclass(frozen=True, slots=True)
class GitHubMilestone:
    """A milestone and how far along it is."""

    number: int
    title: str
    state: str = "open"
    description: str = ""
    due_on: str = ""
    open_issues: int = 0
    closed_issues: int = 0
    url: str = ""

    @property
    def percent_done(self) -> int | None:
        """Closed as a whole percent of everything in it, rounded down as GitHub shows it."""
        total = self.open_issues + self.closed_issues
        return None if total == 0 else self.closed_issues * 100 // total

    def summary(self, today: date | None = None) -> str:
        percent = self.percent_done
        parts = [
            "nothing in it yet" if percent is None else f"{percent} percent done",
            f"{self.open_issues} open",
            f"{self.closed_issues} closed",
        ]
        due = spoken_date(self.due_on, today=today)
        parts.append(f"due {due}" if due else "no due date")
        if self.state == "closed":
            parts.append("closed milestone")
        return ", ".join(parts)

    def label(self, today: date | None = None) -> str:
        return f"{self.title}: {self.summary(today)}"


def _int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    return int(value) if isinstance(value, str) and value.isdecimal() else 0


def parse_milestone(row: object) -> GitHubMilestone | None:
    if not isinstance(row, dict) or not _int(row.get("number")):
        return None
    return GitHubMilestone(
        number=_int(row.get("number")),
        title=str(row.get("title") or ""),
        state=str(row.get("state") or "open"),
        description=str(row.get("description") or ""),
        due_on=str(row.get("due_on") or ""),
        open_issues=_int(row.get("open_issues")),
        closed_issues=_int(row.get("closed_issues")),
        url=str(row.get("html_url") or ""),
    )


def parse_milestones(data: object) -> list[GitHubMilestone]:
    rows = data if isinstance(data, list) else []
    return [milestone for row in rows if (milestone := parse_milestone(row)) is not None]


def clean_logins(logins: Sequence[str]) -> tuple[str, ...]:
    """GitHub usernames from a person's comma- or space-separated list."""
    cleaned: list[str] = []
    for raw in logins:
        login = raw.strip().removeprefix("@")
        if not login:
            continue
        if not _LOGIN.match(login):
            raise GitHubItemsError(f"{raw.strip()!r} is not a GitHub username.")
        cleaned.append(login)
    if not cleaned:
        raise GitHubItemsError("Type at least one GitHub username.")
    return tuple(dict.fromkeys(cleaned))


class _MilestoneAccess(Protocol):
    _token: str | None

    def _require_write_access(self, action: str) -> None: ...


def _send(
    provider: _MilestoneAccess,
    action: str,
    method: str,
    path: str,
    *,
    body: dict[str, object] | None = None,
    query: dict[str, str] | None = None,
    expect: tuple[int, ...] = (200,),
) -> RestResponse:
    try:
        response = request_json(provider._token, method, path, body=body, query=query)
    except GitHubRestError as exc:
        raise GitHubItemsError(rest_failure_message(action, exc)) from exc
    if response.status not in expect:
        raise GitHubItemsError(
            f"Could not {action}. GitHub answered HTTP {response.status} without confirming it."
        )
    return response


def _confirmed(response: RestResponse, action: str) -> GitHubMilestone:
    milestone = parse_milestone(response.data)
    if milestone is None:
        raise GitHubItemsError(f"Could not {action}. GitHub did not send the milestone back.")
    return milestone


class GitHubMilestonesMixin:
    """Milestone reads and writes for ``GitHubItemsProvider``."""

    def fetch_milestones(
        self: _MilestoneAccess, full_name: str, *, state: str = "open", limit: int = 100
    ) -> list[GitHubMilestone]:
        if state not in ("open", "closed", "all"):
            raise GitHubItemsError("Choose open, closed or all milestones.")
        response = _send(
            self,
            "list the milestones",
            "GET",
            f"{repo_path(full_name)}/milestones",
            query={
                "state": state,
                "sort": "due_on",
                "direction": "asc",
                "per_page": str(max(1, min(limit, 100))),
            },
        )
        return parse_milestones(response.data)

    def create_milestone(
        self: _MilestoneAccess,
        full_name: str,
        title: str,
        *,
        description: str = "",
        due_on: str | None = None,
    ) -> GitHubMilestone:
        if not title.strip():
            raise GitHubItemsError("A milestone needs a title.")
        self._require_write_access("create a milestone")
        body: dict[str, object] = {"title": title.strip(), "description": description}
        if due_on:
            body["due_on"] = due_on
        response = _send(
            self,
            "create the milestone",
            "POST",
            f"{repo_path(full_name)}/milestones",
            body=body,
            expect=(201,),
        )
        return _confirmed(response, "create the milestone")

    def update_milestone(
        self: _MilestoneAccess,
        full_name: str,
        number: int,
        *,
        title: str | None = None,
        description: str | None = None,
        due_on: str | None = None,
        clear_due: bool = False,
        state: str | None = None,
    ) -> GitHubMilestone:
        """Edit, close (``state="closed"``) or reopen a milestone."""
        if number <= 0:
            raise GitHubItemsError("This milestone has no number.")
        if state not in (None, "open", "closed"):
            raise GitHubItemsError("A milestone is either open or closed.")
        if title is not None and not title.strip():
            raise GitHubItemsError("A milestone needs a title.")
        verb = {"closed": "close", "open": "reopen"}.get(state or "", "edit")
        self._require_write_access(f"{verb} a milestone")
        body: dict[str, object] = {}
        if title is not None:
            body["title"] = title.strip()
        if description is not None:
            body["description"] = description
        if due_on:
            body["due_on"] = due_on
        elif clear_due:
            body["due_on"] = None
        if state is not None:
            body["state"] = state
        action = f"{verb} the milestone"
        milestone = _confirmed(
            _send(
                self,
                action,
                "PATCH",
                f"{repo_path(full_name)}/milestones/{int(number)}",
                body=body,
            ),
            action,
        )
        if state is not None and milestone.state != state:
            raise GitHubItemsError(
                f"Could not {action}. GitHub still shows the milestone {milestone.state}."
            )
        return milestone

    def assign_milestone(
        self: _MilestoneAccess, full_name: str, numbers: Sequence[int], milestone: int | None
    ) -> list[str]:
        """Set (or, with ``None``, clear) the milestone on each issue; returns failures."""
        self._require_write_access("set a milestone")
        errors: list[str] = []
        for number in numbers:
            try:
                response = _send(
                    self,
                    "set the milestone",
                    "PATCH",
                    f"{repo_path(full_name)}/issues/{int(number)}",
                    body={"milestone": milestone},
                )
                data = response.data if isinstance(response.data, dict) else {}
                got = data.get("milestone")
                got_number = _int(got.get("number")) if isinstance(got, dict) else None
                if got_number != milestone:
                    errors.append(f"#{number}: GitHub did not confirm the milestone.")
            except GitHubItemsError as exc:
                errors.append(f"#{number}: {exc.args[0] if exc.args else exc}")
        return errors

    def add_assignees(
        self: _MilestoneAccess, full_name: str, numbers: Sequence[int], logins: Sequence[str]
    ) -> list[str]:
        """Add *logins* as assignees to each issue; returns failures.

        GitHub silently skips a person who cannot be assigned, so each reply is
        checked and anyone missing from it is named in the failure.
        """
        wanted = clean_logins(logins)
        self._require_write_access("add assignees")
        errors: list[str] = []
        for number in numbers:
            try:
                response = _send(
                    self,
                    "add the assignees",
                    "POST",
                    f"{repo_path(full_name)}/issues/{int(number)}/assignees",
                    body={"assignees": list(wanted)},
                    expect=(200, 201),
                )
                data = response.data if isinstance(response.data, dict) else {}
                raw = data.get("assignees")
                rows = raw if isinstance(raw, list) else []
                present = {
                    str(row.get("login", "")).casefold() for row in rows if isinstance(row, dict)
                }
                missing = [login for login in wanted if login.casefold() not in present]
                if missing:
                    errors.append(
                        f"#{number}: GitHub did not assign {', '.join(missing)}; "
                        "they may not have access to this repository."
                    )
            except GitHubItemsError as exc:
                errors.append(f"#{number}: {exc.args[0] if exc.args else exc}")
        return errors
