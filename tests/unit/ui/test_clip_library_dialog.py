"""Behavioral tests for ClipLibraryDialog (#895)."""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

from quill.core.clip_library import ClipLibrary
from quill.core.fragment import Fragment, FragmentFormat
from quill.ui.clip_library_dialog import ClipLibraryDialog


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _dialog(wx_app, tmp_path: Path, *, promote_cb=None):
    library = ClipLibrary(tmp_path)
    library.remember(Fragment(markup="first clip", title="First"))
    library.remember(Fragment(markup="second clip", title="Second"))
    frame = wx.Frame(None)
    dlg = ClipLibraryDialog(frame, library, promote_cb=promote_cb)
    return dlg, frame, library


def test_lists_entries_newest_first(wx_app, tmp_path: Path) -> None:
    dlg, frame, _lib = _dialog(wx_app, tmp_path)
    assert dlg._listbox.GetCount() == 2
    assert "Second" in dlg._listbox.GetString(0)
    dlg.dialog.Destroy()
    frame.Destroy()


def test_search_filters_the_list(wx_app, tmp_path: Path) -> None:
    dlg, frame, _lib = _dialog(wx_app, tmp_path)
    dlg._search.SetValue("first")
    dlg._on_search(None)
    assert dlg._listbox.GetCount() == 1
    assert "First" in dlg._listbox.GetString(0)
    dlg.dialog.Destroy()
    frame.Destroy()


def test_favorite_toggle_updates_label_and_tag(wx_app, tmp_path: Path) -> None:
    dlg, frame, lib = _dialog(wx_app, tmp_path)
    dlg._listbox.SetSelection(0)
    dlg._on_selection_changed(None)
    assert dlg._btn_favorite.GetLabel() == "&Favorite"
    dlg._on_favorite(None)
    assert lib.entry(dlg._indices[0]).favorite is True
    assert "[favorite]" in dlg._listbox.GetString(0)
    dlg.dialog.Destroy()
    frame.Destroy()


def test_remove_deletes_the_selected_entry(wx_app, tmp_path: Path) -> None:
    dlg, frame, lib = _dialog(wx_app, tmp_path)
    dlg._listbox.SetSelection(0)
    dlg._on_selection_changed(None)
    dlg._on_remove(None)
    assert len(lib) == 1
    dlg.dialog.Destroy()
    frame.Destroy()


def test_promote_calls_the_supplied_callback_with_the_real_index(wx_app, tmp_path: Path) -> None:
    calls: list[int] = []
    dlg, frame, _lib = _dialog(wx_app, tmp_path, promote_cb=calls.append)
    dlg._listbox.SetSelection(1)
    dlg._on_selection_changed(None)
    expected_index = dlg._indices[1]
    dlg._on_promote(None)
    assert calls == [expected_index]
    dlg.dialog.Destroy()
    frame.Destroy()


def test_copy_uses_the_configured_content_format(wx_app, tmp_path: Path) -> None:
    library = ClipLibrary(tmp_path)
    library.remember(Fragment(markup="**bold** clip", title="Formatted"))
    frame = wx.Frame(None)
    dlg = ClipLibraryDialog(frame, library, content_format=FragmentFormat.MARKDOWN)
    dlg._listbox.SetSelection(0)
    dlg._on_selection_changed(None)
    dlg._on_copy(None)
    assert wx.TheClipboard.Open()
    data = wx.TextDataObject()
    wx.TheClipboard.GetData(data)
    wx.TheClipboard.Close()
    assert data.GetText() == "**bold** clip"
    dlg.dialog.Destroy()
    frame.Destroy()


def test_copy_defaults_to_plain_text_format(wx_app, tmp_path: Path) -> None:
    library = ClipLibrary(tmp_path)
    library.remember(Fragment(markup="**bold** clip", title="Formatted"))
    frame = wx.Frame(None)
    dlg = ClipLibraryDialog(frame, library)
    dlg._listbox.SetSelection(0)
    dlg._on_selection_changed(None)
    dlg._on_copy(None)
    assert wx.TheClipboard.Open()
    data = wx.TextDataObject()
    wx.TheClipboard.GetData(data)
    wx.TheClipboard.Close()
    assert data.GetText() == "bold clip"
    dlg.dialog.Destroy()
    frame.Destroy()


def test_no_selection_disables_action_buttons(wx_app, tmp_path: Path) -> None:
    library = ClipLibrary(tmp_path)  # empty
    frame = wx.Frame(None)
    dlg = ClipLibraryDialog(frame, library)
    assert not dlg._btn_copy.IsEnabled()
    assert not dlg._btn_favorite.IsEnabled()
    assert not dlg._btn_promote.IsEnabled()
    assert not dlg._btn_remove.IsEnabled()
    dlg.dialog.Destroy()
    frame.Destroy()
