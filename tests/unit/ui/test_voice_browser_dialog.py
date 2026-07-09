"""Voice Browser dialog: Preview button toggles to Stop while a preview is
generating/playing (Task 5 of the voice-preview-generation-cue plan)."""

from __future__ import annotations

import pytest
import wx


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _make_dialog(frame, *, preview_fn, preview_stop_fn=None):
    from quill.ui.voice_browser_dialog import VoiceBrowserDialog

    dlg = VoiceBrowserDialog(
        frame,
        engine_options=[("SAPI 5", "sapi5")],
        current_engine="sapi5",
        piper_model_dir=__import__("pathlib").Path("."),
        settings=type(
            "S", (), {"read_aloud_rate": 200, "read_aloud_volume": 100, "read_aloud_pitch": 0}
        )(),
        preview_fn=preview_fn,
        preview_stop_fn=preview_stop_fn,
    )
    dlg._all_voices = [type("V", (), {"id": "v1", "name": "Voice 1", "installed": True})()]
    dlg._displayed_voices = dlg._all_voices
    dlg._voice_lb.Append("Voice 1")
    dlg._voice_lb.SetSelection(0)
    return dlg


def test_preview_button_toggles_to_stop_while_active(wx_app) -> None:
    import wx

    states: list[str] = []

    def fake_preview(engine, voice_id, *, live=False, on_state_change=None):
        states.append("called")
        if on_state_change is not None:
            on_state_change("playing")

    frame = wx.Frame(None)
    dlg = _make_dialog(frame, preview_fn=fake_preview)

    dlg._do_preview()
    wx.YieldIfNeeded()

    assert dlg._preview_btn.GetLabel() == "&Stop Preview"
    frame.Destroy()


def test_second_click_while_active_stops_preview_and_reverts_label(wx_app) -> None:
    import wx

    stop_calls: list[str] = []

    def fake_preview(engine, voice_id, *, live=False, on_state_change=None):
        if on_state_change is not None:
            on_state_change("playing")

    def fake_preview_stop() -> None:
        stop_calls.append("stopped")

    frame = wx.Frame(None)
    dlg = _make_dialog(frame, preview_fn=fake_preview, preview_stop_fn=fake_preview_stop)

    dlg._do_preview()
    wx.YieldIfNeeded()
    assert dlg._preview_btn.GetLabel() == "&Stop Preview"

    # Second click while active: stops the preview instead of starting another.
    dlg._do_preview()
    wx.YieldIfNeeded()

    assert stop_calls == ["stopped"]
    assert dlg._preview_btn.GetLabel() == "&Preview Selected Voice"
    frame.Destroy()


def test_on_state_change_idle_reverts_label(wx_app) -> None:
    import wx

    def fake_preview(engine, voice_id, *, live=False, on_state_change=None):
        if on_state_change is not None:
            on_state_change("playing")

    frame = wx.Frame(None)
    dlg = _make_dialog(frame, preview_fn=fake_preview)

    dlg._do_preview()
    wx.YieldIfNeeded()
    assert dlg._preview_btn.GetLabel() == "&Stop Preview"

    # Simulates the error-path fix in MainFrame._preview_voice: a preview that
    # fails still reports "idle" so the button never sticks on "&Stop Preview".
    dlg._on_preview_state("idle")

    assert dlg._preview_btn.GetLabel() == "&Preview Selected Voice"
    frame.Destroy()
