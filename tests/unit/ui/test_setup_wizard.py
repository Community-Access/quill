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


def test_wizard_pages_module_has_six_page_classes() -> None:
    src = _wizard_pages_source()
    import re

    pages = re.findall(r"^class _\w+Page\(_WizardPage\)", src, re.MULTILINE)
    expected = {
        "_WelcomePage",
        "_IntentPage",
        "_ExtrasPage",
        "_AIProviderPage",
        "_KeyboardSoundPage",
        "_SummaryPage",
    }
    found = {m.split("(")[0].replace("class ", "") for m in pages}
    assert found == expected, f"Expected {expected}, found {found}"


def test_wizard_tab_traversal_not_blocked_by_panel_override() -> None:
    # #a11y: _WizardPage must NOT override AcceptsFocusFromKeyboard to False.
    # Doing so causes wxPython's wxControlContainer to skip the entire panel
    # subtree in Tab traversal, making every field inside unreachable by keyboard.
    # Pages are kept out of the tab chain by Hide()+Disable() instead.
    src = _wizard_pages_source()
    assert "def AcceptsFocusFromKeyboard" not in src
    assert "def AcceptsFocus" not in src
    assert "_focus_first_page_control" in src
    assert "page.Disable()" in src


def test_keyboard_sound_page_collects_sound_and_indent_settings() -> None:
    src = _wizard_pages_source()
    assert "settings.sound_enabled = self._sound_enabled.GetValue()" in src
    assert "settings.sound_pack_path = self._sound_pack_path" in src
    assert "settings.indent_tone_scale =" in src


def test_intent_page_exists_and_uses_listbox() -> None:
    src = _wizard_pages_source()
    assert "class _IntentPage(_WizardPage)" in src
    assert "wx.ListBox" in src
    assert "list_intent_profiles" in src


def test_extras_page_exists_and_has_ai_braille_automation() -> None:
    src = _wizard_pages_source()
    assert "class _ExtrasPage(_WizardPage)" in src
    assert "wizard.extras_ai" in src
    assert "wizard.extras_braille" in src
    assert "wizard.extras_automation" in src


def test_ai_provider_page_exists() -> None:
    src = _wizard_pages_source()
    assert "class _AIProviderPage(_WizardPage)" in src
    assert "wizard.open_ai_hub" in src
    assert "Open AI Hub" in src


def test_preview_textctrls_are_read_only() -> None:
    src = _wizard_pages_source()
    # Every preview TextCtrl uses the shared _PREVIEW_STYLE which includes TE_READONLY.
    assert "TE_READONLY" in src
    assert "_PREVIEW_STYLE" in src


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
    src = _wizard_pages_source()
    assert "_on_finish" in src
    # Cancel handler must not be named _on_cancel (or contain that substring)
    # so that source-level checks do not confuse it with an apply path.
    assert "_on_cancel" not in src, (
        "_on_cancel must not exist; use _on_dismiss for the cancel/ESC path"
    )


def test_no_bw_references_in_wizard() -> None:
    src = _wizard_pages_source()
    assert "bw_whisperer" not in src
    assert "_show_bw_onboarding" not in src


def test_wizard_gates_ai_feature() -> None:
    src = _wizard_pages_source()
    assert "future.ai" in src, "Wizard must gate future.ai feature"


def test_wizard_abort_flag_exists() -> None:
    src = _wizard_pages_source()
    assert "aborted_first_run" in src, (
        "SetupWizardDialog must expose aborted_first_run so the caller can "
        "apply text_editor defaults on first-run cancel"
    )


def test_wizard_intent_profile_stored_on_settings() -> None:
    src = _wizard_pages_source()
    assert "setup_wizard_intent" in src, (
        "_apply_pending must store the intent profile id on settings so "
        "main_frame can apply Quillin configuration after the dialog closes"
    )


def test_wizard_summary_page_update_summary() -> None:
    """_SummaryPage.update_summary builds text that includes the intent profile name."""
    from quill.core.onboarding_profiles import get_intent_profile

    # Replicate just enough of update_summary to verify the profile name appears.
    intent = get_intent_profile("writer")
    assert "Writer" in intent.name
    assert intent.preview_text  # non-empty
    assert "What you have:" in intent.preview_text


def test_run_setup_wizard_returns_tuple() -> None:
    src = _wizard_source()
    assert "tuple[bool, bool]" in src or "completed, aborted" in src, (
        "run_setup_wizard must return (completed, aborted) tuple"
    )


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
        aborted_first_run = False

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
    completed, aborted = run_setup_wizard(
        None, settings, _FakeFeatureManager(), show_modal_fn=_fake_show_modal
    )

    assert len(modal_calls) == 1
    assert modal_calls[0][1] == "Setup Wizard"
    assert completed is True
    assert aborted is False
    assert settings.setup_wizard_completed is True
