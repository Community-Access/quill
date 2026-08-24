"""One key for every place in an app, in the order you choose -- the machinery.

Quill Radio has had this since :mod:`quill.core.radio.go_to`: Ctrl+G opens a
short numbered list of *places*, you press the number, and you are there. The
design notes live in that module and are worth reading, because the value is
entirely in one property -- **the numbering does not move**. The Window menu
does not answer the same question, precisely because it renumbers: it lists
windows that are open, in the order they opened, so a place might be 3 today
and 5 tomorrow, and a place that is closed has no number at all. Position can
never become memory.

QUILL Cast has at least as many places worth a key -- Inbox, Queue, a pinned
view, a folder, a playlist -- and had no Go To at all (list.md 5.2). What it
needed was Radio's *feature*, not Radio's *destinations*, so this module is the
part that is genuinely the same and each app keeps its own catalogue:

* a destination is an id, a title, the host method that opens it, and the key
  it already answers to, if it has one;
* a layout is the first ten of them in an order the listener arranged;
* everything known and not in the layout is pooled, **derived rather than
  stored**, so a destination added in a later release lands in the pool and
  nobody's numbering moves on upgrade. The pool is the protection; empty slots
  would not have been.

Ten positions, 1-9 then 0, because that is where the number row ends. An
eleventh entry would have no key, and a menu where some rows have a number and
others do not is worse than a shorter menu.

wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "MAX_ENTRIES",
    "Destination",
    "GoToLayout",
    "available_ids",
    "default_order",
    "load_layout",
    "lookup",
    "position_key",
    "refusal_for_adding",
    "refusal_for_removing",
    "repair",
    "save_layout",
]

#: Ten, because 1-9 then 0 is where the number row ends.
MAX_ENTRIES = 10


@dataclass(frozen=True, slots=True)
class Destination:
    """One place, and the host method that opens it.

    *key* is the destination's own direct shortcut where it still has one,
    shown on its row so the popup teaches: somebody who uses Go To 2 for a
    month learns the direct key by reading it every time, and graduates off the
    popup. A shortcut that trains you out of itself is better than one that
    keeps you.
    """

    id: str
    title: str
    opens: str
    key: str = ""


@dataclass(slots=True)
class GoToLayout:
    """What is in the menu, in order. Everything known and not listed is pooled."""

    order: list[str] = field(default_factory=list)
    #: The catalogue this layout is drawn from. Carried on the layout rather
    #: than passed alongside it everywhere, so a layout is a complete answer to
    #: "what does this menu contain" and a dialog cannot be handed one app's
    #: order with the other app's places.
    catalogue: tuple[Destination, ...] = ()

    def _by_id(self) -> dict[str, Destination]:
        return {destination.id: destination for destination in self.catalogue}

    def ordered(self) -> list[Destination]:
        """The menu, as destinations, in position order."""
        known = self._by_id()
        return [known[i] for i in self.order if i in known]

    def available_ids(self) -> list[str]:
        """Everything not in the menu, in catalogue order."""
        chosen = set(self.order)
        return [d.id for d in self.catalogue if d.id not in chosen]

    def available(self) -> list[Destination]:
        known = self._by_id()
        return [known[i] for i in self.available_ids()]


def position_key(index: int) -> str:
    """The key that jumps to *index*: ``"1"``-``"9"`` then ``"0"``.

    0 sits where a tenth key would be, because that is where a hand goes last.
    """
    if index < 0 or index >= MAX_ENTRIES:
        return ""
    return "0" if index == MAX_ENTRIES - 1 else str(index + 1)


def lookup(catalogue: Sequence[Destination], destination_id: str) -> Destination | None:
    for destination in catalogue:
        if destination.id == destination_id:
            return destination
    return None


def default_order(catalogue: Sequence[Destination]) -> tuple[str, ...]:
    """The first ten of the catalogue, which is what a fresh install gets."""
    return tuple(d.id for d in catalogue[:MAX_ENTRIES])


def available_ids(catalogue: Sequence[Destination], order: Sequence[str]) -> list[str]:
    chosen = set(order)
    return [d.id for d in catalogue if d.id not in chosen]


def repair(layout: GoToLayout) -> GoToLayout:
    """Drop ids we no longer know, de-duplicate, and cap at ten.

    An unknown id is dropped rather than raising: a layout saved by a newer
    build, or one naming a destination since removed, must degrade to a working
    menu rather than to no app.
    """
    known = {d.id for d in layout.catalogue}
    seen: set[str] = set()
    order: list[str] = []
    for destination_id in layout.order:
        if destination_id in known and destination_id not in seen:
            seen.add(destination_id)
            order.append(destination_id)
        if len(order) == MAX_ENTRIES:
            break
    if not order:
        order = list(default_order(layout.catalogue))
    return GoToLayout(order=order, catalogue=layout.catalogue)


def refusal_for_adding(layout: GoToLayout) -> str:
    """Why another entry cannot be added, or ``""`` when one can.

    A sentence rather than a disabled button: a control that says only "no" is
    a control that has to be guessed at.
    """
    if len(layout.order) < MAX_ENTRIES:
        return ""
    return (
        "The Go To menu is full: it holds ten places, numbered 1 to 9 and then "
        "0, and the number row has no eleventh key. Remove one to make room."
    )


def refusal_for_removing(layout: GoToLayout, destination_id: str) -> str:
    """Why this entry cannot be removed, or ``""`` when it can."""
    if destination_id not in layout.order:
        return ""
    if len(layout.order) > 1:
        return ""
    return "The Go To menu cannot be empty. Add another place first, then remove this one."


def load_layout(data_dir: Path, *, file_name: str, catalogue: Sequence[Destination]) -> GoToLayout:
    """Read the saved menu, repaired. A missing or corrupt file is the default."""
    raw = read_json(data_dir / file_name, {})
    order: list[str] = []
    if isinstance(raw, dict):
        entries = raw.get("order")
        if isinstance(entries, list):
            order = [str(entry) for entry in entries if isinstance(entry, str)]
    catalogue = tuple(catalogue)
    if not order:
        return GoToLayout(order=list(default_order(catalogue)), catalogue=catalogue)
    return repair(GoToLayout(order=order, catalogue=catalogue))


def save_layout(data_dir: Path, layout: GoToLayout, *, file_name: str) -> None:
    write_json_atomic(data_dir / file_name, {"order": list(repair(layout).order)})
