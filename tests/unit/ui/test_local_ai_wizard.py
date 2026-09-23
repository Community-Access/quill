"""Smoke + journey tests for the guided local-AI setup dialog (issue #1558)."""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

import quill.core.ai.local_setup as ls  # noqa: E402
import quill.core.ai.onboarding as ob  # noqa: E402
import quill.ui.local_ai_wizard as law  # noqa: E402
from quill.ui.local_ai_wizard import LocalAISetupWizard  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture(autouse=True)
def _isolated_data_dir(quill_data_dir):
    # Finishing writes the assistant connection and onboarding state; keep every
    # test off the developer's real profile.
    return quill_data_dir


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    # Construction fires a background probe; give it deterministic, offline
    # answers so no test's outcome depends on whether this machine runs Ollama.
    monkeypatch.setattr(ls, "ollama_probe", lambda _h: (False, []))
    monkeypatch.setattr(ls, "ollama_executable", lambda: None)


def _wizard(wx_app, announcements=None):
    frame = wx.Frame(None)
    dlg = LocalAISetupWizard(
        frame,
        announce_cb=(announcements.append if announcements is not None else None),
    )
    dlg._busy = False  # settle the construction-time probe without a MainLoop
    return frame, dlg


def _settle(dlg, *, installed, reachable, models=()):
    """Deliver a probe result the way wx.CallAfter would."""
    dlg._busy = True
    dlg._on_probed(installed, reachable, tuple(models), False)


def test_prose_is_readonly_edit_and_no_stray_panel(wx_app):
    frame, dlg = _wizard(wx_app)
    try:
        for state in (
            {"installed": False, "reachable": False},
            {"installed": True, "reachable": False},
            {"installed": True, "reachable": True},
            {"installed": True, "reachable": True, "models": ("m1",)},
        ):
            _settle(dlg, **state)
            kids = dlg.dialog.GetChildren()
            assert not any(isinstance(c, wx.Panel) for c in kids), f"stray panel in {state}"
            ro_edits = [
                c
                for c in kids
                if isinstance(c, wx.TextCtrl) and (c.GetWindowStyleFlag() & wx.TE_READONLY)
            ]
            assert ro_edits, f"{state}: prose should be a read-only edit control"
    finally:
        dlg.close()
        frame.Destroy()


def test_each_stage_lights_exactly_the_right_buttons(wx_app):
    frame, dlg = _wizard(wx_app)
    try:
        _settle(dlg, installed=False, reachable=False)
        assert dlg._install_btn.IsEnabled()
        assert not hasattr(dlg, "_finish_btn") or not dlg._finish_btn

        _settle(dlg, installed=True, reachable=False)
        assert not dlg._install_btn.IsEnabled(), "never offer a reinstall to fix 'not running'"
        assert dlg._check_btn.IsEnabled()

        _settle(dlg, installed=True, reachable=True)
        assert hasattr(dlg, "_pull_btn"), "step two offers the model download"

        _settle(dlg, installed=True, reachable=True, models=("llama3.2:1b",))
        assert hasattr(dlg, "_finish_btn"), "step three offers the connection"
    finally:
        dlg.close()
        frame.Destroy()


def test_banner_announces_only_when_the_step_changes(wx_app):
    said: list[str] = []
    frame, dlg = _wizard(wx_app, announcements=said)
    try:
        _settle(dlg, installed=False, reachable=False)
        said.clear()
        _settle(dlg, installed=False, reachable=False)  # same step: quiet
        assert said == []
        _settle(dlg, installed=True, reachable=True)  # new step: spoken once
        assert any("Step 2" in line for line in said)
    finally:
        dlg.close()
        frame.Destroy()


def test_consent_gates_the_finish_button(wx_app):
    frame, dlg = _wizard(wx_app)
    try:
        _settle(dlg, installed=True, reachable=True, models=("llama3.2:1b",))
        assert not dlg._finish_btn.IsEnabled(), "no connection before consent"
        dlg._consent.SetValue(True)
        event = wx.CommandEvent(wx.EVT_CHECKBOX.typeId, dlg._consent.GetId())
        dlg._consent.ProcessEvent(event)
        assert dlg._finish_btn.IsEnabled()
    finally:
        dlg.close()
        frame.Destroy()


def test_finishing_applies_the_on_device_setup(wx_app, monkeypatch):
    applied = {}
    monkeypatch.setattr(ob, "verify_model", lambda p, m, host="": (True, ""))
    monkeypatch.setattr(ob, "apply_on_device_setup", lambda **kw: applied.update(kw))
    monkeypatch.setattr(ob, "grant_provider_consent", lambda p: applied.update(consent=p))
    monkeypatch.setattr(ob, "mark_onboarding_complete", lambda: applied.update(done=True))
    said: list[str] = []
    frame, dlg = _wizard(wx_app, announcements=said)
    try:
        _settle(dlg, installed=True, reachable=True, models=("llama3.2:1b",))
        dlg._consent.SetValue(True)
        dlg._on_finished("llama3.2:1b", True, "")
        assert applied["model"] == "llama3.2:1b"
        assert applied["consent"] == "ollama"
        assert applied["done"] is True
        assert any("on this computer" in line for line in said)
    finally:
        dlg.close()
        frame.Destroy()


def test_a_failed_connection_reports_and_stays_open(wx_app, monkeypatch):
    monkeypatch.setattr(ob, "apply_on_device_setup", lambda **kw: pytest.fail("must not apply"))
    frame, dlg = _wizard(wx_app)
    try:
        _settle(dlg, installed=True, reachable=True, models=("llama3.2:1b",))
        dlg._consent.SetValue(True)
        dlg._on_finished("llama3.2:1b", False, "server went away")
        assert "server went away" in dlg._status.GetLabel()
    finally:
        dlg.close()
        frame.Destroy()


def test_a_failed_installer_download_reports_and_reenables(wx_app):
    frame, dlg = _wizard(wx_app)
    try:
        _settle(dlg, installed=False, reachable=False)
        dlg._busy = True
        dlg._on_install_failed("Downloading components is disabled in Safe Mode.")
        assert "Safe Mode" in dlg._status.GetLabel()
        assert dlg._install_btn.IsEnabled()
        assert dlg._busy is False
    finally:
        dlg.close()
        frame.Destroy()


def test_safe_mode_refuses_before_any_window_opens(monkeypatch):
    said: list[str] = []

    class _Controller:
        frame = None
        _announce = staticmethod(said.append)

        def _show_modal_dialog(self, *_a, **_k):
            pytest.fail("Safe Mode must refuse before a dialog exists")

    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    law.run_local_ai_setup(_Controller())
    assert said and "Safe Mode" in said[0]
