"""People > Users, the rest: others' application passwords, sign out everywhere, invites (WP-G).

What WordPress's REST API offers, used; what it does not, said:

- **Another person's application passwords** are at
  ``wp/v2/users/{id}/application-passwords``, which WordPress answers only for
  someone allowed to edit that user (``edit_user``, the ``edit_users``
  capability on a single site). Your own are in People > Application Passwords.
- **Sessions** are not in core REST at all: WordPress keeps sign-in sessions in
  user meta it does not expose, so there is no list of them and no route that
  ends them. Sign Out Everywhere opens the person's wp-admin screen, where Log
  Out Everywhere (Log Out Everywhere Else on your own profile) is one button,
  and says so first (:func:`sign_out_pointer`).
- **Invite from a spreadsheet**: a CSV of email, role and name becomes a
  previewed batch of ``POST wp/v2/users``. REST makes the account but sends no
  email, so each new person is given a long random password nobody sees, and
  Send Password Reset on their row sends them the link to choose their own.

Wx-free and network-free except :func:`send_invites` and :func:`existing_people`,
which go through the site's own client.
"""

from __future__ import annotations

import csv
import io
import re
import secrets
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import friendly_date
from quill.core.wordpress.workbench_permissions import ROLE_ORDER

__all__ = [
    "INVITE_NOTE",
    "SESSIONS_NOTE",
    "Invite",
    "InvitePlan",
    "existing_people",
    "invite_body",
    "parse_invites",
    "password_lines",
    "passwords_refusal",
    "preview_lines",
    "send_invites",
    "sign_out_pointer",
]

SESSIONS_NOTE = (
    "WordPress keeps sign-in sessions out of its REST API: there is no route that lists them "
    "or ends them."
)

INVITE_NOTE = (
    "WordPress's REST API makes each account but sends no email. Each person gets a long "
    "random password nobody sees; Send Password Reset on their row sends them the link to "
    "choose their own."
)

_EMAIL = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")
_ROLE_WORDS = {role: role for role in ROLE_ORDER}


# -- sessions ----------------------------------------------------------------------


def sign_out_pointer(
    site_url: str, user_id: int, name: str, *, yourself: bool = False
) -> tuple[str, str]:
    """(the wp-admin address, the sentence) for signing *name* out everywhere."""
    base = (site_url or "").rstrip("/")
    if yourself:
        address = f"{base}/wp-admin/profile.php" if base else ""
        button = "Log Out Everywhere Else"
        whose = "your profile"
    else:
        address = f"{base}/wp-admin/user-edit.php?user_id={int(user_id)}" if base else ""
        button = "Log Out Everywhere"
        whose = f"{name}'s screen"
    sentence = (
        f"{SESSIONS_NOTE} So the Workbench opens {whose} in wp-admin, where {button} is one "
        "button near the bottom, under Sessions."
    )
    return address, sentence


# -- others' application passwords -------------------------------------------------


def passwords_refusal(account: Any, user_id: int, name: str, site: str) -> str:
    """Why *account* may not read *name*'s application passwords ("" when it may)."""
    if account is None or int(getattr(account, "id", 0) or 0) == int(user_id):
        return ""
    if account.can("edit_users"):
        return ""
    return (
        f"WordPress shows {name}'s application passwords only to someone who may edit them, "
        f"the edit_users capability, which your role on {site} does not have."
    )


def password_lines(passwords: Sequence[Any]) -> list[str]:
    """One line per password: its name, when it was made and when it was last used."""
    lines = []
    for pw in passwords:
        made = friendly_date(pw.created) if pw.created else "date not given"
        used = f"last used {friendly_date(pw.last_used)}" if pw.last_used else "never used"
        lines.append(f"{pw.name or 'Unnamed'}, made {made}, {used}")
    return lines


# -- invites -------------------------------------------------------------------------


@dataclass(frozen=True)
class Invite:
    """One person to add: from one spreadsheet row."""

    line: int
    email: str
    role: str
    name: str
    username: str


@dataclass
class InvitePlan:
    """The rows that will be sent, and the rows that will not, each with why."""

    invites: list[Invite] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def _role(text: str) -> str:
    word = text.strip().casefold()
    if not word:
        return "subscriber"
    return _ROLE_WORDS.get(word, "")


def _username(email: str, taken: set[str]) -> str:
    base = re.sub(r"[^a-z0-9._-]+", "", email.split("@", 1)[0].casefold()) or "member"
    name, number = base, 2
    while name in taken:
        name, number = f"{base}{number}", number + 1
    taken.add(name)
    return name


def _columns(header: Sequence[str]) -> dict[str, int] | None:
    words = [cell.strip().casefold() for cell in header]
    if "email" not in words and "e-mail" not in words:
        return None
    found = {"email": words.index("email") if "email" in words else words.index("e-mail")}
    for key, names in (("role", ("role",)), ("name", ("name", "display name", "full name"))):
        for name in names:
            if name in words:
                found[key] = words.index(name)
                break
    return found


def parse_invites(
    text: str,
    *,
    existing_emails: Iterable[str] = (),
    existing_usernames: Iterable[str] = (),
) -> InvitePlan:
    """The invites in a CSV of email, role and name (a header row is optional)."""
    plan = InvitePlan()
    rows = [r for r in csv.reader(io.StringIO(text.lstrip("﻿"))) if any(c.strip() for c in r)]
    if not rows:
        plan.problems.append("The file has no rows.")
        return plan
    columns = _columns(rows[0])
    start = 1 if columns is not None else 0
    columns = columns or {"email": 0, "role": 1, "name": 2}
    known = {e.casefold() for e in existing_emails}
    taken = {u.casefold() for u in existing_usernames}
    seen: set[str] = set()
    for number, row in enumerate(rows[start:], start=start + 1):

        def cell(key: str, row: list[str] = row) -> str:
            index = columns.get(key, -1)
            return row[index].strip() if 0 <= index < len(row) else ""

        email = cell("email")
        if not _EMAIL.match(email):
            plan.problems.append(f"Row {number}: {email or 'no email'} is not an email address.")
            continue
        if email.casefold() in known:
            plan.problems.append(f"Row {number}: {email} already has an account on the site.")
            continue
        if email.casefold() in seen:
            plan.problems.append(f"Row {number}: {email} is in the file twice; the first is used.")
            continue
        role = _role(cell("role"))
        if not role:
            plan.problems.append(
                f"Row {number}: {cell('role')} is not a role. Use one of "
                f"{', '.join(r.title() for r in ROLE_ORDER)}."
            )
            continue
        seen.add(email.casefold())
        plan.invites.append(Invite(number, email, role, cell("name"), _username(email, taken)))
    return plan


def preview_lines(plan: InvitePlan) -> list[str]:
    """What the preview shows: every person to add, then every row left out and why."""
    lines = [
        f"Add {i.name or i.email} as {i.role.title()}, signing in as {i.username}, {i.email}"
        for i in plan.invites
    ]
    return lines + [f"Left out. {problem}" for problem in plan.problems]


def invite_body(invite: Invite) -> dict[str, Any]:
    """The ``POST wp/v2/users`` body: a random password, because REST requires one."""
    body: dict[str, Any] = {
        "username": invite.username,
        "email": invite.email,
        "roles": [invite.role],
        "password": secrets.token_urlsafe(24),
    }
    if invite.name:
        body["name"] = invite.name
        first, _sep, last = invite.name.partition(" ")
        body["first_name"], body["last_name"] = first, last
    return body


def existing_people(api: WordPressApi) -> tuple[set[str], set[str]]:
    """Every email and username already on the site, so the preview can leave them out."""
    emails: set[str] = set()
    names: set[str] = set()
    for raw in api.iter_collection(
        "wp/v2/users",
        {"context": "edit", "_fields": "id,email,username"},
        per_page=100,
        max_pages=50,
    ):
        if isinstance(raw, Mapping):
            emails.add(str(raw.get("email", "") or "").casefold())
            names.add(str(raw.get("username", "") or "").casefold())
    emails.discard("")
    names.discard("")
    return emails, names


def send_invites(api: WordPressApi, invites: Sequence[Invite]) -> list[tuple[Invite, str]]:
    """Each invite sent; its outcome is "" when the account was made, else why not."""
    results: list[tuple[Invite, str]] = []
    for invite in invites:
        try:
            api.post("wp/v2/users", invite_body(invite))
        except WordPressApiError as exc:
            results.append((invite, exc.plain or "the site refused it"))
        else:
            results.append((invite, ""))
    return results
