"""The Experimental-tab gating contract (master switch + per-feature opt-ins).

Settings-level checks run for real; the wx wiring is pinned as source
contracts (headless CI cannot import wx), the same approach as the GLOW
update-wiring tests. What must hold:

* The master switch (``experimental_acknowledged``) governs every experimental
  option; each gated feature also has its own checkbox, all default OFF.
* GLOW is enabled only when the master switch AND its checkbox are on; the
  read-only publishing tools light up from their checkbox the same way.
* On the Experimental tab, an unchecked master disables (and removes from the
  tab order) every other control.

The editor-surface options that once lived here retired in 0.9.0-beta3 when
QuillRichEdit became the one editor surface and the braille fix moved to the
Braille tab (see test_braille_editor_fix.py); this file pins that they stay
retired.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.settings import Settings, load_settings, save_settings
from quill.core.settings_specs import SETTING_SPECS


def _experimental_keys() -> list[str]:
    return [spec.key for spec in SETTING_SPECS if spec.group == "experimental"]


def test_every_experimental_gate_defaults_off() -> None:
    settings = Settings()
    assert settings.experimental_acknowledged is False
    assert settings.glow_experimental_enabled is False
    assert settings.publishing_experimental_enabled is False
    assert settings.edge_read_aloud_enabled is False


def test_experimental_gates_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    settings = load_settings()
    settings.experimental_acknowledged = True
    settings.glow_experimental_enabled = True
    settings.publishing_experimental_enabled = True
    save_settings(settings)
    loaded = load_settings()
    assert loaded.experimental_acknowledged is True
    assert loaded.glow_experimental_enabled is True
    assert loaded.publishing_experimental_enabled is True


def test_experimental_tab_specs_present_and_ordered() -> None:
    keys = _experimental_keys()
    # The master switch leads the tab.
    assert keys[0] == "experimental_acknowledged"
    for expected in ("glow_experimental_enabled", "publishing_experimental_enabled"):
        assert expected in keys


def test_editor_surface_settings_stay_retired() -> None:
    """The surface experiment is decided; no surface knob may return.

    QuillRichEdit is the one editor surface (0.9.0-beta3); the braille fix
    lives on the Braille tab. A resurrected surface setting would silently
    re-fragment the editor, so its absence is pinned.
    """
    keys = {spec.key for spec in SETTING_SPECS}
    retired = {
        "editor_control_kind",
        "experimental_editor_surface",
        "experimental_editor_surfaces_enabled",
        "experimental_richedit_emulate_sysedit",
        "editor_hide_border",
    }
    assert not (retired & keys)
    fields = set(Settings.__dataclass_fields__)
    assert not (retired & fields)


def test_master_label_covers_all_experimental_features() -> None:
    master = next(spec for spec in SETTING_SPECS if spec.key == "experimental_acknowledged")
    assert "experimental features" in master.label.lower()
    assert "master" in master.label.lower() or "master" in master.description.lower()


def _main_frame_source() -> str:
    return Path("quill/ui/main_frame.py").read_text(encoding="utf-8")


def test_feature_enabled_applies_the_experimental_gates() -> None:
    source = _main_frame_source()
    start = source.index("def _feature_enabled(self")
    end = source.index("\n    def ", start + 1)
    end = source.index("\n    def ", end + 1)  # include _experimental_gate_on
    body = source[start:end]
    assert '"core.glow"' in body
    assert '"glow_experimental_enabled"' in body
    assert '"future.publishing_read"' in body
    assert '"publishing_experimental_enabled"' in body
    assert '"experimental_acknowledged"' in body


def test_experimental_tab_wires_live_enable_disable_gating() -> None:
    source = _main_frame_source()
    start = source.index("def _wire_experimental_gates(self")
    end = source.index("\n    def ", start + 1)
    body = source[start:end]
    # Master governs every other control on the tab.
    for key in (
        '"experimental_acknowledged"',
        '"glow_experimental_enabled"',
        '"publishing_experimental_enabled"',
        '"edge_read_aloud_enabled"',
    ):
        assert key in body
    assert "Enable(master_on)" in body
    assert "EVT_CHECKBOX" in body


def test_every_glow_command_is_gated() -> None:
    source = _main_frame_source()
    for handler in (
        "def glow_audit_document",
        "def glow_audit_selection",
        "def glow_fix_document",
        "def glow_fix_selection",
    ):
        start = source.index(handler)
        body = source[start : start + 400]
        assert "_ensure_glow_enabled" in body, handler
    updates = source.index("def check_for_glow_updates")
    assert "_ensure_glow_enabled" in source[updates : updates + 1200]
    mixin = Path("quill/ui/main_frame_glow.py").read_text(encoding="utf-8")
    assert mixin.count("_ensure_glow_enabled") >= 2
