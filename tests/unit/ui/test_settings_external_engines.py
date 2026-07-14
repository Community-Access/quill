"""Source-contract tests: external engines live in the Settings home (AI-24).

The external-engine consent toggle and command configuration are folded into
the registry-driven Settings dialog's AI page rather than a separate dialog.
Live wx dialogs are not instantiated in tests, so these assert the wiring as
source substrings.
"""

from __future__ import annotations

from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)


def test_no_standalone_external_engine_dialog() -> None:
    assert not (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "external_engine_settings.py"
    ).exists()
    assert "external_engine_settings" not in SOURCE


def test_settings_page_offers_master_consent() -> None:
    assert 'label="Allow external engines"' in SOURCE
    assert "external_engines_enabled()" in SOURCE


def test_settings_page_configures_engine_command() -> None:
    assert "External engine name" in SOURCE
    assert "External engine command" in SOURCE
    assert 'label="Enable this external engine"' in SOURCE


def test_settings_persists_external_engine_on_ok() -> None:
    assert "set_external_engines_enabled(ext_master_value)" in SOURCE
    assert "configure_engine(" in SOURCE
