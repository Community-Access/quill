"""Keeping a *place* in Favorites, and the captions toggle beside it.

Split out of ``browse_tree_menu`` under GATE-11 (extract, never rebaseline).
Both concerns here are about acting on something other than the row: one saves
the branch you are standing in, the other reaches the video that is playing.

**Favorites used to hold only things you play.** So the only rows that could be
saved were the leaves -- you could favorite one episode of a show and not the
show itself ("add to favorites should be in the podcast context menu or frankly
all context menus for all types", 2026-08-18). A *place* is a favorite whose
identity is a browse node id rather than a stream address
(:func:`quill.core.radio.favorites.place_station`), so saving a show, a book, a
followed channel or a genre stores the way back to it, and opening it from
Favorites lands exactly where opening it from its own source would -- with
every verb that branch offers, because it *is* that branch.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.browse_nodes import split_id


def toggle_captions(host: Any) -> None:
    """Captions on or off for the video playing, from the row playing it."""
    from quill.ui.radio import video_commands

    try:
        video_commands.toggle_captions(host)
    except Exception as error:  # noqa: BLE001 - a menu action reports, never crashes
        announce = getattr(host, "_announce", None)
        if callable(announce):
            announce(f"Captions could not be changed. {error}.")


def place_record(dialog: Any, node: Any, kind: str, args: list[str]) -> Any:
    """The favorites record standing for this branch."""
    from quill.core.radio.browse_nodes import make_id
    from quill.core.radio.favorites import place_station

    node_id = make_id(kind, *args) if args else kind
    label = dialog._tree.GetItemText(node).split("  (")[0]
    return place_station(node_id, label, source=kind)


def save_place(dialog: Any, node: Any, kind: str, args: list[str]) -> None:
    """Keep this branch in Favorites -- a show, a book, a channel, a genre."""
    station = place_record(dialog, node, kind, args)
    dialog._favorites.add(station)
    dialog._on_favorites_changed()
    dialog._refresh_favorites_branch()
    dialog._announce(f"Added {station.name} to Favorites. It opens back to here.")


def forget_place(dialog: Any, node: Any) -> None:
    """Drop a saved place; nothing it contains is touched."""
    data = dialog._node_data(node) or {}
    kind, args = split_id(str(data.get("node_id") or ""))
    station = place_record(dialog, node, kind, args)
    label = station.name
    dialog._favorites.remove(station.station_uuid)
    dialog._on_favorites_changed()
    dialog._refresh_favorites_branch()
    dialog._announce(f"Removed {label} from Favorites.")


def playing_has(dialog: Any, station: Any, what: str) -> bool:
    """Whether the thing playing has chapters (or captions). Never raises.

    Only asked about the row that is actually playing: the controller can only
    answer about what it holds, and a row further down the list is not it.
    """
    if station is None or not dialog._is_playing(station):
        return False
    controller = getattr(dialog, "_controller", None)
    try:
        if what == "chapters":
            return bool(controller.chapters())
        return bool(getattr(controller, "has_captions", lambda: False)())
    except Exception:  # noqa: BLE001 - a menu must never fail on a player probe
        return False
