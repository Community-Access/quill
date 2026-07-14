"""Tests for quill.tools.check_copy_tray_binding.

The gate is the regression guard for the 12 ``edit.paste_from_tray_N``
slots.  These tests cover the positive case (gate is green against the
shipped defaults and both bundled profiles) and the failure modes (a
slot missing, a slot rebound, a different command stealing a slot).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.keymap import DEFAULT_KEYMAP
from quill.tools import check_copy_tray_binding


def test_default_keymap_owns_all_twelve_slots() -> None:
    errors = check_copy_tray_binding.run_checks()
    assert errors == [], "\n".join(errors)


def test_resolved_profile_default_owns_all_twelve_slots(tmp_path: Path) -> None:
    # Profile JSONs live in the repo.  Override the lookup via monkeypatching
    # the directory to keep this test self-contained.
    monkeypatched = tmp_path / "keymap"
    monkeypatched.mkdir()
    # Copy the real profile JSON so the test exercises the same overlay logic
    # the running app uses.
    real = Path(check_copy_tray_binding._KEYMAP_DIR)
    (monkeypatched / "profile_default.json").write_bytes(
        (real / "profile_default.json").read_bytes()
    )
    (monkeypatched / "profile_sr_friendly.json").write_bytes(
        (real / "profile_sr_friendly.json").read_bytes()
    )
    check_copy_tray_binding._KEYMAP_DIR = monkeypatched  # type: ignore[attr-defined]
    try:
        errors = check_copy_tray_binding.run_checks()
        assert errors == [], "\n".join(errors)
    finally:
        check_copy_tray_binding._KEYMAP_DIR = real  # type: ignore[attr-defined]


def test_drift_missing_slot_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If ``edit.paste_from_tray_3`` is removed from DEFAULT_KEYMAP, the gate
    must report it."""
    from quill.core import keymap as keymap_module

    patched = dict(DEFAULT_KEYMAP)
    patched.pop("edit.paste_from_tray_3")
    monkeypatch.setattr(keymap_module, "DEFAULT_KEYMAP", patched)
    errors = check_copy_tray_binding.run_checks()
    assert any("edit.paste_from_tray_3" in e for e in errors)


def test_drift_rebound_slot_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If a slot's binding is changed to something else (e.g. a heading
    shortcut wants ``Ctrl+Shift+3``), the gate must report it."""
    from quill.core import keymap as keymap_module

    patched = dict(DEFAULT_KEYMAP)
    patched["edit.paste_from_tray_3"] = "Ctrl+Alt+3"
    monkeypatch.setattr(keymap_module, "DEFAULT_KEYMAP", patched)
    errors = check_copy_tray_binding.run_checks()
    assert any("edit.paste_from_tray_3" in e for e in errors)
    assert any("Ctrl+Alt+3" in e for e in errors)


def test_drift_stolen_slot_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If a *different* command claims one of the reserved bindings, the gate
    must report it so a contributor cannot silently shadow a Copy Tray slot."""
    from quill.core import keymap as keymap_module

    patched = dict(DEFAULT_KEYMAP)
    # Add a brand-new command that tries to steal ``Ctrl+Shift+3``.
    patched["format.heading_3_shortcut"] = "Ctrl+Shift+3"
    monkeypatch.setattr(keymap_module, "DEFAULT_KEYMAP", patched)
    errors = check_copy_tray_binding.run_checks()
    assert any("format.heading_3_shortcut" in e for e in errors)
    assert any("edit.paste_from_tray_3" in e for e in errors)


def test_resolved_keymap_overlays_profile_bindings(tmp_path: Path) -> None:
    """The profile overlay must take effect — if a profile re-binds slot 3,
    the resolved keymap must reflect that re-binding, not the default."""
    profile_dir = tmp_path / "keymap"
    profile_dir.mkdir()
    profile = {
        "_name": "Test Profile",
        "bindings": {
            "edit.paste_from_tray_3": "Ctrl+Alt+3",  # intentional violation
            "edit.paste_from_tray_1": "Ctrl+Shift+1",
            "edit.paste_from_tray_2": "Ctrl+Shift+2",
            "edit.paste_from_tray_4": "Ctrl+Shift+4",
            "edit.paste_from_tray_5": "Ctrl+Shift+5",
            "edit.paste_from_tray_6": "Ctrl+Shift+6",
            "edit.paste_from_tray_7": "Ctrl+Shift+7",
            "edit.paste_from_tray_8": "Ctrl+Shift+8",
            "edit.paste_from_tray_9": "Ctrl+Shift+9",
            "edit.paste_from_tray_10": "Ctrl+Shift+0",
            "edit.paste_from_tray_11": "Ctrl+Shift+-",
            "edit.paste_from_tray_12": "Ctrl+Shift+=",
        },
    }
    profile_path = profile_dir / "profile_default.json"
    profile_path.write_text(json.dumps(profile), encoding="utf-8")

    real = check_copy_tray_binding._KEYMAP_DIR
    check_copy_tray_binding._KEYMAP_DIR = profile_dir  # type: ignore[attr-defined]
    try:
        errors = check_copy_tray_binding.run_checks()
    finally:
        check_copy_tray_binding._KEYMAP_DIR = real  # type: ignore[attr-defined]
    assert any("profile_default.json" in e for e in errors)
    assert any("edit.paste_from_tray_3" in e for e in errors)


def test_menu_lint_includes_copy_tray_gate() -> None:
    """``menu_lint.run_checks`` must delegate to the Copy Tray gate so a
    single one-shot invocation covers both structural and keymap invariants."""
    from quill.tools.menu_lint import run_checks

    errors = run_checks()
    assert errors == [], "\n".join(errors)
