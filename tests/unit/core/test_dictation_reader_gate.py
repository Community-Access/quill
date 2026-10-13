"""Dictation does not hear the screen reader (reader_gate.py)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.windows_dictation import reader_gate as rg
from quill.core.windows_dictation.reader_gate import LOUD_RMS, TAIL_S, ReaderGate


class _Clock:
    def __init__(self) -> None:
        self.now = 50.0

    def __call__(self) -> float:
        return self.now


def _talk(gate: ReaderGate, clock: _Clock, seconds: float, rms: float = 4000.0) -> None:
    """The reader talks for *seconds*, one 10 ms block at a time."""
    for _ in range(round(seconds / 0.01)):
        clock.now += 0.01
        gate.heard(rms)


def test_the_gate_is_open_while_the_reader_talks_and_a_tail_after() -> None:
    clock = _Clock()
    gate = ReaderGate(clock)
    assert not gate.speaking()
    _talk(gate, clock, 1.0)
    assert gate.speaking()
    clock.now += TAIL_S / 2
    assert gate.speaking()
    clock.now += TAIL_S
    assert not gate.speaking()


def test_quiet_audio_is_not_the_reader_talking() -> None:
    clock = _Clock()
    gate = ReaderGate(clock)
    _talk(gate, clock, 1.0, rms=LOUD_RMS / 10)  # JAWS idle measured at 1
    assert not gate.speaking()


def test_a_phrase_that_was_mostly_the_reader_is_dropped() -> None:
    clock = _Clock()
    gate = ReaderGate(clock)
    start = clock.now
    _talk(gate, clock, 2.0)
    assert gate.mostly_reader(start)
    # The person's own phrase, after the reader finished, is not.
    clock.now += 1.0
    mine = clock.now
    clock.now += 1.5
    assert not gate.mostly_reader(mine)


def test_the_controller_drops_what_the_reader_said(monkeypatch) -> None:
    from tests.unit.core.test_windows_dictation import _controller, _hear

    clock = _Clock()
    gate = ReaderGate(clock)
    monkeypatch.setattr("quill.core.windows_dictation.microphone_owner.started_gate", lambda: gate)
    controller, _r, document, _f = _controller()
    controller._clock = clock
    controller.start()
    controller.on_speech_started()
    _talk(gate, clock, 1.5)  # "Dictation on" from Narrator, heard by the microphone
    _hear(controller, "dictation on")
    assert document.text == ""
    clock.now += 2.0
    controller.on_speech_started()
    clock.now += 1.0
    _hear(controller, "dear Maria")
    assert document.text == "Dear Maria"


def test_the_built_in_models_say_they_never_hear_the_reader() -> None:
    from quill.core.windows_dictation.local_recognizer import LocalDictationRecognizer

    assert LocalDictationRecognizer.hears_reader is False


def test_the_microphone_is_silence_while_the_reader_talks() -> None:
    # numpy arrives with the live-dictation extra; CI's test environment has none.
    np = pytest.importorskip("numpy")
    from quill.core.windows_dictation.local_recognizer import LocalDictationRecognizer

    recognizer = LocalDictationRecognizer.__new__(LocalDictationRecognizer)
    queued: list = []
    recognizer._running = SimpleNamespace(is_set=lambda: True)
    recognizer._silent_blocks = 0
    recognizer._audio = SimpleNamespace(put=queued.append)
    recognizer._gate = SimpleNamespace(speaking=lambda: True)
    block = np.full((160, 1), 0.3, dtype=np.float32)
    recognizer._on_audio(block, 160, None, None)
    assert not queued[-1].any()
    # Silenced audio is not a lost microphone: the floor counts what came in.
    assert recognizer._silent_blocks == 0
    recognizer._gate = SimpleNamespace(speaking=lambda: False)
    recognizer._on_audio(block, 160, None, None)
    assert queued[-1].any()


def test_without_a_started_gate_nothing_is_dropped(monkeypatch) -> None:
    monkeypatch.setattr(rg, "_GATE", None)
    assert rg.started_gate() is None
