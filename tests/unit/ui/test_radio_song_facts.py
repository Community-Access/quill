"""Song Details: the difference between a list of titles and a history.

Song History has recorded artist and title for a while. Which release a song came
from, what year it is, and how long it runs are the two questions people actually
ask about something they just heard, and neither is answerable from a broadcast
title. These pin the command that answers them -- and, more importantly, the
three rules that keep it from being a cost: opt-in, off the UI thread, and
degrading to "nothing more is known" rather than to an error.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.musicbrainz import RecordingFacts
from quill.ui.radio import song_facts


class _Song:
    def __init__(self, title: str = "Your Song", artist: str = "Elton John") -> None:
        self.title = title
        self.artist = artist

    def display(self) -> str:
        return f"{self.title} by {self.artist}"


class _Tasks:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.submitted: list[str] = []

    def submit(self, name: str, work: Any, *, on_success: Any = None, on_failure: Any = None):
        self.submitted.append(name)
        if self.error is not None:
            if on_failure is not None:
                on_failure(name, self.error)
            return
        if on_success is not None:
            on_success(name, self.result if self.result is not None else work())


class _Wx:
    @staticmethod
    def CallAfter(fn: Any, *args: Any) -> None:  # noqa: N802 - wx's own casing
        fn(*args)


class _Host:
    def __init__(self, tasks: Any = None, *, safe_mode: bool = False) -> None:
        self._task_manager = tasks
        self._safe_mode = safe_mode
        self._wx = _Wx()
        self.said: list[str] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)


def test_the_facts_are_spoken_as_a_sentence() -> None:
    facts = RecordingFacts(release="Elton John", year="1970", length_ms=241_000)
    said = song_facts.describe(_Song(), facts)
    assert said.startswith("Your Song by Elton John,")
    assert "from Elton John" in said
    assert "1970" in said
    # Durations in words, never a timecode.
    assert "4 minutes 1 seconds" in said


def test_nothing_known_says_so_rather_than_an_empty_clause() -> None:
    assert song_facts.describe(_Song(), RecordingFacts()) == song_facts.NOT_FOUND
    assert song_facts.describe(_Song(), None) == song_facts.NOT_FOUND


def test_a_lookup_runs_off_the_ui_thread_and_reports_back() -> None:
    facts = RecordingFacts(release="Album", year="1999")
    host = _Host(_Tasks(result=facts))
    shown: list[str] = []

    song_facts.request(host, _Song(), shown.append)

    assert host._task_manager.submitted == ["radio-song-facts"]
    assert shown and "Album" in shown[0]
    assert any("Album" in m for m in host.said)
    # It says it is working first: a silent pause reads as a dead button.
    assert host.said[0].startswith("Looking up")


def test_a_failed_lookup_degrades_to_not_knowing_rather_than_an_error() -> None:
    # A listener asking "what album is this?" is not served by an HTTP message.
    host = _Host(_Tasks(error=OSError("503 from the server")))
    song_facts.request(host, _Song(), lambda _t: None)
    assert song_facts.NOT_FOUND in host.said
    assert not any("503" in m for m in host.said)


def test_safe_mode_refuses_before_reaching_the_network() -> None:
    host = _Host(_Tasks(), safe_mode=True)
    song_facts.request(host, _Song(), lambda _t: None)
    assert host._task_manager.submitted == []
    assert any("Safe Mode" in m for m in host.said)


def test_no_song_selected_says_so() -> None:
    host = _Host(_Tasks())
    song_facts.request(host, None, lambda _t: None)
    assert song_facts.NO_SELECTION in host.said
    assert host._task_manager.submitted == []


def test_no_task_manager_is_not_a_crash() -> None:
    host = _Host(None)
    song_facts.request(host, _Song(), lambda _t: None)
    assert any("unavailable" in m for m in host.said)
