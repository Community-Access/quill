"""The shared first-task line (FUX-09): shown while empty, never stranding focus."""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture
def frame(wx_session_app):
    window = wx.Frame(None)
    try:
        yield window
    finally:
        window.Destroy()


def _line(frame):
    from quill.ui.empty_state_line import EmptyStateLine

    panel = wx.Panel(frame)
    line = EmptyStateLine(panel, name="Getting started")
    tree = wx.TreeCtrl(panel)
    return line, tree


def test_hidden_until_there_is_something_to_say_and_the_sentence_is_its_tooltip(frame) -> None:
    line, _tree = _line(frame)
    assert not line.shown and line.text == ""
    line.update("No stations yet. Browse Stations (Ctrl+B).")
    assert line.shown and line.text == "No stations yet. Browse Stations (Ctrl+B)."
    assert line.ctrl.GetToolTipText() == line.text
    assert line.ctrl.GetWindowStyleFlag() & wx.TE_READONLY
    assert not line.ctrl.GetWindowStyleFlag() & wx.BORDER_NONE  # a field, with a focus ring


def test_the_name_is_one_a_windows_screen_reader_reads(frame, monkeypatch) -> None:
    from quill.ui import spoken_name

    named: list[str] = []
    monkeypatch.setattr(spoken_name, "set_spoken_name", lambda _c, n: named.append(n))
    _line(frame)
    assert named == ["Getting started"]


def test_hiding_with_focus_on_it_moves_focus_to_the_list(frame, monkeypatch) -> None:
    line, tree = _line(frame)
    line.update("Empty.")
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: line.ctrl))
    moved: list[str] = []
    monkeypatch.setattr(tree, "SetFocus", lambda: moved.append("tree"))
    line.update("", then_focus=tree)
    assert not line.shown and moved == ["tree"]


def test_hiding_while_a_dialog_has_focus_sends_focus_to_the_list_on_return(
    frame, monkeypatch, wx_call_after
) -> None:
    wx_call_after()
    line, tree = _line(frame)
    line.update("Empty.")
    line._last_focus = True  # the line had focus when Add Custom Station opened
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: None))
    moved: list[str] = []
    monkeypatch.setattr(tree, "SetFocus", lambda: moved.append("tree"))
    line.update("", then_focus=tree)
    assert moved == []  # not while the dialog is up
    line._on_activate(wx.ActivateEvent(wx.wxEVT_ACTIVATE, True))
    assert moved == ["tree"]
