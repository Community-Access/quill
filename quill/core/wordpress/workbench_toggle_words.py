"""What a toggle row says it will do to the selected row (review item 29).

"Activate or Deactivate" made a listener work out which way it would go. The
Workbench now names the one thing the row will do -- "Deactivate" on an active
plugin, "Stop Offering to Ask the Site" on an offered ability -- in the Item
menu and the context menu alike. :func:`toggle_label` gives the words; the
frame keeps the row's access letter (:func:`keep_access_key`).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

__all__ = ["toggle_label"]


def _plugin(row: Any, _offered: Callable[[Any], bool]) -> str:
    return "Deactivate" if row.status in ("active", "network-active") else "Activate"


def _feed(row: Any, _offered: Callable[[Any], bool]) -> str:
    return "Deactivate Feed..." if row.status == "active" else "Activate Feed..."


def _offer(row: Any, offered: Callable[[Any], bool]) -> str:
    return "Stop Offering to Ask the Site" if offered(row) else "Offer to Ask the Site"


def _auto_add(row: Any, _offered: Callable[[Any], bool]) -> str:
    on = bool(row.raw.get("auto_add")) if isinstance(row.raw, Mapping) else False
    return "Stop Adding New Pages Automatically..." if on else "Add New Pages Automatically..."


def _gateway(row: Any, _offered: Callable[[Any], bool]) -> str:
    return "Turn Off..." if row.status == "active" else "Turn On..."


_WORDS: Mapping[str, Callable[[Any, Callable[[Any], bool]], str]] = {
    "toggle_gateway": _gateway,
    "toggle_plugin": _plugin,
    "toggle_feed": _feed,
    "offer_to_ask": _offer,
    "menu_auto_add": _auto_add,
}


def toggle_label(command_id: str, row: Any, offered: Callable[[Any], bool]) -> str:
    """The one thing *command_id* will do to *row*; "" when it is not a toggle.

    *offered* says whether Ask the Site offers an ability row (kept on this
    computer, so the provider answers it).
    """
    words = _WORDS.get(command_id.rsplit(".", 1)[-1])
    if words is None or row is None:
        return ""
    return words(row, offered)
