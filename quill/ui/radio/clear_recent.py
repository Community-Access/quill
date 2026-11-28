"""Clear Recent Searches...: forget the searches and websites Radio remembers.

Two lists ride ``radio_history.json``: the station searches Find Stations has
run (:mod:`quill.core.radio.search_history`) and the websites Find Streams
found a live stream on (:mod:`quill.core.radio.recent_websites`). This command
clears both, after one question that names only the lists that have entries:
"Clear 15 recent station searches and 10 recent websites? No station or
favorite is removed." No is the default, so Enter keeps them.

It sits directly after Find Streams from a Website... in Quill Radio's Station
menu and QUILL's Internet Radio menu. With nothing to clear it stays enabled
and says so, because a greyed item says nothing about why. When Find Stations
is open, its search box's list is emptied too, and the text in it is kept.
"""

from __future__ import annotations

import weakref
from typing import Any

__all__ = [
    "LABEL",
    "QUILL_LABEL",
    "add_menu_item",
    "clear_recent_searches",
    "confirm_text",
    "done_text",
    "register_find_stations",
]

#: Quill Radio's Station menu. L is shared with Play Last Station: the menu has
#: more items than letters, and no letter of this label is free there. The key
#: is written into the label, like the menu's other settings rows.
LABEL = "C&lear Recent Searches...\tCtrl+Alt+Shift+Backspace"
#: QUILL's Internet Radio menu, where Play &Last Station also has L and N is
#: free; QUILL adds the Alt path to the label itself (quill.ui.menu_routes).
QUILL_LABEL = "Clear Rece&nt Searches..."
TITLE = "Clear Recent Searches"
NOTHING = "There are no recent searches or websites to clear."

_open_find_stations: weakref.WeakSet[Any] = weakref.WeakSet()


def register_find_stations(dialog: Any) -> None:
    """Find Stations registers itself, so a clear can refresh its box."""
    _open_find_stations.add(dialog)


def _counted(count: int, one: str, many: str) -> str:
    return f"{count:,} {one if count == 1 else many}"


def confirm_text(searches: int, websites: int) -> str:
    """The question, naming only the lists that have entries."""
    parts = []
    if searches:
        parts.append(_counted(searches, "recent station search", "recent station searches"))
    if websites:
        parts.append(_counted(websites, "recent website", "recent websites"))
    return f"Clear {' and '.join(parts)}? No station or favorite is removed."


def done_text(searches: int, websites: int) -> str:
    """The one sentence after Yes."""
    parts = []
    if searches:
        parts.append(_counted(searches, "recent search", "recent searches"))
    if websites:
        parts.append(_counted(websites, "recent website", "recent websites"))
    return f"Cleared {' and '.join(parts)}."


def _confirm(host: Any, wx: Any, message: str) -> bool:
    from quill.ui import modal_stack
    from quill.ui.dialog_contract import show_modal_dialog

    dialog = wx.MessageDialog(
        modal_stack.parent_window(host),
        message,
        TITLE,
        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
    )
    try:
        return bool(show_modal_dialog(dialog, TITLE) == wx.ID_YES)
    finally:
        dialog.Destroy()


def _refresh_find_stations() -> None:
    for dialog in list(_open_find_stations):
        try:
            box = dialog._name_ctrl
            text = box.GetValue()
            dialog._recent_searches = ()
            dialog._fill_recent_searches()
            if box.GetValue() != text:
                box.ChangeValue(text)
        except RuntimeError:  # the dialog was destroyed meanwhile
            continue


def _forget_last_results() -> None:
    """The saved Find Streams results go with them (not counted in the sentence)."""
    from quill.core.paths import app_data_dir
    from quill.core.radio import last_results

    last_results.clear(app_data_dir())


def clear_recent_searches(host: Any) -> None:
    """Ask, then clear both lists and say once what was cleared."""
    import wx

    history = host._radio_history
    searches = len(tuple(getattr(history, "recent_searches", ()) or ()))
    websites = len(tuple(getattr(history, "recent_websites", ()) or ()))
    if not searches and not websites:
        host._announce(NOTHING)
        return
    if not _confirm(host, wx, confirm_text(searches, websites)):
        return
    history.recent_searches = ()
    history.recent_websites = ()
    host._save_radio_history()
    _forget_last_results()
    _refresh_find_stations()
    host._announce(done_text(searches, websites))


def add_menu_item(host: Any, menu: Any, wx: Any, label: str) -> Any:
    """Append the item to *menu*, bound on *host*'s frame; returns its id."""
    item_id = wx.NewIdRef()
    menu.Append(item_id, label)
    host.frame.Bind(wx.EVT_MENU, lambda _e: clear_recent_searches(host), id=item_id)
    return item_id
