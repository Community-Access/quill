"""OCR review dialog — displays OCR results with Insert/Copy/Discard actions (OCR-4).

This module provides a stock, screen-reader-friendly dialog that displays OCR
recognition results (from :func:`quill.io.ocr.render_ocr_review`) in a
``wx.TextCtrl(... TE_MULTILINE | TE_READONLY)`` for accessible review.

The dialog offers three actions:
- **Insert**: insert the recognized text into the editor at the current cursor position
- **Copy**: copy the recognized text to the clipboard
- **Discard**: close the dialog without taking any action

Focus returns to the editor on close, meeting the A11Y-4 dialog contract.
"""

from __future__ import annotations

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog


class OcrReviewDialog:
    """A modal dialog for reviewing OCR results before inserting or copying.

    Constructor takes ``parent`` (the MainFrame), ``title`` (dialog title),
    and ``text`` (the rendered OCR result from :func:`quill.io.ocr.render_ocr_review`).

    Call :meth:`show_modal` to display the dialog; it returns ``ID_INSERT``,
    ``ID_COPY``, or ``ID_DISCARD`` depending on the user's choice.
    """

    # Return codes for the three actions
    ID_INSERT = 1
    ID_COPY = 2
    ID_DISCARD = 3

    def __init__(self, parent: object, title: str, text: str) -> None:
        """Create an OCR review dialog.

        Args:
            parent: The parent window (typically MainFrame).
            title: The dialog title.
            text: The rendered OCR result text to display.
        """
        # Defer wx import to avoid import-time dependency on wx when testing
        import wx

        self._wx = wx
        self._result = self.ID_DISCARD

        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize((820, 640))
        self.dialog.SetName(title)

        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        # Instructions at the top
        intro = wx.StaticText(
            panel,
            label="Review the recognized text below, then choose Insert, Copy, or Discard.",
        )
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        # Main text display (multiline readonly TextCtrl for screen-reader review)
        label = wx.StaticText(panel, label="Recognized text")
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.text_ctrl = wx.TextCtrl(panel, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.text_ctrl.SetMinSize((760, 440))
        root.Add(self.text_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Button row with Insert, Copy, Discard
        button_row = wx.BoxSizer(wx.HORIZONTAL)
        insert_btn = wx.Button(panel, label="Insert")
        copy_btn = wx.Button(panel, label="Copy")
        discard_btn = wx.Button(panel, label="Discard")

        insert_btn.Bind(wx.EVT_BUTTON, lambda _e: self._end(self.ID_INSERT))
        copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self._end(self.ID_COPY))
        discard_btn.Bind(wx.EVT_BUTTON, lambda _e: self._end(self.ID_DISCARD))

        button_row.Add(insert_btn, 0, wx.RIGHT, 8)
        button_row.Add(copy_btn, 0, wx.RIGHT, 8)
        button_row.AddStretchSpacer(1)
        button_row.Add(discard_btn, 0)
        root.Add(button_row, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizerAndFit(outer)

        # Set Insert as the affirmative (default) action, Discard as the escape action
        apply_modal_ids(self.dialog, affirmative_id=self.ID_INSERT, escape_id=self.ID_DISCARD)

        # Bind Escape key to discard
        self.dialog.Bind(
            wx.EVT_CHAR_HOOK,
            lambda e: self._end(self.ID_DISCARD) if e.GetKeyCode() == wx.WXK_ESCAPE else e.Skip(),
        )

    def _end(self, result: int) -> None:
        """End the dialog with the given result code."""
        self._result = result
        self.dialog.EndModal(result)

    def show_modal(
        self,
        *,
        announce=None,
        enter_region=None,
        exit_region=None,
    ) -> int:
        """Show the dialog modally and return the user's choice.

        Returns:
            One of ``ID_INSERT``, ``ID_COPY``, or ``ID_DISCARD``.
        """
        self.dialog.CentreOnParent()
        try:
            show_modal_dialog(
                self.dialog,
                self.dialog.GetTitle(),
                announce=announce,
                enter_region=enter_region,
                exit_region=exit_region,
            )
        finally:
            self.dialog.Destroy()
        return self._result


__all__ = ["OcrReviewDialog"]
