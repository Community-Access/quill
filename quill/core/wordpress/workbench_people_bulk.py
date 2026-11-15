"""People in the Workbench, the rest of wp-admin's Users screens (wordpress.md 9.18, package 5).

Built on :mod:`~quill.core.wordpress.workbench_people` and its guards in
:mod:`~quill.core.wordpress.workbench_permissions`, which this calls rather
than repeats:

- **Change Role and Remove on many people** (:func:`role_plan`,
  :func:`remove_plan`): each person is checked in turn against the site's list
  *as it would be after the ones before*, so a batch can never take away the
  last Administrator two at a time, nor your own role or account. The preview
  names who is left out and why; the send gives one result per person.
- **Add New, the whole form** (:data:`NEW_USER_SHEET`, :func:`new_user_body`):
  username, email, first and last name, display name, website, language and
  role, as ``POST wp/v2/users``. WordPress's REST API sends no email, so there
  is no "Send the new user an email" box: each person gets a long random
  password nobody sees, and Send Password Reset on their row (which opens
  wp-admin, because REST has no route for it either) sends the link.
- **Set New Password** (:func:`set_password`): wp-admin's Set New Password,
  through ``POST wp/v2/users/{id}`` with ``password``. The value is sent once;
  it is never announced, logged or kept, and it is not in any repr.

Wx-free; only :func:`change_roles`, :func:`remove_each` and
:func:`set_password` reach the network, through the site's own client.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.wordpress import site_admin as admin
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import Account
from quill.core.wordpress.workbench_edit import EditRefused
from quill.core.wordpress.workbench_permissions import (
    ROLE_ORDER,
    remove_problem,
    role_change_problem,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec

__all__ = [
    "NEW_USER_SHEET",
    "NO_EMAIL_NOTE",
    "PASSWORD_NOTE",
    "change_roles",
    "new_user_body",
    "new_user_preview",
    "password_problem",
    "plan_lines",
    "remove_each",
    "remove_plan",
    "role_plan",
    "set_password",
    "user_post_count",
]

NO_EMAIL_NOTE = (
    "WordPress's REST API makes the account but sends no email, so there is no choice to send "
    "one. They get a long random password nobody sees; Send Password Reset on their row opens "
    "wp-admin, where one button emails them the link to choose their own."
)

PASSWORD_NOTE = (
    "The password is shown as text, the way wp-admin shows the one it suggests, so you can read "
    "or copy it. QUILL sends it once and never says it, logs it or keeps it."
)

_ROLE_WORDS = dict(admin.ROLES)


def _f(
    key: str, label: str, help_text: str, kind: FieldKind = FieldKind.TEXT, **kw: Any
) -> FieldSpec:
    return FieldSpec(key, label, kind, help=help_text, **kw)


NEW_USER_SHEET = SheetSpec(
    "new_user",
    "New Person",
    (
        PageSpec(
            "general",
            "General",
            (
                _f(
                    "username",
                    "Username",
                    "The name they sign in with. It cannot be changed later.",
                ),
                _f(
                    "email", "Email", "Where WordPress can reach them. Two people cannot share one."
                ),
                _f("first_name", "First name", "Optional."),
                _f("last_name", "Last name", "Optional."),
                _f("name", "Display name", "The name shown on what they write. Optional."),
                _f("url", "Website", "Their own web address. Optional."),
                _f(
                    "locale",
                    "Language",
                    "A WordPress language code such as en_US or fr_FR, for their wp-admin. "
                    "Empty uses the site's language.",
                ),
            ),
        ),
        PageSpec(
            "role",
            "Role",
            (
                _f(
                    "roles",
                    "Role",
                    "What they may do on the site. " + NO_EMAIL_NOTE,
                    FieldKind.CHOICE,
                    choices=ROLE_ORDER,
                ),
            ),
        ),
    ),
)
"""wp-admin's Add New User, as a sheet; saving it previews and then sends."""


def new_user_body(values: Mapping[str, object]) -> dict[str, Any]:
    """The ``POST wp/v2/users`` body for the sheet's *values*. Raises :class:`EditRefused`."""
    text = {
        key: str(values.get(key, "") or "").strip()
        for key in ("username", "email", "first_name", "last_name", "name", "url", "locale")
    }
    if not text["username"]:
        raise EditRefused("A new person needs a username: the name they sign in with.")
    if "@" not in text["email"] or text["email"].startswith("@") or text["email"].endswith("@"):
        raise EditRefused("A new person needs an email address WordPress can reach them at.")
    role = str(values.get("roles", "") or "subscriber")
    if role not in ROLE_ORDER:
        raise EditRefused(f"{role} is not a role this site has.")
    body: dict[str, Any] = {k: v for k, v in text.items() if v}
    body["roles"] = [role]
    body["password"] = admin.generated_password()
    return body


def new_user_preview(body: Mapping[str, Any], site: str) -> str:
    """The sentence before Add: who, on which site, as what, and that no email goes."""
    name = body.get("name") or " ".join(
        str(body.get(k, "")) for k in ("first_name", "last_name") if body.get(k)
    )
    who = f"{name} ({body['username']})" if name else str(body["username"])
    role = _ROLE_WORDS.get(str(body["roles"][0]), str(body["roles"][0]))
    return f"Add {who}, {body['email']}, to {site} as {role}? {NO_EMAIL_NOTE}"


def _users_after(
    users: Sequence[Mapping[str, object]], user_id: int, roles: list[str]
) -> list[dict[str, object]]:
    return [
        {**dict(u), "roles": roles} if int(str(u.get("id", 0) or 0)) == user_id else dict(u)
        for u in users
    ]


def role_plan(
    account: Account, rows: Sequence[WbRow], role: str, users: Sequence[Mapping[str, object]]
) -> list[tuple[WbRow, str]]:
    """Each person with why they are left out ("" when they will change), checked in turn."""
    current = [dict(u) for u in users]
    plan: list[tuple[WbRow, str]] = []
    for row in rows:
        if row.status == role:
            plan.append((row, f"already {_ROLE_WORDS.get(role, role)}"))
            continue
        problem = role_change_problem(account, row.object_id, role, current)
        plan.append((row, problem))
        if not problem:
            current = _users_after(current, row.object_id, [role])
    return plan


def remove_plan(
    account: Account, rows: Sequence[WbRow], reassign: int, users: Sequence[Mapping[str, object]]
) -> list[tuple[WbRow, str]]:
    """Each person with why they cannot be removed ("" when they can), checked in turn."""
    current = [dict(u) for u in users]
    plan: list[tuple[WbRow, str]] = []
    for row in rows:
        problem = remove_problem(account, row.object_id, current)
        if not problem and row.object_id == reassign:
            problem = "they are the one chosen to receive the posts"
        plan.append((row, problem))
        if not problem:
            current = [u for u in current if int(str(u.get("id", 0) or 0)) != row.object_id]
    return plan


def plan_lines(plan: Sequence[tuple[WbRow, str]]) -> tuple[list[WbRow], list[str]]:
    """The people who will change, and a line for each left out."""
    going = [row for row, problem in plan if not problem]
    left = [f"{row.title}: {problem}" for row, problem in plan if problem]
    return going, left


def change_roles(
    api: WordPressApi, rows: Sequence[WbRow], role: str
) -> tuple[list[WbRow], list[str]]:
    """``roles: [role]`` for each person; the ones changed, and why each other was not."""
    changed: list[WbRow] = []
    failed: list[str] = []
    for row in rows:
        try:
            admin.update_user(api, row.object_id, roles=[role])
        except WordPressApiError as exc:
            failed.append(f"{row.title}: {exc.plain}")
            continue
        changed.append(row)
    return changed, failed


def remove_each(
    api: WordPressApi, rows: Sequence[WbRow], reassign: int
) -> tuple[list[WbRow], list[str]]:
    """Remove each person, their content to *reassign*: removed, and why each other was not."""
    if not reassign:
        raise EditRefused("Choose who gets these people's posts before removing them.")
    removed: list[WbRow] = []
    failed: list[str] = []
    for row in rows:
        try:
            admin.delete_user(api, row.object_id, reassign)
        except WordPressApiError as exc:
            failed.append(f"{row.title}: {exc.plain}")
            continue
        removed.append(row)
    return removed, failed


def password_problem(password: str) -> str:
    """Why *password* will not be sent ("" when it will): empty, short, or padded."""
    if not password:
        return "Type a password, or keep the strong one offered."
    if password != password.strip():
        return "The password starts or ends with a space, which is easy to lose. Take it out."
    if len(password) < 12:
        return "Use at least 12 characters; the one offered is 24."
    return ""


def set_password(api: WordPressApi, user: int | str, password: str) -> None:
    """Send a new sign-in password for *user* (an id, or ``me``). Raises :class:`EditRefused`."""
    problem = password_problem(password)
    if problem:
        raise EditRefused(problem)
    api.post(f"wp/v2/users/{user}", {"password": password}, context="edit")


def user_post_count(api: WordPressApi, user_id: int) -> str:
    """How many posts *user_id* wrote, any status, as wp-admin's Posts column says; "" unknown."""
    if user_id <= 0:
        return ""
    try:
        return str(admin.post_count(api, user_id))
    except WordPressApiError:
        return ""
