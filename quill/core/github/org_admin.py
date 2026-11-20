"""An organization's roles and rulesets, read and changed (GitHub PRD 18.3.1 and 18.6).

Two things an organization owner keeps coming back to, kept apart from the
Organization sheet because both are lists you act on rather than values you
edit:

* **Roles.** GitHub's organization roles (All-repository read, write, triage,
  maintain and admin, the security manager, the app manager, and any custom
  role) and who holds each one, people and teams. A role is given to a person
  or a team, taken from one, or every role is taken from one at once.
* **Rulesets.** The organization's rulesets, which apply across its
  repositories: each one read in plain words (:func:`rulesets.summary`), its
  enforcement changed (Active, Evaluate or Disabled), its history of changes,
  the recent pushes it judged (rule insights), and deleting it.

Every write needs an owner's sign-in with the ``admin:org`` scope; GitHub says
so when it is missing and that sentence is passed on. wx-free and
strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.github import rulesets as ruleset_words
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import (
    GitHubRestError,
    RestResponse,
    request_json,
    rest_failure_message,
)

__all__ = [
    "ENFORCEMENTS",
    "INSIGHT_PERIODS",
    "GitHubOrgAdmin",
    "Holder",
    "Role",
    "RulesetRow",
]

#: Ruleset enforcement: GitHub's word, then what a person hears.
ENFORCEMENTS: tuple[tuple[str, str], ...] = (
    ("active", "Active: the rules are enforced"),
    ("evaluate", "Evaluate: report what would be blocked, block nothing"),
    ("disabled", "Disabled: the rules do nothing"),
)

#: Rule insights' time periods, GitHub's word then the words.
INSIGHT_PERIODS: tuple[tuple[str, str], ...] = (
    ("day", "The last day"),
    ("week", "The last week"),
    ("month", "The last month"),
)

_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,98})$")


def _part(value: str, what: str) -> str:
    text = value.strip().lstrip("@")
    if not _NAME.match(text):
        raise GitHubItemsError(f"{value!r} is not a GitHub {what}.")
    return text


@dataclass(frozen=True, slots=True)
class Role:
    """One organization role."""

    id: int
    name: str
    description: str = ""
    base_role: str = ""

    def label(self) -> str:
        base = f", based on {self.base_role}" if self.base_role else ""
        about = f": {self.description}" if self.description else ""
        return f"{self.name}{base}{about}"


@dataclass(frozen=True, slots=True)
class Holder:
    """A person or team holding a role. ``how`` is direct, indirect or mixed."""

    kind: str  # "person" or "team"
    name: str  # login or team slug
    how: str = "direct"
    through: tuple[str, ...] = ()

    def label(self) -> str:
        kind = "Person" if self.kind == "person" else "Team"
        if self.how == "indirect" and self.through:
            return f"{kind}: {self.name}, through {', '.join(self.through)}"
        if self.how == "mixed" and self.through:
            return f"{kind}: {self.name}, directly and through {', '.join(self.through)}"
        return f"{kind}: {self.name}"


@dataclass(frozen=True, slots=True)
class RulesetRow:
    """One organization ruleset, as its list row reads."""

    id: int
    name: str
    target: str
    enforcement: str

    def label(self) -> str:
        said = dict(ENFORCEMENTS).get(self.enforcement, self.enforcement).split(":", 1)[0]
        return f"{self.name}: {said}, on {self.target or 'branch'}es"


class GitHubOrgAdmin:
    """Read and change one organization's roles and rulesets."""

    def __init__(
        self, token: str | None, request: Callable[..., RestResponse] = request_json
    ) -> None:
        self._token = token
        self._request = request

    def _call(self, action: str, method: str, path: str, expect: tuple[int, ...], **kw: Any) -> Any:
        try:
            response = self._request(self._token, method, path, **kw)
        except GitHubRestError as exc:
            raise GitHubItemsError(rest_failure_message(action, exc)) from exc
        if response.status not in expect:
            raise GitHubItemsError(
                f"Could not {action}. GitHub answered HTTP {response.status} without confirming it."
            )
        return response.data

    def _write(self, action: str) -> None:
        if not self._token:
            raise GitHubItemsError(
                f"To {action} you need a signed-in GitHub account; "
                "the anonymous viewer is read-only."
            )

    @staticmethod
    def _org(org: str) -> str:
        return "/orgs/" + _part(org, "organization")

    # -- roles -----------------------------------------------------------------------

    def roles(self, org: str) -> list[Role]:
        data = self._call(
            "read the organization's roles", "GET", self._org(org) + "/organization-roles", (200,)
        )
        rows = data.get("roles", []) if isinstance(data, Mapping) else []
        return [
            Role(
                int(r.get("id") or 0),
                str(r.get("name") or ""),
                str(r.get("description") or ""),
                str(r.get("base_role") or ""),
            )
            for r in rows
            if isinstance(r, Mapping)
        ]

    def holders(self, org: str, role: Role) -> list[Holder]:
        base = f"{self._org(org)}/organization-roles/{int(role.id)}"
        query = {"per_page": "100"}
        people = self._call(
            f"read who holds {role.name}", "GET", base + "/users", (200,), query=query
        )
        teams = self._call(
            f"read who holds {role.name}", "GET", base + "/teams", (200,), query=query
        )

        def through(row: Mapping[str, Any]) -> tuple[str, ...]:
            return tuple(
                str(t.get("slug") or t.get("name") or "")
                for t in row.get("inherited_from") or ()
                if isinstance(t, Mapping)
            )

        found = [
            Holder(
                "person",
                str(p.get("login") or ""),
                str(p.get("assignment") or "direct"),
                through(p),
            )
            for p in people or ()
            if isinstance(p, Mapping)
        ]
        found += [
            Holder(
                "team", str(t.get("slug") or ""), str(t.get("assignment") or "direct"), through(t)
            )
            for t in teams or ()
            if isinstance(t, Mapping)
        ]
        return found

    def _holder_path(self, org: str, kind: str, name: str) -> str:
        if kind == "person":
            return f"{self._org(org)}/organization-roles/users/{_part(name, 'username')}"
        return f"{self._org(org)}/organization-roles/teams/{_part(name, 'team')}"

    def assign(self, org: str, kind: str, name: str, role: Role) -> None:
        action = f"give {name} the {role.name} role"
        self._write(action)
        self._call(action, "PUT", f"{self._holder_path(org, kind, name)}/{int(role.id)}", (204,))

    def unassign(self, org: str, kind: str, name: str, role: Role) -> None:
        action = f"take the {role.name} role from {name}"
        self._write(action)
        self._call(action, "DELETE", f"{self._holder_path(org, kind, name)}/{int(role.id)}", (204,))

    def unassign_all(self, org: str, kind: str, name: str) -> None:
        action = f"take every organization role from {name}"
        self._write(action)
        self._call(action, "DELETE", self._holder_path(org, kind, name), (204,))

    # -- rulesets --------------------------------------------------------------------

    def rulesets(self, org: str) -> list[RulesetRow]:
        data = self._call(
            "read the organization's rulesets",
            "GET",
            self._org(org) + "/rulesets",
            (200,),
            query={"per_page": "100"},
        )
        return [
            RulesetRow(
                int(r.get("id") or 0),
                str(r.get("name") or ""),
                str(r.get("target") or "branch"),
                str(r.get("enforcement") or ""),
            )
            for r in data or ()
            if isinstance(r, Mapping)
        ]

    def ruleset_summary(self, org: str, ruleset: RulesetRow) -> str:
        data = self._call(
            f"read the {ruleset.name} ruleset",
            "GET",
            f"{self._org(org)}/rulesets/{int(ruleset.id)}",
            (200,),
        )
        whole = data if isinstance(data, Mapping) else {}
        return ruleset_words.summary(whole)  # names the repositories it covers, too

    def set_enforcement(self, org: str, ruleset: RulesetRow, enforcement: str) -> None:
        if enforcement not in dict(ENFORCEMENTS):
            raise GitHubItemsError(f"{enforcement!r} is not a ruleset enforcement.")
        action = f"change the {ruleset.name} ruleset"
        self._write(action)
        self._call(
            action,
            "PUT",
            f"{self._org(org)}/rulesets/{int(ruleset.id)}",
            (200,),
            body={"enforcement": enforcement},
        )

    def delete_ruleset(self, org: str, ruleset: RulesetRow) -> None:
        action = f"delete the {ruleset.name} ruleset"
        self._write(action)
        self._call(action, "DELETE", f"{self._org(org)}/rulesets/{int(ruleset.id)}", (204,))

    def history(self, org: str, ruleset: RulesetRow) -> list[str]:
        data = self._call(
            f"read the history of {ruleset.name}",
            "GET",
            f"{self._org(org)}/rulesets/{int(ruleset.id)}/history",
            (200,),
            query={"per_page": "100"},
        )
        lines = []
        for version in data or ():
            if not isinstance(version, Mapping):
                continue
            actor = version.get("actor") or {}
            who = f"{actor.get('type') or 'someone'} {actor.get('id') or ''}".strip()
            lines.append(
                f"Version {version.get('version_id')}: changed {version.get('updated_at')} by {who}"
            )
        return lines

    def insights(self, org: str, period: str = "day") -> list[str]:
        if period not in dict(INSIGHT_PERIODS):
            raise GitHubItemsError(f"{period!r} is not a time period GitHub offers.")
        data = self._call(
            "read rule insights",
            "GET",
            self._org(org) + "/rulesets/rule-suites",
            (200,),
            query={"time_period": period, "per_page": "100"},
        )
        words = {"pass": "passed", "fail": "blocked", "bypass": "bypassed"}
        lines = []
        for suite in data or ():
            if not isinstance(suite, Mapping):
                continue
            result = words.get(str(suite.get("result")), str(suite.get("result") or ""))
            ref = str(suite.get("ref") or "").removeprefix("refs/heads/")
            lines.append(
                f"{result.capitalize()}: {suite.get('actor_name') or 'someone'} pushed to "
                f"{suite.get('repository_name') or ''} {ref}, {suite.get('pushed_at') or ''}"
            )
        return lines
