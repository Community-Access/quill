"""Printing commands for MainFrame (#891) -- Page Setup, Print, and Print
Studio's accessible preview + odd/even/reverse/skip-first-page options.

Extracted into a mixin (CQ-1). ``PrintMixin`` relies on ``self.editor``,
``self.document``, ``self.frame``, ``self._wx``, ``self._print_data``,
``self._page_setup_data``, ``self._set_status``, ``self._announce``,
``self._show_modal_dialog``, and ``self._show_message_box`` staying on
``MainFrame``.

Print Studio sits *before* the OS print dialog, not in place of it: no
WYSIWYG renderer (explicitly out of scope, per #891), just a spoken/textual
preview -- "3 pages, Letter, default margins" -- and a page-set choice, both
computed from the pure :mod:`quill.core.print_pagination` before any native
dialog opens. Header/footer *authoring* is #892, a separate feature.
"""

from __future__ import annotations


class PrintMixin:
    """Page Setup, Print, and Print Studio."""

    _PRINT_MARGIN_PX = 50
    _PRINT_FONT_POINT_SIZE = 10

    def _print_font(self) -> object:
        wx = self._wx
        return wx.Font(
            self._PRINT_FONT_POINT_SIZE,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )

    def _paginate_for_dc(self, dc: object, lines: list[str]) -> list[list[str]]:
        from quill.core.print_pagination import paginate_lines

        dc.SetFont(self._print_font())
        _width, height = dc.GetSize()
        line_height = dc.GetTextExtent("A")[1] + 2
        lines_per_page = max(1, (height - 2 * self._PRINT_MARGIN_PX) // line_height)
        return paginate_lines(lines, lines_per_page)

    def _compute_print_preview(self, text: str) -> object:
        """A :class:`~quill.core.print_pagination.PrintPreview` for *text*.

        Uses a throwaway ``wx.PrinterDC`` for realistic font-metric-based
        pagination without starting an actual print job -- the same DC type
        ``print_document`` prints through, so the page count Print Studio
        shows matches what actually prints.
        """
        from quill.core.print_pagination import PrintPreview, margins_text, paper_name

        wx = self._wx
        dc = wx.PrinterDC(self._print_data)
        pages = self._paginate_for_dc(dc, text.splitlines() or [""])
        paper_id = self._page_setup_data.GetPaperId()
        top_left = tuple(self._page_setup_data.GetMarginTopLeft())
        bottom_right = tuple(self._page_setup_data.GetMarginBottomRight())
        return PrintPreview(
            page_count=len(pages),
            paper_name=paper_name(int(paper_id)),
            margins_text=margins_text(top_left, bottom_right),
        )

    def _build_text_printout(self, title: str, text: str, pages: list[int] | None = None) -> object:
        wx = self._wx
        font = self._print_font()
        lines = text.splitlines() or [""]
        margin = self._PRINT_MARGIN_PX
        paginate_for_dc = self._paginate_for_dc

        class _TextPrintout(wx.Printout):
            def __init__(self, print_title: str) -> None:
                super().__init__(print_title)
                self._pages: list[list[str]] = [lines]
                self._print_order: list[int] = [1]

            def OnPreparePrinting(self) -> None:
                dc = self.GetDC()
                self._pages = paginate_for_dc(dc, lines) if dc is not None else [lines]
                if pages is not None:
                    self._print_order = [p for p in pages if 1 <= p <= len(self._pages)]
                else:
                    self._print_order = list(range(1, len(self._pages) + 1))

            def OnPrintPage(self, page_index: int) -> bool:
                dc = self.GetDC()
                if dc is None or not (1 <= page_index <= len(self._print_order)):
                    return False
                real_page = self._print_order[page_index - 1]
                dc.SetFont(font)
                y = margin
                line_height = dc.GetTextExtent("A")[1] + 2
                for line in self._pages[real_page - 1]:
                    dc.DrawText(line, margin, y)
                    y += line_height
                return True

            def HasPage(self, page: int) -> bool:
                return 1 <= page <= len(self._print_order)

            def GetPageInfo(self) -> tuple[int, int, int, int]:
                count = max(1, len(self._print_order))
                return (1, count, 1, count)

        return _TextPrintout(title)

    def page_setup(self) -> None:
        wx = self._wx
        dialog = wx.PageSetupDialog(self.frame, self._page_setup_data)
        try:
            if self._show_modal_dialog(dialog, "Page Setup") != wx.ID_OK:
                self._set_status("Page setup cancelled")
                return
            self._page_setup_data = dialog.GetPageSetupData()
            self._print_data = self._page_setup_data.GetPrintData()
            self._set_status("Page setup updated")
        finally:
            dialog.Destroy()

    def print_document(self) -> None:
        printout = self._build_text_printout(self.document.name, self.editor.GetValue())
        self._run_print_job(printout)

    def print_studio(self) -> None:
        """File > Print Studio...: an accessible preview + page-set options.

        Computes real pagination first (the same DC type the print job
        itself uses, so the page count matches what actually prints), shows
        Print Studio, then hands off to the identical ``wx.Printer`` flow
        ``print_document`` uses -- Print Studio is a step *before* the OS
        print dialog, not a replacement for it (no WYSIWYG renderer; that
        is explicitly out of scope).
        """
        from quill.core.print_pagination import select_pages
        from quill.ui.print_studio_dialog import PrintStudioDialog

        text = self.editor.GetValue()
        preview = self._compute_print_preview(text)
        dlg = PrintStudioDialog(self.frame, preview, announce_cb=self._announce)
        accepted = dlg.show()
        dlg.close()
        if not accepted:
            self._set_status("Print Studio cancelled")
            return
        pages = select_pages(
            preview.page_count,
            page_set=dlg.page_set,
            reverse=dlg.reverse,
            skip_first_page=dlg.skip_first_page,
        )
        if not pages:
            self._set_status("No pages match the chosen options -- nothing to print.")
            return
        printout = self._build_text_printout(self.document.name, text, pages=pages)
        self._run_print_job(printout)

    def _run_print_job(self, printout: object) -> None:
        wx = self._wx
        printer = wx.Printer(wx.PrintDialogData(self._print_data))
        try:
            success = bool(printer.Print(self.frame, printout, True))
        except Exception as error:
            printout.Destroy()
            self._show_message_box(f"Printing failed: {error}", "Print", wx.ICON_ERROR | wx.OK)
            return
        if not success:
            read_last_error = getattr(printer, "GetLastError", None)
            last_error = read_last_error() if callable(read_last_error) else None
            cancelled_code = getattr(wx, "PRINTER_CANCELLED", None)
            no_error_code = getattr(wx, "PRINTER_NO_ERROR", None)
            if last_error == cancelled_code or last_error in {None, no_error_code}:
                self._set_status("Printing cancelled")
                printout.Destroy()
                return
            self._show_message_box("Printing failed.", "Print", wx.ICON_ERROR | wx.OK)
            printout.Destroy()
            return
        self._print_data = printer.GetPrintDialogData().GetPrintData()
        printout.Destroy()
        self._set_status("Printed document")
