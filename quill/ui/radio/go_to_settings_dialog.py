"""Go To Settings: which places are in the menu, and in what order.

Deliberately the same two-list shape as Choose Columns, and for the same
reasons. Somebody who has arranged their columns already knows this window.

**Two lists, not checkboxes.** A checkbox inside a list is a state a screen
reader has to be asked for; a list position is a place you land on, and the
announcement after a move says where you are now.

**Out of the menu means out, not last.** An entry that is not in the menu has no
number, so leaving it at the bottom would give it a position it cannot be
reached by. The two lists say exactly what is true.

**Refusals are sentences.** Full, or down to the last entry, both say why --
:func:`quill.core.radio.go_to.refusal_for_adding` and ``refusal_for_removing``
own the wording, so the dialog cannot invent a different reason.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.radio import go_to
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

TITLE = "Go To Settings"


def _menu_rows(order: list[str]) -> list[str]:
    """Each row carries the number it answers to, because that is the point."""
    rows = []
    for index, destination_id in enumerate(order):
        destination = go_to.destination(destination_id)
        if destination is not None:
            rows.append(f"{go_to.position_key(index)}. {destination.title}")
    return rows


def _pool_rows(order: list[str]) -> list[str]:
    return [d.title for d in go_to.GoToLayout(order=list(order)).available()]


def edit(host: Any, layout: go_to.GoToLayout, data_dir: Path) -> bool:
    """Show the editor. Returns True when a new layout was saved."""
    wx = host._wx
    announce = getattr(host, "_announce", None)
    order = list(layout.order)

    dialog = wx.Dialog(host.frame, title=TITLE)
    root = wx.BoxSizer(wx.VERTICAL)

    intro = wx.StaticText(
        dialog,
        label=(
            "The Go To menu holds up to ten places, numbered 1 to 9 and then 0.\n"
            "The number never changes on its own, so it is worth learning."
        ),
    )
    root.Add(intro, 0, wx.ALL, 10)

    columns = wx.BoxSizer(wx.HORIZONTAL)

    in_box = wx.BoxSizer(wx.VERTICAL)
    in_box.Add(wx.StaticText(dialog, label="&In the menu:"), 0)
    in_list = wx.ListBox(dialog, choices=_menu_rows(order))
    in_list.SetName("Places in the Go To menu, in order")
    in_box.Add(in_list, 1, wx.EXPAND | wx.TOP, 4)
    columns.Add(in_box, 1, wx.EXPAND | wx.RIGHT, 8)

    out_box = wx.BoxSizer(wx.VERTICAL)
    out_box.Add(wx.StaticText(dialog, label="&Not in the menu:"), 0)
    out_list = wx.ListBox(dialog, choices=_pool_rows(order))
    out_list.SetName("Places available to add")
    out_box.Add(out_list, 1, wx.EXPAND | wx.TOP, 4)
    columns.Add(out_box, 1, wx.EXPAND)

    root.Add(columns, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

    moves = wx.BoxSizer(wx.HORIZONTAL)
    up_btn = wx.Button(dialog, label="Move &Up")
    down_btn = wx.Button(dialog, label="Move &Down")
    remove_btn = wx.Button(dialog, label="&Remove")
    add_btn = wx.Button(dialog, label="&Add")
    for button in (up_btn, down_btn, remove_btn, add_btn):
        moves.Add(button, 0, wx.RIGHT, 6)
    root.Add(moves, 0, wx.ALL, 10)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    ok_btn = wx.Button(dialog, wx.ID_OK, "&OK")
    cancel_btn = wx.Button(dialog, wx.ID_CANCEL, "Cancel")
    buttons.AddStretchSpacer()
    buttons.Add(ok_btn, 0, wx.RIGHT, 6)
    buttons.Add(cancel_btn)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

    dialog.SetSizerAndFit(root)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

    def _say(message: str) -> None:
        if callable(announce) and message:
            announce(message)

    def _redraw(select_in: int | None = None, select_out: int | None = None) -> None:
        in_list.Set(_menu_rows(order))
        out_list.Set(_pool_rows(order))
        if select_in is not None and in_list.GetCount():
            in_list.SetSelection(min(select_in, in_list.GetCount() - 1))
        if select_out is not None and out_list.GetCount():
            out_list.SetSelection(min(select_out, out_list.GetCount() - 1))

    def _move(delta: int) -> None:
        index = in_list.GetSelection()
        target = index + delta
        if index < 0 or target < 0 or target >= len(order):
            return
        order[index], order[target] = order[target], order[index]
        _redraw(select_in=target)
        destination = go_to.destination(order[target])
        if destination is not None:
            # Where it landed, not that it moved: the number is the fact.
            _say(f"{destination.title} is now {go_to.position_key(target)}.")

    def _remove(_event: Any) -> None:
        index = in_list.GetSelection()
        if index < 0:
            return
        refusal = go_to.refusal_for_removing(go_to.GoToLayout(order=list(order)), order[index])
        if refusal:
            _say(refusal)
            return
        removed = go_to.destination(order.pop(index))
        _redraw(select_in=index, select_out=0)
        if removed is not None:
            _say(f"{removed.title} removed from the menu.")

    def _add(_event: Any) -> None:
        index = out_list.GetSelection()
        pool = go_to.GoToLayout(order=list(order)).available_ids()
        if index < 0 or index >= len(pool):
            return
        refusal = go_to.refusal_for_adding(go_to.GoToLayout(order=list(order)))
        if refusal:
            _say(refusal)
            return
        order.append(pool[index])
        _redraw(select_in=len(order) - 1, select_out=index)
        added = go_to.destination(order[-1])
        if added is not None:
            _say(f"{added.title} is now {go_to.position_key(len(order) - 1)}.")

    up_btn.Bind(wx.EVT_BUTTON, lambda _e: _move(-1))
    down_btn.Bind(wx.EVT_BUTTON, lambda _e: _move(1))
    remove_btn.Bind(wx.EVT_BUTTON, _remove)
    add_btn.Bind(wx.EVT_BUTTON, _add)
    if in_list.GetCount():
        in_list.SetSelection(0)
    wx.CallAfter(in_list.SetFocus)

    try:
        if show_modal_dialog(dialog, TITLE, announce=announce) != wx.ID_OK:
            return False
        go_to.save_layout(data_dir, go_to.GoToLayout(order=order))
        _say("Go To menu saved.")
        return True
    finally:
        dialog.Destroy()
