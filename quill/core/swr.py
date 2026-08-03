"""Stale-while-revalidate for slow-enumerated lists (the Start Menu
pattern, assessment item 11).

The shape every slow list should have::

    render from cache instantly
    rescan on a worker
    compare a structural signature
    if unchanged: keep quiet, touch the cache
    if changed:   rebuild silently, keep the selection

The accessibility insight is the last line: when a background rescan finds
changes, the user is mid-navigation. Announcing "37 items found" or resetting
their selection while they are arrowing is hostile — the list changes silently
underneath them and their position survives.

This module is the pure core: signatures and the refresh decision. The UI side
supplies the worker thread and the rebuild; :class:`~quill.core.generation.
GenerationCounter` guards the completion so a superseded rescan never lands.
wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

__all__ = ["RefreshDecision", "decide_refresh", "structural_signature"]


def structural_signature(
    items: Iterable[object],
    key: Callable[[object], tuple[object, ...]] | None = None,
) -> tuple[tuple[object, ...], ...]:
    """A cheap, order-sensitive signature of a list for change detection.

    By default each item contributes ``(str(item).casefold(),)``; pass *key*
    to pick the fields that constitute identity (name, target, source, ...).
    A tuple compare beats hashing serialized JSON: no serialization cost, and
    equality short-circuits on the first differing item.
    """
    if key is None:
        return tuple((str(item).casefold(),) for item in items)
    return tuple(tuple(key(item)) for item in items)


@dataclass(frozen=True, slots=True)
class RefreshDecision:
    """What the UI should do with a completed rescan."""

    changed: bool

    @property
    def announce(self) -> bool:
        """Never announce a background refresh; the user did not ask for it."""
        return False

    @property
    def keep_selection(self) -> bool:
        """Always preserve the user's position through a silent rebuild."""
        return True


def decide_refresh(
    cached_signature: tuple[tuple[object, ...], ...],
    fresh_signature: tuple[tuple[object, ...], ...],
) -> RefreshDecision:
    """Compare signatures: unchanged means say and change nothing."""
    return RefreshDecision(changed=cached_signature != fresh_signature)
