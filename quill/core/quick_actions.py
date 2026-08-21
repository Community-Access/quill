"""Quick Actions: the actions you use, in the order you use them.

The idea is Earshot's headline feature -- a user-ordered action list per content
type, whose first entry is the default. The VoiceOver rotor it feeds has no
desktop equivalent, so translating it literally would be pointless, but the
*idea* translates to three things a Windows app does better than a phone:

1. a chosen **default action for Enter** on a row;
2. **context-menu ordering**, so the four items a given listener actually uses
   are the first four, in the same place, every time;
3. **direct keys** -- Ctrl+1 through Ctrl+9 run the first nine actions of
   whichever list has focus, so the common ones need no menu at all.

This module is the app-independent half: the record, the ordering, the repair,
and the store. An app supplies its own **catalogue** -- a mapping of context id
to the actions that context offers -- and its own store filename, and gets all
of the above for nothing.

**Repair matters more than it sounds.** An order saved by a later version can
name actions this build has never heard of, and one saved by an earlier version
is missing everything added since. Dropping unknown ids and appending missing
ones means an upgrade, a downgrade, or a settings file that arrived from another
machine can never stand a listener in front of an empty context menu.

**Nine is nine in both apps.** ``DIRECT_KEY_COUNT`` lives here rather than in
either app so the muscle memory transfers: Ctrl+3 is the third action of
whatever list has focus, in Cast and in Radio alike.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "DIRECT_KEY_COUNT",
    "QuickAction",
    "QuickActionOrders",
    "load_quick_actions",
    "save_quick_actions",
]

#: How many actions the direct Ctrl+N keys reach. Nine because Ctrl+0 is not a
#: tenth, and because a listener who has to count past nine has a list that
#: wants reordering rather than more keys.
DIRECT_KEY_COUNT = 9

#: An app's action catalogue: context id -> the actions that context offers,
#: in the shipped default order.
Catalogue = Mapping[str, tuple["QuickAction", ...]]


@dataclass(frozen=True, slots=True)
class QuickAction:
    """One orderable action: a stable id and the words the listener sees."""

    id: str
    label: str
    #: Shown in the reorder dialog's description field, so the list is
    #: self-explanatory without a manual.
    description: str = ""


@dataclass(slots=True)
class QuickActionOrders:
    """One ordered list per context, and the catalogue it is checked against.

    The catalogue travels with the orders rather than being looked up globally,
    so two apps' orders can exist in one process without either being able to
    repair itself against the other's actions.
    """

    catalogue: Catalogue
    orders: dict[str, list[str]]

    @classmethod
    def defaults(cls, catalogue: Catalogue) -> QuickActionOrders:
        """Every context in its shipped order."""
        return cls(
            catalogue=catalogue,
            orders={context: default_order(catalogue, context) for context in catalogue},
        )

    def order(self, context: str) -> list[str]:
        """The repaired order for *context* (empty for an unknown context)."""
        if context not in self.catalogue:
            return []
        return repair_order(self.catalogue, context, self.orders.get(context, []))

    def actions(self, context: str) -> list[QuickAction]:
        """The repaired order as real :class:`QuickAction` records."""
        by_id = {action.id: action for action in self.catalogue.get(context, ())}
        return [by_id[action_id] for action_id in self.order(context) if action_id in by_id]

    def default_action(self, context: str) -> str:
        """The id Enter runs in *context* -- the first in the list."""
        order = self.order(context)
        return order[0] if order else ""

    def set_order(self, context: str, ids: list[str]) -> None:
        if context in self.catalogue:
            self.orders[context] = repair_order(self.catalogue, context, ids)

    def reset(self, context: str) -> None:
        self.set_order(context, default_order(self.catalogue, context))

    def copy(self) -> QuickActionOrders:
        """An independent copy, for a dialog that has to be cancellable."""
        return QuickActionOrders(
            catalogue=self.catalogue,
            orders={context: list(ids) for context, ids in self.orders.items()},
        )

    def to_dict(self) -> dict[str, list[str]]:
        return {context: list(self.order(context)) for context in self.catalogue}

    @classmethod
    def from_dict(cls, catalogue: Catalogue, data: object) -> QuickActionOrders:
        orders = cls.defaults(catalogue)
        if not isinstance(data, dict):
            return orders
        for context in catalogue:
            raw = data.get(context)
            if isinstance(raw, list):
                orders.set_order(context, [str(entry) for entry in raw])
        return orders


def default_order(catalogue: Catalogue, context: str) -> list[str]:
    """The shipped order for one context (also the Reset target)."""
    return [action.id for action in catalogue.get(context, ())]


def repair_order(catalogue: Catalogue, context: str, ids: list[str]) -> list[str]:
    """A saved order made safe for this build.

    Unknown ids are dropped (an action this build does not have), duplicates
    collapse to their first appearance, and every known action missing from the
    list is appended in its default position -- so an action added in a later
    release shows up at the end of an existing listener's menu instead of not at
    all.
    """
    known = {action.id for action in catalogue.get(context, ())}
    seen: set[str] = set()
    ordered: list[str] = []
    for action_id in ids:
        if action_id in known and action_id not in seen:
            seen.add(action_id)
            ordered.append(action_id)
    ordered.extend(
        action_id for action_id in default_order(catalogue, context) if action_id not in seen
    )
    return ordered


def load_quick_actions(
    data_dir: Path, *, file_name: str, catalogue: Catalogue
) -> QuickActionOrders:
    """Read the saved order. An absent or broken file reads as the default.

    A store of its own rather than fields on an app's settings record: no
    per-item override ever wants its own action order, and putting them in the
    settings would push several lists through every clone of it.
    """
    try:
        raw = json.loads((data_dir / file_name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return QuickActionOrders.defaults(catalogue)
    return QuickActionOrders.from_dict(catalogue, raw)


def save_quick_actions(data_dir: Path, orders: QuickActionOrders, *, file_name: str) -> None:
    """Persist the order atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(data_dir / file_name, orders.to_dict())
