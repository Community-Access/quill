"""The Find Streams menus and keys, with fixed letters (wx).

Two menus, built fresh each time they open, and one key table:

* **Sort and Filter** (the button, and a submenu of the context menu):
  &Scan order; &Name, A to Z; &Bitrate, highest first; L&isteners, most first
  (only when a row has a count); &Live streams only; &All formats; &MP3 only;
  AA&C only; &Ogg only; &HLS only; O&pus only (only the formats present). The
  current choice is checked explicitly.
* **The list's context menu** mirrors the buttons and shows their keys:
  &Test (Enter); &Use This Link...; Add to &Favorites; Save as Play&list...
  (Ctrl+S); &Copy Stream Link(s) (Ctrl+C);
  &Scan This Stream's Server (only when it applies); then F&ind... (Ctrl+F),
  Find &Next (F3), Find &Previous (Shift+F3), Select &All (Ctrl+A); then the
  S&ort and Filter submenu.
* **Keys**, read by the dialog's key hook in the list only, with modifiers
  matched exactly: Ctrl+A, Ctrl+C, Ctrl+F, Ctrl+S, F3 and Shift+F3. Ctrl+Shift+C
  stays Chapters, and Ctrl+Up and Ctrl+Down stay the volume.

The letters are written out, never generated, so a test can pin them and a
listener can learn them. The menu-accelerator gate walks menu bars, not pop-up
menus, so ``tests/unit/ui/radio/test_find_streams_dialog.py`` pins these.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.radio import find_streams_view as view
from quill.core.radio.page_links import PageStreamCandidate

__all__ = [
    "ALL_FORMATS_LABEL",
    "FORMAT_LABELS",
    "LIVE_ONLY_LABEL",
    "MENU_NAMES",
    "ORDER_LABELS",
    "add_label",
    "context_menu",
    "copy_label",
    "key_command",
    "save_label",
    "sort_menu",
]

ORDER_LABELS = {
    view.SCAN: "&Scan order",
    view.NAME: "&Name, A to Z",
    view.BITRATE: "&Bitrate, highest first",
    view.LISTENERS: "L&isteners, most first",
}
LIVE_ONLY_LABEL = "&Live streams only"
ALL_FORMATS_LABEL = "&All formats"
FORMAT_LABELS = {
    "MP3": "&MP3 only",
    "AAC": "AA&C only",
    "Ogg": "&Ogg only",
    "HLS": "&HLS only",
    "Opus": "O&pus only",
}

#: Every command a menu or key can name; the dialog makes one id for each.
MENU_NAMES = (
    *(f"order:{order}" for order in view.ORDERS),
    "live_only",
    "format:",
    *(f"format:{name}" for name in view.FORMATS),
    "test",
    "use",
    "add",
    "save",
    "copy",
    "server",
    "find",
    "find_next",
    "find_previous",
    "select_all",
)


def add_label(count: int) -> str:
    return f"Add {count} to &Favorites" if count > 1 else "Add to &Favorites"


def save_label(count: int) -> str:
    return f"Save {count} as Play&list..." if count > 1 else "Save as Play&list..."


def copy_label(count: int) -> str:
    return f"&Copy {count} Stream Links\tCtrl+C" if count > 1 else "&Copy Stream Link\tCtrl+C"


def sort_menu(
    wx: Any,
    ids: dict[str, Any],
    candidates: Sequence[PageStreamCandidate],
    state: view.ViewState,
) -> Any:
    """The Sort and Filter menu for these rows, the current choices checked."""
    menu = wx.Menu()
    with_counts = view.has_listeners(candidates)
    for order in view.ORDERS:
        if order == view.LISTENERS and not with_counts:
            continue
        item = menu.AppendRadioItem(ids[f"order:{order}"], ORDER_LABELS[order])
        item.Check(order == state.order)
    menu.AppendSeparator()
    menu.AppendCheckItem(ids["live_only"], LIVE_ONLY_LABEL).Check(state.live_only)
    menu.AppendSeparator()
    menu.AppendRadioItem(ids["format:"], ALL_FORMATS_LABEL).Check(not state.format)
    for name in view.formats_present(candidates):
        item = menu.AppendRadioItem(ids[f"format:{name}"], FORMAT_LABELS[name])
        item.Check(name == state.format)
    return menu


def context_menu(
    wx: Any,
    ids: dict[str, Any],
    *,
    count: int,
    testing: bool,
    server: bool,
    submenu: Any,
) -> Any:
    """The list's context menu; *submenu* is a fresh Sort and Filter menu."""
    menu = wx.Menu()
    menu.Append(ids["test"], "S&top Test" if testing else "&Test	Enter")
    menu.Append(ids["use"], "&Use This Link...")
    menu.Append(ids["add"], add_label(count))
    menu.Append(ids["save"], save_label(count) + "	Ctrl+S")
    menu.Append(ids["copy"], copy_label(count))
    if server:
        menu.Append(ids["server"], "&Scan This Stream's Server")
    menu.AppendSeparator()
    menu.Append(ids["find"], "F&ind...\tCtrl+F")
    menu.Append(ids["find_next"], "Find &Next\tF3")
    menu.Append(ids["find_previous"], "Find &Previous\tShift+F3")
    menu.Append(ids["select_all"], "Select &All\tCtrl+A")
    menu.AppendSeparator()
    menu.AppendSubMenu(submenu, "S&ort and Filter")
    return menu


_CTRL_KEYS = {"A": "select_all", "C": "copy", "F": "find", "S": "save"}


def key_command(wx: Any, code: int, modifiers: int) -> str | None:
    """The command a key in the list runs, or None to let it through."""
    if modifiers == wx.MOD_CONTROL and 0 <= code < 0x110000:
        return _CTRL_KEYS.get(chr(code).upper())
    if code == wx.WXK_F3 and modifiers == wx.MOD_NONE:
        return "find_next"
    if code == wx.WXK_F3 and modifiers == wx.MOD_SHIFT:
        return "find_previous"
    return None
