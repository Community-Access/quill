"""Source-contract tests for the wake-word UI wiring (Hey QUILL Phase 3)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def _src(rel: str) -> str:
    # SpeechCommandsMixin was split into
    # main_frame_speech{,_downloads,_voice}.py (CQ-1); scan all three so voice
    # handler pins survive wherever they landed.
    if rel == "quill/ui/main_frame_speech.py":
        ui = _ROOT / "quill" / "ui"
        return chr(10).join(
            p.read_text(encoding="utf-8") for p in sorted(ui.glob("main_frame_speech*.py"))
        )
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_command_registered_under_voice_feature() -> None:
    src = _src("quill/ui/main_frame_commands.py")
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
    """Present in the defaults, deliberately unbound: users bind their own.

    Asserted against DEFAULT_KEYMAP rather than profile_default.json, which is
    where this lived until 2026-09-17. The profiles are deltas over these
    defaults now (bad.md P2.6), so an entry that exists only in a profile is
    one the Keyboard Manager and the generated reference never see -- which is
    the opposite of "discoverable".
    """
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["tools.voice_wakeword"] == ""


def test_always_listening_off_by_default_and_not_persisted() -> None:
    # A saved enabled flag must not survive a restart unless persist is on.
    from quill.core.settings import Settings

    loaded = Settings.from_dict({"voice_wakeword_enabled": True, "voice_wakeword_persist": False})
    assert loaded.voice_wakeword_enabled is False
    persisted = Settings.from_dict({"voice_wakeword_enabled": True, "voice_wakeword_persist": True})
    assert persisted.voice_wakeword_enabled is True
