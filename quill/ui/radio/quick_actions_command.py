"""Station > Quick Actions... in Quill Radio, and the order it produces.

Three small jobs, none of which belongs in a frame at its GATE-11 ceiling:
open the shared reorder dialog on Radio's catalogue, keep the result, and hand
the current order to whoever is building a row menu.

**The order is loaded once and kept on the host.** A row menu is built on every
right-click, and reading a JSON file on each one would be a file read per
keystroke for a preference that changes about twice a year.
"""

from __future__ import annotations

from typing import Any

from quill.core.quick_actions import QuickActionOrders

__all__ = ["current_orders", "open_quick_actions", "order_row_actions"]

_ATTR = "_radio_quick_actions"


def current_orders(host: Any) -> QuickActionOrders | None:
    """Radio's action order, loaded once per session. ``None`` if it will not load."""
    cached = getattr(host, _ATTR, None)
    if isinstance(cached, QuickActionOrders):
        return cached
    try:
        from quill.core.paths import app_data_dir
        from quill.core.radio.quick_actions import load_radio_quick_actions

        orders = load_radio_quick_actions(app_data_dir())
    except Exception:  # noqa: BLE001 - a preference that will not load is not fatal
        return None
    setattr(host, _ATTR, orders)
    return orders


def order_row_actions(host: Any, actions: list[Any], context: str) -> list[Any]:
    """A row's built menu, in the listener's preferred order.

    The row still decides *which* actions it has -- a station already in
    Favorites offers Remove and not Add, and a live stream offers no Download.
    The preference only decides the order, so nothing here can put an action on
    a row that cannot perform it.
    """
    from quill.core.radio.quick_actions import apply_order

    return apply_order(actions, current_orders(host), context)


def open_quick_actions(host: Any) -> None:
    """The reorder window, on Radio's own catalogue."""
    from quill.core.paths import app_data_dir
    from quill.core.radio.quick_actions import CONTEXT_LABELS, save_radio_quick_actions
    from quill.ui.media.quick_actions_dialog import QuickActionsDialog

    orders = current_orders(host)
    if orders is None:
        announce = getattr(host, "_announce", None)
        if callable(announce):
            announce("Quick Actions could not be opened.")
        return
    dialog = QuickActionsDialog(
        getattr(host, "frame", None) or host,
        orders=orders,
        context_labels=CONTEXT_LABELS,
        announce_cb=getattr(host, "_announce", None),
        title="Quick Actions",
    )
    edited = dialog.show()
    if edited is None:
        return
    setattr(host, _ATTR, edited)
    try:
        save_radio_quick_actions(app_data_dir(), edited)
    except Exception:  # noqa: BLE001 - an order that could not be saved still applies now
        pass
    announce = getattr(host, "_announce", None)
    if callable(announce):
        announce("Quick Actions saved.")
