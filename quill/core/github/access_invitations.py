"""Pending invitations on an Access page: cancel one, or change its role (GH-R-063).

A repository's and an organization's Access pages list who has been invited
and not yet answered. GitHub lets the inviter cancel an invitation, and change
the role a repository invitation offers, but its list names the invitation by
number, so these helpers find the number from the row's login or email and
plan the one request, previewed in words like every other access change
(:mod:`quill.core.github.access`).

An organization invitation's role cannot be changed in place: cancel it and
invite again.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.github.access import AccessChange
from quill.core.github.permissions import WriteTier

__all__ = [
    "find_invitation",
    "invitations_path",
    "plan_cancel_invitation",
    "plan_invitation_role",
]


def invitations_path(scope: str, ident: Mapping[str, str]) -> str:
    """Where the scope's pending invitations are listed; empty when GitHub has none."""
    if scope == "repository":
        return f"/repos/{ident['repo']}/invitations"
    if scope == "organization":
        return f"/orgs/{ident['org']}/invitations"
    return ""


def _who(raw: Mapping[str, Any]) -> str:
    invitee = raw.get("invitee")
    login = invitee.get("login") if isinstance(invitee, Mapping) else raw.get("login")
    return str(login or raw.get("email") or "")


def find_invitation(found: Sequence[Mapping[str, Any]], who: str) -> int | None:
    """The number of the invitation for *who* (a login or an email), if it is pending."""
    wanted = who.strip().lstrip("@").casefold()
    for raw in found:
        if isinstance(raw, Mapping) and _who(raw).casefold() == wanted:
            number = raw.get("id")
            if isinstance(number, int) and not isinstance(number, bool):
                return number
    return None


def plan_cancel_invitation(
    scope: str, ident: Mapping[str, str], number: int, who: str
) -> AccessChange:
    """Cancel *who*'s invitation; they can be invited again afterwards."""
    where = ident.get("repo") or ident.get("org", "")
    return AccessChange(
        "DELETE",
        f"{invitations_path(scope, ident)}/{number}",
        None,
        f"Cancel the invitation to {who} for {where}. They can be invited again.",
        WriteTier.ACCESS,
    )


def plan_invitation_role(
    ident: Mapping[str, str], number: int, who: str, role: str
) -> AccessChange:
    """Change the role a repository invitation offers, before it is answered."""
    repo = ident["repo"]
    return AccessChange(
        "PATCH",
        f"/repos/{repo}/invitations/{number}",
        {"permissions": role},  # this route takes read and write, not pull and push
        f"Change the invitation to {who} for {repo} to {role} access.",
        WriteTier.ACCESS,
    )
