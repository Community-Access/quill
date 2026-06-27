"""Tests for the audiobook chapter editor (rename / reorder / merge -> plan)."""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui.audiobook_chapter_editor_dialog import ChapterEditorDialog  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _make(wx_app):
    frame = wx.Frame(None)
    rows = [
        ("/audio/01 intro.mp3", "intro"),
        ("/audio/02 body.mp3", "body"),
        ("/audio/03 outro.mp3", "outro"),
    ]
    dlg = ChapterEditorDialog(frame, rows=rows, announce=None)
    return frame, dlg


def test_initial_plan_is_one_chapter_per_file(wx_app):
    frame, dlg = _make(wx_app)
    try:
        dlg._on_ok(_FakeEvt())
        plan = dlg._result
        assert plan == [
            ("intro", ["/audio/01 intro.mp3"]),
            ("body", ["/audio/02 body.mp3"]),
            ("outro", ["/audio/03 outro.mp3"]),
        ]
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_rename_reorder_merge_then_collect(wx_app):
    frame, dlg = _make(wx_app)
    try:
        # Rename chapter 1.
        dlg._chapter_list.SetSelection(0)
        dlg._on_chapter_selected()
        dlg._title_edit.SetValue("Welcome")
        dlg._on_rename()
        # Move chapter 3 (outro) up to position 2.
        dlg._chapter_list.SetSelection(2)
        dlg._on_move(-1)
        # Now order: Welcome, outro, body. Merge body into outro.
        dlg._chapter_list.SetSelection(2)
        dlg._on_merge_up()
        dlg._on_ok(_FakeEvt())
        plan = dlg._result
        assert plan == [
            ("Welcome", ["/audio/01 intro.mp3"]),
            ("outro", ["/audio/03 outro.mp3", "/audio/02 body.mp3"]),
        ]
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_empty_title_rename_is_rejected(wx_app, monkeypatch):
    # Suppress the modal error box so the headless test does not block.
    import quill.ui.audiobook_chapter_editor_dialog as mod

    monkeypatch.setattr(mod, "show_message_box", lambda *a, **k: None)
    frame, dlg = _make(wx_app)
    try:
        dlg._chapter_list.SetSelection(1)
        dlg._on_chapter_selected()
        dlg._title_edit.SetValue("   ")
        # _on_rename shows an error and leaves the title unchanged (no crash).
        dlg._on_rename()
        assert dlg._chapters[1].title == "body"
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


class _FakeEvt:
    def Skip(self) -> None:  # noqa: N802 - wx event API
        pass
