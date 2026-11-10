"""People in the Workbench: add, change role, remove with reassignment, passwords (PRD 11).

Built on :mod:`~quill.core.wordpress.site_admin`, which already adds users
with a strong password QUILL never shows or keeps, and lists and revokes
application passwords. What this adds is the Workbench's half:

- the guards (:mod:`~quill.core.wordpress.workbench_permissions`) checked
  before anything is sent, against the site's current list of people, so
  nobody removes the last Administrator or their own;
- the preview sentence for a removal, with how many posts move to whom;
- making an application password, whose new secret the site shows once. It
  is returned to the window to show in a read-only box for the person to
  copy, and is never logged, kept or put in a repr (:class:`NewPassword`).

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress import site_admin as admin
from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site import Account
from quill.core.wordpress.workbench_edit import EditRefused
from quill.core.wordpress.workbench_permissions import remove_problem, role_change_problem

__all__ = [
    "NewPassword",
    "change_role",
    "create_app_password",
    "people",
    "remove_preview",
    "remove_user",
]


@dataclass(frozen=True)
class NewPassword:
    """A just-made application password. The secret is shown once and never printed."""

    uuid: str
    name: str
    secret: str = field(repr=False)

    def __repr__(self) -> str:
        return f"NewPassword(uuid={self.uuid!r}, name={self.name!r})"


def people(api: WordPressApi) -> list[dict[str, Any]]:
    """Everyone on the site with their roles, for the guards (``context=edit``)."""
    found = api.iter_collection("wp/v2/users", {"context": "edit", "_fields": "id,name,roles"})
    return [dict(u) for u in found]


def change_role(
    api: WordPressApi,
    account: Account,
    user_id: int,
    role: str,
    users: Sequence[Mapping[str, object]],
) -> admin.User:
    problem = role_change_problem(account, user_id, role, users)
    if problem:
        raise EditRefused(problem)
    return admin.update_user(api, user_id, roles=[role])


def remove_preview(api: WordPressApi, name: str, user_id: int, to_name: str) -> str:
    count = admin.post_count(api, user_id)
    noun = "post moves" if count == 1 else "posts move"
    return f"Remove {name}? {count} {noun} to {to_name}. This cannot be undone."


def remove_user(
    api: WordPressApi,
    account: Account,
    user_id: int,
    reassign: int,
    users: Sequence[Mapping[str, object]],
) -> None:
    problem = remove_problem(account, user_id, users)
    if problem:
        raise EditRefused(problem)
    if not reassign or reassign == user_id:
        raise EditRefused("Choose someone else to give this person's posts to.")
    admin.delete_user(api, user_id, reassign)


def create_app_password(api: WordPressApi, name: str, user: str = "me") -> NewPassword:
    """A new application password called *name*; the site sends its secret this once."""
    clean = " ".join(name.split())
    if not clean:
        raise EditRefused("Give the new password a name, so you know later what uses it.")
    raw = api.post(f"wp/v2/users/{user}/application-passwords", {"name": clean})
    data = raw if isinstance(raw, dict) else {}
    return NewPassword(
        str(data.get("uuid", "")), str(data.get("name", clean)), str(data.get("password", ""))
    )
