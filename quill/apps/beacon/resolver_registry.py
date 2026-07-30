"""Process-wide registry of Quillin-supplied location (ULD) resolvers.

A Quillin running in Quill Beacon may contribute a ``beacon.resolver`` that
places a Universal Location Descriptor against current content when the built-in
locator layers (native / structural / text-quote / fuzzy / positional) all fail.
:class:`~quill.core.quillins.app_host.QuillinAppHost` populates this registry
from every enabled resolver contribution, and :func:`quill.apps.beacon.uld.resolve`
consults it as a fallback layer before giving up.

The registry is deliberately tiny and wx-free: a resolver is a callable
``(loc, content) -> dict | None`` returning a resolution mapping (``matched`` /
``confidence`` / ``layer`` / ``position`` / ``message``), or ``None`` when it
cannot place the location. The handler makes no network call of its own, so
consulting the registry never introduces a new egress site.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

#: A resolver callable. Given the ULD as a mapping and the current ``content``,
#: it returns a resolution mapping or ``None`` when it has nothing to contribute.
LocationResolver = Callable[[dict[str, Any], str], dict[str, Any] | None]


@dataclass(frozen=True, slots=True)
class LocationResolverEntry:
    """A registered location resolver and the content kinds it handles."""

    resolver_id: str
    content_types: tuple[str, ...]
    handler: LocationResolver


_resolvers: list[LocationResolverEntry] = []


def register_resolver(
    resolver_id: str, content_types: tuple[str, ...], handler: LocationResolver
) -> None:
    """Register (or replace, by id) a location resolver."""

    clear_resolver(resolver_id)
    _resolvers.append(LocationResolverEntry(resolver_id, tuple(content_types), handler))


def clear_resolver(resolver_id: str) -> None:
    """Remove the resolver with ``resolver_id`` if present."""

    _resolvers[:] = [r for r in _resolvers if r.resolver_id != resolver_id]


def clear_resolvers() -> None:
    """Forget every registered resolver (a full host reload starts here)."""

    _resolvers.clear()


def registered_resolver_ids() -> tuple[str, ...]:
    """The ids of every currently registered resolver (for tests / diagnostics)."""

    return tuple(r.resolver_id for r in _resolvers)


def resolve_from_providers(
    loc: dict[str, Any], content: str, *, content_type: str = ""
) -> dict[str, Any] | None:
    """Return the first non-empty resolution a matching resolver supplies.

    A resolver matches when its ``content_types`` is empty (any) or contains
    ``content_type``. Resolvers are consulted in registration order; a handler
    that raises is skipped so one faulty resolver never blocks the chain. Returns
    ``None`` when no resolver places the location.
    """

    if not _resolvers:
        return None
    for resolver in _resolvers:
        if resolver.content_types and content_type and content_type not in resolver.content_types:
            continue
        try:
            resolution = resolver.handler(loc, content)
        except Exception:  # noqa: BLE001 - a faulty resolver must never break the chain
            continue
        if isinstance(resolution, dict) and resolution.get("matched"):
            return resolution
    return None
