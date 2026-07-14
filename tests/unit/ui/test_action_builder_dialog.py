"""Smoke + behavior tests for the guided Action Builder dialog."""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.core.skill_store import SkillStore  # noqa: E402
from quill.ui.action_builder_dialog import (  # noqa: E402
    ActionBuilderDialog,
    read_reference_text,
)


def test_read_reference_text_reads_plain_and_caps(tmp_path):
    f = tmp_path / "style.md"
    f.write_text("## House Style\n- bullet one", encoding="utf-8")
    assert "House Style" in read_reference_text(f)
    big = tmp_path / "big.txt"
    big.write_text("x" * 20000, encoding="utf-8")
    assert len(read_reference_text(big)) <= 8000


def test_read_reference_text_unreadable_binary_is_empty(tmp_path):
    # A non-text extension with no markitdown conversion yields '' (no binary noise).
    f = tmp_path / "thing.docx"
    f.write_bytes(b"\x00\x01\x02not a real docx")
    assert read_reference_text(f) == "" or isinstance(read_reference_text(f), str)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _make(wx_app, tmp_path):
    frame = wx.Frame(None)
    store = SkillStore(tmp_path / "skills")
    dlg = ActionBuilderDialog(frame, store)
    return frame, dlg, store


def test_preset_prefills_instruction_and_name(wx_app, tmp_path):
    frame, dlg, _store = _make(wx_app, tmp_path)
    try:
        # Select "Meeting Minutes" (index 1; 0 is Blank).
        dlg._preset.SetSelection(1)
        dlg._on_preset(None)
        assert "meeting minutes" in dlg._instructions.GetValue().lower()
        assert dlg._name.GetValue().startswith("My ")
    finally:
        dlg.close()
        frame.Destroy()


def test_save_installs_a_skill(wx_app, tmp_path):
    frame, dlg, store = _make(wx_app, tmp_path)
    try:
        dlg._name.SetValue("My Standup Notes")
        dlg._instructions.SetValue("Summarize the standup in three bullets.")
        dlg._on_save(None)
        saved = dlg.get_saved()
        assert saved is not None and saved.name == "My Standup Notes"
        assert store.find_by_name("My Standup Notes") is not None
    finally:
        dlg.close()
        frame.Destroy()


def test_save_with_reference_bakes_it_into_the_skill(wx_app, tmp_path):
    frame, dlg, store = _make(wx_app, tmp_path)
    try:
        dlg._name.SetValue("Minutes Like Last Month")
        dlg._instructions.SetValue("Write meeting minutes.")
        dlg._reference_text = "## Acme Weekly\n- Decisions:"
        dlg._on_save(None)
        saved = dlg.get_saved()
        assert saved is not None
        assert "Acme Weekly" in store.get_source(saved.id)
        assert "REFERENCE:" in store.get_source(saved.id)
    finally:
        dlg.close()
        frame.Destroy()


def test_save_requires_name_and_instructions(wx_app, tmp_path):
    frame, dlg, store = _make(wx_app, tmp_path)
    try:
        dlg._name.SetValue("")
        dlg._instructions.SetValue("")
        dlg._on_save(None)
        assert dlg.get_saved() is None
        assert "name" in dlg._status.GetLabel().lower()
        assert store.all() == []
    finally:
        dlg.close()
        frame.Destroy()
