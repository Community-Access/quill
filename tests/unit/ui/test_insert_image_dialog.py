"""Behavioral tests for InsertImageDialog (#899)."""

from __future__ import annotations

import pytest
import wx

from quill.ui.insert_image_dialog import InsertImageDialog


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_insert_with_alt_text_builds_markdown(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = InsertImageDialog(frame)
    dlg._path_ctrl.SetValue("cat.png")
    dlg._alt_ctrl.SetValue("a sleeping cat")
    dlg._on_insert(None)
    assert dlg._result == "![a sleeping cat](cat.png)"
    dlg.dialog.Destroy()
    frame.Destroy()


def test_insert_without_path_reports_status_and_does_not_close(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = InsertImageDialog(frame)
    dlg._alt_ctrl.SetValue("a cat")
    dlg._on_insert(None)
    assert dlg._result is None
    assert "image file" in dlg._status.GetLabel().lower()
    dlg.dialog.Destroy()
    frame.Destroy()


def test_insert_without_alt_text_or_decorative_flag_is_rejected(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = InsertImageDialog(frame)
    dlg._path_ctrl.SetValue("cat.png")
    dlg._on_insert(None)
    assert dlg._result is None
    assert "alt text" in dlg._status.GetLabel().lower()
    dlg.dialog.Destroy()
    frame.Destroy()


def test_decorative_checkbox_allows_empty_alt_text(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = InsertImageDialog(frame)
    dlg._path_ctrl.SetValue("divider.png")
    dlg._decorative_check.SetValue(True)
    dlg._on_insert(None)
    assert dlg._result == "![](divider.png)"
    dlg.dialog.Destroy()
    frame.Destroy()


def test_decorative_checkbox_disables_alt_text_field(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = InsertImageDialog(frame)
    dlg._decorative_check.SetValue(True)
    dlg._on_decorative_toggle(None)
    assert dlg._alt_ctrl.IsEnabled() is False
    dlg._decorative_check.SetValue(False)
    dlg._on_decorative_toggle(None)
    assert dlg._alt_ctrl.IsEnabled() is True
    dlg.dialog.Destroy()
    frame.Destroy()
