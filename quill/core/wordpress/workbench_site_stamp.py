"""Noticing that a site changed under the Workbench, so no stale claim is reused (complete.md WP-B).

The Workbench reads a site's account (``users/me?context=edit``: role and
capabilities), its REST index (WordPress version, namespaces and routes) and,
from those, its post types, taxonomies, statuses and field schemas, once per
window. Installing or turning off a plugin, switching the theme or updating
WordPress can change every one of those, and so can somebody changing your
role. A :class:`SiteStamp` is what those depend on; :func:`read_stamp` takes it
again and :func:`stamp_changes` says, in words, what moved. When anything
did, the caller forgets what it read (:func:`forget_site`) and reads it again
before the next thing is offered or saved.

When it is taken: at most once every :data:`RECHECK_SECONDS` per site, as
something loads, and at once after the Workbench itself turns a plugin on or
off. Plugins and the theme are read only where the account may read them
(``activate_plugins``, ``switch_themes``); otherwise the index and the
account carry the check. Wx-free.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress import site_taxonomies as tx
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import Account, SiteInfo, load_account, load_site_info

__all__ = [
    "RECHECK_SECONDS",
    "SiteStamp",
    "forget_site",
    "read_stamp",
    "stamp_changes",
    "stamp_of",
]

#: How long a site's stamp is trusted before the next load takes it again.
RECHECK_SECONDS = 300.0


@dataclass(frozen=True)
class SiteStamp:
    """What a site's capability and schema claims depend on."""

    wp_version: str = ""
    namespaces: tuple[str, ...] = ()
    routes: str = ""  #: a digest of the index's routes: a new type or field route moves it
    plugins: tuple[tuple[str, str, str], ...] | None = None  #: (plugin, version, status)
    theme: str | None = None  #: the active theme's stylesheet and version
    roles: tuple[str, ...] = ()
    capabilities: str = ""  #: a digest of your capabilities


def _digest(words: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(sorted(words)).encode("utf-8")).hexdigest()[:16]


def stamp_of(
    info: SiteInfo | None,
    account: Account | None,
    *,
    plugins: Iterable[Mapping[str, Any]] | None = None,
    theme: Mapping[str, Any] | None = None,
) -> SiteStamp:
    """The stamp of what was read: the index, the account, and plugins and theme when readable."""
    found = None
    if plugins is not None:
        found = tuple(
            sorted(
                (str(p.get("plugin", "")), str(p.get("version", "")), str(p.get("status", "")))
                for p in plugins
                if isinstance(p, Mapping)
            )
        )
    look = None
    if theme is not None:
        look = f"{theme.get('stylesheet', '')} {theme.get('version', '')}".strip()
    return SiteStamp(
        wp_version=info.wp_version if info is not None else "",
        namespaces=tuple(sorted(info.namespaces)) if info is not None else (),
        routes=_digest(info.routes) if info is not None else "",
        plugins=found,
        theme=look,
        roles=tuple(account.roles) if account is not None else (),
        capabilities=_digest(account.capabilities) if account is not None else "",
    )


def _optional(api: WordPressApi, route: str, **params: object) -> Any:
    try:
        return api.get(route, **params)
    except WordPressApiError as exc:
        if exc.status in (401, 403, 404):
            return None  # this account may not read it; the rest of the stamp still counts
        raise


def read_stamp(api: WordPressApi) -> tuple[SiteStamp, SiteInfo, Account]:
    """Read the stamp afresh: the index, the account, and plugins and the theme if allowed."""
    info = load_site_info(api)
    account = load_account(api)
    plugins = None
    if account.can("activate_plugins"):
        raw = _optional(api, "wp/v2/plugins", context="edit")
        plugins = raw if isinstance(raw, list) else None
    theme = None
    if account.can("switch_themes"):
        raw = _optional(api, "wp/v2/themes", status="active")
        theme = raw[0] if isinstance(raw, list) and raw and isinstance(raw[0], dict) else None
    return stamp_of(info, account, plugins=plugins, theme=theme), info, account


def _plugin_words(
    old: Iterable[tuple[str, str, str]], new: Iterable[tuple[str, str, str]]
) -> list[str]:
    before = {p: (v, s) for p, v, s in old}
    after = {p: (v, s) for p, v, s in new}
    said: list[str] = []
    for plugin in sorted(set(before) | set(after)):
        name = plugin.split("/", 1)[0]
        if plugin not in before:
            said.append(f"{name} was installed")
        elif plugin not in after:
            said.append(f"{name} was removed")
        elif before[plugin][1] != after[plugin][1]:
            said.append(f"{name} is now {after[plugin][1]}")
        elif before[plugin][0] != after[plugin][0]:
            said.append(f"{name} went from {before[plugin][0]} to {after[plugin][0]}")
    return said


def stamp_changes(old: SiteStamp | None, new: SiteStamp) -> list[str]:
    """What changed between two stamps, in words; empty when nothing did (or no old one)."""
    if old is None:
        return []
    said: list[str] = []
    if old.wp_version and new.wp_version and old.wp_version != new.wp_version:
        said.append(f"WordPress went from {old.wp_version} to {new.wp_version}")
    if old.plugins is not None and new.plugins is not None:
        said += _plugin_words(old.plugins, new.plugins)
    if old.theme is not None and new.theme is not None and old.theme != new.theme:
        said.append(f"the theme is now {new.theme}")
    if old.namespaces != new.namespaces:
        said.append("the site's REST namespaces changed")
    elif old.routes != new.routes:
        said.append("the site's REST routes changed")
    if old.roles != new.roles:
        said.append(f"your role is now {', '.join(new.roles) or 'none'}")
    elif old.capabilities != new.capabilities:
        said.append("what your role may do changed")
    return said


def forget_site(api: WordPressApi) -> None:
    """Drop what was read of the site's types, taxonomies and statuses; the next caller asks."""
    tx.forget(api)
