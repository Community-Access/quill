"""Studio is an explicit, release-gated companion, never a document export."""

from __future__ import annotations

import pytest
import wx

from quill.core import app_launcher
from quill.core.lite.command_areas import visible_commands
from quill.core.lite.keymap import (
    command_titles,
    conflicting_handlers,
    default_aliases,
    default_keymap,
    resolved_commands,
)
from quill.core.lite.shortcut_text import shortcut_text


@pytest.mark.parametrize("developer", [False, True])
def test_studio_visibility_follows_the_shared_release_gate(monkeypatch, developer) -> None:
    monkeypatch.setenv("QUILL_DEV_BUILD", "1" if developer else "0")
    rows = visible_commands(lambda _area: True)
    assert any(r[3] == "cmd_open_studio" for r in rows) is developer
    assert ("Open QUILL Studio" in shortcut_text()) is developer
    assert ("cmd_open_studio" in command_titles()) is developer


@pytest.mark.parametrize("developer", [False, True])
def test_studio_palette_visibility_and_dispatch(lite_window, monkeypatch, developer) -> None:
    from quill.apps.lite_services import LiteServicesMixin

    monkeypatch.setenv("QUILL_DEV_BUILD", "1" if developer else "0")
    calls = []
    monkeypatch.setattr(app_launcher, "launch_app", lambda key: calls.append(key) or True)
    win = lite_window("Private unsaved document")
    win.run_unless_read_only = lambda handler: getattr(win, handler)()
    win.app.feature_enabled = lambda _area: True
    win.app.keymap = {}
    registry = LiteServicesMixin.command_registry(win.app, win)
    command = registry.get("lite.cmd_open_studio")
    assert (command is not None) is developer
    if command is not None:
        command.handler()
        assert calls == ["studio"]
        assert win.control.GetValue() == "Private unsaved document"


@pytest.mark.parametrize("succeeds", [False, True])
def test_studio_launch_uses_the_shared_launcher_without_document_data(
    lite_window, monkeypatch, succeeds
) -> None:
    monkeypatch.setenv("QUILL_DEV_BUILD", "1")
    calls = []

    def launch(key, **kwargs):
        calls.append((key, kwargs))
        return succeeds

    monkeypatch.setattr(app_launcher, "launch_app", launch)
    win = lite_window("Private unsaved document")
    win.cmd_open_studio()
    assert calls == [("studio", {})]
    assert win.control.GetValue() == "Private unsaved document"
    assert win.app.voice.said[-1] == (
        "Opening QUILL Studio."
        if succeeds
        else "QUILL Studio could not be opened; it may not be installed."
    )


def test_hidden_studio_command_also_refuses_direct_dispatch(lite_window, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DEV_BUILD", "0")
    calls = []
    monkeypatch.setattr(app_launcher, "launch_app", calls.append)
    win = lite_window("unchanged")
    win.cmd_open_studio()
    assert calls == []
    assert win.app.voice.said[-1] == "QUILL Studio is not available in this build."


def test_studio_has_a_real_document_menu_event_and_honors_rebinding(
    wx_session_app, monkeypatch
) -> None:
    from quill.apps.lite_window_menus import DocumentMenuMixin
    from quill.apps.lite_window_tools import DocumentToolsMixin

    monkeypatch.setenv("QUILL_DEV_BUILD", "1")
    calls = []
    monkeypatch.setattr(app_launcher, "launch_app", lambda key: calls.append(key) or True)

    class Frame(DocumentToolsMixin, DocumentMenuMixin, wx.Frame):
        def __init__(self):
            wx.Frame.__init__(self, None)
            self.said = []
            self._menu_items = {}
            self._check_items = {}
            self._hideable_rows = {}
            rows = [
                row
                for row in resolved_commands(
                    lambda _area: True, {"cmd_open_studio": "Ctrl+Alt+Shift+F24"}
                )
                if row[3] == "cmd_open_studio"
            ]
            menu = self._fill_menu(wx.Menu(), "&Tools", {"&Tools": rows})
            bar = wx.MenuBar()
            bar.Append(menu, "&Tools")
            self.SetMenuBar(bar)

        def _announce(self, message):
            self.said.append(message)

        def run_unless_read_only(self, handler):
            getattr(self, handler)()

    frame = Frame()
    try:
        item = frame._menu_items["cmd_open_studio"]
        for bindings in (default_keymap(), default_aliases()):
            assert not conflicting_handlers(bindings, "cmd_open_studio", "Ctrl+Alt+Shift+F24")
        assert item.GetItemLabel() == "Open &QUILL Studio\tCtrl+Alt+Shift+F24"
        event = wx.CommandEvent(wx.EVT_MENU.typeId, item.GetId())
        assert frame.ProcessEvent(event)
        assert calls == ["studio"]
        assert frame.said == ["Opening QUILL Studio."]
    finally:
        frame.Destroy()
