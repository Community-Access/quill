"""Print Studio dialog (#891): the accessible preview and page-set options
that sit between "Print" and the OS print dialog.

QUILL has real print plumbing already (Page Setup, ``wx.Printer``); what
was missing was any preview at all, and any odd/even/reverse/skip-first-page
control. This dialog is a screen-reader-first equivalent of a visual print
preview -- a spoken/textual summary ("3 pages, Letter, default margins")
rather than a WYSIWYG renderer -- plus the page-set choice, both computed by
the pure :mod:`quill.core.print_pagination` before any native dialog opens.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.print_pagination import PageSetOption, PrintPreview, describe_preview


class PrintStudioDialog:
    """Accessible print preview plus odd/even/reverse/skip-first-page options."""

    def __init__(
        self,
        parent: object,
        preview: PrintPreview,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._announce = announce_cb or (lambda _msg: None)
        self.page_set = PageSetOption.ALL
        self.reverse = False
        self.skip_first_page = False
        self._accepted = False

        self.dialog = wx.Dialog(
            parent, title="Print Studio", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(440, 320))
        root = wx.BoxSizer(wx.VERTICAL)

        self._preview_ctrl = wx.TextCtrl(
            self.dialog, value=describe_preview(preview), style=wx.TE_READONLY
        )
        self._preview_ctrl.SetName("Print preview summary")
        root.Add(self._preview_ctrl, 0, wx.EXPAND | wx.ALL, 8)

        root.Add(wx.StaticText(self.dialog, label="&Pages to print:"), 0, wx.LEFT | wx.RIGHT, 8)
        self._page_set_choice = wx.Choice(
            self.dialog, choices=["All pages", "Odd pages only", "Even pages only"]
        )
        self._page_set_choice.SetSelection(0)
        self._page_set_choice.SetName("Pages to print")
        root.Add(self._page_set_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._reverse_check = wx.CheckBox(self.dialog, label="Print in &reverse order")
        self._reverse_check.SetName("Print in reverse order")
        root.Add(self._reverse_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._skip_first_check = wx.CheckBox(
            self.dialog, label="&Skip the first page (e.g. pre-printed letterhead)"
        )
        self._skip_first_check.SetName("Skip the first page")
        root.Add(self._skip_first_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_print = wx.Button(self.dialog, wx.ID_OK, label="&Print...")
        btn_cancel = wx.Button(self.dialog, wx.ID_CANCEL, label="C&ancel")
        btn_row.AddStretchSpacer(1)
        btn_row.Add(self._btn_print, 0, wx.RIGHT, 4)
        btn_row.Add(btn_cancel, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()

        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Print",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )

        self._btn_print.Bind(wx.EVT_BUTTON, self._on_print)
        self._preview_ctrl.SetFocus()
        self._announce(describe_preview(preview))

    # -- public API --

    def show(self) -> bool:
        """Show the dialog modally; return True if Print was chosen."""
        from quill.ui.dialog_contract import show_modal_dialog

        show_modal_dialog(self.dialog, "Print Studio")
        return self._accepted

    def close(self) -> None:
        self.dialog.Destroy()

    # -- event handlers --

    def _on_print(self, _event: object) -> None:
        selection = self._page_set_choice.GetSelection()
        self.page_set = {0: PageSetOption.ALL, 1: PageSetOption.ODD, 2: PageSetOption.EVEN}.get(
            selection, PageSetOption.ALL
        )
        self.reverse = self._reverse_check.GetValue()
        self.skip_first_page = self._skip_first_check.GetValue()
        self._accepted = True
        if self.dialog.IsModal():
            self.dialog.EndModal(wx.ID_OK)
