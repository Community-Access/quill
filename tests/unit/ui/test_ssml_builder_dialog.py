"""Tests for the SSML Builder dialog (validation + quick-insert + result)."""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui.ssml_builder_dialog import SsmlBuilderDialog  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _make(wx_app, **kw):
    frame = wx.Frame(None)
    dlg = SsmlBuilderDialog(frame, term=kw.pop("term", "QUILL"), **kw)
    return frame, dlg


def test_quick_insert_and_validation(wx_app):
    frame, dlg = _make(wx_app)
    try:
        # "Spell out" inserts a well-formed say-as fragment
        dlg._append(dlg._fragment.GetValue())  # no-op append of empty
        from quill.core.speech.pronunciation import ssml_say_as

        dlg._fragment.SetValue(ssml_say_as("QUILL", "characters"))
        assert dlg._validate() is True
        dlg._fragment.SetValue("<broken")
        assert dlg._validate() is False
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_ok_returns_fragment_and_fallback(wx_app):
    frame, dlg = _make(wx_app, term="SQL", fallback="sequel")
    try:
        dlg._fragment.SetValue('<sub alias="sequel">SQL</sub>')
        evt = wx.CommandEvent()
        dlg._on_ok(evt)
        assert dlg._result is not None
        fragment, fallback = dlg._result
        assert fragment == '<sub alias="sequel">SQL</sub>'
        assert fallback == "sequel"
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_ok_blocked_on_invalid_ssml(wx_app, monkeypatch):
    # Invalid SSML pops a modal error; stub it so the test never blocks on a real
    # wx.MessageBox (which would hang headless CI) while still asserting it fired.
    import quill.ui.ssml_builder_dialog as ssml_mod

    shown: list[str] = []
    monkeypatch.setattr(ssml_mod, "show_message_box", lambda *a, **k: shown.append(a[0]))
    frame, dlg = _make(wx_app)
    try:
        dlg._fragment.SetValue("<nope")
        dlg._on_ok(wx.CommandEvent())
        assert dlg._result is None  # invalid -> not accepted
        assert shown and "SSML" in shown[0]  # the error was surfaced to the user
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()
