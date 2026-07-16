"""#1055: F1 (context-sensitive help) must work in the Preferences hub and
the Command Palette, not just the document editor.

MainFrame's own F1 binding only ever reaches the main editor frame; both of
these are separate modal wx.Dialogs with their own EVT_CHAR_HOOK, so each
needs its own explicit F1 handling wired to show_help_on_control.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
import wx

from quill.core.commands import CommandRegistry
from quill.ui.main_frame import MainFrame
from quill.ui.palette import CommandPaletteDialog


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _send_f1(dialog: wx.Dialog) -> None:
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetEventObject(dialog)
    event.SetKeyCode(wx.WXK_F1)
    dialog.GetEventHandler().ProcessEvent(event)


def test_command_palette_f1_calls_on_help(wx_app) -> None:
    parent = wx.Frame(None)
    calls: list[bool] = []
    dialog = CommandPaletteDialog(
        parent, CommandRegistry(), None, on_help=lambda: calls.append(True)
    )

    _send_f1(dialog.dialog)

    assert calls == [True]
    dialog.dialog.Destroy()
    parent.Destroy()


def test_command_palette_f1_is_a_no_op_without_on_help(wx_app) -> None:
    # Radio/Cast's own command palette (app_shell.py) doesn't pass on_help --
    # F1 there must not raise, just fall through like any other unhandled key.
    parent = wx.Frame(None)
    dialog = CommandPaletteDialog(parent, CommandRegistry(), None)

    _send_f1(dialog.dialog)  # must not raise

    dialog.dialog.Destroy()
    parent.Destroy()


def _preferences_frame(help_calls: list[bool]) -> Any:
    frame = MainFrame.__new__(MainFrame)
    frame._wx = wx
    frame.frame = wx.Frame(None)
    frame.open_general_preferences = lambda: None
    frame.open_profiles_and_features_settings = lambda: None
    frame.open_status_bar_settings = lambda: None
    frame.open_keymap_editor = lambda: None
    frame.open_ai_preferences = lambda: None
    frame.open_watch_folder_settings = lambda: None
    frame.open_glow_settings = lambda: None
    frame.install_starter_snippet_packs = lambda: None
    frame.open_quillin_preferences = lambda _m: None
    frame._feature_enabled = lambda _gate: True
    frame._pref_manifests = lambda: []
    frame._set_status = lambda _msg: None
    frame.show_help_on_control = lambda: help_calls.append(True)
    return frame


def test_preferences_hub_f1_calls_show_help_on_control(wx_app) -> None:
    help_calls: list[bool] = []
    frame = _preferences_frame(help_calls)
    captured: dict[str, wx.Dialog] = {}

    def fake_show_modal_dialog(dialog: wx.Dialog, _label: str) -> int:
        captured["dialog"] = dialog
        _send_f1(dialog)
        return wx.ID_CLOSE

    frame._show_modal_dialog = fake_show_modal_dialog  # type: ignore[method-assign]

    MainFrame.open_preferences(frame)

    assert help_calls == [True]
    frame.frame.Destroy()
