"""Verbosity data-order editor dialog (verbosity §14).

Reorders the fields a verb announces when it has no custom template. A list with
Move Up / Move Down / Reset / Preview, backed by the pure
:class:`quill.core.verbosity.data_order.DataOrder`. A11Y-4 hardened.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.verbosity.data_order import DataOrder
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["VerbosityDataOrderDialog"]


class VerbosityDataOrderDialog:
    """Edit the field order for one verb's announcement."""

    def __init__(
        self,
        parent: object,
        order: DataOrder,
        *,
        default_fields: tuple[str, ...] | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._order = order
        self._default = default_fields if default_fields is not None else order.fields
        self._announce = announce_cb or (lambda _m: None)
        self._result: DataOrder | None = None

        self.dialog = wx.Dialog(
            parent,
            title=f"Data order — {order.verb_id}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(420, 360))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(self.dialog, label="&Fields (read top to bottom):"),
            0,
            wx.LEFT | wx.TOP,
            8,
        )
        self._list = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._list.SetName("Announcement fields")
        self._list.SetMinSize(wx.Size(-1, 200))
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self._up_btn = wx.Button(self.dialog, label="Move &Up")
        self._down_btn = wx.Button(self.dialog, label="Move &Down")
        self._reset_btn = wx.Button(self.dialog, label="&Reset")
        self._preview_btn = wx.Button(self.dialog, label="&Preview")
        save_btn = wx.Button(self.dialog, id=wx.ID_SAVE, label="Sa&ve")
        cancel_btn = wx.Button(self.dialog, id=wx.ID_CANCEL, label="Cancel")
        for b in (self._up_btn, self._down_btn, self._reset_btn, self._preview_btn):
            btns.Add(b, 0, wx.RIGHT, 6)
        btns.AddStretchSpacer()
        btns.Add(save_btn, 0, wx.RIGHT, 6)
        btns.Add(cancel_btn)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        apply_modal_ids(
            self.dialog, affirmative_id=wx.ID_SAVE, affirmative_label="Save", cancel_id=wx.ID_CANCEL
        )

        self._up_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(-1))
        self._down_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(1))
        self._reset_btn.Bind(wx.EVT_BUTTON, lambda _e: self._reset())
        self._preview_btn.Bind(wx.EVT_BUTTON, lambda _e: self._preview())
        save_btn.Bind(wx.EVT_BUTTON, lambda _e: self._save())
        cancel_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CANCEL))
        self._repopulate()

    def _repopulate(self, keep: str | None = None) -> None:
        self._list.Clear()
        for field in self._order.fields:
            self._list.Append(field)
        if keep is not None and keep in self._order.fields:
            self._list.SetSelection(self._order.fields.index(keep))
        elif self._order.fields:
            self._list.SetSelection(0)

    def _selected(self) -> str | None:
        index = self._list.GetSelection()
        if index < 0:
            return None
        return self._order.fields[index]

    def _move(self, delta: int) -> None:
        field = self._selected()
        if field is None:
            return
        self._order = self._order.move_down(field) if delta > 0 else self._order.move_up(field)
        self._repopulate(keep=field)
        self._announce(f"{field} moved {'down' if delta > 0 else 'up'}")

    def _reset(self) -> None:
        self._order = self._order.reset(self._default)
        self._repopulate()
        self._announce("Field order reset to default")

    def _preview(self) -> None:
        values = {field: field for field in self._order.fields}
        self._announce(f"Preview. {self._order.render(values)}")

    def _save(self) -> None:
        self._result = self._order
        self.dialog.EndModal(wx.ID_SAVE)

    @property
    def order(self) -> DataOrder | None:
        return self._result

    def show(self) -> int:
        result = self.dialog.ShowModal()
        self.dialog.Destroy()
        return result

    def close(self) -> None:
        self.dialog.EndModal(wx.ID_CANCEL)
