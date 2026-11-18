"""Invitations to repositories: see them, accept or decline (GitHub PRD 14.1).

Until now an invitation reached QUILL only as a notification. Needs My
Attention > Invitations lists every repository you have been invited to
(``GET /user/repository_invitations``), who invited you and with what access,
and Accept (``PATCH``) or Decline (``DELETE``) answers one.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.workbench_api import GitHubApi

__all__ = ["ACCESS_WORDS", "accept", "decline", "fetch_invitations", "invitation_row"]

#: GitHub's permission names, as the access the invitation gives.
ACCESS_WORDS: dict[str, str] = {
    "read": "read",
    "triage": "triage",
    "write": "write",
    "maintain": "maintain",
    "admin": "admin",
}


def invitation_row(raw: Mapping[str, Any]) -> ExploreRow:
    repo = raw.get("repository") or {}
    name = str(repo.get("full_name") or "") if isinstance(repo, Mapping) else ""
    inviter = raw.get("inviter") or {}
    who = str(inviter.get("login") or "someone") if isinstance(inviter, Mapping) else "someone"
    access = ACCESS_WORDS.get(str(raw.get("permissions") or ""), str(raw.get("permissions") or ""))
    when = str(raw.get("created_at") or "")[:10]
    expired = bool(raw.get("expired"))
    label = f"{name}: {who} invited you, {access} access" + (", expired" if expired else "")
    detail = f"Invitation to {name}, from {who}, for {access} access, on {when}." + (
        " It has expired; ask for a new one." if expired else " Accept or Decline answers it."
    )
    url = str(raw.get("html_url") or "")
    return ExploreRow(label, detail, url, name, "invitation", str(raw.get("id") or ""), when, name)


def fetch_invitations(api: GitHubApi, *, limit: int = 100) -> list[ExploreRow]:
    rows: list[ExploreRow] = []
    page = 1
    while len(rows) < limit:
        data = api.rest(
            "GET", "/user/repository_invitations", query={"per_page": "100", "page": str(page)}
        ).data
        found = [row for row in (data or []) if isinstance(row, Mapping)]
        rows.extend(invitation_row(row) for row in found)
        if len(found) < 100:
            break
        page += 1
    return rows[:limit]


def accept(api: GitHubApi, invitation_id: str, repository: str) -> str:
    api.rest("PATCH", f"/user/repository_invitations/{int(invitation_id)}")
    return f"Accepted. You can now work in {repository}."


def decline(api: GitHubApi, invitation_id: str, repository: str) -> str:
    api.rest("DELETE", f"/user/repository_invitations/{int(invitation_id)}")
    return f"Declined the invitation to {repository}."
