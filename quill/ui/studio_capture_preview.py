"""Optional keyboard-scrollable image preview; editing keeps a parallel text list."""

from __future__ import annotations

import wx

from quill.ui.dialog_contract import apply_modal_ids


class ScreenshotPreviewDialog(wx.Dialog):
    def __init__(self, parent, image, scale):
        super().__init__(
            parent,
            title="Screenshot visual preview",
            size=(800, 600),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        if size[0] * size[1] > 20_000_000:
            raise ValueError("Choose a smaller preview zoom for this image.")
        image = image.resize(size)
        native = wx.Image(*size)
        native.SetData(image.convert("RGB").tobytes())
        scroller = wx.ScrolledWindow(self)
        scroller.SetScrollRate(20, 20)
        bitmap = wx.StaticBitmap(scroller, bitmap=wx.Bitmap(native))
        bitmap.SetName(
            "Rendered screenshot preview. Edit descriptions remain in the editor's text list."
        )
        content = wx.BoxSizer(wx.VERTICAL)
        content.Add(bitmap)
        scroller.SetSizer(content)
        scroller.FitInside()
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(scroller, 1, wx.EXPAND)
        layout.Add(self.CreateButtonSizer(wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="Close preview")
        self.SetSizer(layout)
        scroller.SetFocus()
        # a11y: needs manual verification — keyboard panning and scaling.
        # Parallel text descriptions remain in the editor.


def show_screenshot_preview(host, parent, image, scale):
    dialog = ScreenshotPreviewDialog(parent, image, scale)
    try:
        host._show_modal_dialog(dialog, "Screenshot visual preview")
    finally:
        dialog.Destroy()
