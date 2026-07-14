"""Source-contract test for the AI Hub Engines (harnesses) tab (slice 3)."""

from __future__ import annotations

from pathlib import Path


def _hub_source() -> str:
    return Path("quill/ui/ai_hub_dialog.py").read_text(encoding="utf-8")


def _panel_source() -> str:
    return Path("quill/ui/ai_hub_engines_panel.py").read_text(encoding="utf-8")


def test_engines_tab_is_registered_in_hub() -> None:
    body = _hub_source()
    assert "_build_harnesses_tab()" in body
    assert 'str(_("Engines"))' in body
    # The tab logic is extracted to keep the Hub within its size budget.
    assert "from quill.ui.ai_hub_engines_panel import EnginesPanel" in body


def test_engine_list_is_named_and_populated_from_targets() -> None:
    body = _panel_source()
    assert 'self.engine_list.SetName("AI engines")' in body
    assert "list_targets(self._build_registry())" in body
    # The three states the user needs to distinguish.
    assert '_("Active")' in body
    assert '_("Available")' in body
    assert '_("Not installed")' in body


def test_set_active_and_setup_are_wired() -> None:
    body = _panel_source()
    assert "set_active(self._build_registry(), target.harness_id)" in body
    assert "CopilotOnboardingDialog(" in body
    assert "install_pack(pack_id)" in body


def test_install_runs_off_ui_thread() -> None:
    body = _panel_source()
    # The pip install must not block the UI thread; result posts via CallAfter.
    assert "threading.Thread(target=worker, daemon=True).start()" in body
    assert "wx.CallAfter(self._after_install" in body
