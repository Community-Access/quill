"""The block form: one window for Insert Block's fields and Block Settings (wordpress.md 8.2, 8.4).

A form is a list of :class:`~quill.core.wordpress.block_catalog.Field` built
by the wx-free core -- hand-built for core blocks, generated from a block
type's attribute schema for the rest, or the theme's colours and sizes for
settings -- so this window knows nothing about blocks. Every control is a
plain edit field, check box or combo box with its own F1 help, and the
labels arrive with distinct access keys already (GATE-14).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import wx

from quill.core.wordpress.block_catalog import Field
from quill.ui import wordpress_dialogs as dlg
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.


class BlockFormDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        title: str,
        purpose: str,
        fields: Sequence[Field],
        ok_label: str,
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetHelpText(purpose)
        self.fields = list(fields)
        self.controls: list[wx.Window] = []
        sizer = wx.BoxSizer(wx.VERTICAL)
        for f in self.fields:
            if f.kind == "check":
                box = wx.CheckBox(self, label=f.label)
                box.SetValue(bool(f.value))
                box.SetHelpText(f.help)
                sizer.Add(box, 0, wx.ALL, 8)
                self.controls.append(box)
                continue
            if f.kind == "choice":
                combo = wx.Choice(self, choices=list(f.choices))
                combo.SetHelpText(f.help)
                index = f.values.index(f.value) if f.value in f.values else 0
                if f.choices:
                    combo.SetSelection(index)
                control: wx.Window = combo
            else:
                style = wx.TE_MULTILINE if f.kind == "multiline" else 0
                edit = wx.TextCtrl(self, value=str(f.value or ""), style=style)
                edit.SetHelpText(f.help)
                if f.kind == "multiline":
                    edit.SetMinSize(dip_size(self, 420, 100))
                control = edit
            dlg._row(sizer, self, f.label, control)
            self.controls.append(control)
        sizer.Add(dlg._buttons(self, ok_label), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)

    def answers(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for f, control in zip(self.fields, self.controls, strict=True):
            if isinstance(control, wx.CheckBox):
                out[f.key] = control.GetValue()
            elif isinstance(control, wx.Choice):
                index = control.GetSelection()
                out[f.key] = f.values[index] if 0 <= index < len(f.values) else f.value
            elif isinstance(control, wx.TextCtrl):
                out[f.key] = control.GetValue()
        return out


def ask_fields(
    parent: wx.Window,
    show_modal: dlg.ShowModal,
    *,
    title: str,
    purpose: str,
    fields: Sequence[Field],
    ok_label: str = "OK",
) -> dict[str, Any] | None:
    """Show a block form; the answers by field key, or None when cancelled."""
    dialog = BlockFormDialog(parent, title=title, purpose=purpose, fields=fields, ok_label=ok_label)
    try:
        if show_modal(dialog, title) != wx.ID_OK:
            return None
        return dialog.answers()
    finally:
        dialog.Destroy()
