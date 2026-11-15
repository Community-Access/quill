"""Check for Updates on WordPress.org: which plugins, themes and WordPress have one waiting.

WordPress's REST API never says an update waits (:mod:`~quill.core.wordpress.workbench_updates`),
but WordPress.org says which version is current, and comparing that with the
version a site reports is what wp-admin's own update check does. This asks
the same public API Check on WordPress.org already asks, through
:func:`quill.core.wordpress.dotorg.ask_wordpress_org` and only after the same
consent:

- ``plugins/info/1.2`` ``plugin_information``, one plugin's short name (slug)
  a request (:func:`quill.core.wordpress.dotorg.plugin_details`);
- ``themes/info/1.2`` ``theme_information``, one theme's slug a request;
- ``core/version-check/1.7``, with nothing at all: the current WordPress.

No site address, installed version, account or password is sent; the
comparison is made here. A plugin or theme WordPress.org does not list (a
paid one such as Gravity Forms, a PMPro add-on or Yoast Premium, or a custom
one) is "unknown", never "up to date". Wx-free.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import urlencode

from quill.core.wordpress import dotorg
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "CORE_CHECK_URL",
    "NOT_SAID",
    "UNKNOWN",
    "UP_TO_DATE",
    "Latest",
    "is_newer",
    "latest_core",
    "latest_plugins",
    "latest_themes",
    "mark_rows",
    "slug_of",
    "theme_info_url",
    "update_word",
    "waiting_count",
]

CORE_CHECK_URL = f"https://{dotorg.DOTORG_HOST}/core/version-check/1.7/"
UNKNOWN = "Unknown: not on WordPress.org"
UP_TO_DATE = "Up to date"
NOT_SAID = "Unknown: the site does not say its version"
_WAITING = "Update waiting"


def theme_info_url(slug: str) -> str:
    query = {
        "action": "theme_information",
        "request[slug]": slug.strip(),
        "request[fields][sections]": "0",
    }
    return f"https://{dotorg.DOTORG_HOST}/themes/info/1.2/?{urlencode(query)}"


def _parts(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", version or ""))


def is_newer(installed: str, latest: str) -> bool:
    """Whether *latest* is a later version than *installed* (both as WordPress writes them)."""
    have, offered = _parts(installed), _parts(latest)
    if not have or not offered:
        return False
    width = max(len(have), len(offered))
    return offered + (0,) * (width - len(offered)) > have + (0,) * (width - len(have))


def latest_core(*, opener: dotorg.Opener | None = None) -> str:
    """The current WordPress version, from the first offer WordPress.org makes."""
    payload = dotorg._get(CORE_CHECK_URL, opener)  # noqa: SLF001 - the module's one door
    offers = payload.get("offers") if isinstance(payload, Mapping) else None
    for offer in offers or []:
        if isinstance(offer, Mapping):
            found = str(offer.get("current") or offer.get("version") or "")
            if found:
                return found
    return ""


def latest_plugins(
    slugs: Iterable[str], *, opener: dotorg.Opener | None = None
) -> dict[str, str | None]:
    """Each slug's current version on WordPress.org; None when it is not listed or closed."""
    found = dotorg.plugin_details(slugs, opener=opener)
    return {
        slug: (plugin.version or None) if plugin is not None and not plugin.closed else None
        for slug, plugin in found.items()
    }


def latest_themes(
    slugs: Iterable[str], *, opener: dotorg.Opener | None = None, limit: int = 100
) -> dict[str, str | None]:
    """Each theme slug's current version on WordPress.org; None when it is not listed."""
    found: dict[str, str | None] = {}
    for slug in slugs:
        slug = slug.strip()
        if not slug or slug in found or len(found) >= limit:
            continue
        raw = dotorg._get(theme_info_url(slug), opener, answer_404=True)  # noqa: SLF001
        ok = isinstance(raw, Mapping) and not raw.get("error") and raw.get("version")
        found[slug] = str(raw["version"]) if ok else None
    return found


@dataclass(frozen=True)
class Latest:
    """What WordPress.org said: WordPress, then plugins and themes by slug."""

    core: str = ""
    plugins: Mapping[str, str | None] = field(default_factory=dict)
    themes: Mapping[str, str | None] = field(default_factory=dict)

    def merged(self, other: Latest) -> Latest:
        return Latest(
            other.core or self.core,
            {**self.plugins, **other.plugins},
            {**self.themes, **other.themes},
        )


def update_word(installed: str, latest: str | None) -> str:
    """The Update cell: waiting (with the version), up to date, or unknown."""
    if not latest:
        return UNKNOWN
    if not _parts(installed):
        return NOT_SAID
    if is_newer(installed, latest):
        return f"{_WAITING}: version {latest}"
    return UP_TO_DATE


def slug_of(row: WbRow) -> tuple[str, str]:
    """(``core``, ``plugin`` or ``theme``; its slug) for a row this check marks, else blanks."""
    if row.kind == "plugin":
        return "plugin", dotorg.plugin_slug(row.key)
    if row.kind == "theme":
        return "theme", row.key
    if row.kind == "update":
        _prefix, _sep, rest = row.key.partition(":")
        if rest == "core":
            return "core", "core"
        what, _sep, ident = rest.partition(":")
        if what == "plugin":
            return "plugin", dotorg.plugin_slug(ident)
        if what == "theme":
            return "theme", ident
    return "", ""


def _latest_for(latest: Latest, what: str, slug: str) -> tuple[bool, str | None]:
    """(asked, version) for one row: asked is False when WordPress.org was not asked of it."""
    if what == "core":
        return bool(latest.core), latest.core or None
    table = latest.plugins if what == "plugin" else latest.themes
    return slug in table, table.get(slug)


def _sentence(word: str, installed: str, version: str | None) -> str:
    if word.startswith(_WAITING):
        return (
            f"WordPress.org has version {version}; this site has {installed}, so an update "
            "waits. Dashboard > Updates runs it."
        )
    if word == UP_TO_DATE:
        return f"WordPress.org has version {version}, the version installed."
    if word == NOT_SAID:
        return f"WordPress.org has version {version}; the site does not say which it has."
    return (
        "WordPress.org does not list it (a paid, custom or closed one), so whether an update "
        "waits is unknown."
    )


def mark_rows(rows: Sequence[Any], latest: Latest) -> list[Any]:
    """Rows with WordPress.org's answer in their Update cell and details; others unchanged."""
    marked: list[Any] = []
    for row in rows:
        what, slug = slug_of(row) if isinstance(row, WbRow) else ("", "")
        asked, version = _latest_for(latest, what, slug) if what else (False, None)
        if not asked:
            marked.append(row)
            continue
        installed = row.cell("installed") if row.kind == "update" else row.cell("version")
        word = update_word(installed, version)
        cells = {**row.cells, "update": word}
        if row.kind != "update" and word.startswith(_WAITING):
            cells["version"] = f"{installed}, update waiting: {version}"
        said = _sentence(word, installed, version)
        marked.append(replace(row, cells=cells, detail=f"{row.detail} {said}"))
    return marked


def waiting_count(rows: Sequence[Any]) -> tuple[int, int]:
    """(how many rows have an update waiting, how many are unknown) after :func:`mark_rows`."""
    words = [row.cell("update") for row in rows if isinstance(row, WbRow)]
    return (
        sum(1 for word in words if word.startswith(_WAITING)),
        sum(1 for word in words if word in (UNKNOWN, NOT_SAID)),
    )
