"""Insert Image dialog (#899): a mandatory-alt-text insertion flow.

Every other way an image reaches a QUILL document -- pasted, typed by hand,
imported from another format -- can carry no alt text at all, and did until
now. This dialog is the one insertion path that makes the choice explicit:
either write alt text, or deliberately mark the image decorative (the
correct accessible pattern for an image with no informational content --
distinct from an image nobody ever gave alt text to, which is the actual
problem #899 is about).
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.inline_image_alt import build_image_markdown


class InsertImageDialog:
    """Collect a file path and alt text (or a decorative flag) for Insert Image."""

    def __init__(
        self,
        parent: object,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._announce = announce_cb or (lambda _msg: None)
        self._result: str | None = None

        self.dialog = wx.Dialog(
            parent, title="Insert Image", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(480, 260))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(self.dialog, label="Image &file:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8
        )
        path_row = wx.BoxSizer(wx.HORIZONTAL)
        self._path_ctrl = wx.TextCtrl(self.dialog)
        self._path_ctrl.SetName("Image file path")
        path_row.Add(self._path_ctrl, 1)
        self._btn_browse = wx.Button(self.dialog, label="&Browse...")
        path_row.Add(self._btn_browse, 0, wx.LEFT, 4)
        root.Add(path_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        root.Add(
            wx.StaticText(self.dialog, label="&Alt text (what this image shows):"),
            0,
            wx.LEFT | wx.RIGHT,
            8,
        )
        self._alt_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE)
        self._alt_ctrl.SetName("Alt text")
        root.Add(self._alt_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._decorative_check = wx.CheckBox(
            self.dialog,
            label="This image is &decorative (no informational content -- skip alt text)",
        )
        self._decorative_check.SetName("Decorative image, no alt text needed")
        root.Add(self._decorative_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_insert = wx.Button(self.dialog, wx.ID_OK, label="&Insert")
        btn_cancel = wx.Button(self.dialog, wx.ID_CANCEL, label="C&ancel")
        btn_row.AddStretchSpacer(1)
        btn_row.Add(self._btn_insert, 0, wx.RIGHT, 4)
        btn_row.Add(btn_cancel, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()

        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Insert",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )

        self._btn_browse.Bind(wx.EVT_BUTTON, self._on_browse)
        self._decorative_check.Bind(wx.EVT_CHECKBOX, self._on_decorative_toggle)
        self._btn_insert.Bind(wx.EVT_BUTTON, self._on_insert)

        self._path_ctrl.SetFocus()

    # -- public API --

    def show(self) -> str | None:
        """Show the dialog modally; return the Markdown to insert, or None if canceled."""
        from quill.ui.dialog_contract import show_modal_dialog

        show_modal_dialog(self.dialog, "Insert Image")
        return self._result

    def close(self) -> None:
        self.dialog.Destroy()

    # -- event handlers --

    def _on_browse(self, _event: object) -> None:
        wildcard = (
            "Image files (*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp)"
            "|*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp|All files (*.*)|*.*"
        )
        with wx.FileDialog(
            self.dialog,
            "Choose an image",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as pick:
            if pick.ShowModal() == wx.ID_OK:
                self._path_ctrl.SetValue(pick.GetPath())

    def _on_decorative_toggle(self, _event: object) -> None:
        decorative = self._decorative_check.GetValue()
        self._alt_ctrl.Enable(not decorative)

    def _on_insert(self, _event: object) -> None:
        path = self._path_ctrl.GetValue().strip()
        if not path:
            self._status.SetLabel("Choose an image file first.")
            self._announce("Choose an image file first.")
            return
        decorative = self._decorative_check.GetValue()
        alt_text = self._alt_ctrl.GetValue().strip()
        if not decorative and not alt_text:
            self._status.SetLabel(
                "Enter alt text describing this image, or mark it decorative."
            )
            self._announce("Enter alt text describing this image, or mark it decorative.")
            return
        self._result = build_image_markdown(path, alt_text, decorative=decorative)
        if self.dialog.IsModal():
            self.dialog.EndModal(wx.ID_OK)
