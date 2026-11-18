"""Your own account's list-shaped settings, for the resource engine.

Split from :mod:`quill.core.github.resource_specs` to keep each module under
the size budget; that module adds these to ``RESOURCE_SPECS``. wx-free and
strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.resource_engine import Field, ResourceSpec

__all__ = ["USER_SPECS"]


def _login(raw: Mapping[str, Any]) -> str:
    return str(raw.get("login") or "someone")


USER_SPECS: tuple[ResourceSpec, ...] = (
    ResourceSpec(
        key="my_emails",
        label="My Email Addresses",
        scope="user",
        parent="people",
        noun="email address",
        list_path="{base}/emails",
        id_field="email",
        sentence=lambda raw: (
            f"{raw.get('email')}"
            + (", primary" if raw.get("primary") else "")
            + (", verified" if raw.get("verified") else ", not verified yet")
            + (f", {raw['visibility']}" if raw.get("visibility") else "")
            + "."
        ),
        help="My Email Addresses: the addresses on your account. Ctrl+N adds one.",
        page="https://github.com/settings/emails",
        create=(Field("emails", "The address to add:", "list"),),
        delete_body="emails",
    ),
    ResourceSpec(
        key="my_social_accounts",
        label="My Social Accounts",
        scope="user",
        parent="people",
        noun="social account",
        list_path="{base}/social_accounts",
        id_field="url",
        sentence=lambda raw: f"{raw.get('provider')}: {raw.get('url')}.",
        help="My Social Accounts: the links on your profile.",
        page="https://github.com/settings/profile",
        create=(Field("account_urls", "The address of the account:", "list"),),
        delete_body="account_urls",
    ),
    ResourceSpec(
        key="my_blocks",
        label="Blocked People",
        scope="user",
        parent="people",
        noun="blocked person",
        list_path="{base}/blocks",
        id_field="login",
        id_param="{username}",
        sentence=lambda raw: f"{_login(raw)} is blocked.",
        help="Blocked People: who cannot follow you or take part in your repositories.",
        page="https://github.com/settings/blocked_users",
        create=(Field("username", "The username to block:", is_id=True),),
        create_method="PUT",
        create_path="{list}/{id}",
    ),
    ResourceSpec(
        key="my_followers",
        label="My Followers",
        scope="user",
        parent="people",
        noun="follower",
        list_path="{base}/followers",
        id_field="login",
        sentence=lambda raw: f"{_login(raw)} follows you.",
        help="My Followers: who follows you on GitHub.",
        page="https://github.com/settings/profile",
        delete=False,
    ),
    ResourceSpec(
        key="my_issue_types",
        label="My Issue Types",
        scope="user",
        parent="people",
        noun="issue type",
        list_path="{base}/issue-types",
        id_field="id",
        id_param="{issue_type_id}",
        sentence=lambda raw: f"{raw.get('name')}: {raw.get('description') or 'no description'}.",
        help="My Issue Types: the kinds of issue your own repositories offer.",
        page="https://github.com/settings",
        create=(
            Field("name", "The type's name, such as Bug:"),
            Field("description", "A description, or leave it empty:", optional=True),
            Field("is_enabled", "Turn it on now?", "bool"),
        ),
        edit=(Field("name", "Its name:"), Field("is_enabled", "Turned on?", "bool")),
        edit_method="PUT",
    ),
    ResourceSpec(
        key="my_org_memberships",
        label="My Organizations' Memberships",
        scope="user",
        parent="people",
        noun="membership",
        list_path="{base}/memberships/orgs",
        id_field="url",
        sentence=lambda raw: (
            f"{_login(raw.get('organization') or {})}: {raw.get('role')}, {raw.get('state')}."
        ),
        help="My Organizations' Memberships: your role in each organization, and invitations.",
        page="https://github.com/settings/organizations",
        delete=False,
    ),
)
