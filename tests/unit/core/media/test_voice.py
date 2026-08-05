"""Tests for the voice-command parser (quill.core.media.voice)."""

from __future__ import annotations

import pytest

from quill.core.media.voice import VoiceIntent, parse_voice_command


@pytest.mark.parametrize(
    ("phrase", "action"),
    [
        ("play", "play"),
        ("Resume", "play"),
        ("continue", "play"),
        ("pause", "pause"),
        ("stop", "stop"),
        ("play pause", "toggle"),
        ("next chapter", "next_chapter"),
        ("next", "next_chapter"),
        ("previous chapter", "prev_chapter"),
        ("back a chapter", "prev_chapter"),
        ("bookmark this", "bookmark"),
        ("add a bookmark", "bookmark"),
        ("where am i", "where_am_i"),
        ("how much time is left", "where_am_i"),
        ("mute", "mute"),
        ("speed up", "faster"),
        ("slow down", "slower"),
        ("volume up", "volume_up"),
        ("quieter please", "volume_down"),
        ("summarize this chapter", "summarize"),
        ("give me a recap", "recap"),
        ("catch me up", "recap"),
    ],
)
def test_fixed_commands(phrase: str, action: str) -> None:
    intent = parse_voice_command(phrase)
    assert intent == VoiceIntent(action)


def test_case_and_whitespace_insensitive() -> None:
    assert parse_voice_command("  NEXT   Chapter  ") == VoiceIntent("next_chapter")


@pytest.mark.parametrize(
    ("phrase", "value_ms"),
    [
        ("skip back thirty", -30_000),
        ("skip back thirty seconds", -30_000),
        ("skip forward ten", 10_000),
        ("jump ahead fifteen", 15_000),
        ("skip back", -30_000),  # default skip
        ("rewind", -30_000),
        ("fast forward", 30_000),
    ],
)
def test_skip(phrase: str, value_ms: int) -> None:
    intent = parse_voice_command(phrase)
    assert intent is not None
    assert intent.action == "skip"
    assert intent.value == value_ms


@pytest.mark.parametrize(
    ("phrase", "value_ms"),
    [
        ("go to 1:23:45", (1 * 3600 + 23 * 60 + 45) * 1000),
        ("jump to 5:00", 5 * 60 * 1000),
        ("go to one hour twenty three minutes", (3600 + 23 * 60) * 1000),
        ("seek to forty five seconds", 45 * 1000),
        ("go to two minutes", 2 * 60 * 1000),
    ],
)
def test_seek(phrase: str, value_ms: int) -> None:
    intent = parse_voice_command(phrase)
    assert intent is not None
    assert intent.action == "seek"
    assert intent.value == value_ms


@pytest.mark.parametrize(
    ("phrase", "action", "value"),
    [
        ("sleep in twenty", "sleep", 20),
        ("sleep timer thirty minutes", "sleep", 30),
        ("sleep off", "sleep", 0),
        ("cancel sleep", "sleep", 0),
        ("sleep at end of chapter", "sleep_eoc", 0),
    ],
)
def test_sleep(phrase: str, action: str, value: int) -> None:
    assert parse_voice_command(phrase) == VoiceIntent(action, value)


@pytest.mark.parametrize("phrase", ["", "   ", "banana", "what time is it", "hello there"])
def test_unrecognized(phrase: str) -> None:
    assert parse_voice_command(phrase) is None


def test_non_string_is_none() -> None:
    assert parse_voice_command(None) is None  # type: ignore[arg-type]
