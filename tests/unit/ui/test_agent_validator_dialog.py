"""Source-contract test for the Validate Agents dialog (agent linter in the UI)."""

from __future__ import annotations

from pathlib import Path


def _source() -> str:
    return Path("quill/ui/agent_validator_dialog.py").read_text(encoding="utf-8")


def test_uses_the_shared_linter_rules() -> None:
    body = _source()
    # The dialog must run the SAME standards linter the CI gate uses, not a fork.
    assert "from quill.tools.agent_lint import" in body
    assert "lint_dir(self._target)" in body
    assert "lint_path(self._target)" in body


def test_follows_modal_contract_and_destroys() -> None:
    body = _source()
    assert "apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)" in body
    assert "self._show_modal(self.dialog)" in body
    assert "self.dialog.Destroy()" in body
    assert "focus_primary_control(self.dialog)" in body


def test_results_and_path_are_named_for_screen_readers() -> None:
    body = _source()
    assert 'self.results.SetName("Validation findings")' in body
    assert 'self.path_ctrl.SetName("Path being validated")' in body


def test_defaults_to_bundled_and_offers_browse() -> None:
    body = _source()
    assert "bundled_agents_dir()" in body
    assert "wx.DirDialog(" in body
    assert "wx.FileDialog(" in body


def test_summary_announces_findings() -> None:
    body = _source()
    assert "self._announce(summary)" in body
    assert "error(s)" in body and "warning(s)" in body


def test_handler_is_wired_into_ai_library() -> None:
    # Validate Agents folded out of its own menu item into the AI Library Agents
    # tab (redesign §4.1): the Library's Validate opens this same dialog via the
    # host's open_agent_validator, and the handler still constructs it.
    library = Path("quill/ui/ai_library_dialog.py").read_text(encoding="utf-8")
    assert "on_validate_agents=controller.open_agent_validator" in library
    assert "self._on_validate_agents()" in library
    actions = Path("quill/ui/main_frame_ai_actions.py").read_text(encoding="utf-8")
    assert "def open_agent_validator(self)" in actions
    assert "AgentValidatorDialog(" in actions
