"""Source-contract tests for the offline voice-command wiring (#663)."""

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


def test_command_registered() -> None:
    src = _src("quill/ui/main_frame_commands.py")
    assert '"tools.voice_command"' in src
    assert "self.voice_command_toggle" in src


def test_handler_present_and_gated() -> None:
    src = _src("quill/ui/main_frame_speech.py")
    assert "def voice_command_toggle" in src
    assert "voice_commands_available" in src  # off-by-default + Safe Mode gate
    assert "SAFE_TOOL_IDS" in src  # double-gate before dispatch


def test_menu_item_is_surfaced() -> None:
    # Hey QUILL Phase 1: the Voice Command (Offline) menu item is live in the
    # Speech menu (a real Append, not the old commented-out block).
    src = _src("quill/ui/main_frame_menu.py")
    idx = src.index('_("&Voice Command (Offline)")')
    line_start = src.rfind("\n", 0, idx) + 1
    assert not src[line_start:idx].lstrip().startswith("#")
    assert "self._id_speech_voice_command," in src


def test_legacy_dictation_scanner_is_retired() -> None:
    # The Windows-dictation-era Hey QUILL scanner is gone: no transcript
    # polling, no dictation-toggle command, no legacy module import.
    for rel in ("quill/ui/main_frame.py", "quill/ui/main_frame_menu.py"):
        src = _src(rel)
        assert "dictation_voice_commands" not in src
        assert "_voice_command_scan" not in src
        assert "from quill.core.voice_commands" not in src
    assert not (_ROOT / "quill" / "core" / "voice_commands.py").exists()


def test_command_uses_voice_feature() -> None:
    # tools.voice_command stays behind core.voice_commands so profiles and
    # Safe Mode can hide it; the runtime gate is voice_commands_available.
    src = _src("quill/ui/main_frame_commands.py")
    idx = src.index('"tools.voice_command"')
    block = src[idx : idx + 600]
    assert 'feature_id="core.voice_commands"' in block


def test_keymap_entry_present_unbound_by_default() -> None:
    """Present in the defaults, deliberately unbound: users bind their own.

    Asserted against DEFAULT_KEYMAP rather than profile_default.json, which is
    where this lived until 2026-09-17. The profiles are deltas over these
    defaults now (bad.md P2.6), so an entry that exists only in a profile is
    one the Keyboard Manager and the generated reference never see -- which is
    the opposite of "discoverable".
    """
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["tools.voice_command"] == ""


def test_dispatch_only_runs_safe_tool_ids() -> None:
    # The dispatch path checks command_id in SAFE_TOOL_IDS before registry.run.
    src = _src("quill/ui/main_frame_speech.py")
    assert "outcome.command_id in SAFE_TOOL_IDS" in src
