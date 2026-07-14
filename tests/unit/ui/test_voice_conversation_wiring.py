"""Source-contract tests for the conversation-mode UI wiring (Phase 2)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def _src(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_command_registered_under_voice_feature() -> None:
    src = _src("quill/ui/main_frame.py")
    assert '"tools.voice_conversation"' in src
    assert "self.voice_conversation_toggle" in src
    idx = src.index('"tools.voice_conversation"')
    assert 'feature_id="core.voice_commands"' in src[idx : idx + 600]


def test_menu_item_is_live() -> None:
    src = _src("quill/ui/main_frame_menu.py")
    idx = src.index('_("Voice &Conversation Mode")')
    line_start = src.rfind("\n", 0, idx) + 1
    assert not src[line_start:idx].lstrip().startswith("#")
    assert "_id_speech_voice_conversation" in src


def test_handler_gates_on_availability_and_allowlist() -> None:
    src = _src("quill/ui/main_frame_speech.py")
    assert "def voice_conversation_toggle" in src
    assert "voice_commands_available" in src  # off-by-default + Safe Mode gate
    assert "SAFE_TOOL_IDS" in src  # dispatch only via the safe allowlist
    assert "ConversationController" in src


def test_dispatch_only_runs_allowlisted_ids() -> None:
    src = _src("quill/ui/main_frame_speech.py")
    # The controller only receives a command id after the UI checks it against
    # SAFE_TOOL_IDS in _conv_on_transcript.
    assert "outcome.command_id in SAFE_TOOL_IDS" in src


def test_keymap_entry_present_unbound() -> None:
    import json

    bindings = json.loads(
        (_ROOT / "quill" / "core" / "keymap" / "profile_default.json").read_text(encoding="utf-8")
    )["bindings"]
    assert bindings.get("tools.voice_conversation") == ""
