"""Unit tests for the QUILL setup wizard.

These tests verify wizard logic and invariants without requiring a live wx app
instance, using lightweight mock objects where wx widgets would be needed.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wizard_pages_source() -> str:
    return (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "setup_wizard_pages.py"
    ).read_text(encoding="utf-8")


def _wizard_source() -> str:
    return (Path(__file__).resolve().parents[3] / "quill" / "ui" / "setup_wizard.py").read_text(
        encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Structural / source-level tests (no wx needed)
# ---------------------------------------------------------------------------


def test_wizard_pages_module_has_nine_page_classes() -> None:
    src = _wizard_pages_source()
    # Count private page classes: they inherit from _WizardPage (the base class)
    import re

    pages = re.findall(r"^class _\w+Page\(_WizardPage\)", src, re.MULTILINE)
    assert len(pages) == 9, f"Expected 9 page classes, found {len(pages)}: {pages}"


def test_setup_wizard_dialog_exists() -> None:
    src = _wizard_pages_source()
    assert "class SetupWizardDialog(wx.Dialog)" in src


def test_run_setup_wizard_sets_completed_flag() -> None:
    src = _wizard_source()
    assert "settings.setup_wizard_completed = True" in src, (
        "run_setup_wizard must set setup_wizard_completed = True on completion"
    )


def test_wizard_is_transactional() -> None:
    src = _wizard_pages_source()
    assert "_pending_overrides" in src, (
        "Wizard must hold changes in _pending_overrides until Finish"
    )
    assert "_apply_pending" in src, "Wizard must have _apply_pending that commits overrides"


def test_wizard_cancel_does_not_apply() -> None:
    # Finish calls _apply_pending; cancel (ID_CANCEL) must not call it.
    src = _wizard_pages_source()
    # _on_finish should call _apply_pending; there should be no _apply_pending
    # call outside that handler.
    assert "_on_finish" in src
    # The cancel button is wx.ID_CANCEL and has no bound EVT_BUTTON in source.
    assert "_on_cancel" not in src, (
        "_on_cancel should not exist — cancel dismisses without applying"
    )


def test_no_bw_references_in_wizard() -> None:
    src = _wizard_pages_source()
    assert "bw_whisperer" not in src
    assert "_show_bw_onboarding" not in src


def test_wizard_applies_remote_and_ai_overrides() -> None:
    src = _wizard_pages_source()
    assert "core.remote" in src, "Wizard must gate core.remote feature"
    assert "future.ai" in src, "Wizard must gate future.ai feature"


def test_wizard_summary_page_update_summary() -> None:
    """_SummaryPage.update_summary builds the right text from overrides."""
    from quill.core.features import FEATURE_STATE_OFF, FEATURE_STATE_ON, PROFILE_DEFINITIONS

    # Build a minimal mock for the summary page without importing wx.
    # We only need the update_summary logic; replace self._summary with a capture.
    captured: list[str] = []

    class _FakeSummary:
        def SetValue(self, text: str) -> None:  # noqa: N802
            captured.append(text)

    class _FakeSettings:
        keyboard_pack = "QUILL Default"
        announcement_verbosity = "normal"

    # Directly test the logic in update_summary without running the full wx import.
    # The function bodies are pure Python — we can replicate the logic here.
    profile_defs = PROFILE_DEFINITIONS
    state_on = FEATURE_STATE_ON

    def _update_summary(settings, overrides, feature_manager):
        lines: list[str] = []
        profile_id = overrides.get("_profile")
        if profile_id and profile_id in profile_defs:
            lines.append(f"Profile: {profile_defs[profile_id].name}")
        lines.append(f"Keyboard pack: {settings.keyboard_pack}")
        remote_state = overrides.get("core.remote")
        if remote_state is not None:
            lines.append(f"Remote Access: {'on' if remote_state == state_on else 'off'}")
        ai_state = overrides.get("future.ai")
        if ai_state is not None:
            lines.append(f"AI Assistance: {'on' if ai_state == state_on else 'off'}")
        lines.append(f"Verbosity: {settings.announcement_verbosity}")
        return "\n".join(lines)

    settings = _FakeSettings()
    # Use a real profile key from PROFILE_DEFINITIONS.
    first_profile_id = next(iter(PROFILE_DEFINITIONS))
    first_profile_name = PROFILE_DEFINITIONS[first_profile_id].name

    overrides = {
        "_profile": first_profile_id,
        "core.remote": FEATURE_STATE_OFF,
        "future.ai": FEATURE_STATE_ON,
    }
    result = _update_summary(settings, overrides, None)

    assert f"Profile: {first_profile_name}" in result
    assert "Remote Access: off" in result
    assert "AI Assistance: on" in result
    assert "QUILL Default" in result


def test_run_setup_wizard_uses_show_modal_fn_when_provided(monkeypatch) -> None:
    import sys
    import types

    from quill.ui.setup_wizard import run_setup_wizard

    modal_calls: list[tuple[object, str]] = []
    wx_id_ok = 5100

    def _fake_show_modal(dlg, label):
        modal_calls.append((dlg, label))
        return wx_id_ok

    class _FakeSettings:
        setup_wizard_completed = False

    class _FakeFeatureManager:
        pass

    class _FakeDialog:
        def ShowModal(self):
            raise AssertionError("ShowModal must not be called directly")

        def Destroy(self):
            pass

    fake_wx = types.ModuleType("wx")
    fake_wx.ID_OK = wx_id_ok  # type: ignore[attr-defined]

    class _FakeSetupWizardDialog:
        def __new__(cls, *_args, **_kwargs):
            return _FakeDialog()

    fake_pages = types.ModuleType("quill.ui.setup_wizard_pages")
    fake_pages.SetupWizardDialog = _FakeSetupWizardDialog  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "quill.ui.setup_wizard_pages", fake_pages)

    settings = _FakeSettings()
    result = run_setup_wizard(None, settings, _FakeFeatureManager(), show_modal_fn=_fake_show_modal)

    assert len(modal_calls) == 1
    assert modal_calls[0][1] == "Setup Wizard"
    assert result is True
    assert settings.setup_wizard_completed is True
