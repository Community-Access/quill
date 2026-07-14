"""Tests for offline voice commands (#663, Speech S5)."""

from __future__ import annotations

import pytest

from quill.core.ai.agent import SAFE_TOOL_IDS
from quill.core.speech import voice_commands as vc


class _FakeCommand:
    def __init__(self, command_id: str, title: str) -> None:
        self.id = command_id
        self.title = title


class _FakeRegistry:
    """A registry stub exposing get(); knows every SAFE_TOOL_IDS command."""

    _TITLES = {
        "file.save": "Save",
        "file.new": "New",
        "edit.undo": "Undo",
        "edit.select_all": "Select All",
        "format.bold": "Bold",
        "tools.word_count": "Word Count",
        "navigate.next_heading": "Next Heading",
        "view.toggle_soft_wrap": "Toggle Soft Wrap",
        "app.command_palette": "Command Palette",
    }

    def get(self, command_id: str):
        if command_id in self._TITLES:
            return _FakeCommand(command_id, self._TITLES[command_id])
        return None


def _commands():
    return vc.build_voice_commands(_FakeRegistry())


def test_normalize() -> None:
    assert vc.normalize("  Save, the File!  ") == "save the file"


def test_aliases_are_all_in_allowlist() -> None:
    # Security invariant: every aliased command is in the safe-tool allowlist.
    for command_id in vc._ALIASES:
        assert command_id in SAFE_TOOL_IDS


def test_build_only_includes_registered_allowlisted() -> None:
    commands = _commands()
    ids = {c.command_id for c in commands}
    # Only the fake registry's known commands appear (others aren't registered).
    assert "file.save" in ids
    assert "tools.spell_check_dialog" not in ids  # not in the fake registry
    assert ids <= set(SAFE_TOOL_IDS)


def test_exact_phrase_match() -> None:
    match = vc.match_command("save", _commands())
    assert match is not None and match.command_id == "file.save"
    assert match.score == 1.0


def test_alias_match() -> None:
    assert vc.match_command("save the file", _commands()).command_id == "file.save"
    assert vc.match_command("count words", _commands()).command_id == "tools.word_count"
    assert vc.match_command("next heading", _commands()).command_id == "navigate.next_heading"


def test_phrase_embedded_in_sentence() -> None:
    # A phrase appearing as a sub-sequence still matches.
    assert vc.match_command("please make it bold now", _commands()).command_id == "format.bold"


def test_no_match_below_threshold() -> None:
    assert vc.match_command("what is the weather", _commands()) is None
    assert vc.match_command("", _commands()) is None


def test_resolve_run() -> None:
    out = vc.resolve_transcript("select all", _FakeRegistry())
    assert out.kind == "run"
    assert out.command_id == "edit.select_all"
    assert "Select All" in out.message


def test_resolve_cancel() -> None:
    for phrase in ("cancel", "never mind", "Stop."):
        out = vc.resolve_transcript(phrase, _FakeRegistry())
        assert out.kind == "cancel"


def test_resolve_no_match_reports_what_it_heard() -> None:
    out = vc.resolve_transcript("order a pizza", _FakeRegistry())
    assert out.kind == "no_match"
    assert "order a pizza" in out.message


def test_resolve_only_runs_allowlisted() -> None:
    # Even if a phrase matches, the resolved id is always within the allowlist.
    out = vc.resolve_transcript("undo", _FakeRegistry())
    assert out.command_id in SAFE_TOOL_IDS


class _Settings:
    def __init__(self, enabled: bool) -> None:
        self.voice_commands_enabled = enabled


@pytest.mark.parametrize(
    ("enabled", "safe_mode", "expected"),
    [(True, False, True), (False, False, False), (True, True, False), (False, True, False)],
)
def test_availability_gate(enabled: bool, safe_mode: bool, expected: bool) -> None:
    assert vc.voice_commands_available(_Settings(enabled), safe_mode_active=safe_mode) is expected


def test_availability_default_off() -> None:
    class _Bare:
        pass

    assert vc.voice_commands_available(_Bare(), safe_mode_active=False) is False


# --- wake phrase (Phase 3 groundwork, kept from the retired legacy module) ---


def test_wake_only_utterance_returns_empty_body() -> None:
    assert vc.extract_transcript_body("Hey QUILL") == ""
    assert vc.extract_transcript_body("quill") == ""


def test_wake_phrase_prefix_yields_the_command_body() -> None:
    assert vc.extract_transcript_body("Hey QUILL, save file!") == "save file"
    assert vc.extract_transcript_body("QUILL word count") == "word count"


def test_unaddressed_speech_returns_none() -> None:
    assert vc.extract_transcript_body("please save the file") is None
    assert vc.extract_transcript_body("") is None
