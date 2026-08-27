"""Process-wide registry of Quillin-supplied station-directory providers.

A Quillin running in Quill Radio may contribute a ``radio.directory`` provider
that returns station rows for a search query (a community directory, a curated
list). :class:`~quill.core.quillins.app_host.QuillinAppHost` populates this
registry from every enabled provider contribution, and
:func:`quill.core.radio.directory_search.directory_provider_stations` consults it
during the Find Stations fan-out, alongside the built-in sources.

The registry is deliberately tiny and wx-free: a provider is a callable
``(query) -> list[dict]`` returning ``{"name", "url", "source"}`` rows. The
*search* handler makes no network call of its own -- it returns rows from its
own storage or a bundled static list -- so consulting the registry never
introduces a new egress site. The **browse** providers further down may reach
the network, but only through the Quillin host's own fetch API, which is
SSRF-hardened and bounded by each manifest's ``net_allowed_hosts``; the
registry itself still contacts nothing.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

#: A provider callable. Given the search ``query``, it returns a list of station
#: rows -- each a mapping with at least ``name`` and ``url`` (and an optional
#: ``source`` badge). An empty list means "nothing to contribute for this query".
DirectoryProvider = Callable[[str], list[dict[str, str]]]


@dataclass(frozen=True, slots=True)
class DirectoryProviderEntry:
    """A registered station-directory provider and its display badge."""

    provider_id: str
    display_name: str
    handler: DirectoryProvider


_providers: list[DirectoryProviderEntry] = []


def register_provider(provider_id: str, display_name: str, handler: DirectoryProvider) -> None:
    """Register (or replace, by id) a station-directory provider."""

    clear_provider(provider_id)
    _providers.append(DirectoryProviderEntry(provider_id, display_name, handler))


def clear_provider(provider_id: str) -> None:
    """Remove the provider with ``provider_id`` if present."""

    _providers[:] = [p for p in _providers if p.provider_id != provider_id]


def clear_providers() -> None:
    """Forget every registered provider (a full host reload starts here)."""

    _providers.clear()


def registered_provider_ids() -> tuple[str, ...]:
    """The ids of every currently registered provider (for tests / diagnostics)."""

    return tuple(p.provider_id for p in _providers)


def stations_from_providers(query: str) -> list[dict[str, str]]:
    """Return the station rows every registered provider supplies for ``query``.

    Providers are consulted in registration order; each provider's own
    ``display_name`` is stamped as the row ``source`` when the row omits one, so
    the Find Stations Source filter can badge contributed stations. A handler
    that raises is skipped so one faulty provider never blanks the search.
    """

    rows: list[dict[str, str]] = []
    for provider in _providers:
        try:
            supplied = provider.handler(query)
        except Exception:  # noqa: BLE001 - a faulty provider must never break a search
            continue
        if not supplied:
            continue
        for row in supplied:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name", "")).strip()
            url = str(row.get("url", "")).strip()
            if not name or not url:
                continue
            source = str(row.get("source", "")).strip() or provider.display_name
            rows.append({"name": name, "url": url, "source": source})
    return rows


# --- browse providers (2026-08-27, radio2.md part VIII) -----------------------
#
# A search provider answers one question; a BROWSE provider is a whole source:
# categories, station lists, and optionally a resolve step for rows whose
# address only exists at play time. The handlers are host-mediated exactly like
# the search handler above -- and unlike it they MAY reach the network, through
# the Quillin host's fetch API, which is SSRF-hardened and bounded by the
# manifest's net_allowed_hosts. Consulting this registry still contacts
# nothing: calling a handler is the browse tree's explicit act.


@dataclass(frozen=True, slots=True)
class BrowseProviderEntry:
    """A registered browse-capable provider."""

    provider_id: str
    display_name: str
    #: () -> list of category names. Empty list means a flat source.
    categories: Callable[[], list[str]]
    #: (category, query) -> station rows.
    stations: Callable[[str, str], list[dict[str, str]]]
    #: (key) -> playable URL, or "". None when the provider declared no resolver.
    resolve: Callable[[str], str] | None


_browse_providers: list[BrowseProviderEntry] = []


def register_browse_provider(
    provider_id: str,
    display_name: str,
    *,
    categories: Callable[[], list[str]],
    stations: Callable[[str, str], list[dict[str, str]]],
    resolve: Callable[[str], str] | None = None,
) -> None:
    """Register (or replace, by id) a browse-capable provider."""

    clear_browse_provider(provider_id)
    _browse_providers.append(
        BrowseProviderEntry(provider_id, display_name, categories, stations, resolve)
    )


def clear_browse_provider(provider_id: str) -> None:
    """Remove the browse provider with ``provider_id`` if present."""

    _browse_providers[:] = [p for p in _browse_providers if p.provider_id != provider_id]


def browse_providers() -> tuple[BrowseProviderEntry, ...]:
    """Every registered browse provider, in registration order."""

    return tuple(_browse_providers)


def browse_provider(provider_id: str) -> BrowseProviderEntry | None:
    """The browse provider with this id, or ``None``."""

    for entry in _browse_providers:
        if entry.provider_id == provider_id:
            return entry
    return None


def station_from_row(row: object, display_name: str) -> object | None:
    """One provider row as a RadioStation-or-locator (validated, tolerant).

    The single coercion every contributed row passes through, per the review:
    unknown keys are dropped, wrong types are coerced or zeroed, and a row with
    neither a ``url`` nor a ``key`` is refused -- it could never play. Returns
    ``(station, key)``: *key* is non-empty when the row asked to be resolved at
    play time.
    """

    from quill.core.radio.models import RadioStation, _coerce_int

    if not isinstance(row, dict):
        return None
    name = str(row.get("name") or "").strip()
    url = str(row.get("url") or "").strip()
    key = str(row.get("key") or "").strip()
    if not name or (not url and not key):
        return None
    tags_raw = row.get("tags")
    tags = (
        tuple(str(t) for t in tags_raw if str(t).strip())
        if isinstance(tags_raw, (list, tuple))
        else ()
    )
    station = RadioStation(
        name=name,
        stream_url=url,
        station_uuid="",
        homepage=str(row.get("homepage") or ""),
        country=str(row.get("country") or ""),
        tags=tags,
        codec=str(row.get("codec") or ""),
        bitrate_kbps=_coerce_int(row.get("bitrate_kbps")),
        source=str(row.get("source") or display_name),
    )
    return (station, key)
