"""Source-contract tests for voice->Ask Quill routing (Hey QUILL Phase 4)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def _src(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_conversation_and_wake_route_questions() -> None:
    src = _src("quill/ui/main_frame_speech.py")
    assert "_voice_route_to_ask_quill" in src
    # Both the conversation and wake no-match paths consult the router.
    assert src.count("_voice_route_to_ask_quill(") >= 3  # def + 2 call sites


def test_router_used_and_prompt_prefilled_not_auto_sent() -> None:
    src = _src("quill/ui/main_frame_speech.py")
    assert "from quill.core.speech.voice_routing import" in src
    assert "open_ask_quill_conversation" in src
    assert "initial_prompt=question_text(transcript)" in src


def test_ask_quill_opener_accepts_initial_prompt() -> None:
    src = _src("quill/ui/main_frame.py")
    assert "def open_ask_quill_conversation(self, initial_prompt: str" in src
    assert "initial_prompt=initial_prompt," in src


def test_composer_prefill_does_not_auto_send() -> None:
    # The dialog pre-fills the input control; a person still presses Enter, so
    # voice never fires an AI request on its own.
    src = _src("quill/ui/assistant_panel.py")
    assert "self._initial_prompt" in src
    assert "self.input.SetValue(self._initial_prompt)" in src
