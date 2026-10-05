"""qc.md 18.7: a one-key outcome as a sound, words, or both."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.ui.podcasts import outcome_feedback


class _Host:
    def __init__(self, mode: str) -> None:
        self._podcast_history = SimpleNamespace(action_feedback=mode)
        self.said: list[tuple[str, str]] = []
        self.status: list[str] = []

    def _announce(self, message: str, *, sound: str = "") -> None:
        self.said.append((message, sound))

    def _set_status(self, message: str) -> None:
        self.status.append(message)


@pytest.fixture
def cues(monkeypatch):
    played: list[str] = []
    monkeypatch.setattr("quill.ui.companion_cues.post_cue", played.append)
    return played


@pytest.mark.parametrize(
    ("mode", "has_sound", "said", "played"),
    [
        ("both", True, [("Added", "cast_queue_added")], []),
        ("speech", True, [("Added", "")], []),
        ("sound", True, [], ["cast_queue_added"]),
        ("sound", False, [("Added", "")], []),
        ("silent", True, [], []),
    ],
)
def test_the_choice_decides_sound_and_words(monkeypatch, cues, mode, has_sound, said, played):
    monkeypatch.setattr(outcome_feedback, "_has_sound", lambda _e: has_sound)
    host = _Host(mode)
    outcome_feedback.say_outcome(host, "Added", sound="cast_queue_added")
    assert host.said == said
    assert cues == played
    if not said:
        assert host.status == ["Added"]


def test_a_failure_is_always_said_the_first_time(monkeypatch, cues) -> None:
    monkeypatch.setattr(outcome_feedback, "_has_sound", lambda _e: True)
    host = _Host("sound")
    outcome_feedback.say_failure(host, "Lectures is unavailable.")
    assert host.said and host.said[0][0] == "Lectures is unavailable."


def test_cast_starts_on_both_and_keeps_the_choice(tmp_path) -> None:
    from quill.core.podcasts.history import PodcastHistory

    assert PodcastHistory().action_feedback == "both"
