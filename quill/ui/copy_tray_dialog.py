"""Copy Tray dialog — browse, edit, label, and paste slots.

Layout: slot list on the left; inline label field and full editable content
area on the right.  Changing the list selection auto-saves any edits in
flight so no content is lost.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.copy_tray import CopyTray


def _slot_row_text(n: int, slot_text: str, slot_label: str, pinned: bool = False) -> str:
    pin_tag = "[pinned] " if pinned else ""
    if not slot_text:
        return f"{n}.  {pin_tag}(empty)"
    preview_src = " ".join(slot_text.split())
    preview = preview_src[:55] + ("..." if len(preview_src) > 55 else "")
    if slot_label:
        return f"{n}.  {pin_tag}{slot_label} — {preview}"
    return f"{n}.  {pin_tag}{preview}"


class CopyTrayDialog:
    """Browse, edit, label, and paste from the persistent copy tray slots."""

    def __init__(
        self,
        parent: object,
        tray: CopyTray,
        selection: str = "",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._tray = tray
        self._selection = selection
        self._paste_slot: int = 0
        self._guard = False
        self._announce = announce_cb or (lambda _msg: None)

        self.dialog = wx.Dialog(
            parent,
            title="Copy Tray",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(640, 400))

        root = wx.BoxSizer(wx.VERTICAL)
        body = wx.BoxSizer(wx.HORIZONTAL)

        # -- Left: slot list --
        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(self.dialog, label="&Slots"), 0, wx.BOTTOM, 2)
        self._listbox = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._listbox.SetName("Copy tray slots")
        self._rebuild_list(keep=False)
        left.Add(self._listbox, 1, wx.EXPAND)
        self._status_label = wx.StaticText(self.dialog, label="")
        self._status_label.SetName("Status")
        left.Add(self._status_label, 0, wx.EXPAND | wx.TOP, 4)
        body.Add(left, 1, wx.EXPAND | wx.RIGHT, 8)

        # -- Right: label + content editor --
        right = wx.BoxSizer(wx.VERTICAL)

        lbl_row = wx.BoxSizer(wx.HORIZONTAL)
        lbl_row.Add(
            wx.StaticText(self.dialog, label="&Label:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self._label_ctrl = wx.TextCtrl(self.dialog)
        self._label_ctrl.SetName("Slot label — short name spoken in announcements")
        lbl_row.Add(self._label_ctrl, 1)
        right.Add(lbl_row, 0, wx.EXPAND | wx.BOTTOM, 6)

        right.Add(
            wx.StaticText(self.dialog, label="&Content — edit and save to tray:"), 0, wx.BOTTOM, 2
        )
        self._content_ctrl = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER | wx.TE_RICH2,
        )
        self._content_ctrl.SetName("Slot content — fully editable text")
        right.Add(self._content_ctrl, 1, wx.EXPAND)
        body.Add(right, 2, wx.EXPAND)
        root.Add(body, 1, wx.EXPAND | wx.ALL, 8)

        # -- Buttons --
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_paste = wx.Button(self.dialog, wx.ID_OK, label="&Paste")
        self._btn_clip = wx.Button(self.dialog, wx.ID_ANY, label="Paste from C&lipboard")
        self._btn_save = wx.Button(self.dialog, wx.ID_ANY, label="&Save Changes")
        self._btn_clear = wx.Button(self.dialog, wx.ID_ANY, label="Clea&r Slot")
        self._btn_pin = wx.Button(self.dialog, wx.ID_ANY, label="P&in")
        btn_close = wx.Button(self.dialog, wx.ID_CANCEL, label="C&lose")

        for btn in (
            self._btn_paste,
            self._btn_clip,
            self._btn_save,
            self._btn_clear,
            self._btn_pin,
        ):
            btn_sizer.Add(btn, 0, wx.RIGHT, 4)
        btn_sizer.AddStretchSpacer(1)
        btn_sizer.Add(btn_close, 0)
        root.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()

        from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Paste",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
        )

        self._listbox.Bind(wx.EVT_LISTBOX, self._on_slot_changed)
        apply_listbox_activation(self._listbox, self._on_double_click)
        self._btn_paste.Bind(wx.EVT_BUTTON, self._on_paste)
        self._btn_clip.Bind(wx.EVT_BUTTON, self._on_paste_clipboard)
        self._btn_save.Bind(wx.EVT_BUTTON, self._on_save)
        self._btn_clear.Bind(wx.EVT_BUTTON, self._on_clear_slot)
        self._btn_pin.Bind(wx.EVT_BUTTON, self._on_pin_toggle)

        self._load_slot(1)
        self._update_buttons()
        self._listbox.SetFocus()

    # -- public API --

    def show(self) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return show_modal_dialog(self.dialog, "Copy Tray")

    def close(self) -> None:
        self.dialog.Destroy()

    def selected_slot(self) -> int:
        return self._paste_slot

    def selected_text_to_paste(self) -> str:
        if self._paste_slot < 1:
            return ""
        return self._tray.paste_from(self._paste_slot)

    # -- internal helpers --

    def _sel_n(self) -> int:
        idx = self._listbox.GetSelection()
        return max(1, idx + 1)

    def _set_status(self, msg: str) -> None:
        self._status_label.SetLabel(msg)
        self._announce(msg)

    def _load_slot(self, n: int) -> None:
        self._guard = True
        slot = self._tray.slot(n)
        self._label_ctrl.SetValue(slot.label)
        self._content_ctrl.SetValue(slot.text)
        pin_part = " [pinned]" if slot.pinned else ""
        label_part = f" ({slot.label})" if slot.label else ""
        self._set_status(f"Slot {n}{label_part}{pin_part} loaded")
        self._guard = False

    def _flush_edits(self) -> None:
        if self._guard:
            return
        n = self._listbox.GetSelection() + 1
        if n < 1:
            return
        new_text = self._content_ctrl.GetValue()
        new_label = self._label_ctrl.GetValue().strip()
        slot = self._tray.slot(n)
        if new_text != slot.text:
            self._tray.copy_to(n, new_text)
        if new_label != slot.label:
            self._tray.set_label(n, new_label)

    def _rebuild_list(self, *, keep: bool = True) -> None:
        self._guard = True
        idx = self._listbox.GetSelection() if keep else 0
        self._listbox.Clear()
        for n, slot in self._tray.all_slots():
            self._listbox.Append(_slot_row_text(n, slot.text, slot.label, slot.pinned))
        count = self._listbox.GetCount()
        if count > 0:
            self._listbox.SetSelection(max(0, min(idx, count - 1)))
        self._guard = False

    def _update_buttons(self) -> None:
        n = self._sel_n()
        slot = self._tray.slot(n)
        has_content = bool(self._content_ctrl.GetValue().strip())
        self._btn_paste.Enable(has_content)
        self._btn_clear.Enable(not slot.is_empty())
        self._btn_clip.Enable(self._clipboard_text() != "")
        self._btn_pin.SetLabel("Un&pin" if slot.pinned else "P&in")

    def _clipboard_text(self) -> str:
        text = ""
        if wx.TheClipboard.Open():
            data = wx.TextDataObject()
            if wx.TheClipboard.GetData(data):
                text = data.GetText()
            wx.TheClipboard.Close()
        return text

    # -- event handlers --

    def _on_slot_changed(self, _event: object) -> None:
        if self._guard:
            return
        self._flush_edits()
        n = self._listbox.GetSelection() + 1
        self._rebuild_list()
        self._load_slot(n)
        self._update_buttons()

    def _on_double_click(self, _event: object) -> None:
        if self._content_ctrl.GetValue().strip():
            self._flush_edits()
            self._paste_slot = self._sel_n()
            self.dialog.EndModal(wx.ID_OK)

    def _on_paste(self, _event: object) -> None:
        self._flush_edits()
        self._paste_slot = self._sel_n()
        self.dialog.EndModal(wx.ID_OK)

    def _on_paste_clipboard(self, _event: object) -> None:
        text = self._clipboard_text()
        if not text:
            wx.Bell()
            return
        n = self._sel_n()
        self._guard = True
        self._content_ctrl.SetValue(text)
        self._guard = False
        self._tray.copy_to(n, text)
        self._rebuild_list()
        self._update_buttons()
        label_part = f" ({self._tray.slot(n).label})" if self._tray.slot(n).label else ""
        self._set_status(f"Pasted from system clipboard to slot {n}{label_part}")
        self._content_ctrl.SetFocus()

    def _on_save(self, _event: object) -> None:
        self._flush_edits()
        n = self._sel_n()
        self._rebuild_list()
        self._update_buttons()
        label_part = f" ({self._tray.slot(n).label})" if self._tray.slot(n).label else ""
        self._set_status(f"Slot {n} saved{label_part}")
        self._content_ctrl.SetFocus()

    def _on_clear_slot(self, _event: object) -> None:
        n = self._sel_n()
        self._tray.clear_slot(n)
        self._load_slot(n)
        self._rebuild_list()
        self._update_buttons()
        self._set_status(f"Slot {n} cleared")

    def _on_pin_toggle(self, _event: object) -> None:
        n = self._sel_n()
        if self._tray.slot(n).pinned:
            self._tray.unpin_slot(n)
            state = "unpinned"
        else:
            self._tray.pin_slot(n)
            state = "pinned"
        self._rebuild_list()
        self._update_buttons()
        self._set_status(f"Slot {n} {state}")
