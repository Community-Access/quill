"""Saving the station that is playing, and what every door onto it says.

Split out of :mod:`quill.apps.radio` under GATE-11 (extract, never rebaseline)
when the action gained a second and third home.

Until 2026-08-21 this existed only as a button on the main window: no menu item,
no key. So removing that button would have removed the capability outright. It
could not simply move into the favorites tree's context menu either -- the
station it acts on is very often one you found in Browse, which is exactly the
station that is *not* in the tree.

It now has three surfaces -- the Station menu (Ctrl+Shift+F), the summoned
player panel, and, until it was removed, the main-window button -- and one rule:
they all say the same thing at the same time, because they are all reading the
same two facts. That rule is why this is a module rather than three refreshers.

wx is touched only through widgets the host already owns.
"""

from __future__ import annotations

from typing import Any


def state_of(host: Any) -> tuple[bool, bool]:
    """``(something is playing, and it is already a favorite)``. Never raises."""
    controller = getattr(host, "_radio_controller", None)
    station = getattr(getattr(controller, "state", None), "station", None)
    if station is None:
        return False, False
    favorites = getattr(host, "_radio_favorites", None)
    try:
        return True, bool(favorites is not None and favorites.contains(station))
    except Exception:  # noqa: BLE001 - a label must never break the window
        return True, False


def refresh(host: Any) -> None:
    """Re-label the menu item and the button, and refuse when nothing is on."""
    playing, saved = state_of(host)
    _refresh_menu_item(host, playing=playing, saved=saved)
    _refresh_button(host, playing=playing, saved=saved)


def _refresh_menu_item(host: Any, *, playing: bool, saved: bool) -> None:
    """Station > Add/Remove Playing Station, kept true to what is on air.

    Disabled with nothing playing: there is no station to save, and an item that
    looks available and then refuses is worse than one that says no up front.
    """
    menu_id = getattr(host, "_fav_toggle_menu_id", None)
    menu_bar = host.frame.GetMenuBar() if getattr(host, "frame", None) is not None else None
    if menu_id is None or menu_bar is None:
        return
    item = menu_bar.FindItemById(int(menu_id))
    if item is None:
        return
    verb, preposition = ("Remove", "from") if saved else ("Add", "to")
    label = host._menu_label(
        f"{verb} Playing Station {preposition} &Favorites",
        "radio.toggle_playing_favorite",
    )
    if item.GetItemLabel() != label:
        item.SetItemLabel(label)
    item.Enable(playing)


def _refresh_button(host: Any, *, playing: bool, saved: bool) -> None:
    """The main window's button, for as long as any surface still has one."""
    from quill.ui.accessible_names import set_accessible_name

    button = getattr(host, "_favorite_toggle_btn", None)
    if button is None:
        return
    label = "Remove from &Favorites" if saved else "Add to &Favorites"
    if button.GetLabel() != label:
        button.SetLabel(label)
        set_accessible_name(
            button,
            "Remove the playing station from favorites"
            if saved
            else "Add the playing station to favorites",
        )
    button.Enable(playing)
