"""Undo stack for QuillBeacon (PRD 18.5, 44.3).

A small, dependency-free undo manager. Each mutating action pushes an inverse
operation (a callable) plus a human label. ``undo`` pops and runs the most
recent inverse. Bulk operations push a single composite inverse that restores
every affected beacon to its pre-action snapshot, so one Undo reverts the whole
batch as a step -- never one item at a time against the user's expectation.

The manager holds no wx references; it is unit-testable. The shell passes an
optional announcer callable so Undo can speak what it reverted.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Any


class UndoManager:
    def __init__(self, announcer: Callable[[str], None] | None = None, limit: int = 100) -> None:
        self._stack: deque[tuple[str, Callable[[], None]]] = deque(maxlen=limit)
        self.announcer = announcer

    def push(self, label: str, inverse: Callable[[], None]) -> None:
        """Record an inverse operation with a human-readable label."""
        self._stack.append((label, inverse))

    def can_undo(self) -> bool:
        return bool(self._stack)

    def undo(self) -> str | None:
        """Run the most recent inverse. Returns the label, or None if empty."""
        if not self._stack:
            if self.announcer:
                self.announcer("Nothing to undo")
            return None
        label, inverse = self._stack.pop()
        try:
            inverse()
        except Exception as ex:  # never let a failed undo lose the label
            if self.announcer:
                self.announcer(f"Undo failed: {ex}")
            return label
        if self.announcer:
            self.announcer(f"Undid: {label}")
        return label

    def clear(self) -> None:
        self._stack.clear()

    def depth(self) -> int:
        return len(self._stack)


def snapshot_beacons(store, beacon_ids: list[str]) -> list[Any]:
    """Capture full pre-state Beacon objects for a set of ids (for bulk undo).

    ``get_beacon`` populates the joined fields (tags, collections, locations),
    so a snapshot is a complete, restorable copy. ``put_beacon`` re-inserts the
    row and re-syncs its join/FTS rows, so restoring works even after a permanent
    delete (the row is gone -- put_beacon re-creates it).
    """
    out = []
    for bid in beacon_ids:
        b = store.get_beacon(bid)
        if b is not None:
            out.append(b)
    return out


def restore_beacons(store, snaps: list[Any]) -> None:
    """Apply a snapshot back to the store (inverse of a bulk op).

    Re-puts each captured Beacon; put_beacon upserts the row and re-syncs tags,
    collections, locations, and the FTS index, so the item reappears exactly as
    it was -- including after a permanent delete.
    """
    for b in snaps:
        store.put_beacon(b)
