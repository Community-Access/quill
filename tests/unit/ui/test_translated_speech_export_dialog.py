"""Tests for the single-document translated speech export dialog."""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui.translated_speech_export_dialog import (  # noqa: E402
    TranslatedSpeechExportDialog,
)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _make(wx_app):
    frame = wx.Frame(None)
    dlg = TranslatedSpeechExportDialog(frame, document_name="report.docx")
    return frame, dlg


def test_add_language_then_collect(wx_app):
    frame, dlg = _make(wx_app)
    try:
        # Pick Spanish (the language Choice is sorted by name).
        names = [n for n, _c in dlg._lang_pairs]
        dlg._lang.SetSelection(names.index("Spanish"))
        dlg._reload_voices()
        assert dlg._voice_opts  # eSpeak always offers a Spanish voice
        dlg._voice.SetSelection(0)
        dlg._on_add()
        assert len(dlg._targets) == 1
        code, engine, _voice, _label = dlg._targets[0]
        assert code == "es" and engine  # a real engine id was captured
        dlg._on_ok(wx.CommandEvent())
        assert dlg._result is not None
        assert dlg._result.targets and dlg._result.targets[0][0] == "es"
        assert dlg._result.output_format == "mp3"
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_ok_blocked_without_targets(wx_app):
    import quill.ui.translated_speech_export_dialog as mod

    frame, dlg = _make(wx_app)
    shown: list[str] = []
    try:
        mod_show = mod.show_message_box
        mod.show_message_box = lambda *a, **k: shown.append(a[0])  # type: ignore[assignment]
        dlg._on_ok(wx.CommandEvent())
        assert dlg._result is None  # nothing added -> not accepted
        assert shown and "language" in shown[0].lower()
    finally:
        mod.show_message_box = mod_show  # type: ignore[assignment]
        dlg.dialog.Destroy()
        frame.Destroy()


def test_duplicate_language_voice_not_added_twice(wx_app):
    frame, dlg = _make(wx_app)
    try:
        names = [n for n, _c in dlg._lang_pairs]
        dlg._lang.SetSelection(names.index("French"))
        dlg._reload_voices()
        dlg._voice.SetSelection(0)
        dlg._on_add()
        dlg._on_add()  # same language+voice again
        assert len(dlg._targets) == 1
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()
