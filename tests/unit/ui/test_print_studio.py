"""Tests for Print Studio (#891): pagination-aware printing and the
accessible preview, on the real MainFrame print methods."""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

from quill.core.document import Document
from quill.core.print_pagination import PrintPreview
from quill.ui.main_frame import MainFrame


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Editor:
    def __init__(self, text: str) -> None:
        self._text = text

    def GetValue(self) -> str:
        return self._text


def _build_frame(wx_app, text: str) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame._wx = wx
    frame.document = Document(path=Path("note.md"))
    frame.editor = _Editor(text)
    frame.frame = wx.Frame(None)
    frame._print_data = wx.PrintData()
    frame._page_setup_data = wx.PageSetupDialogData(frame._print_data)
    frame.status: list[str] = []
    frame._set_status = lambda msg: frame.status.append(msg)
    frame._announce = lambda _msg: None
    return frame


def test_compute_print_preview_short_document_is_one_page(wx_app) -> None:
    frame = _build_frame(wx_app, "just one short line")
    preview = frame._compute_print_preview(frame.editor.GetValue())
    assert isinstance(preview, PrintPreview)
    assert preview.page_count == 1
    frame.frame.Destroy()


def test_compute_print_preview_long_document_is_multiple_pages(wx_app) -> None:
    text = "\n".join(f"line {i}" for i in range(500))
    frame = _build_frame(wx_app, text)
    preview = frame._compute_print_preview(text)
    assert preview.page_count > 1
    frame.frame.Destroy()


def test_paginate_for_dc_splits_a_long_document_into_multiple_pages(wx_app) -> None:
    # Exercises the real pagination math against a live wx.PrinterDC -- the
    # same DC type both _compute_print_preview and the actual print job use.
    text_lines = [f"line {i}" for i in range(500)]
    frame = _build_frame(wx_app, "\n".join(text_lines))
    dc = wx.PrinterDC(frame._print_data)
    pages = frame._paginate_for_dc(dc, text_lines)
    assert len(pages) >= 2
    assert sum(len(p) for p in pages) == len(text_lines)
    frame.frame.Destroy()


def test_build_text_printout_without_a_live_dc_falls_back_to_one_page(wx_app) -> None:
    # wx only attaches a real DC to a Printout during an actual print job;
    # calling OnPreparePrinting outside of one (as this unit test does) sees
    # no DC, exercising the documented fallback: treat the document as a
    # single page rather than raising.
    text = "\n".join(f"line {i}" for i in range(500))
    frame = _build_frame(wx_app, text)
    printout = frame._build_text_printout("Test", text)
    printout.OnPreparePrinting()
    _min_page, max_page, _from, _to = printout.GetPageInfo()
    assert max_page == 1
    printout.Destroy()
    frame.frame.Destroy()


def test_build_text_printout_with_explicit_pages_restricts_to_valid_pages(wx_app) -> None:
    # With no live DC the fallback is a single real page; requesting pages
    # [1, 3] must be filtered down to just the page that actually exists.
    text = "short document"
    frame = _build_frame(wx_app, text)
    printout = frame._build_text_printout("Test", text, pages=[1, 3])
    printout.OnPreparePrinting()
    _min_page, max_page, _from, _to = printout.GetPageInfo()
    assert max_page == 1
    printout.Destroy()
    frame.frame.Destroy()


def test_print_studio_cancelled_dialog_does_not_print(wx_app, monkeypatch) -> None:
    class _FakeDialog:
        def __init__(self, parent, preview, announce_cb=None) -> None:
            pass

        def show(self) -> bool:
            return False

        def close(self) -> None:
            pass

    ran: list[bool] = []
    monkeypatch.setattr("quill.ui.print_studio_dialog.PrintStudioDialog", _FakeDialog)
    frame = _build_frame(wx_app, "hello world")
    frame._run_print_job = lambda printout: ran.append(True)
    frame.print_studio()
    assert ran == []
    assert frame.status == ["Print Studio cancelled"]
    frame.frame.Destroy()


def test_print_studio_accepted_runs_the_print_job_with_selected_pages(wx_app, monkeypatch) -> None:
    from quill.core.print_pagination import PageSetOption

    class _FakeDialog:
        def __init__(self, parent, preview, announce_cb=None) -> None:
            self.page_set = PageSetOption.ALL
            self.reverse = False
            self.skip_first_page = False

        def show(self) -> bool:
            return True

        def close(self) -> None:
            pass

    captured: dict[str, object] = {}
    monkeypatch.setattr("quill.ui.print_studio_dialog.PrintStudioDialog", _FakeDialog)
    frame = _build_frame(wx_app, "hello world")
    frame._run_print_job = lambda printout: captured.__setitem__("printout", printout)
    frame.print_studio()
    assert "printout" in captured
    captured["printout"].Destroy()
    frame.frame.Destroy()


def test_print_studio_no_matching_pages_reports_status_without_printing(
    wx_app, monkeypatch
) -> None:
    from quill.core.print_pagination import PageSetOption

    class _FakeDialog:
        def __init__(self, parent, preview, announce_cb=None) -> None:
            self.page_set = PageSetOption.EVEN
            self.reverse = False
            self.skip_first_page = False

        def show(self) -> bool:
            return True

        def close(self) -> None:
            pass

    ran: list[bool] = []
    monkeypatch.setattr("quill.ui.print_studio_dialog.PrintStudioDialog", _FakeDialog)
    frame = _build_frame(wx_app, "just one short line")  # single page -> no even pages
    frame._run_print_job = lambda printout: ran.append(True)
    frame.print_studio()
    assert ran == []
    assert "No pages match" in frame.status[-1]
    frame.frame.Destroy()
