"""Process-wide registry of Quillin-supplied station-directory providers.

A Quillin running in Quill Radio may contribute a ``radio.directory`` provider
that returns station rows for a search query (a community directory, a curated
list). :class:`~quill.core.quillins.app_host.QuillinAppHost` populates this
registry from every enabled provider contribution, and
:func:`quill.core.radio.directory_search.directory_provider_stations` consults it
during the Find Stations fan-out, alongside the built-in sources.

The registry is deliberately tiny and wx-free: a provider is a callable
``(query) -> list[dict]`` returning ``{"name", "url", "source"}`` rows. The
handler makes no network call of its own -- it returns rows from its own storage
or a bundled static list -- so consulting the registry never introduces a new
egress site.
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
