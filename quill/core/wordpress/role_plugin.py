"""Roles edited through a role plugin's own REST routes, and who has never signed in (15.11).

Core WordPress reads roles over REST but cannot change what a role may do
(:data:`quill.core.wordpress.workbench_create.ROLES_CANNOT_CHANGE`). A role
plugin can, when it publishes routes for it. This module is the QUILL side:

- :func:`role_namespace`: the role plugin's namespace, when the site's REST
  index lists one of :data:`ROLE_NAMESPACES`; otherwise "" and the old
  read-only Roles report stays.
- :func:`read_roles`, :func:`plan_capabilities`, :func:`save_capabilities`,
  :func:`create_role` and :func:`delete_role`: read each role with its
  capabilities, change what one may do (previewed line by line, the old set
  kept for undo), and make a new role (undone by deleting it).

**The routes are assumed, not verified.** Neither Members nor User Role Editor
documents a REST API for roles as of 2026-11. The routes below are the ones
QUILL asks for, named so they are easy to find when a plugin ships them:
``GET members/v1/roles``, ``POST members/v1/roles`` (slug, name,
capabilities), ``POST members/v1/roles/{slug}`` (capabilities) and
``DELETE members/v1/roles/{slug}``. A site without them answers exactly as
before.

**Who has never signed in** (:func:`never_signed_in`): WordPress keeps no
sign-in time over REST. Some security and activity plugins register one on
the user (:data:`LOGIN_FIELDS`, at the top level or under ``meta``); where a
site gives one, people with no value are listed, and where none does, the
answer says so (:data:`NO_SIGN_IN_TIMES`) instead of calling everyone new.

Wx-free; requests go through the site's own client, off the UI thread.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.api import WordPressApi

__all__ = [
    "LOGIN_FIELDS",
    "NO_ROLE_PLUGIN",
    "NO_SIGN_IN_TIMES",
    "ROLE_NAMESPACES",
    "CapabilityPlan",
    "SiteRole",
    "create_role",
    "delete_role",
    "never_signed_in",
    "parse_capabilities",
    "plan_capabilities",
    "read_roles",
    "role_namespace",
    "save_capabilities",
    "valid_slug",
]

#: Role plugins whose REST namespace QUILL uses, with the plugin's name.
ROLE_NAMESPACES: Mapping[str, str] = {"members/v1": "Members"}

NO_ROLE_PLUGIN = (
    "No role plugin on this site publishes REST routes for roles, so what a role may do is "
    "changed in wp-admin, with Members or User Role Editor."
)

#: Where plugins put a person's last sign-in on the user, at the top level or under meta.
LOGIN_FIELDS: tuple[str, ...] = (
    "last_login",
    "wfls_last_login",
    "last_activity",
    "last_logged_in",
    "wp_last_login",
)

NO_SIGN_IN_TIMES = (
    "WordPress does not give sign-in times over REST, and nothing on this site adds them, so "
    "QUILL cannot tell who has never signed in. A plugin that records the last sign-in and "
    "registers it on the user in REST, as last_login, makes this list possible."
)

_SLUG = re.compile(r"^[a-z][a-z0-9_]{1,59}$")
_CAP = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class SiteRole:
    """One role as the role plugin reports it: its slug, name and capabilities."""

    slug: str
    name: str
    capabilities: frozenset[str] = frozenset()

    @property
    def line(self) -> str:
        count = len(self.capabilities)
        noun = "capability" if count == 1 else "capabilities"
        return f"{self.name} ({self.slug}): {count} {noun}"


@dataclass
class CapabilityPlan:
    """A role's change: what it gains and loses, and its whole set before and after."""

    role: SiteRole
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)  # asked to remove but never had

    @property
    def after(self) -> list[str]:
        return sorted((self.role.capabilities - set(self.removed)) | set(self.added))

    @property
    def before(self) -> list[str]:
        return sorted(self.role.capabilities)

    @property
    def empty(self) -> bool:
        return not self.added and not self.removed

    def lines(self) -> list[str]:
        out = [f"{self.role.name} may now also: {c}" for c in self.added]
        out += [f"{self.role.name} may no longer: {c}" for c in self.removed]
        out += [f"Left alone, {self.role.name} never had it: {c}" for c in self.unknown]
        return out


def role_namespace(namespaces: Iterable[str]) -> str:
    """The first of :data:`ROLE_NAMESPACES` the site lists, or ""."""
    listed = {str(n).strip("/") for n in namespaces}
    return next((ns for ns in ROLE_NAMESPACES if ns in listed), "")


def _caps(raw: Any) -> frozenset[str]:
    if isinstance(raw, Mapping):
        return frozenset(str(k) for k, v in raw.items() if v)
    if isinstance(raw, (list, tuple)):
        return frozenset(str(c) for c in raw)
    return frozenset()


def read_roles(api: WordPressApi, namespace: str) -> list[SiteRole]:
    """Every role the plugin reports, by name; a list or a slug-keyed object both read."""
    answer = api.get(f"{namespace}/roles")
    entries: list[tuple[str, Any]] = []
    if isinstance(answer, Mapping):
        entries = [(str(k), v) for k, v in answer.items()]
    elif isinstance(answer, list):
        entries = [(str(v.get("slug", "")), v) for v in answer if isinstance(v, Mapping)]
    roles = []
    for slug, raw in entries:
        if not slug or not isinstance(raw, Mapping):
            continue
        name = str(raw.get("name") or raw.get("label") or slug)
        roles.append(SiteRole(slug, name, _caps(raw.get("capabilities"))))
    return sorted(roles, key=lambda r: r.name.casefold())


def parse_capabilities(text: str) -> tuple[list[str], list[str]]:
    """Capability names from a comma or line separated list: (good, not a capability name)."""
    good: list[str] = []
    bad: list[str] = []
    for word in re.split(r"[,\n]", text):
        word = word.strip()
        if not word:
            continue
        (good if _CAP.match(word) else bad).append(word)
    return list(dict.fromkeys(good)), bad


def plan_capabilities(role: SiteRole, add: Sequence[str], remove: Sequence[str]) -> CapabilityPlan:
    """What adding *add* and taking away *remove* does to *role*."""
    plan = CapabilityPlan(role)
    plan.added = [c for c in add if c not in role.capabilities and c not in remove]
    plan.removed = [c for c in remove if c in role.capabilities]
    plan.unknown = [c for c in remove if c not in role.capabilities]
    return plan


def _body(capabilities: Iterable[str]) -> dict[str, bool]:
    return {c: True for c in sorted(capabilities)}


def save_capabilities(
    api: WordPressApi, namespace: str, slug: str, capabilities: Iterable[str]
) -> Any:
    """Send *slug*'s whole capability set (undo sends the old one the same way)."""
    return api.post(f"{namespace}/roles/{slug}", {"capabilities": _body(capabilities)})


def valid_slug(slug: str, existing: Iterable[str]) -> str:
    """Why *slug* cannot name a new role ("" when it can)."""
    if not _SLUG.match(slug):
        return (
            f"{slug or 'An empty name'} cannot be a role's slug: use lower-case letters, digits "
            "and underscores, starting with a letter."
        )
    if slug in set(existing):
        return f"The site already has a role {slug}."
    return ""


def create_role(
    api: WordPressApi, namespace: str, slug: str, name: str, capabilities: Iterable[str]
) -> Any:
    """Make a new role with *capabilities*."""
    return api.post(
        f"{namespace}/roles", {"slug": slug, "name": name, "capabilities": _body(capabilities)}
    )


def delete_role(api: WordPressApi, namespace: str, slug: str) -> Any:
    """Take a role away (the undo of :func:`create_role`)."""
    return api.delete(f"{namespace}/roles/{slug}")


# -- who has never signed in -----------------------------------------------------------


def _login(raw: Mapping[str, Any]) -> tuple[str, Any]:
    """(the field that holds the last sign-in, its value), or ("", None) when none is there."""
    meta = raw.get("meta")
    for key in LOGIN_FIELDS:
        if key in raw:
            return key, raw[key]
        if isinstance(meta, Mapping) and key in meta:
            return f"meta.{key}", meta[key]
    return "", None


def _empty(value: Any) -> bool:
    if isinstance(value, list):
        return all(_empty(v) for v in value)
    return value in (None, "", 0, "0", False)


def never_signed_in(users: Sequence[Mapping[str, Any]]) -> tuple[str, list[str]]:
    """(the field the site gives sign-in times in, the people with none); ("", []) if none.

    A field counts as given when any person carries it; a person who does not
    carry it on such a site has never signed in as far as that plugin knows.
    """
    found = ""
    for raw in users:
        found = found or _login(raw)[0]
    if not found:
        return "", []
    names = []
    for raw in users:
        _key, value = _login(raw)
        if _empty(value):
            names.append(str(raw.get("name") or raw.get("username") or raw.get("id", "")))
    return found, names
