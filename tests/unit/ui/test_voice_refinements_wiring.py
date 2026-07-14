"""Source-contract tests for the Hey QUILL refinements wiring."""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def _src(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_conversation_capture_uses_vad() -> None:
    src = _src("quill/ui/main_frame_speech.py")
    assert "SilenceDetector" in src
    assert "_conv_poll_vad" in src
    assert "frames_since(" in src  # incremental polling, not O(n^2) re-joins


def test_spoken_cues_respect_screen_reader_parity() -> None:
    src = _src("quill/ui/main_frame_speech.py")
    assert "_voice_spoken_cues_active" in src
    assert "detect_screen_reader" in src  # do not talk over a screen reader
    assert "voice_conversation_spoken_cues" in src


def test_conversation_uses_varied_prompts() -> None:
    src = _src("quill/ui/main_frame_speech.py")
    assert "varied_prompts=True" in src


def test_voice_status_command_registered_and_menued() -> None:
    assert '"tools.voice_status"' in _src("quill/ui/main_frame.py")
    assert "self.speak_voice_status" in _src("quill/ui/main_frame.py")
    menu = _src("quill/ui/main_frame_menu.py")
    idx = menu.index('_("Speak Voice &Status")')
    line_start = menu.rfind("\n", 0, idx) + 1
    assert not menu[line_start:idx].lstrip().startswith("#")


def test_new_voice_settings_round_trip() -> None:
    from quill.core.settings import Settings

    s = Settings.from_dict({
        "voice_conversation_user_name": "  Jeff  ",
        "voice_conversation_spoken_cues": True,
    })
    assert s.voice_conversation_user_name == "Jeff"
    assert s.voice_conversation_spoken_cues is True


def test_voice_status_keymap_present_unbound() -> None:
    bindings = json.loads(
        (_ROOT / "quill" / "core" / "keymap" / "profile_default.json").read_text(encoding="utf-8")
    )["bindings"]
    assert bindings.get("tools.voice_status") == ""


def test_voice_engine_choice_round_trips_and_validates() -> None:
    from quill.core.settings import Settings

    assert (
        Settings.from_dict({"voice_recognition_engine": "vosk"}).voice_recognition_engine == "vosk"
    )
    assert (
        Settings.from_dict({"voice_recognition_engine": "whispercpp"}).voice_recognition_engine
        == "whispercpp"
    )
    # Unknown engine falls back to "follow main engine".
    assert Settings.from_dict({"voice_recognition_engine": "bogus"}).voice_recognition_engine == ""


def test_voice_paths_use_the_voice_provider_resolver() -> None:
    src = _src("quill/ui/main_frame_speech.py")
    assert "def _voice_provider" in src
    assert "voice_recognition_engine" in src
    # The wake, conversation, and command capture paths resolve through it.
    assert src.count("self._voice_provider()") >= 5
