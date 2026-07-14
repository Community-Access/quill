"""Behavioral tests for WorkPersonaDialog (#896)."""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

from quill.core.work_persona import WorkPersona, WorkPersonaStore
from quill.ui.work_persona_dialog import WorkPersonaDialog


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _dialog(wx_app, tmp_path: Path, *, apply_cb=None):
    store = WorkPersonaStore(tmp_path)
    store.create(WorkPersona(name="Work", technical_profile="writer"))
    store.create(WorkPersona(name="School", technical_profile="essential"))
    frame = wx.Frame(None)
    dlg = WorkPersonaDialog(frame, store, apply_cb=apply_cb)
    return dlg, frame, store


def test_lists_personas_sorted_and_loads_first_into_form(wx_app, tmp_path: Path) -> None:
    dlg, frame, _store = _dialog(wx_app, tmp_path)
    assert dlg._listbox.GetCount() == 2
    assert dlg._name_ctrl.GetValue() == "School"
    dlg.dialog.Destroy()
    frame.Destroy()


def test_new_clears_the_form_for_a_fresh_persona(wx_app, tmp_path: Path) -> None:
    dlg, frame, _store = _dialog(wx_app, tmp_path)
    dlg._on_new(None)
    assert dlg._name_ctrl.GetValue() == ""
    assert dlg._listbox.GetSelection() == wx.NOT_FOUND
    dlg.dialog.Destroy()
    frame.Destroy()


def test_save_requires_a_name(wx_app, tmp_path: Path) -> None:
    dlg, frame, store = _dialog(wx_app, tmp_path)
    dlg._on_new(None)
    dlg._name_ctrl.SetValue("")
    dlg._on_save(None)
    assert len(store) == 2
    dlg.dialog.Destroy()
    frame.Destroy()


def test_save_creates_a_new_persona(wx_app, tmp_path: Path) -> None:
    dlg, frame, store = _dialog(wx_app, tmp_path)
    dlg._on_new(None)
    dlg._name_ctrl.SetValue("Hobby")
    dlg._on_save(None)
    assert len(store) == 3
    assert store.get("Hobby") is not None
    dlg.dialog.Destroy()
    frame.Destroy()


def test_save_updates_the_selected_persona(wx_app, tmp_path: Path) -> None:
    dlg, frame, store = _dialog(wx_app, tmp_path)
    dlg._listbox.SetSelection(1)  # "Work"
    dlg._on_selection_changed(None)
    dlg._folder_ctrl.SetValue("C:/Projects/Work")
    dlg._on_save(None)
    assert store.get("Work").working_folder == "C:/Projects/Work"
    assert len(store) == 2
    dlg.dialog.Destroy()
    frame.Destroy()


def test_delete_removes_the_selected_persona(wx_app, tmp_path: Path) -> None:
    dlg, frame, store = _dialog(wx_app, tmp_path)
    dlg._listbox.SetSelection(0)
    dlg._on_selection_changed(None)
    dlg._on_delete(None)
    assert len(store) == 1
    dlg.dialog.Destroy()
    frame.Destroy()


def test_apply_calls_the_supplied_callback_with_the_selected_persona(
    wx_app, tmp_path: Path
) -> None:
    calls: list[WorkPersona] = []
    dlg, frame, _store = _dialog(wx_app, tmp_path, apply_cb=calls.append)
    dlg._listbox.SetSelection(1)  # "Work"
    dlg._on_selection_changed(None)
    dlg._on_apply(None)
    assert len(calls) == 1
    assert calls[0].name == "Work"
    dlg.dialog.Destroy()
    frame.Destroy()


def test_add_and_remove_favorite_file(wx_app, tmp_path: Path) -> None:
    dlg, frame, _store = _dialog(wx_app, tmp_path)
    sample = tmp_path / "chapter1.md"
    sample.write_text("hi", encoding="utf-8")
    dlg._favorite_files.append(str(sample))
    dlg._refresh_favorites_list()
    assert dlg._favorites_list.GetCount() == 1
    dlg._favorites_list.SetSelection(0)
    dlg._on_remove_file(None)
    assert dlg._favorites_list.GetCount() == 0
    dlg.dialog.Destroy()
    frame.Destroy()


def test_no_personas_disables_action_buttons(wx_app, tmp_path: Path) -> None:
    store = WorkPersonaStore(tmp_path)  # empty
    frame = wx.Frame(None)
    dlg = WorkPersonaDialog(frame, store)
    assert not dlg._btn_delete.IsEnabled()
    assert not dlg._btn_apply.IsEnabled()
    assert not dlg._btn_shortcut.IsEnabled()
    dlg.dialog.Destroy()
    frame.Destroy()
