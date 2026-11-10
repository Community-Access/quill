"""How a list on a sheet reads: one line per person, team, hook or key (GitHub PRD 15.2, 18.3).

Every list on a sheet is a real list whose rows read in full: "kellylford,
person, maintain, direct" or "docs, team, write, through organization". These
renderers turn GitHub's JSON rows into those lines, for the Repository sheet's
pages and for the Access pages, which parse them back with
:func:`quill.core.github.access.parse_row`.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import repo_role
from quill.core.github.sheet_fields import dig
from quill.core.workbench.properties import Value

__all__ = [
    "autolink_row",
    "collaborator_row",
    "hook_row",
    "invitation_row",
    "key_row",
    "rows_of",
    "team_row",
]


def rows_of(key: str, render: Any) -> Any:
    def extract(data: Mapping[str, Any]) -> dict[str, Value]:
        items = data.get("items") if "items" in data else data
        if isinstance(items, Mapping):
            for inner in ("environments", "secrets", "variables", "repositories"):
                if isinstance(items.get(inner), list):
                    items = items[inner]
                    break
        rows = items if isinstance(items, list) else []
        return {key: tuple(render(row) for row in rows if isinstance(row, Mapping))}

    return extract


def collaborator_row(row: Mapping[str, Any]) -> str:
    role = str(row.get("role_name") or repo_role(row.get("permissions")) or "")
    return f"{row.get('login', '')}, person, {role}, direct"


def team_row(row: Mapping[str, Any]) -> str:
    return f"{row.get('slug', '')}, team, {row.get('permission', '')}, through organization"


def invitation_row(row: Mapping[str, Any]) -> str:
    who = dig(row, "invitee", "login") or row.get("email") or ""
    return f"{who}, invited, {row.get('permissions', '')}, pending"


def hook_row(row: Mapping[str, Any]) -> str:
    url = dig(row, "config", "url") or ""
    events = ", ".join(str(e) for e in row.get("events") or ())
    state = "active" if row.get("active") else "inactive"
    return f"{url} ({events}), {state}, id {row.get('id', '')}"


def key_row(row: Mapping[str, Any]) -> str:
    access = "read-only" if row.get("read_only") else "read-write"
    return f"{row.get('title', '')}, {access}, id {row.get('id', '')}"


def autolink_row(row: Mapping[str, Any]) -> str:
    return f"{row.get('key_prefix', '')} to {row.get('url_template', '')}"
