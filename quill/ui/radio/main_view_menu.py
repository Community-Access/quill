"""View > Main Window Shows: the five radio items, and switching live.

Radio items rather than a submenu of commands, because it is a choice of
exactly one and a checkmark is how a menu says which one is in force. The
alternative -- five plain items -- makes somebody open the menu, pick one, and
listen to the announcement to find out where they already were.

Every item carries a keyboard route, which is the house rule and not a
preference: Ctrl+Shift+1..5, in the order the views are listed. They are digits
because the views are a numbered set with no mnemonic that survives renaming,
and they sit one modifier away from the window manager's own Ctrl+1..9: one
question is *which window*, the other is *what this window shows*. Ctrl+Alt+
digits were the first choice and are already Text Size and Video Size.

The switch is immediate and persists. It is not a restart-required setting: a
setting that changes where you land, and then does not, is worse than one that
was never offered.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import main_view

#: Accelerator per view, in :data:`main_view.MAIN_VIEWS` order.
KEYS: tuple[str, ...] = (
    "Ctrl+Shift+1",
    "Ctrl+Shift+2",
    "Ctrl+Shift+3",
    "Ctrl+Shift+4",
    "Ctrl+Shift+5",
)


def append(app: Any, menu: Any, wx: Any) -> tuple[Any, ...]:
    """Append the submenu. Returns the ids for the caller to pin."""
    submenu = wx.Menu()
    ids = []
    current = main_view.normalize(getattr(app._radio_history, "main_view", ""))
    app._main_view_item_ids = {}
    for index, (view_id, label) in enumerate(main_view.MAIN_VIEWS):
        item_id = wx.NewIdRef()
        key = KEYS[index] if index < len(KEYS) else ""
        item = submenu.AppendRadioItem(item_id, f"{label}\t{key}" if key else label)
        item.SetHelp(main_view.description(view_id))
        submenu.Check(item_id, view_id == current)
        app.frame.Bind(wx.EVT_MENU, lambda _e, v=view_id: switch(app, v), id=item_id)
        app._main_view_item_ids[view_id] = item_id
        ids.append(item_id)
    menu.AppendSubMenu(submenu, "&Main Window Shows")
    return tuple(ids)


def switch(app: Any, view_id: str) -> None:
    """Show *view_id* in the main window and remember the choice.

    Saved before it is shown, so a build that cannot show a surface still
    records what was asked for rather than silently reverting -- and the
    host says out loud which view it fell back to.
    """
    from quill.core.paths import app_data_dir
    from quill.core.radio import history as radio_history

    wanted = main_view.normalize(view_id)
    host = getattr(app, "_main_view_host", None)
    if host is None:
        return
    if host.current == wanted:
        # Already there. Take focus to it anyway: the same item pressed twice
        # is somebody trying to get back to the list, not a mistake.
        host.focus_current()
        return
    app._radio_history.main_view = wanted
    radio_history.save_history(app_data_dir(), app._radio_history)
    shown = host.show(wanted)
    if shown != wanted:
        # The fallback is what is actually on screen, so it is what the menu
        # must show and what is stored -- a checkmark on a view that failed to
        # build is a menu lying about where you are.
        app._radio_history.main_view = shown
        radio_history.save_history(app_data_dir(), app._radio_history)
    sync_checkmarks(app)


def sync_checkmarks(app: Any) -> None:
    """Pin the radio items to the view actually showing."""
    ids = getattr(app, "_main_view_item_ids", None)
    menu_bar = app.frame.GetMenuBar()
    if not ids or menu_bar is None:
        return
    host = getattr(app, "_main_view_host", None)
    current = host.current if host is not None else main_view.FAVORITES
    for view_id, item_id in ids.items():
        try:
            menu_bar.Check(int(item_id), view_id == current)
        except Exception:  # noqa: BLE001 - a stale id must not break the menu
            continue


__all__ = ["KEYS", "append", "switch", "sync_checkmarks"]
