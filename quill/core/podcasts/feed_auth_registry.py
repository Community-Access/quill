"""Process-wide registry of Quillin-supplied podcast feed-auth providers.

A Quillin running in Quill Cast may contribute a ``podcast.feed.auth`` provider
that supplies an ``Authorization`` header for feeds on hosts it recognises (a
premium/authenticated podcast network, say). :class:`QuillinAppHost` populates
this registry from every enabled provider contribution, and
:func:`quill.core.podcasts.feed_auth.auth_header_for_url` consults it *before*
falling back to the built-in per-show HTTP Basic path.

The registry is deliberately tiny and wx-free: a provider is just a callable
``(feed_url, request_url) -> header`` plus the host patterns it matches. The
handler itself makes no network call -- it returns a header string the host then
attaches -- so consulting the registry never introduces a new egress site.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass

#: A provider callable. Given the show's ``feed_url`` and the concrete
#: ``request_url`` being fetched, it returns an ``Authorization`` header value
#: (e.g. ``"Bearer abc"``) or ``""`` when it has nothing to contribute.
AuthHeaderProvider = Callable[[str, str], str]


@dataclass(frozen=True, slots=True)
class FeedAuthProvider:
    """A registered feed-auth provider and the hosts it answers for."""

    provider_id: str
    match_hosts: tuple[str, ...]
    handler: AuthHeaderProvider


_providers: list[FeedAuthProvider] = []


def _host_matches(pattern: str, host: str) -> bool:
    """Match ``host`` against a ``match_hosts`` entry (exact or ``*.suffix``)."""

    host = host.lower()
    pattern = pattern.lower()
    if pattern.startswith("*."):
        return host.endswith("." + pattern[2:])
    return host == pattern


def register_provider(
    provider_id: str, match_hosts: tuple[str, ...], handler: AuthHeaderProvider
) -> None:
    """Register (or replace, by id) a feed-auth provider."""

    clear_provider(provider_id)
    _providers.append(FeedAuthProvider(provider_id, tuple(match_hosts), handler))


def clear_provider(provider_id: str) -> None:
    """Remove the provider with ``provider_id`` if present."""

    _providers[:] = [p for p in _providers if p.provider_id != provider_id]


def clear_providers() -> None:
    """Forget every registered provider (a full host reload starts here)."""

    _providers.clear()


def registered_provider_ids() -> tuple[str, ...]:
    """The ids of every currently registered provider (for tests / diagnostics)."""

    return tuple(p.provider_id for p in _providers)


def auth_header_from_providers(feed_url: str, request_url: str) -> str:
    """Return the first non-empty header a matching provider supplies, or ``""``.

    A provider matches when ``request_url``'s host matches one of its
    ``match_hosts`` patterns. Providers are consulted in registration order; a
    handler that raises is skipped so one faulty provider never blocks a fetch.
    """

    if not _providers:
        return ""
    try:
        host = (urllib.parse.urlsplit(request_url).hostname or "").lower()
    except ValueError:
        return ""
    if not host:
        return ""
    for provider in _providers:
        if not any(_host_matches(pattern, host) for pattern in provider.match_hosts):
            continue
        try:
            header = provider.handler(feed_url, request_url)
        except Exception:  # noqa: BLE001 - a faulty provider must never break a fetch
            continue
        if header:
            return header
    return ""
