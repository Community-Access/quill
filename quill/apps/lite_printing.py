"""Print and Page Setup -- the one thing Notepad and WordPad have that a first
cut of QuillLite did not.

Ctrl+P is in every text editor Windows has ever shipped, and an editor that
answers it with nothing is an editor somebody has to copy their document out of.
So it is here, and it is deliberately the *simple* one: page setup, a print
dialog, page numbers, and the document's own font.

Three decisions worth stating, because each is a limit somebody will meet:

* **Pagination is QUILL's**, not a second implementation:
  :func:`quill.core.print_pagination.paginate_lines` decides which lines land on
  which page, from a line height measured on the real printer DC. That function
  is wx-free and directly tested, which is the half of printing that can be
  tested at all.
* **Long lines wrap to the page**, always -- independently of the editor's own
  Word Wrap setting. Word Wrap is about the window; a printed line that runs off
  the right edge of the paper is simply lost, and no setting should be able to
  cause that.
* **Rich formatting does not print in 1.0.** The text prints, in the editor's
  font, with headings *marked* rather than styled. Printing a Rich Edit's real
  formatting means driving ``EM_FORMATRANGE``, which cannot be verified without
  a printer in the room; shipping an untested path that produces blank pages
  would be worse than shipping a plain one that says so. The user guide says so
  too, in as many words.

Page setup is shared across every open document, because it is a property of the
printer and the paper rather than of one file.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.print_pagination import paginate_lines
from quill.ui.richedit_editing import RICH

__all__ = ["DocumentPrintMixin", "PrintSettings"]

#: Page margin in device units. QUILL's own value, so the two products put text
#: in the same place on the page.
_MARGIN_PX = 50

#: Room left under the text for the page number.
_FOOTER_GAP_PX = 24


class PrintSettings:
    """The printer and paper choices, shared by every open document.

    Owned by the app rather than by a window: paper size and margins are a
    property of the printer, and answering Page Setup separately in each window
    would mean setting it again for every document.

    **And they outlive the session**, since 2026-09-16. They did not: Page Setup
    wrote into this object and nothing wrote it anywhere, so paper, orientation
    and all four margins reverted at every launch. For somebody who prints on
    Letter, or who wants wide margins because they print large, that is the same
    dialog every day (bad.md F13, PR2). Three fields in the settings file, which
    is a configuration rather than a record of one desk, so it travels with the
    portable backup like everything else.

    The printer *itself* is deliberately not stored: which printer is attached
    is a fact about the machine and about today, and a stored one that has gone
    away is worse than the system default.
    """

    def __init__(self, settings: Any | None = None) -> None:
        margins = list(getattr(settings, "print_margins_mm", None) or [15, 15, 15, 15])
        if len(margins) != 4:
            margins = [15, 15, 15, 15]
        self.print_data = wx.PrintData()
        self.print_data.SetPaperId(int(getattr(settings, "print_paper_id", wx.PAPER_A4)))
        self.print_data.SetOrientation(
            wx.LANDSCAPE if getattr(settings, "print_landscape", False) else wx.PORTRAIT
        )
        self.page_setup = wx.PageSetupDialogData(self.print_data)
        self.page_setup.SetMarginTopLeft(wx.Point(margins[0], margins[1]))
        self.page_setup.SetMarginBottomRight(wx.Point(margins[2], margins[3]))

    def store_into(self, settings: Any) -> None:
        """Copy the current paper, orientation and margins back into *settings*."""
        top_left = self.page_setup.GetMarginTopLeft()
        bottom_right = self.page_setup.GetMarginBottomRight()
        settings.print_paper_id = int(self.print_data.GetPaperId())
        settings.print_landscape = self.print_data.GetOrientation() == wx.LANDSCAPE
        settings.print_margins_mm = [
            int(top_left.x),
            int(top_left.y),
            int(bottom_right.x),
            int(bottom_right.y),
        ]


class _LitePrintout(wx.Printout):
    """One document, paginated against the real printer DC."""

    def __init__(self, title: str, lines: list[str], font: wx.Font) -> None:
        super().__init__(title)
        self._title = title
        self._lines = lines or [""]
        self._font = font
        self._pages: list[list[str]] = [self._lines]

    # -- wx.Printout contract ---------------------------------------------- #

    def OnPreparePrinting(self) -> None:  # noqa: N802 - wx API shape
        """Wrap and paginate once, against the DC that will actually print."""
        dc = self.GetDC()
        if dc is None:
            return
        dc.SetFont(self._font)
        width, height = dc.GetSize()
        line_height = dc.GetTextExtent("A")[1] + 2
        usable_height = height - 2 * _MARGIN_PX - _FOOTER_GAP_PX
        lines_per_page = max(1, int(usable_height // max(1, line_height)))
        wrapped = _wrap_to_width(dc, self._lines, width - 2 * _MARGIN_PX)
        self._pages = paginate_lines(wrapped, lines_per_page)

    def HasPage(self, page: int) -> bool:  # noqa: N802 - wx API shape
        return 1 <= page <= len(self._pages)

    def GetPageInfo(self) -> tuple[int, int, int, int]:  # noqa: N802 - wx API shape
        last = max(1, len(self._pages))
        return (1, last, 1, last)

    def OnPrintPage(self, page: int) -> bool:  # noqa: N802 - wx API shape
        dc = self.GetDC()
        if dc is None or not self.HasPage(page):
            return False
        dc.SetFont(self._font)
        width, _height = dc.GetSize()
        line_height = dc.GetTextExtent("A")[1] + 2
        y = _MARGIN_PX
        for line in self._pages[page - 1]:
            dc.DrawText(line, _MARGIN_PX, y)
            y += line_height
        footer = f"{self._title}    Page {page} of {len(self._pages)}"
        footer_width = dc.GetTextExtent(footer)[0]
        dc.DrawText(footer, (width - footer_width) // 2, y + _FOOTER_GAP_PX // 2)
        return True


def _wrap_to_width(dc: wx.DC, lines: list[str], width: int) -> list[str]:
    """Break every line that is wider than the page, on word boundaries.

    Independent of the editor's Word Wrap setting on purpose: that setting is
    about the window, and a printed line that runs off the right edge of the
    paper is not scrolled to, it is gone.
    """
    out: list[str] = []
    for line in lines:
        if not line:
            out.append("")
            continue
        if dc.GetTextExtent(line)[0] <= width:
            out.append(line)
            continue
        current = ""
        for word in line.split(" "):
            candidate = f"{current} {word}".strip()
            if current and dc.GetTextExtent(candidate)[0] > width:
                out.append(current)
                current = word
            else:
                current = candidate
        out.append(current)
    return out


class DocumentPrintMixin:
    """Page Setup and Print for a QuillLite document window."""

    def _printable_lines(self) -> list[str]:
        """The document as lines, with headings marked rather than styled.

        A heading that prints at body weight and body size is indistinguishable
        from body text on paper, which loses the one piece of structure the
        document had. Until real formatted printing lands, the level is written
        in front of the line -- ugly, honest, and better than losing it.
        """
        lines = self.control.GetValue().splitlines() or [""]
        if self.editor.mode != RICH:
            return lines
        marks = self._heading_marks()
        if not marks:
            return lines
        return [
            f"[H{marks[index]}] {line}" if index in marks else line
            for index, line in enumerate(lines)
        ]

    def _heading_marks(self) -> dict[int, int]:
        """``{line index: heading level}`` for this document. Best effort."""
        text = self.control.GetValue()
        marks: dict[int, int] = {}
        try:
            for offset, level, _heading_text in self.editor.all_headings():
                marks[text.count("\n", 0, min(offset, len(text)))] = level
        except Exception:  # noqa: BLE001 - printing must never fail on a readback
            return {}
        return marks

    def cmd_page_setup(self) -> None:
        """Paper, orientation and margins, shared by every open document."""
        settings = self.app.print_settings
        data = wx.PageSetupDialogData(settings.page_setup)
        data.SetPrintData(settings.print_data)
        # Not a `with` block: wx.PageSetupDialog is one of the few Phoenix
        # dialogs that is **not** a context manager, so `with` raised TypeError
        # before the dialog was ever shown -- Page Setup did nothing at all, and
        # nothing said why. try/finally does the same job with no assumption.
        dialog = wx.PageSetupDialog(self, data)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            settings.page_setup = wx.PageSetupDialogData(dialog.GetPageSetupData())
            settings.print_data = wx.PrintData(settings.page_setup.GetPrintData())
        finally:
            dialog.Destroy()
        # Written to disk, not just to memory: "Page setup saved" was a sentence
        # about a variable until 2026-09-16 (bad.md F13, PR2).
        settings.store_into(self.app.settings)
        self.app.save_settings()
        self._announce("Page setup saved")

    def cmd_print(self) -> None:
        """Print this document. Cancelling is not a failure and says nothing."""
        settings = self.app.print_settings
        print_dialog_data = wx.PrintDialogData(settings.print_data)
        printer = wx.Printer(print_dialog_data)
        printout = _LitePrintout(self.document_name(), self._printable_lines(), self._print_font())
        from quill.core.sound_events import SoundEvent

        self._cue(SoundEvent.PRINT_STARTED)
        if printer.Print(self, printout, True):
            settings.print_data = wx.PrintData(printer.GetPrintDialogData().GetPrintData())
            # Handed to the spooler, which is as far as this app can see. The
            # cue says "it left here", which is the fact the user is waiting for.
            self._cue(SoundEvent.PRINT_COMPLETE)
            self._announce(f"Printing {self.document_name()}")
        elif printer.GetLastError() == wx.PRINTER_ERROR:
            # Cancelled is the common case and needs no announcement; a real
            # error does, because nothing else in the app will mention it.
            self._report_failure(
                "Print failed",
                "The document could not be printed. Check that a printer is "
                "installed and available, then try again.",
            )
        printout.Destroy()

    def _print_font(self) -> Any:
        """The document's own face and size, at a printable point size.

        Not a fixed teletype font: what QuillLite shows is what it should print,
        and somebody who chose a face for legibility on screen chose it for a
        reason. The size is clamped, because a 72-point document would print one
        word per page and a 6-point one is unreadable on paper.
        """
        settings = self.app.settings
        points = max(8, min(16, int(settings.font_size)))
        return wx.Font(
            points,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
            faceName=settings.font_name,
        )
