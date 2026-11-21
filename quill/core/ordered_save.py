"""One settings file, written in the order its snapshots were taken.

plan.md (settings review) found QUILL Lite could put an older choice back on
disk: a snapshot queued for a background writer, paused just before its write,
landed after a newer synchronous save. The family audit that followed found
the same shape wherever an app both queues snapshots and saves inline -- Quill
Inkwell's preference saver beside its menu toggles, QUILL Cast's record queue
beside its Resume on Launch toggle, Quill Radio's writer beside the save it
makes once that writer has closed, and QUILL's worker threads beside the UI.

The rule, once, for every file:

* **A ticket when the snapshot is taken** (:func:`take_ticket`). A writer that
  saves live state takes it as it writes, which is the same moment.
* **One writer at a time per file** (:func:`ordered_write`), and a ticket older
  than one already written is dropped rather than written: what is on disk is
  already newer than it.

QUILL Lite has its own copy of this rule with a merge on top
(``quill/apps/lite_settings_persistence.py``). wx-free, strict-typed.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from pathlib import Path

__all__ = ["ordered_write", "take_ticket"]


class _Order:
    __slots__ = ("taken", "write_lock", "written")

    def __init__(self) -> None:
        self.taken = 0
        self.written = 0
        self.write_lock = threading.Lock()


_lock = threading.Lock()
_orders: dict[str, _Order] = {}


def _order(path: Path) -> _Order:
    key = os.path.normcase(os.path.abspath(os.fspath(path)))
    with _lock:
        order = _orders.get(key)
        if order is None:
            order = _orders[key] = _Order()
        return order


def take_ticket(path: Path) -> int:
    """Number a snapshot of *path*'s content at the moment it is taken."""
    order = _order(path)
    with _lock:
        order.taken += 1
        return order.taken


def ordered_write(path: Path, write: Callable[[], None], *, ticket: int | None = None) -> bool:
    """Run *write* in ticket order. ``False`` when a newer snapshot was already written.

    *ticket* comes from :func:`take_ticket` when the snapshot was taken; leave it
    out when *write* saves the live state, which is current as it runs. An
    ``OSError`` from *write* propagates, and the file's order is unchanged.
    """
    order = _order(path)
    if ticket is None:
        ticket = take_ticket(path)
    with order.write_lock:
        if ticket <= order.written:
            return False
        write()
        order.written = ticket
        return True
