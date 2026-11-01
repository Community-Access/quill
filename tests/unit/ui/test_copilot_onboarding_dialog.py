"""Source-contract tests for the Copilot onboarding dialog (Phase 6 UI, AI-19).

wxPython cannot be imported headless in CI, so these read the UI source as text
and pin the accessibility + flow wiring: the modal contract, the two setup steps
(install then device sign-in), the three action buttons, and the live status area
that carries the speakable device code.
"""

from __future__ import annotations

from pathlib import Path


def _source() -> str:
    return Path("quill/ui/copilot_onboarding_dialog.py").read_text(encoding="utf-8")


def test_follows_modal_contract_and_destroys() -> None:
    body = _source()
    assert "apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)" in body
    # The label is required -- omitting it was the #1442 crash.
    assert 'self._show_modal(self.dialog, "Set Up GitHub Copilot")' in body
    assert "self.dialog.Destroy()" in body
    assert "focus_primary_control(self.dialog)" in body


def test_status_area_is_named_for_screen_readers() -> None:
    body = _source()
    assert 'self.status.SetName("Setup status")' in body


def test_two_steps_install_then_device_sign_in() -> None:
    body = _source()
    # Step 1 installs the pack on demand; step 2 runs the device flow.
    assert "install_pack(_PACK_ID" in body
    assert "request_device_code(config, poster=post_form)" in body
    assert "run_device_login(" in body
    # The speakable device code is surfaced as live status.
    assert "announce_device_code(grant)" in body
    assert "describe_login_result(result)" in body


def test_persists_token_per_app_and_never_exports_it() -> None:
    body = _source()
    # Stored under this app's own Copilot entry; the pack hands it to the SDK
    # at session start, so nothing is ever exported to the environment.
    assert "copilot_auth.persist_token(token, self._agent_name)" in body
    assert "apply_token_to_environment" not in body
    assert "os.environ" not in body


def test_has_three_action_buttons_and_close() -> None:
    body = _source()
    assert "Install Copilot SDK" in body
    assert "Sign in to GitHub" in body
    assert "Open Sign-in Page in &Browser" in body
    assert "wx.ID_CANCEL, label=" in body


def test_unconfigured_says_sign_in_is_not_available_yet() -> None:
    body = _source()
    assert "copilot_auth.is_configured(self._agent_name)" in body
    assert "copilot_auth.sign_in_unavailable_message(self._agent_name)" in body


def test_setup_is_reachable_from_the_hub_engines_tab() -> None:
    # The standalone "Set Up GitHub Copilot" menu item folded into the AI Hub
    # Engines tab (redesign §6.5): picking Copilot there and choosing Set Up opens
    # this onboarding dialog. The status-bar engine cell also opens it via
    # open_copilot_onboarding(), which remains wired in the menu module.
    engines = Path("quill/ui/ai_hub_engines_panel.py").read_text(encoding="utf-8")
    assert "CopilotOnboardingDialog(" in engines
    assert 'harness_id == "copilot"' in engines
    menu = Path("quill/ui/main_frame_menu.py").read_text(encoding="utf-8") + Path(
        "quill/ui/main_frame_menu_bindings.py"
    ).read_text(encoding="utf-8")
    assert "open_copilot_onboarding()" in menu
