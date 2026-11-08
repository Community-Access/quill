"""Dial tuning's two commands, their Playback menu rows, and Go to Playing Station.

* **Tune as I Move Through Stations** (Alt+Shift+U, a check item): switches dial
  tuning on and off and says the new state, which the screen reader cannot
  know. The same setting as Preferences' check box.
* **Go to Playing Station** (Alt+Shift+P): puts the cursor on the row of the
  station that is playing, in the list the main window shows, or in Favorites
  when it is one. Leaving a list keeps the last station playing, so this is the
  way back to it. The reader reads the row it lands on; nothing more is said
  unless the station is in no list here.

The idea of dial tuning comes from BlindRadio by serrebidev (MIT).
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "append_menu_items",
    "go_to_playing_station",
    "sync_menu",
    "toggle_dial_tuning",
]

TOGGLE_LABEL = "Tune as I &Move Through Stations"
GO_TO_LABEL = "Go to Playing Stat&ion"


def toggle_dial_tuning(app: Any) -> None:
    from quill.ui.radio import dial_tuning_ui

    dial_ui = dial_tuning_ui.for_app(app)
    if dial_ui is None:
        app._announce("Tune as you move is not available in this window.")
        return
    dial_ui.toggle()
    sync_menu(app)


def sync_menu(app: Any) -> None:
    """Keep the check item in step with the setting, however it changed."""
    item_id = getattr(app, "_dial_menu_item_id", None)
    frame = getattr(app, "frame", None)
    menu_bar = frame.GetMenuBar() if frame is not None else None
    if item_id is None or menu_bar is None:
        return
    try:
        menu_bar.Check(int(item_id), bool(getattr(app._radio_history, "dial_tuning", False)))
    except Exception:  # noqa: BLE001 - a menu being rebuilt has nothing to check
        pass


def append_menu_items(app: Any, menu: Any, wx: Any) -> tuple[Any, ...]:
    """Add both rows to *menu*. Returns the ids to pin."""
    toggle_id = wx.NewIdRef()
    menu.AppendCheckItem(toggle_id, app._menu_label(TOGGLE_LABEL, "radio.dial_tuning"))
    menu.Check(toggle_id, bool(getattr(app._radio_history, "dial_tuning", False)))
    app._dial_menu_item_id = toggle_id
    app.frame.Bind(wx.EVT_MENU, lambda _e: toggle_dial_tuning(app), id=toggle_id)
    go_id = wx.NewIdRef()
    menu.Append(go_id, app._menu_label(GO_TO_LABEL, "radio.go_to_playing_station"))
    app.frame.Bind(wx.EVT_MENU, lambda _e: go_to_playing_station(app), id=go_id)
    return (toggle_id, go_id)


def _select_in_tree(tree: Any, matches: Any) -> bool:
    """Select and focus the first row *matches* accepts. True when found."""
    root = tree.GetRootItem()
    if not root.IsOk():
        return False
    pending = [root]
    while pending:
        item = pending.pop(0)
        child, cookie = tree.GetFirstChild(item)
        while child.IsOk():
            if matches(tree.GetItemData(child)):
                tree.EnsureVisible(child)
                tree.SelectItem(child)
                tree.SetFocus()
                return True
            pending.append(child)
            child, cookie = tree.GetNextChild(item, cookie)
    return False


def go_to_playing_station(app: Any) -> None:
    """Alt+Shift+P: the cursor on the playing station's row."""
    from quill.ui.radio.dial_tuning_ui import station_key

    controller = getattr(app, "_radio_controller", None)
    station = getattr(getattr(controller, "state", None), "station", None)
    if station is None:
        app._announce("Nothing is playing.")
        return
    key = station_key(station)
    url = str(getattr(station, "stream_url", "") or "")
    host = getattr(app, "_main_view_host", None)
    if host is not None and host.current == "browse":
        surface = host.surface("browse")
        tree = getattr(surface, "_tree", None)
        if tree is not None and _select_in_tree(
            tree,
            lambda data: (
                isinstance(data, dict)
                and data.get("station") is not None
                and str(getattr(data["station"], "stream_url", "")) == url
            ),
        ):
            return
    favorite = app._radio_favorites.find(key)
    tree = getattr(app, "_favorites_tree", None)
    if favorite is not None and tree is not None:
        if host is not None and host.current != "favorites":
            host.show("favorites", announce=False)
        if _select_in_tree(
            tree,
            lambda data: isinstance(data, tuple) and len(data) == 2 and data[1] == favorite.key,
        ):
            return
    name = str(getattr(station, "display_name", "") or getattr(station, "name", "") or "")
    app._announce(f"{name or 'The station'} is playing. It is not in this list.")
