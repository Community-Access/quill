"""Help > Redeem Unlock Code... -- a single text field for pasting in a
signed unlock code (see ``quill/core/unlock_codes.py``)."""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids


class UnlockCodeDialog:
    """Returns the entered code string, or ``None`` if cancelled."""

    def __init__(
        self,
        parent: object,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)

        self.dialog = wx.Dialog(parent, title="Redeem Unlock Code")
        self.dialog.SetMinSize((420, 180))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Enter an unlock code to access a pre-beta feature you've "
                    "been given early access to:"
                ),
            ),
            0,
            wx.EXPAND | wx.ALL,
            10,
        )
        self._code_ctrl = wx.TextCtrl(self.dialog)
        self._code_ctrl.SetName("Unlock code")
        root.Add(self._code_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "&Redeem")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        btn_row.AddStretchSpacer()
        btn_row.Add(ok_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self._code_ctrl.SetFocus()

    def show(self) -> str | None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Redeem",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            answer = show_modal_dialog(self.dialog, "Redeem Unlock Code", announce=self._announce)
            if answer != self._wx.ID_OK:
                return None
            code = self._code_ctrl.GetValue().strip()
            return code or None
        finally:
            self.dialog.Destroy()
