"""Tests for the Pronunciation manager dialog logic (no audio, no real engine)."""

from __future__ import annotations

from pathlib import Path

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.core.speech.pronunciation import (  # noqa: E402
    PronunciationDictionary,
    PronunciationEntry,
)
from quill.ui.pronunciation_dictionary_dialog import (  # noqa: E402
    PronunciationDictionaryDialog,
    PronunciationEntryDialog,
    _slugify,
)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_slugify():
    assert _slugify("Client Names!") == "client_names"
    assert _slugify("  A B  ") == "a_b"


def test_entry_dialog_collects_fields(wx_app):
    frame = wx.Frame(None)
    try:
        dlg = PronunciationEntryDialog(frame, PronunciationEntry(term="GIF", replacement="jiff"))
        dlg._term.SetValue("SQL")
        dlg._spoken.SetValue("sequel")
        # simulate OK
        evt = wx.CommandEvent()
        dlg._on_ok(evt)
        assert dlg._result is not None
        assert dlg._result.term == "SQL"
        assert dlg._result.replacement == "sequel"
        dlg.dialog.Destroy()
    finally:
        frame.Destroy()


def test_manager_enabled_ids_track_toggle(wx_app, tmp_path: Path):
    frame = wx.Frame(None)
    try:
        dlg = PronunciationDictionaryDialog(frame, project_dir=None, enabled_ids=set())
        dlg._dicts = [
            PronunciationDictionary(id="a", name="A", enabled=True),
            PronunciationDictionary(id="b", name="B", enabled=False),
        ]
        dlg._refresh_dict_list()
        assert dlg.enabled_ids() == ["a"]
        # toggle B on via the checkbox path
        dlg._dict_list.SetSelection(1)
        dlg._on_select_dict()
        dlg._enabled.SetValue(True)
        dlg._on_toggle_enabled(None)
        assert set(dlg.enabled_ids()) == {"a", "b"}
        dlg.dialog.Destroy()
    finally:
        frame.Destroy()


def test_manager_add_and_remove_entry(wx_app):
    frame = wx.Frame(None)
    try:
        dlg = PronunciationDictionaryDialog(frame, project_dir=None, enabled_ids=set())
        dlg._dicts = [PronunciationDictionary(id="a", name="A")]
        dlg._refresh_dict_list()
        dlg._dict_list.SetSelection(0)
        dlg._on_select_dict()
        d = dlg._selected_dict()
        d.entries.append(PronunciationEntry(term="QUILL", replacement="kwill"))
        dlg._on_select_dict()
        assert dlg._entry_list.GetCount() == 1
        dlg._entry_list.SetSelection(0)
        dlg._on_remove_entry(None)
        assert dlg._entry_list.GetCount() == 0
        dlg.dialog.Destroy()
    finally:
        frame.Destroy()
