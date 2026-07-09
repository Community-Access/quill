"""Behavioral tests for PrintStudioDialog (#891)."""

from __future__ import annotations

import pytest
import wx

from quill.core.print_pagination import PageSetOption, PrintPreview
from quill.ui.print_studio_dialog import PrintStudioDialog


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _preview() -> PrintPreview:
    return PrintPreview(page_count=3, paper_name="Letter", margins_text="default margins")


def test_preview_summary_shown_in_readonly_field(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = PrintStudioDialog(frame, _preview())
    assert dlg._preview_ctrl.GetValue() == "3 pages, Letter, default margins"
    dlg.dialog.Destroy()
    frame.Destroy()


def test_defaults_are_all_pages_no_reverse_no_skip(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = PrintStudioDialog(frame, _preview())
    assert dlg.page_set == PageSetOption.ALL
    assert dlg.reverse is False
    assert dlg.skip_first_page is False
    dlg.dialog.Destroy()
    frame.Destroy()


def test_print_captures_odd_pages_choice(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = PrintStudioDialog(frame, _preview())
    dlg._page_set_choice.SetSelection(1)
    dlg._on_print(None)
    assert dlg.page_set == PageSetOption.ODD
    dlg.dialog.Destroy()
    frame.Destroy()


def test_print_captures_even_pages_choice(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = PrintStudioDialog(frame, _preview())
    dlg._page_set_choice.SetSelection(2)
    dlg._on_print(None)
    assert dlg.page_set == PageSetOption.EVEN
    dlg.dialog.Destroy()
    frame.Destroy()


def test_print_captures_reverse_and_skip_first(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = PrintStudioDialog(frame, _preview())
    dlg._reverse_check.SetValue(True)
    dlg._skip_first_check.SetValue(True)
    dlg._on_print(None)
    assert dlg.reverse is True
    assert dlg.skip_first_page is True
    dlg.dialog.Destroy()
    frame.Destroy()


def test_show_returns_false_when_not_accepted(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = PrintStudioDialog(frame, _preview())
    assert dlg._accepted is False
    dlg.dialog.Destroy()
    frame.Destroy()
