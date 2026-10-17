"""D-24: Programs Dictation Never Types Into, the window."""

from __future__ import annotations

from typing import Any

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    yield app


def _dialog(names: list[str], front: str = "") -> tuple[Any, list[str]]:
    from quill.ui.dictation_never_type_dialog import NeverTypeDialog

    said: list[str] = []
    dialog = NeverTypeDialog(None, names, said.append, front=lambda: front)
    return dialog, said


def test_the_list_shows_each_program_by_name_and_file_name(wx_app) -> None:
    dialog, _said = _dialog(["KeePass", "notepad.exe"])
    try:
        assert dialog.list.GetStrings() == ["KeePass (keepass.exe)", "notepad.exe"]
        assert dialog.names() == ["keepass.exe", "notepad.exe"]
    finally:
        dialog.Destroy()


def test_the_front_button_names_the_program_it_adds(wx_app) -> None:
    dialog, said = _dialog([], front="KeePassXC.exe")
    try:
        assert dialog.add_front.GetLabel() == "Add &Front Program: KeePassXC (keepassxc.exe)"
        assert dialog.add_program_in_front() is True
        assert dialog.names() == ["keepassxc.exe"]
        assert said[-1] == "Added KeePassXC (keepassxc.exe)."
        assert dialog.add_program_in_front() is False
        assert said[-1] == "keepassxc.exe is already on the list."
    finally:
        dialog.Destroy()


def test_with_no_program_in_front_it_says_to_type_the_name(wx_app) -> None:
    dialog, said = _dialog([])
    try:
        assert dialog.add_front.GetLabel() == "Add the Program in &Front"
        assert dialog.add_program_in_front() is False
        assert "Type its file name instead" in said[-1]
    finally:
        dialog.Destroy()


def test_add_by_name_adds_clears_the_field_and_refuses_an_empty_one(wx_app) -> None:
    dialog, said = _dialog([])
    try:
        assert dialog.add_by_name() is False
        assert said[-1] == "Type a program file name first, like keepass.exe."
        dialog.name.SetValue("Bitwarden")
        assert dialog.add_by_name() is True
        assert dialog.names() == ["bitwarden.exe"]
        assert dialog.name.GetValue() == ""
    finally:
        dialog.Destroy()


def test_enter_in_the_name_field_adds_it_instead_of_closing(wx_app) -> None:
    dialog, _said = _dialog([])
    try:
        assert dialog.name.GetWindowStyleFlag() & wx.TE_PROCESS_ENTER
        dialog.name.SetValue("roboform")
        event = wx.CommandEvent(wx.wxEVT_TEXT_ENTER, dialog.name.GetId())
        event.SetEventObject(dialog.name)
        dialog.name.GetEventHandler().ProcessEvent(event)
        assert dialog.names() == ["roboform.exe"]
    finally:
        dialog.Destroy()


def test_ok_keeps_a_name_typed_and_never_added(wx_app) -> None:
    dialog, _said = _dialog(["keepass.exe"])
    try:
        dialog.name.SetValue("enpass")
        event = wx.CommandEvent(wx.wxEVT_BUTTON, wx.ID_OK)
        dialog._on_ok(event)
        assert dialog.names() == ["keepass.exe", "enpass.exe"]
    finally:
        dialog.Destroy()


def test_remove_and_the_delete_key_take_the_chosen_program_off(wx_app) -> None:
    dialog, said = _dialog(["a.exe", "b.exe", "c.exe"])
    try:
        dialog.list.SetSelection(1)
        assert dialog.remove_chosen() is True
        assert dialog.names() == ["a.exe", "c.exe"]
        assert said[-1] == "Removed b.exe."
        assert dialog.list.GetSelection() == 1

        key = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        key.SetKeyCode(wx.WXK_DELETE)
        dialog._on_list_key(key)
        assert dialog.names() == ["a.exe"]
    finally:
        dialog.Destroy()


def test_remove_with_nothing_chosen_says_so(wx_app) -> None:
    dialog, said = _dialog([])
    try:
        assert dialog.remove_chosen() is False
        assert said[-1] == "Choose a program in the list first."
    finally:
        dialog.Destroy()
