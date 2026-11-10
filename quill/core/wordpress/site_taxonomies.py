"""The site's taxonomies and statuses, as the site describes them (WP-R-031).

``wp/v2/taxonomies`` says, for every taxonomy the site shows in REST, its
route (``rest_base`` under ``rest_namespace``), whether it is hierarchical,
and which post types it belongs to. ``wp/v2/statuses`` lists every post
status, the plugins' own included (WooCommerce's order statuses, The Events
Calendar's). Before this, QUILL guessed a taxonomy's route from its name,
which breaks for any taxonomy registered with a different ``rest_base``
(``product_cat`` is served at ``wp/v2/product_cat`` on one site and somewhere
else on the next), and knew only the six core statuses.

What a site says is kept per connection (the site's address and the account
signing in) for a few minutes, so a command that touches terms many times asks
once. A site that will not answer leaves the cache empty and every caller falls
back to what it did before.

Wx-free.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError

__all__ = [
    "CORE_TAXONOMY_BASES",
    "StatusInfo",
    "TaxonomyInfo",
    "cached_taxonomies",
    "clear_cache",
    "discover_statuses",
    "discover_taxonomies",
    "forget",
    "lookup",
    "parse_statuses",
    "parse_taxonomies",
    "taxonomies_for_type",
]

#: The two core taxonomies' routes, used when a site has not been asked yet.
CORE_TAXONOMY_BASES: Mapping[str, str] = {"category": "categories", "post_tag": "tags"}

#: How long what a site said is trusted before it is asked again, in seconds.
CACHE_SECONDS = 600.0


@dataclass(frozen=True)
class TaxonomyInfo:
    """One taxonomy as ``wp/v2/taxonomies`` describes it."""

    slug: str
    name: str
    rest_base: str
    rest_namespace: str = "wp/v2"
    hierarchical: bool = False
    #: The post types (their slugs, ``post``, ``product``) the taxonomy belongs to.
    types: tuple[str, ...] = ()

    @property
    def route(self) -> str:
        """The collection route, such as ``wp/v2/categories``."""
        return f"{self.rest_namespace.strip('/')}/{self.rest_base.strip('/')}"


@dataclass(frozen=True)
class StatusInfo:
    """One post status as ``wp/v2/statuses`` describes it."""

    slug: str
    name: str
    public: bool = False
    private: bool = False
    protected: bool = False
    queryable: bool = False
    show_in_list: bool = True
    date_floating: bool = False


def parse_taxonomies(raw: Any) -> dict[str, TaxonomyInfo]:
    """Slug -> :class:`TaxonomyInfo` from a ``wp/v2/taxonomies`` answer."""
    found: dict[str, TaxonomyInfo] = {}
    if not isinstance(raw, dict):
        return found
    for key, info in raw.items():
        if not isinstance(info, dict):
            continue
        slug = str(info.get("slug") or key)
        base = str(info.get("rest_base") or "").strip("/")
        if not slug or not base:
            continue
        types = info.get("types")
        found[slug] = TaxonomyInfo(
            slug=slug,
            name=str(info.get("name") or slug),
            rest_base=base,
            rest_namespace=str(info.get("rest_namespace") or "wp/v2").strip("/"),
            hierarchical=bool(info.get("hierarchical", False)),
            types=tuple(str(t) for t in types) if isinstance(types, list) else (),
        )
    return found


def parse_statuses(raw: Any) -> dict[str, StatusInfo]:
    """Slug -> :class:`StatusInfo` from a ``wp/v2/statuses`` answer."""
    found: dict[str, StatusInfo] = {}
    if not isinstance(raw, dict):
        return found
    for key, info in raw.items():
        if not isinstance(info, dict):
            continue
        slug = str(info.get("slug") or key)
        if not slug:
            continue
        found[slug] = StatusInfo(
            slug=slug,
            name=str(info.get("name") or slug),
            public=bool(info.get("public", False)),
            private=bool(info.get("private", False)),
            protected=bool(info.get("protected", False)),
            queryable=bool(info.get("queryable", False)),
            show_in_list=bool(info.get("show_in_list", True)),
            date_floating=bool(info.get("date_floating", False)),
        )
    return found


# --------------------------------------------------------------------------- #
# The per-connection cache


_lock = threading.Lock()
_cache: dict[tuple[str, str, str, str], tuple[float, Any]] = {}


def _key(api: WordPressApi, what: str) -> tuple[str, str, str, str]:
    site = api.address.wpcom_site or api.address.site_url
    return (site.rstrip("/").lower(), str(api.auth.kind), api.auth.username, what)


def _cached(api: WordPressApi, what: str) -> Any:
    with _lock:
        entry = _cache.get(_key(api, what))
    if entry is None or time.monotonic() - entry[0] > CACHE_SECONDS:
        return None
    return entry[1]


def _keep(api: WordPressApi, what: str, value: Any) -> None:
    with _lock:
        _cache[_key(api, what)] = (time.monotonic(), value)


def forget(api: WordPressApi) -> None:
    """Drop what this connection's site said, so the next caller asks again."""
    site, kind, user, _what = _key(api, "")
    with _lock:
        for key in [k for k in _cache if k[:3] == (site, kind, user)]:
            del _cache[key]


def clear_cache() -> None:
    """Forget every site (tests, and signing out)."""
    with _lock:
        _cache.clear()


def _ask(api: WordPressApi, route: str) -> Any:
    # Edit context says more (and lists statuses a visitor cannot see); an
    # account that may not ask for it still gets the public answer.
    try:
        return api.get(route, context="edit")
    except WordPressApiError as exc:
        if exc.status not in (401, 403):
            raise
    return api.get(route)


def discover_taxonomies(api: WordPressApi, *, refresh: bool = False) -> dict[str, TaxonomyInfo]:
    """Every taxonomy the site shows in REST, asked once per connection.

    Raises :class:`~quill.core.wordpress.api.WordPressApiError` when the site
    cannot be reached; a site that answers with nothing usable is ``{}``.
    """
    if not refresh:
        found = _cached(api, "taxonomies")
        if found is not None:
            return dict(found)
    parsed = parse_taxonomies(_ask(api, "wp/v2/taxonomies"))
    _keep(api, "taxonomies", parsed)
    return dict(parsed)


def cached_taxonomies(api: WordPressApi) -> dict[str, TaxonomyInfo] | None:
    """What the site already said about its taxonomies, without asking; ``None`` if not yet."""
    found = _cached(api, "taxonomies")
    return dict(found) if found is not None else None


def discover_statuses(api: WordPressApi, *, refresh: bool = False) -> dict[str, StatusInfo]:
    """Every post status the site lists, its plugins' own included, asked once per connection."""
    if not refresh:
        found = _cached(api, "statuses")
        if found is not None:
            return dict(found)
    parsed = parse_statuses(_ask(api, "wp/v2/statuses"))
    _keep(api, "statuses", parsed)
    return dict(parsed)


def taxonomies_for_type(api: WordPressApi, post_type: str) -> list[TaxonomyInfo]:
    """The taxonomies that belong to *post_type* (its slug: ``post``, ``tribe_events``)."""
    return [t for t in discover_taxonomies(api).values() if post_type in t.types]


def lookup(api: WordPressApi | None, taxonomy: str) -> TaxonomyInfo | None:
    """The site's word on *taxonomy*, asking it only for a taxonomy core does not fix.

    ``category`` and ``post_tag`` are never worth a request on their own: their
    routes are fixed by core. Anything else is asked about once per connection,
    and a site that cannot say leaves ``None`` (the caller guesses as before).
    """
    if api is None:
        return None
    known = cached_taxonomies(api)
    if known is None and taxonomy not in CORE_TAXONOMY_BASES:
        try:
            known = discover_taxonomies(api)
        except WordPressApiError:
            _keep(api, "taxonomies", {})
            known = {}
    if not known:
        return None
    found = known.get(taxonomy)
    if found is None:
        # A caller may name a taxonomy by its route rather than its slug.
        found = next((t for t in known.values() if t.rest_base == taxonomy), None)
    return found
