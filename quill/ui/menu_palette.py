"""Find a Setting or Command, for the apps whose settings live in their menus (qc.md X-01).

Quill Converter, the Media Player and Quill Inkwell have no Preferences
window: every option is a menu row, many of them check items. The family's
settings search (:mod:`quill.ui.preferences_search`) only reaches a settings
*window*, so in these three apps there was nothing to search. This is their
entry point: one field, the matching menu rows -- each with its menu path and,
for an option, whether it is on -- and Enter does the row, exactly as choosing
it from its menu would. An option is toggled and its new state is said.

Only enabled rows are offered; a dimmed row is listed with "(not available
now)" so a search for it is answered rather than met with nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["MenuRow", "append_palette_row", "find", "menu_rows", "open_menu_palette"]

TITLE = "Find a Setting or Command"


@dataclass(frozen=True, slots=True)
class MenuRow:
    item_id: int
    path: str
    label: str
    checkable: bool
    checked: bool
    enabled: bool

    def spoken(self) -> str:
        state = ""
        if self.checkable:
            state = ", on" if self.checked else ", off"
        unavailable = "" if self.enabled else " (not available now)"
        return f"{self.label}{state} -- {self.path}{unavailable}"


def _clean(label: str) -> str:
    return label.split("\t")[0].replace("&", "").strip().rstrip(".").strip()


def menu_rows(menu_bar: Any) -> list[MenuRow]:
    """Every leaf row of *menu_bar*, with its path."""
    rows: list[MenuRow] = []

    def walk(menu: Any, path: str) -> None:
        for item in menu.GetMenuItems():
            if item.IsSeparator():
                continue
            label = _clean(item.GetItemLabel())
            submenu = item.GetSubMenu()
            if submenu is not None:
                walk(submenu, f"{path} > {label}")
                continue
            if not label:
                continue
            rows.append(
                MenuRow(
                    item_id=item.GetId(),
                    path=path,
                    label=label,
                    checkable=bool(item.IsCheckable()),
                    checked=bool(item.IsCheckable() and item.IsChecked()),
                    enabled=bool(item.IsEnabled()),
                )
            )

    for index in range(menu_bar.GetMenuCount()):
        walk(menu_bar.GetMenu(index), _clean(menu_bar.GetMenuLabel(index)))
    return rows


def find(rows: list[MenuRow], query: str) -> list[MenuRow]:
    words = query.casefold().split()
    if not words:
        return list(rows)
    return [row for row in rows if all(w in f"{row.label} {row.path}".casefold() for w in words)]


def _run(host: Any, row: MenuRow) -> None:
    import wx

    frame = host.frame
    item = frame.GetMenuBar().FindItemById(row.item_id)
    event = wx.CommandEvent(wx.wxEVT_MENU, row.item_id)
    event.SetEventObject(frame)
    if item is not None and item.IsCheckable():
        new_state = not item.IsChecked()
        if not item.IsRadio() or new_state:
            item.Check(new_state)
        event.SetInt(1 if item.IsChecked() else 0)
    frame.GetEventHandler().ProcessEvent(event)
    if item is not None and item.IsCheckable():
        host._announce(f"{row.label}, {'on' if item.IsChecked() else 'off'}.")


def open_menu_palette(host: Any) -> None:
    """Show the search; Enter does the chosen row."""
    import wx

    from quill.ui.dialog_contract import apply_modal_ids

    rows = [row for row in menu_rows(host.frame.GetMenuBar()) if row.label != TITLE]
    dialog = wx.Dialog(host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(wx.StaticText(dialog, label="&Find a setting or command:"), 0, wx.LEFT | wx.TOP, 8)
    field = wx.TextCtrl(dialog)
    field.SetHelpText(
        "Type part of a setting's or command's name. The list below narrows as you "
        "type; Down moves into it, and Enter does the highlighted row."
    )
    root.Add(field, 0, wx.EXPAND | wx.ALL, 8)
    root.Add(wx.StaticText(dialog, label="&Matches:"), 0, wx.LEFT, 8)
    listbox = wx.ListBox(dialog)
    listbox.SetHelpText(
        "Each row is a menu command with its menu, and for an option whether it is on. "
        "Enter does it, exactly as choosing it from its menu would."
    )
    root.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    buttons.AddStretchSpacer(1)
    do_it = wx.Button(dialog, wx.ID_OK, label="Do It")
    do_it.SetHelpText("Does the highlighted row and closes this window.")
    cancel = wx.Button(dialog, wx.ID_CANCEL, label="Cancel")
    cancel.SetHelpText("Closes this window. Nothing changes.")
    buttons.Add(do_it, 0, wx.RIGHT, 6)
    buttons.Add(cancel, 0)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizer(root)
    dialog.SetSize((620, 420))
    apply_modal_ids(
        dialog, affirmative_id=wx.ID_OK, affirmative_label="Do It", cancel_id=wx.ID_CANCEL
    )
    shown: list[MenuRow] = []

    def _refill(_event: Any = None) -> None:
        shown[:] = find(rows, field.GetValue())
        listbox.Set([row.spoken() for row in shown] or ["No matches."])
        if shown:
            listbox.SetSelection(0)

    def _on_key(event: Any) -> None:
        if event.GetKeyCode() == wx.WXK_DOWN and shown:
            listbox.SetFocus()
            return
        event.Skip()

    field.Bind(wx.EVT_TEXT, _refill)
    field.Bind(wx.EVT_KEY_DOWN, _on_key)
    listbox.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: dialog.EndModal(wx.ID_OK))
    _refill()
    field.SetFocus()
    try:
        answer = host._show_modal_dialog(dialog, TITLE)
        index = listbox.GetSelection()
    finally:
        dialog.Destroy()
    if answer != wx.ID_OK or not (0 <= index < len(shown)):
        return
    row = shown[index]
    if not row.enabled:
        host._announce(f"{row.label} is not available now.")
        return
    wx.CallAfter(_run, host, row)


#: One key in all three apps, free in each (checked 2026-10-03).
PALETTE_KEY = "Ctrl+Alt+Shift+S"


def append_palette_row(host: Any, menu: Any) -> Any:
    """Help > Find a Setting or Command..., at the top of *menu*."""
    import wx

    item_id = wx.NewIdRef()
    menu.Prepend(item_id, f"Find a &Setting or Command...\t{PALETTE_KEY}")
    host.frame.Bind(wx.EVT_MENU, lambda _e: open_menu_palette(host), id=item_id)
    keep = getattr(host, "_keep_menu_ids", None)
    if callable(keep):
        keep(item_id)
    return item_id
