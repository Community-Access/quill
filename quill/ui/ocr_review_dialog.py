"""OCR review dialog surface (OCR-4).

A screen-reader-friendly stock-control review dialog that displays recognized text
from ``quill.io.ocr.render_ocr_review`` with Insert / Copy / Discard actions and
returns focus to the editor on close.

Uses wx.TextCtrl(... TE_MULTILINE | TE_READONLY) per the dialog lessons in
``.github/copilot-instructions.md``.
"""

from __future__ import annotations

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

try:
    import wx

    _HAS_WX = True
except ImportError:
    _HAS_WX = False


class OcrReviewDialog:
    """Accessible review dialog for OCR results.

    Displays OCR-recognized text in a read-only multiline text control
    with Insert, Copy, and Discard action buttons.

    Args:
        parent: Parent window (typically MainFrame)
        ocr_text: The rendered OCR review text from render_ocr_review()

    Returns:
        wx.ID_OK if user chose Insert
        wx.ID_COPY if user chose Copy
        wx.ID_CANCEL if user chose Discard or closed the dialog
    """

    def __init__(self, parent: object, ocr_text: str) -> None:
        if not _HAS_WX:
            raise ImportError("wx is not available")

        self._wx = wx
        self._result = wx.ID_CANCEL

        # Create dialog with resize capability for screen-reader users
        self.dialog = wx.Dialog(
            parent,
            title="OCR Review",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetName("OCR Review")

        # Build layout
        outer = wx.BoxSizer(wx.VERTICAL)

        # Add instruction label
        instruction = wx.StaticText(
            self.dialog,
            label=(
                "Review recognized text. Use Insert to add to document, "
                "Copy to clipboard, or Discard."
            ),
        )
        outer.Add(instruction, 0, wx.ALL | wx.EXPAND, 8)

        # Add read-only multiline text control for the OCR result
        self.text_ctrl = wx.TextCtrl(
            self.dialog,
            value=ocr_text or "",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP,
        )
        self.text_ctrl.SetName("OCR Result")
        # Allow screen reader users to navigate the text
        self.text_ctrl.SetFocus()
        outer.Add(self.text_ctrl, 1, wx.ALL | wx.EXPAND, 8)

        # Add button row
        button_row = wx.BoxSizer(wx.HORIZONTAL)
        button_row.AddStretchSpacer()

        # Insert button (affirmative action)
        insert_btn = wx.Button(self.dialog, wx.ID_OK, label="&Insert")
        insert_btn.SetToolTip("Insert recognized text into the document")
        insert_btn.Bind(wx.EVT_BUTTON, lambda _e: self._end(wx.ID_OK))
        insert_btn.SetDefault()
        button_row.Add(insert_btn, 0, wx.LEFT, 8)

        # Copy button
        copy_btn = wx.Button(self.dialog, wx.ID_COPY, label="&Copy")
        copy_btn.SetToolTip("Copy recognized text to clipboard")
        copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self._end(wx.ID_COPY))
        button_row.Add(copy_btn, 0, wx.LEFT, 8)

        # Discard button (escape action)
        discard_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="&Discard")
        discard_btn.SetToolTip("Discard recognized text")
        discard_btn.Bind(wx.EVT_BUTTON, lambda _e: self._end(wx.ID_CANCEL))
        button_row.Add(discard_btn, 0, wx.LEFT, 8)

        outer.Add(button_row, 0, wx.EXPAND | wx.ALL, 12)

        self.dialog.SetSizer(outer)
        self.dialog.SetSize((700, 500))

        # Bind Escape key for cancel
        self.dialog.Bind(
            wx.EVT_CHAR_HOOK,
            lambda e: self._end(wx.ID_CANCEL) if e.GetKeyCode() == wx.WXK_ESCAPE else e.Skip(),
        )

    def _end(self, return_id: int) -> None:
        """End the dialog with the given result ID."""
        self._result = return_id
        self.dialog.EndModal(return_id)

    def show_modal(self) -> int:
        """Show the dialog modally and return the result ID.

        Returns:
            wx.ID_OK for Insert
            wx.ID_COPY for Copy
            wx.ID_CANCEL for Discard or dialog close
        """
        self.dialog.CentreOnParent()

        # Apply modal IDs for keyboard navigation support
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            escape_id=self._wx.ID_CANCEL,
        )

        try:
            show_modal_dialog(self.dialog, "OCR Review")
        finally:
            self.dialog.Destroy()

        return self._result


__all__ = ["OcrReviewDialog"]
