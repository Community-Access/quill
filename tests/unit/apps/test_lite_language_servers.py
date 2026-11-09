"""QUILL Lite's Navigate > Code > Parameter Hints and Language Servers...,
called the way the menu calls them (quill/apps/lite_window_word_prediction.py)."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.lite.parity import COMMAND_EQUIVALENTS


def test_parameter_hints_with_no_server_say_why(lite_window) -> None:
    win = lite_window("print(", cursor=6)
    win.cmd_parameter_hints()
    assert win.announcements[-1] == "No parameter hints: no language server for this file"


def test_language_servers_window_saves_on_ok_and_not_on_cancel(lite_window, monkeypatch) -> None:
    import wx

    import quill.ui.dialog_contract as contract
    import quill.ui.language_servers_dialog as dialog_module

    applied: list[bool] = []

    class _Window:
        def __init__(self, parent, settings) -> None:
            self.dialog = SimpleNamespace()

        def apply(self) -> None:
            applied.append(True)

        def destroy(self) -> None:
            pass

    answers = [wx.ID_CANCEL, wx.ID_OK]
    monkeypatch.setattr(dialog_module, "LanguageServersDialog", _Window)
    monkeypatch.setattr(contract, "show_modal_dialog", lambda dialog, label: answers.pop(0))
    win = lite_window("x", cursor=0)
    queued = win.app.queued_settings
    win.cmd_language_servers()
    assert applied == [] and win.app.queued_settings == queued
    win.cmd_language_servers()
    assert applied == [True] and win.app.queued_settings == queued + 1
    assert win.announcements[-1] == "Language server settings saved"


def test_the_rows_are_quills_commands() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS

    rows = {r[3]: r for r in COMMANDS if r[0] == "&Navigate|&Code" and r[3]}
    assert rows["cmd_parameter_hints"][1] == "Parameter &Hints"
    assert rows["cmd_language_servers"][1] == "&Language Servers..."
    for handler, command in (
        ("cmd_parameter_hints", "edit.parameter_hints"),
        ("cmd_language_servers", "tools.language_servers"),
    ):
        assert COMMAND_EQUIVALENTS[handler] == command
        assert DEFAULT_KEYMAP[command] == rows[handler][2] == ""
