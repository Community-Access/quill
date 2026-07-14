"""Source-contract tests for the wake-word UI wiring (Hey QUILL Phase 3)."""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def _src(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_command_registered_under_voice_feature() -> None:
    src = _src("quill/ui/main_frame.py")
    assert '"tools.voice_wakeword"' in src
    assert "self.voice_wakeword_toggle" in src
    idx = src.index('"tools.voice_wakeword"')
    assert 'feature_id="core.voice_commands"' in src[idx : idx + 600]


def test_menu_item_is_live() -> None:
    src = _src("quill/ui/main_frame_menu.py")
    idx = src.index('_("Listen for &Hey QUILL")')
    line_start = src.rfind("\n", 0, idx) + 1
    assert not src[line_start:idx].lstrip().startswith("#")
    assert "_id_speech_wakeword" in src


def test_handler_gates_and_dispatch_is_allowlisted() -> None:
    src = _src("quill/ui/main_frame_speech.py")
    assert "def voice_wakeword_toggle" in src
    assert "voice_commands_available" in src  # off-by-default + Safe Mode gate
    assert "WakeController" in src
    # Inline "Hey QUILL, save file" still only runs allowlisted ids.
    assert "outcome.command_id in SAFE_TOOL_IDS" in src


def test_keymap_entry_present_unbound() -> None:
    bindings = json.loads(
        (_ROOT / "quill" / "core" / "keymap" / "profile_default.json").read_text(encoding="utf-8")
    )["bindings"]
    assert bindings.get("tools.voice_wakeword") == ""


def test_always_listening_off_by_default_and_not_persisted() -> None:
    # A saved enabled flag must not survive a restart unless persist is on.
    from quill.core.settings import Settings

    loaded = Settings.from_dict({"voice_wakeword_enabled": True, "voice_wakeword_persist": False})
    assert loaded.voice_wakeword_enabled is False
    persisted = Settings.from_dict({"voice_wakeword_enabled": True, "voice_wakeword_persist": True})
    assert persisted.voice_wakeword_enabled is True
