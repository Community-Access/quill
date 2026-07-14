"""Voice Browser dialog: Preview button toggles to Stop while a preview is
generating/playing (Task 5 of the voice-preview-generation-cue plan).

IMPORTANT: no ``wx.YieldIfNeeded()`` (or ``wx.Yield``/``SafeYield``) here.
These tests were the only CI-reachable call sites in the whole suite that
pumped the native event loop (test_voice_preview_generation.py's are skipped
in CI for the same class of problem: YieldIfNeeded blocks in a native call on
the headless Windows runner). On the macOS release runner, that first native
pump -- arriving at 99% of the suite, after dozens of modules have created
and destroyed their own wx.App and thousands of native widgets -- dispatched
stale deferred Cocoa events and segfaulted the whole pytest process
(reproduced identically on the 0.9.0 Beta 2 and Beta 3 release runs; adding
MORE yields moved the crash earlier, confirming the pump itself was the
trigger). None of the yields were needed for correctness anyway: the fake
``preview_fn`` used below invokes ``on_state_change`` synchronously, so the
button label is already updated when ``_do_preview()`` returns. If a future
test here genuinely needs to flush ``wx.CallAfter``, use
``wx_app.ProcessPendingEvents()`` (wx-level queue only, never the native
loop) like test_ai_progress_dialog_close.py does.
"""

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
    # __init__ -> _build_ui() -> _refresh_voices() already ran _on_voice_selected()
    # once, against whatever the REAL list_voices() found on this machine at
    # construction time (real installed SAPI 5 voices on Windows -- possibly
    # none at all on macOS/CI, where SAPI 5 doesn't exist). That call may have
    # disabled _preview_btn (no selection -> Enable(False)) before the fake
    # single-voice list above was ever injected, and _do_preview() never
    # touches Enable() itself -- only _on_preview_state() does, which only
    # runs once a preview has actually started. Re-run it now so the button's
    # enabled state reflects the test's injected voice, not the real
    # machine's environment-dependent (and possibly empty) voice list.
    dlg._on_voice_selected()
    return dlg


def test_preview_button_toggles_to_stop_while_active(wx_app) -> None:
    states: list[str] = []

    def fake_preview(engine, voice_id, *, live=False, on_state_change=None):
        states.append("called")
        if on_state_change is not None:
            on_state_change("playing")

    frame = wx.Frame(None)
    dlg = _make_dialog(frame, preview_fn=fake_preview)

    dlg._do_preview()

    assert dlg._preview_btn.GetLabel() == "&Stop Preview"
    frame.Destroy()


def test_second_click_while_active_stops_preview_and_reverts_label(wx_app) -> None:
    stop_calls: list[str] = []

    def fake_preview(engine, voice_id, *, live=False, on_state_change=None):
        if on_state_change is not None:
            on_state_change("playing")

    def fake_preview_stop() -> None:
        stop_calls.append("stopped")

    frame = wx.Frame(None)
    dlg = _make_dialog(frame, preview_fn=fake_preview, preview_stop_fn=fake_preview_stop)

    dlg._do_preview()
    assert dlg._preview_btn.GetLabel() == "&Stop Preview"

    # Second click while active: stops the preview instead of starting another.
    dlg._do_preview()

    assert stop_calls == ["stopped"]
    assert dlg._preview_btn.GetLabel() == "&Preview Selected Voice"
    frame.Destroy()


def test_on_state_change_idle_reverts_label(wx_app) -> None:
    def fake_preview(engine, voice_id, *, live=False, on_state_change=None):
        if on_state_change is not None:
            on_state_change("playing")

    frame = wx.Frame(None)
    dlg = _make_dialog(frame, preview_fn=fake_preview)

    dlg._do_preview()
    assert dlg._preview_btn.GetLabel() == "&Stop Preview"

    # Simulates the error-path fix in MainFrame._preview_voice: a preview that
    # fails still reports "idle" so the button never sticks on "&Stop Preview".
    dlg._on_preview_state("idle")

    assert dlg._preview_btn.GetLabel() == "&Preview Selected Voice"
    frame.Destroy()


def test_preview_button_stays_enabled_after_selecting_a_not_ready_voice(wx_app) -> None:
    """Regression (voice-preview-feedback final review): starting a preview on
    a ready voice, then navigating the list to a not-yet-downloaded voice with
    no bundled sample, must not disable the button out from under a running
    preview -- the user needs Stop reachable no matter what is selected."""

    def fake_preview(engine, voice_id, *, live=False, on_state_change=None):
        if on_state_change is not None:
            on_state_change("playing")

    stop_calls: list[str] = []

    def fake_preview_stop() -> None:
        stop_calls.append("stopped")

    frame = wx.Frame(None)
    dlg = _make_dialog(frame, preview_fn=fake_preview, preview_stop_fn=fake_preview_stop)
    # A second voice that is neither downloaded nor has a bundled sample clip,
    # so _on_voice_selected would ordinarily disable the button for it.
    not_ready_voice = type("V", (), {"id": "v2", "name": "Voice 2", "installed": False})()
    dlg._all_voices.append(not_ready_voice)
    dlg._displayed_voices = dlg._all_voices
    dlg._voice_lb.Append("Voice 2")

    dlg._voice_lb.SetSelection(0)
    dlg._do_preview()
    assert dlg._preview_btn.GetLabel() == "&Stop Preview"
    assert dlg._preview_btn.IsEnabled()

    # Navigate to the not-ready voice while the preview is still running.
    dlg._voice_lb.SetSelection(1)
    dlg._on_voice_selected()

    assert dlg._preview_btn.GetLabel() == "&Stop Preview"
    assert dlg._preview_btn.IsEnabled(), "Stop must stay reachable while a preview is active"

    # And clicking it still works to stop the preview from the not-ready row.
    dlg._do_preview()
    assert stop_calls == ["stopped"]
    assert dlg._preview_btn.GetLabel() == "&Preview Selected Voice"
    frame.Destroy()
