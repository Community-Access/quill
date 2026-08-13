"""Subscriptions > Quick Actions... -- put the actions you use at the top.

The reorder pattern here is the one QUILL uses everywhere a list is
rearranged by keyboard: a real ``wx.ListBox`` plus Move Up / Move Down /
Move to Top buttons, never checkboxes inside a list control. A checkbox in a
list is a state a screen reader has to be asked for; a list position is a
place you land on, and the announcement after a move says where you are now.

Three lists, one per context, chosen with a combobox above the list so the
whole dialog is one tab stop deeper rather than three panels wide.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts.quick_actions import (
    CONTEXT_LABELS,
    CONTEXTS,
    DIRECT_KEY_COUNT,
    QuickActionOrders,
)
from quill.ui.dialog_contract import apply_modal_ids


class QuickActionsDialog:
    """Returns the edited :class:`QuickActionOrders`, or ``None`` on Cancel."""

    def __init__(
        self,
        parent: object,
        *,
        orders: QuickActionOrders,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        # Edit a copy: Cancel has to mean cancel, and the caller is holding
        # the live record the menus are already built from.
        self._orders = QuickActionOrders.from_dict(orders.to_dict())
        self._result: QuickActionOrders | None = None
        self._context = CONTEXT_LABELS[0][0]

        self.dialog = wx.Dialog(
            parent, title="Quick Actions", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((560, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                "The first action in each list is what Enter does. The first "
                f"{DIRECT_KEY_COUNT} also answer to Ctrl+1 through "
                f"Ctrl+{DIRECT_KEY_COUNT}, and the whole list is the order of "
                "the right-click menu."
            ),
        )
        intro.Wrap(520)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        context_row = wx.BoxSizer(wx.HORIZONTAL)
        context_row.Add(
            wx.StaticText(self.dialog, label="Actions &for:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._context_choice = wx.Choice(
            self.dialog, choices=[label for _cid, label in CONTEXT_LABELS]
        )
        self._context_choice.SetName("Which list of actions to reorder")
        self._context_choice.SetSelection(0)
        context_row.Add(self._context_choice, 1, wx.EXPAND)
        root.Add(context_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        body = wx.BoxSizer(wx.HORIZONTAL)
        list_col = wx.BoxSizer(wx.VERTICAL)
        list_col.Add(
            wx.StaticText(self.dialog, label="&Order (first is the default):"), 0, wx.BOTTOM, 4
        )
        self._list = wx.ListBox(self.dialog, choices=[], style=wx.LB_SINGLE)
        self._list.SetName(
            "Action order; use Move Up and Move Down, or Alt+Up and Alt+Down, to rearrange"
        )
        list_col.Add(self._list, 1, wx.EXPAND)
        self._description = wx.StaticText(self.dialog, label="")
        self._description.SetName("What the selected action does")
        list_col.Add(self._description, 0, wx.EXPAND | wx.TOP, 6)
        body.Add(list_col, 1, wx.EXPAND | wx.RIGHT, 10)

        button_col = wx.BoxSizer(wx.VERTICAL)
        self._up_btn = wx.Button(self.dialog, label="Move &Up")
        self._down_btn = wx.Button(self.dialog, label="Move &Down")
        self._top_btn = wx.Button(self.dialog, label="Make Defaul&t")
        self._top_btn.SetName("Move the selected action to the top, making it what Enter does")
        reset_btn = wx.Button(self.dialog, label="&Reset This List")
        for widget in (self._up_btn, self._down_btn, self._top_btn, reset_btn):
            button_col.Add(widget, 0, wx.EXPAND | wx.BOTTOM, 6)
        body.Add(button_col, 0)
        root.Add(body, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "&OK")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        btn_row.AddStretchSpacer()
        btn_row.Add(ok_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._context_choice.Bind(wx.EVT_CHOICE, self._on_context_choice)
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._describe_selection())
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        self._up_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(-1))
        self._down_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(1))
        self._top_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move_to_top())
        reset_btn.Bind(wx.EVT_BUTTON, lambda _e: self._reset())
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)

        self._refill()

    def show(self) -> QuickActionOrders | None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="OK",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            answer = show_modal_dialog(self.dialog, "Quick Actions", announce=self._announce)
            return self._result if answer == self._wx.ID_OK else None
        finally:
            self.dialog.Destroy()

    # -- list ------------------------------------------------------------

    def _actions(self) -> list:
        return self._orders.actions(self._context)

    def _refill(self, *, select: int = 0) -> None:
        actions = self._actions()
        self._list.Set([action.label for action in actions])
        if actions:
            index = max(0, min(select, len(actions) - 1))
            self._list.SetSelection(index)
        self._describe_selection()

    def _describe_selection(self) -> None:
        index = self._list.GetSelection()
        actions = self._actions()
        if not (0 <= index < len(actions)):
            self._description.SetLabel("")
            return
        action = actions[index]
        position = f"Position {index + 1} of {len(actions)}"
        if index == 0:
            position += " -- this is what Enter does"
        elif index < DIRECT_KEY_COUNT:
            position += f" -- Ctrl+{index + 1}"
        self._description.SetLabel(f"{action.description} {position}.")

    def _on_context_choice(self, _event: object) -> None:
        index = max(0, self._context_choice.GetSelection())
        self._context = CONTEXT_LABELS[index][0]
        self._refill()
        self._announce(f"{CONTEXT_LABELS[index][1]}: {len(self._actions())} actions")

    def _on_list_key(self, event: object) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        if event.AltDown() and code == wx.WXK_UP:
            self._move(-1)
            return
        if event.AltDown() and code == wx.WXK_DOWN:
            self._move(1)
            return
        event.Skip()

    def _move(self, delta: int) -> None:
        index = self._list.GetSelection()
        order = self._orders.order(self._context)
        target = index + delta
        if not (0 <= index < len(order)) or not (0 <= target < len(order)):
            self._announce("Already at the end of the list.")
            return
        order[index], order[target] = order[target], order[index]
        self._orders.set_order(self._context, order)
        self._refill(select=target)
        actions = self._actions()
        self._announce(f"{actions[target].label} is now number {target + 1}")

    def _move_to_top(self) -> None:
        index = self._list.GetSelection()
        order = self._orders.order(self._context)
        if not (0 <= index < len(order)) or index == 0:
            return
        moved = order.pop(index)
        order.insert(0, moved)
        self._orders.set_order(self._context, order)
        self._refill(select=0)
        self._announce(f"{self._actions()[0].label} is now the default action")

    def _reset(self) -> None:
        self._orders.reset(self._context)
        self._refill()
        label = dict(CONTEXT_LABELS)[self._context]
        self._announce(f"{label} reset to the shipped order")

    def _on_ok(self, _event: object) -> None:
        # Repair once more on the way out: nothing here can produce an
        # invalid order, but the record is about to be written to disk and
        # read back by a future build, and that is the file that has to be
        # trustworthy.
        for context in CONTEXTS:
            self._orders.set_order(context, self._orders.order(context))
        self._result = self._orders
        self.dialog.EndModal(self._wx.ID_OK)
