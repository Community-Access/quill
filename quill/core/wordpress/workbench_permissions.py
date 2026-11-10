"""Who may do what in the WordPress Workbench (PRD 11, WP-R-010 to 012).

Three layers decide whether a command is offered, checked in this order:

1. **Workbench access, per site** (:class:`Access`): Read Only, Organize or
   Full, chosen by the person; Safe Mode and View As Role are always Read
   Only. Read Only allows tier 0 (reading), Organize adds tier 1 (Trash,
   moderation: easily undone), Full allows everything.
2. **The site's own capabilities** from ``users/me?context=edit``
   (:class:`~quill.core.wordpress.site.Account`), or, while viewing as a role,
   the capabilities WordPress gives that role by default
   (:data:`ROLE_CAPABILITIES`).
3. **Guards no capability lifts:** never your own Administrator role, never
   the last Administrator, and a warning before deactivating the plugin QUILL
   itself relies on.

Each refusal is one sentence naming the role that would allow it and the
role you have: "Publishing pages needs the Editor role or higher. You are an
Author on Community Radio." Wx-free; the access choice is kept in one JSON
file beside the site list, written atomically.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from enum import StrEnum
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress.site import Account
from quill.core.wordpress.sites import sites_path
from quill.core.workbench.actions import ActionRow, Tier

__all__ = [
    "ROLE_CAPABILITIES",
    "ROLE_ORDER",
    "Access",
    "AccessStore",
    "account_as_role",
    "capability_for",
    "deactivate_warning",
    "refusal",
    "remove_problem",
    "role_change_problem",
    "tier_allowed",
]

ROLE_ORDER = ("subscriber", "contributor", "author", "editor", "administrator")

_SUBSCRIBER = frozenset({"read"})
_CONTRIBUTOR = _SUBSCRIBER | {"edit_posts", "delete_posts"}
_AUTHOR = _CONTRIBUTOR | {
    "upload_files",
    "publish_posts",
    "edit_published_posts",
    "delete_published_posts",
}
_EDITOR = _AUTHOR | {
    "moderate_comments",
    "manage_categories",
    "manage_links",
    "unfiltered_html",
    "edit_others_posts",
    "edit_pages",
    "edit_others_pages",
    "edit_published_pages",
    "publish_pages",
    "delete_pages",
    "delete_others_pages",
    "delete_published_pages",
    "delete_others_posts",
    "delete_private_posts",
    "edit_private_posts",
    "read_private_posts",
    "delete_private_pages",
    "edit_private_pages",
    "read_private_pages",
}
_ADMINISTRATOR = _EDITOR | {
    "switch_themes",
    "edit_themes",
    "edit_theme_options",
    "activate_plugins",
    "edit_plugins",
    "install_plugins",
    "update_plugins",
    "delete_plugins",
    "install_themes",
    "update_themes",
    "delete_themes",
    "list_users",
    "create_users",
    "edit_users",
    "delete_users",
    "promote_users",
    "remove_users",
    "manage_options",
    "import",
    "export",
    "update_core",
    "view_site_health_checks",
    "edit_dashboard",
    "customize",
}

ROLE_CAPABILITIES: Mapping[str, frozenset[str]] = {
    "subscriber": frozenset(_SUBSCRIBER),
    "contributor": frozenset(_CONTRIBUTOR),
    "author": frozenset(_AUTHOR),
    "editor": frozenset(_EDITOR),
    "administrator": frozenset(_ADMINISTRATOR),
}
"""What WordPress gives each default role, for View As Role and for the refusal's role name."""

_VERBS = {
    "publish_posts": "Publishing posts",
    "publish_pages": "Publishing pages",
    "edit_posts": "Editing posts",
    "edit_pages": "Editing pages",
    "delete_posts": "Deleting posts",
    "delete_pages": "Deleting pages",
    "moderate_comments": "Moderating comments",
    "manage_categories": "Managing categories and tags",
    "upload_files": "Changing media",
    "activate_plugins": "Turning plugins on and off",
    "switch_themes": "Changing the theme",
    "list_users": "Seeing the people on the site",
    "promote_users": "Changing someone's role",
    "create_users": "Adding people",
    "delete_users": "Removing people",
    "manage_options": "Changing site settings",
    "edit_theme_options": "Changing menus and the theme's options",
}

#: Plugins whose deactivation would cut QUILL off from part of the site.
_QUILL_RELIES_ON = {
    "quill-accessible-forms": "QUILL's Forms commands and Held as Spam for form entries",
    "bits-accessible-forms": "QUILL's Forms commands, under the plugin's older name",
    "application-passwords": "the application password QUILL signs in with",
}


class Access(StrEnum):
    """How much the Workbench may change on one site."""

    READ_ONLY = "read_only"
    ORGANIZE = "organize"
    FULL = "full"

    @property
    def words(self) -> str:
        return {"read_only": "Read Only", "organize": "Organize", "full": "Full"}[self.value]


def tier_allowed(tier: Tier, access: Access) -> bool:
    if access is Access.FULL:
        return True
    if access is Access.ORGANIZE:
        return tier <= Tier.ORGANIZE
    return tier <= Tier.READ


class AccessStore:
    """Each site's Workbench access, by site id; Full when never chosen."""

    def __init__(self, base: Path | None = None) -> None:
        self.path = sites_path(base).parent / "workbench_access.json"

    def _read(self) -> dict[str, str]:
        raw = read_json(self.path, default={})
        return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}

    def get(self, site_id: str) -> Access:
        value = self._read().get(site_id, Access.FULL.value)
        try:
            return Access(value)
        except ValueError:
            return Access.FULL

    def set(self, site_id: str, access: Access) -> None:
        data = self._read()
        data[site_id] = access.value
        write_json_atomic(self.path, data)


def capability_for(row: ActionRow, row_kind: str, subkind: str = "") -> str:
    """The site capability *row* needs on a *row_kind* row ("" for none)."""
    need = row.requirement
    plural = "pages" if subkind == "page" else "posts"
    if need == "edit":
        return {"item": f"edit_{plural}", "comment": "moderate_comments"}.get(row_kind, "")
    if need == "publish":
        return f"publish_{plural}"
    if need == "delete":
        return {
            "item": f"delete_{plural}",
            "comment": "moderate_comments",
            "term": "manage_categories",
            "media": "upload_files",
        }.get(row_kind, "")
    if need == "forms":
        return "edit_posts"
    return need


def _lowest_role(capability: str) -> str:
    return next((r for r in ROLE_ORDER if capability in ROLE_CAPABILITIES[r]), "")


def _a(role: str) -> str:
    return f"an {role}" if role[:1].lower() in "aeiou" else f"a {role}"


def refusal(capability: str, account: Account | None, site: str) -> str:
    """Why *account* may not do what *capability* allows ("" when it may)."""
    if not capability or (account is not None and account.can(capability)):
        return ""
    lowest = _lowest_role(capability).title()
    if account is not None:
        you = f"You are {_a(account.role_name)} on {site}."
    else:
        you = f"QUILL does not yet know your role on {site}."
    what = _VERBS.get(capability, f"Doing this ({capability.replace('_', ' ')})")
    if lowest:
        return f"{what} needs the {lowest} role or higher. {you}"
    return f"{what} needs a role this site defines. {you}"


def account_as_role(account: Account, role: str) -> Account:
    """*account* as a *role* would meet the site, for View As Role (read only)."""
    return Account(
        account.id,
        account.name,
        account.username,
        (role,),
        ROLE_CAPABILITIES.get(role, frozenset({"read"})),
    )


def _admins(users: Iterable[Mapping[str, object]]) -> list[int]:
    found = []
    for user in users:
        roles = user.get("roles") or []
        if isinstance(roles, (list, tuple)) and "administrator" in roles:
            found.append(int(str(user.get("id", 0) or 0)))
    return found


def role_change_problem(
    account: Account, target_id: int, new_role: str, users: Sequence[Mapping[str, object]]
) -> str:
    """Why changing *target_id* to *new_role* would lock somebody out ("" when it is safe)."""
    if new_role == "administrator":
        return ""
    admins = _admins(users)
    if target_id == account.id and "administrator" in account.roles:
        return (
            "You cannot take away your own Administrator role from here: you would lose the "
            "right to put it back. Ask another administrator to do it."
        )
    if target_id in admins and len(admins) == 1:
        return "This is the site's only Administrator. Make someone else an Administrator first."
    return ""


def remove_problem(account: Account, target_id: int, users: Sequence[Mapping[str, object]]) -> str:
    """Why removing *target_id* is refused ("" when it is allowed)."""
    if target_id == account.id:
        return "You cannot remove your own account from here."
    admins = _admins(users)
    if target_id in admins and len(admins) == 1:
        return "This is the site's only Administrator, so it cannot be removed."
    return ""


def deactivate_warning(plugin: str) -> str:
    """A warning before deactivating a plugin QUILL relies on ("" for any other)."""
    slug = plugin.split("/", 1)[0]
    found = _QUILL_RELIES_ON.get(slug)
    return f"QUILL relies on this plugin for {found}. Turning it off stops that." if found else ""
