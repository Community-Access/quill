"""The SAPI self-voice fallback is logged, and only *spoken* when no screen
reader is handling speech (John's report: JAWS announced a benign failure)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.platform.windows import prism_bridge, sr_detect
from quill.ui.main_frame import MainFrame


class _Stub:
    _check_tts_fallback_on_startup = MainFrame._check_tts_fallback_on_startup
    _screen_reader_handling_speech = MainFrame._screen_reader_handling_speech

    def __init__(self, backend: str = "status_only") -> None:
        self._announcement_engine = SimpleNamespace(
            state=lambda: SimpleNamespace(active_backend=backend)
        )
        self.spoken: list[str] = []
        self.quiet: list[str] = []
        self.notes: list[tuple[str, str]] = []

    def _set_status(self, message: str) -> None:
        self.spoken.append(message)

    def _set_status_quiet(self, message: str) -> None:
        self.quiet.append(message)

    def _record_notification(self, message: str, category: str = "info") -> None:
        self.notes.append((message, category))


def test_no_failure_means_no_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prism_bridge, "tts_init_failed", lambda: False)
    stub = _Stub()
    stub._check_tts_fallback_on_startup()
    assert stub.spoken == [] and stub.quiet == [] and stub.notes == []


def test_failure_with_screen_reader_is_benign_not_alarming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prism_bridge, "tts_init_failed", lambda: True)
    stub = _Stub(backend="accessible_output2")  # a reader is voicing announcements
    stub._check_tts_fallback_on_startup()
    assert stub.spoken == []  # the benign failure is never spoken
    assert len(stub.quiet) == 1  # quiet, unspoken status note
    # The breadcrumb is informational (category "info", not an alarming
    # "accessibility" error) and tells the screen-reader user nothing is wrong (#749).
    assert len(stub.notes) == 1
    message, category = stub.notes[0]
    assert category == "info"
    assert "no action is needed" in message
    assert "no effect" in message
    assert "no voice" not in message.lower()


def test_failure_without_screen_reader_speaks_correct_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prism_bridge, "tts_init_failed", lambda: True)
    monkeypatch.setattr(
        sr_detect,
        "detect_screen_reader",
        lambda *a, **k: sr_detect.ScreenReaderDetection(False, "none", ""),
    )
    stub = _Stub(backend="status_only")  # no reader -> self-voice was the only voice
    stub._check_tts_fallback_on_startup()
    assert len(stub.spoken) == 1
    message = stub.spoken[0]
    assert "F8" not in message  # the old wrong instruction is gone
    assert "Retry TTS Engine" in message  # the real retry path
    assert len(stub.notes) == 1


def test_screen_reader_handling_speech_detects_backend() -> None:
    assert _Stub(backend="prism")._screen_reader_handling_speech() is True
    assert _Stub(backend="accessible_output2")._screen_reader_handling_speech() is True
