"""The Key Cheatsheet: every command, in menu, name or key order (Alt+Shift+/).

Moved out of ``main_frame.py`` on 2026-11-18 when it gained EdSharp's other two
orders; the list itself is built by :mod:`quill.core.command_list`.
"""

from __future__ import annotations

from typing import Any

from quill.core.command_list import LABELS, ORDERS, command_list_text
from quill.core.keymap import DEFAULT_KEYMAP
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name


class KeyCheatsheetMixin:
    """Help > Key Cheatsheet for the editor's frame."""

    _wx: Any
    frame: Any
    commands: Any
    keymap: Any

    def open_key_cheatsheet(self) -> None:
        """§8.1 QK-1..9: every command in a read-only, searchable list.

        **Order** chooses menu order (each menu under its own name), name order
        or key order; the search box keeps the commands whose name or key
        contains what you type, in whichever order is chosen.
        """
        wx = self._wx
        dialog = wx.Dialog(
            self.frame,
            title="Key Cheatsheet",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        dialog.SetSize(dip_size(dialog, 720, 560))
        root = wx.BoxSizer(wx.VERTICAL)

        search = wx.SearchCtrl(dialog, style=wx.TE_PROCESS_ENTER)
        search.SetDescriptiveText("Search by command name or key binding")
        set_accessible_name(search, "Search by command name or key binding")
        set_spoken_name(search, "Search by command name or key binding")
        search.SetHelpText("Keeps only the commands whose name or key contains what you type.")
        root.Add(search, 0, wx.EXPAND | wx.ALL, 8)

        order_row = wx.BoxSizer(wx.HORIZONTAL)
        order_row.Add(
            wx.StaticText(dialog, label="&Order:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        order = wx.Choice(dialog, choices=[LABELS[name] for name in ORDERS])
        order.SetSelection(ORDERS.index("name"))
        order.SetName("Order")
        set_spoken_name(order, "Order")
        order.SetHelpText(
            "Menu order lists each menu's commands under its name; name order is "
            "alphabetical; key order puts the keys first, so you can find what a key does."
        )
        order_row.Add(order, 0)
        root.Add(order_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        cheatsheet_ctrl = wx.TextCtrl(
            dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        )
        set_accessible_name(cheatsheet_ctrl, "Key cheatsheet")
        set_spoken_name(cheatsheet_ctrl, "Key cheatsheet")
        cheatsheet_ctrl.SetHelpText("Every command and its key, one a line.")
        root.Add(cheatsheet_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        close_btn = wx.Button(dialog, id=wx.ID_CANCEL, label="Close")
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)
        dialog.SetSizer(root)

        def refill(_event: object = None) -> None:
            chosen = ORDERS[max(0, order.GetSelection())]
            cheatsheet_ctrl.SetValue(
                self._build_cheatsheet_text(search.GetValue().strip().lower(), chosen)
            )
            skip = getattr(_event, "Skip", None)
            if callable(skip):
                skip()

        refill()
        apply_modal_ids(dialog, affirmative_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
        search.Bind(wx.EVT_TEXT, refill)
        order.Bind(wx.EVT_CHOICE, refill)
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))

        try:
            self._show_modal_dialog(dialog, "Key Cheatsheet")  # type: ignore[attr-defined]
        finally:
            dialog.Destroy()

    def _build_cheatsheet_text(self, query: str, order: str = "name") -> str:
        """Every command and its key, filtered by *query*, in *order*."""
        commands = self.commands.list(feature_manager=getattr(self, "features", None))
        return command_list_text(
            ((cmd.id, cmd.title) for cmd in commands),
            lambda cid: self.keymap.get(cid) or DEFAULT_KEYMAP.get(cid) or "",
            order=order,
            query=query,
        )
