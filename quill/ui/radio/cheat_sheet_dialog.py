"""Keyboard Shortcuts sheet: every key, read off the menu bar you actually have.

The pure half is :mod:`quill.core.radio.cheat_sheet`; this walks the live
``wx.MenuBar`` and draws the window.

Walking the menu bar rather than the keymap is the whole design. It means the
sheet lists the keys the listener has -- rebindings included, literal keys like
F1 included -- and that it can never fall out of step with the menus, because
it *is* the menus. A cheat sheet maintained as a second list is a cheat sheet
that is wrong by the second release.

Filterable, because a list of 130 rows read one at a time is a worse answer
than the menus were. Type "record" and the sheet is the eight rows about
recording.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.cheat_sheet import (
    CheatRow,
    build_sheet,
    filter_rows,
    summary,
)
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

TITLE = "Keyboard Shortcuts Sheet"


def menu_items(menu_bar: Any) -> list[tuple[str, str]]:
    """``(menu title, item label)`` for every item on *menu_bar*, submenus too.

    Separators (which have no label) and submenu parents are skipped; a submenu
    contributes its children under the top-level menu's name rather than its
    own, because "Playback" is the group somebody is thinking in and the
    submenu is an implementation detail of a menu that got long.
    """
    out: list[tuple[str, str]] = []
    if menu_bar is None:
        return out
    for index in range(menu_bar.GetMenuCount()):
        title = menu_bar.GetMenuLabel(index)
        _walk(menu_bar.GetMenu(index), title, out)
    return out


def menu_titles(menu_bar: Any) -> list[tuple[str, str]]:
    """``(menu name, "Alt+X")`` for every top-level menu on *menu_bar*.

    The access key is read out of the label's own mnemonic -- the ``&S`` in
    ``&Station`` -- rather than guessed from the first letter, because several
    of them are not the first letter (``Vi&deo``, ``F&ormat``) and a sheet that
    guessed would be confidently wrong.
    """
    out: list[tuple[str, str]] = []
    if menu_bar is None:
        return out
    for index in range(menu_bar.GetMenuCount()):
        label = str(menu_bar.GetMenuLabel(index) or "")
        marker = label.find("&")
        # "&&" is a literal ampersand in a label, not a mnemonic.
        while marker != -1 and label[marker : marker + 2] == "&&":
            marker = label.find("&", marker + 2)
        if marker == -1 or marker + 1 >= len(label):
            continue
        out.append((label.replace("&&", "&").replace("&", ""), f"Alt+{label[marker + 1].upper()}"))
    return out


def _walk(menu: Any, title: str, out: list[tuple[str, str]]) -> None:
    for item in menu.GetMenuItems():
        submenu = item.GetSubMenu()
        if submenu is not None:
            _walk(submenu, title, out)
            continue
        if item.IsSeparator():
            continue
        label = item.GetItemLabel()
        if not label:
            continue
        # A disabled item is a status readout, not something to press. It is
        # also the one case the menu-accelerator gate exempts from carrying a
        # key, so listing it would produce a row with nothing to show.
        if not item.IsEnabled():
            continue
        out.append((title, label))


def show_cheat_sheet(host: Any) -> None:
    """Open the sheet. Modal, house pattern."""
    wx = host._wx

    menu_bar = host.frame.GetMenuBar()
    rows: list[CheatRow] = build_sheet(menu_items(menu_bar), menu_titles(menu_bar))
    total = len(rows)
    shown: list[CheatRow] = list(rows)

    dialog = wx.Dialog(host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetSize(wx.Size(760, 560))
    root = wx.BoxSizer(wx.VERTICAL)

    root.Add(wx.StaticText(dialog, label="&Filter (a key, or what you want to do):"), 0, wx.ALL, 8)
    search = wx.TextCtrl(dialog, style=wx.TE_PROCESS_ENTER)
    search.SetName("Filter the shortcut list; matches the key, the action, and the menu")
    root.Add(search, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

    count_label = wx.StaticText(dialog, label=summary(shown, total))
    root.Add(count_label, 0, wx.ALL, 8)

    listbox = wx.ListBox(dialog, choices=[row.spoken() for row in shown], style=wx.LB_SINGLE)
    listbox.SetName("Every keyboard shortcut, with what it does and where it works")
    root.Add(listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

    row_sizer = wx.BoxSizer(wx.HORIZONTAL)
    copy_btn = wx.Button(dialog, label="&Copy All")
    copy_btn.SetName("Copy the whole list, as filtered, to the clipboard")
    edit_btn = wx.Button(dialog, label="Change &Shortcuts...")
    edit_btn.SetName("Open the Keyboard Shortcuts editor to rebind a key")
    close_btn = wx.Button(dialog, wx.ID_CLOSE, label="C&lose")
    close_btn.SetHelpText("Closes the sheet; press Ctrl+Alt+Shift+K to open it again anywhere.")
    for button in (copy_btn, edit_btn, close_btn):
        row_sizer.Add(button, 0, wx.RIGHT, 6)
    root.Add(row_sizer, 0, wx.ALL, 8)
    apply_modal_ids(dialog, affirmative_id=close_btn.GetId(), escape_id=close_btn.GetId())
    dialog.SetSizer(root)

    def _refilter(_event: Any) -> None:
        nonlocal shown
        shown = filter_rows(rows, search.GetValue())
        listbox.Set([row.spoken() for row in shown])
        count_label.SetLabel(summary(shown, total))
        if listbox.GetCount():
            listbox.SetSelection(0)

    def _copy(_event: Any) -> None:
        text = "\n".join(row.spoken() for row in shown)
        copier = getattr(host, "_copy_to_clipboard", None)
        if copier is not None and copier(text):
            host._announce(f"Copied {len(shown)} shortcuts.")
            return
        host._announce("The shortcuts could not be copied.")

    def _edit(_event: Any) -> None:
        # Close first: the editor is where rebinding happens, and leaving a
        # now-stale sheet open behind it would show the old keys.
        dialog.EndModal(wx.ID_CLOSE)
        opener = getattr(host, "open_keymap_editor", None)
        if opener is not None:
            opener()

    search.Bind(wx.EVT_TEXT, _refilter)
    search.Bind(wx.EVT_TEXT_ENTER, lambda _e: listbox.SetFocus())
    copy_btn.Bind(wx.EVT_BUTTON, _copy)
    edit_btn.Bind(wx.EVT_BUTTON, _edit)
    close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
    apply_listbox_activation(listbox, lambda _e: None)
    if listbox.GetCount():
        listbox.SetSelection(0)
    # Focus lands in the filter box, not the list: somebody who opened this
    # window has a question, and typing it is faster than arrowing 130 rows.
    wx.CallAfter(search.SetFocus)
    try:
        host._show_modal_dialog(dialog, TITLE)
    finally:
        dialog.Destroy()
