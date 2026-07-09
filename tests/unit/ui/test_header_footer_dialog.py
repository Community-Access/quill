"""Behavioral tests for HeaderFooterDialog (#892)."""

from __future__ import annotations

import pytest
import wx

from quill.core.header_footer import HeaderFooterSpec, PageNumberStyle
from quill.ui.header_footer_dialog import HeaderFooterDialog


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_starts_with_blank_when_no_existing_spec(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = HeaderFooterDialog(frame, None)
    assert dlg._header_left.GetValue() == ""
    assert dlg._footer_right.GetValue() == ""
    dlg.dialog.Destroy()
    frame.Destroy()


def test_loads_an_existing_spec(wx_app) -> None:
    frame = wx.Frame(None)
    spec = HeaderFooterSpec(header_left="{title}", footer_right="{page}", start_page_number=5)
    dlg = HeaderFooterDialog(frame, spec)
    assert dlg._header_left.GetValue() == "{title}"
    assert dlg._footer_right.GetValue() == "{page}"
    assert dlg._start_page_ctrl.GetValue() == 5
    dlg.dialog.Destroy()
    frame.Destroy()


def test_selecting_a_preset_fills_in_its_zones(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = HeaderFooterDialog(frame, None)
    index = dlg._preset_names.index("Title left, page number right")
    dlg._preset_choice.SetSelection(index)
    dlg._on_preset_selected(None)
    assert dlg._header_left.GetValue() == "{title}"
    assert dlg._footer_right.GetValue() == "{page}"
    dlg.dialog.Destroy()
    frame.Destroy()


def test_first_page_fields_disabled_until_checkbox_is_checked(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = HeaderFooterDialog(frame, None)
    assert dlg._first_page_header_left.IsEnabled() is False
    dlg._first_page_check.SetValue(True)
    dlg._on_first_page_toggle(None)
    assert dlg._first_page_header_left.IsEnabled() is True
    dlg.dialog.Destroy()
    frame.Destroy()


def test_save_captures_all_fields_into_a_spec(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = HeaderFooterDialog(frame, None)
    dlg._header_center.SetValue("{title}")
    dlg._footer_right.SetValue("{page}")
    dlg._page_style_choice.SetSelection(1)
    dlg._start_page_ctrl.SetValue(7)
    dlg._on_save(None)
    assert dlg._result is not None
    assert dlg._result.header_center == "{title}"
    assert dlg._result.footer_right == "{page}"
    assert dlg._result.page_number_style == PageNumberStyle.ROMAN
    assert dlg._result.start_page_number == 7
    dlg.dialog.Destroy()
    frame.Destroy()


def test_roman_page_style_round_trips_through_the_form(wx_app) -> None:
    frame = wx.Frame(None)
    spec = HeaderFooterSpec(page_number_style=PageNumberStyle.ROMAN)
    dlg = HeaderFooterDialog(frame, spec)
    assert dlg._page_style_choice.GetSelection() == 1
    dlg.dialog.Destroy()
    frame.Destroy()
