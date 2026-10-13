"""QUILL's Locked Dictation (F9, Ctrl+F9) takes the family's one microphone (D-11).

The same :class:`~quill.core.dictation_owner.MicrophoneLock` as Ctrl+F11, QUILL
Lite, QUILL Transcribe and Inkwell, against a real operating-system lock in a
temporary folder: refused by name while another program listens, naming
"QUILL" to the others while it records, and let go on every way out of a
recording -- stop, discard, a failed start, a failed session, the window closing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.dictation_owner import MicrophoneLock, microphone_holder
from quill.core.speech.dictation.controller import DictationController, FeedbackEvent
from quill.core.speech.dictation.session import InsertionContext
from quill.core.speech.dictation.states import DictationState
from quill.core.windows_dictation import DictationController as LiveController
from quill.core.windows_dictation import DictationPreferences


class _Services:
    def __init__(self, *, wav: Path | None = Path("capture.wav")) -> None:
        self.wav = wav
        self.started = 0
        self.fail_start = False
        self.events: list[FeedbackEvent] = []
        self.busy: list[str] = []

    def start_capture(self, session: Any) -> None:
        if self.fail_start:
            raise RuntimeError("no microphone")
        self.started += 1

    def stop_capture(self, session: Any) -> Path | None:
        return self.wav

    def pause_capture(self, session: Any) -> None:
        pass

    def resume_capture(self, session: Any) -> None:
        pass

    def discard_capture(self, session: Any) -> None:
        pass

    def save_audio(self, session: Any, wav_path: Path) -> None:
        pass

    def transcribe(self, session: Any) -> None:
        pass

    def insert(self, session: Any, text: str) -> bool:
        return True

    def feedback(self, event: FeedbackEvent, session: Any) -> None:
        self.events.append(event)

    def microphone_busy(self, sentence: str) -> None:
        self.busy.append(sentence)

    def now(self) -> float:
        return 1000.0


def _locked(tmp_path: Path, services: _Services | None = None) -> tuple[Any, _Services, Any]:
    services = services or _Services()
    gate = MicrophoneLock("quill", folder=tmp_path, key="Ctrl+F9")
    return DictationController(services, microphone=gate), services, gate


def test_f9_is_refused_by_name_while_transcribe_listens(tmp_path: Path) -> None:
    transcribe = MicrophoneLock("transcribe", folder=tmp_path, key="Alt+Shift+\\")
    assert transcribe.take() == ""
    controller, services, _gate = _locked(tmp_path)
    controller.toggle_locked(InsertionContext())
    assert controller.state is DictationState.IDLE and services.started == 0
    assert services.busy == [
        "QUILL Transcribe is listening. Press Alt+Shift+Backslash to stop it, then try again."
    ]
    controller.start_hold(InsertionContext())  # Hold to Dictate too
    assert services.started == 0 and len(services.busy) == 2
    transcribe.release()


def test_f9_is_refused_while_quill_lite_dictates(tmp_path: Path) -> None:
    lite = MicrophoneLock("lite", folder=tmp_path, key="Ctrl+F11")
    assert lite.take() == ""
    controller, services, _gate = _locked(tmp_path)
    controller.toggle_locked(InsertionContext())
    assert services.busy == [
        "QUILL Lite is dictating. Press Ctrl+F11 in QUILL Lite to stop it, then try again."
    ]
    lite.release()


def test_while_f9_records_the_others_are_told_it_is_quill(tmp_path: Path) -> None:
    controller, _services, gate = _locked(tmp_path)
    controller.toggle_locked(InsertionContext())
    assert controller.state is DictationState.LOCKED_RECORDING and gate.held
    assert microphone_holder(folder=tmp_path) == "quill"
    assert MicrophoneLock("transcribe", folder=tmp_path).take() == (
        "QUILL is dictating. Press Ctrl+F9 in QUILL to stop it, then try again."
    )
    assert MicrophoneLock("lite", folder=tmp_path).take() == (
        "QUILL is dictating. Press Ctrl+F9 in QUILL to stop it, then try again."
    )


def test_ctrl_f11_in_the_same_quill_says_dictation_is_already_on(tmp_path: Path) -> None:
    controller, _services, _gate = _locked(tmp_path)
    controller.toggle_locked(InsertionContext())
    said: list[str] = []

    class _Feedback:
        def has_cue(self, _m: Any) -> bool:
            return False

        def cue(self, _m: Any) -> None:
            pass

        def say(self, text: str) -> None:
            said.append(text)

        def read_back(self, _t: str) -> None:
            pass

        def show(self, _t: str) -> None:
            pass

        def state_changed(self, _s: Any) -> None:
            pass

        def show_commands(self) -> None:
            pass

    class _Document:
        def unavailable_reason(self, *, writing: bool) -> str:
            return ""

    live = LiveController(
        recognizer=lambda _c, _p: None,  # never reached
        document=_Document(),  # type: ignore[arg-type]
        feedback=_Feedback(),
        preferences=lambda: DictationPreferences(),
        microphone=MicrophoneLock("quill", folder=tmp_path),
    )
    live.start()
    assert not live.active
    assert said == ["QUILL is already dictating. Press Ctrl+F9 to stop it, then try again."]


def test_stopping_lets_go_before_the_transcript_is_made(tmp_path: Path) -> None:
    controller, _services, gate = _locked(tmp_path)
    controller.toggle_locked(InsertionContext())
    controller.toggle_locked(InsertionContext())  # stop: transcription begins
    assert controller.state is DictationState.TRANSCRIBING
    assert not gate.held and microphone_holder(folder=tmp_path) is None


def test_discarding_lets_go(tmp_path: Path) -> None:
    controller, _services, gate = _locked(tmp_path)
    controller.toggle_locked(InsertionContext())
    controller.cancel_and_discard()
    assert not gate.held


def test_a_capture_that_will_not_start_lets_go(tmp_path: Path) -> None:
    services = _Services()
    services.fail_start = True
    controller, _services, gate = _locked(tmp_path, services)
    controller.toggle_locked(InsertionContext())
    assert FeedbackEvent.MIC_UNAVAILABLE in services.events and not gate.held


def test_nothing_recorded_or_a_failed_session_lets_go(tmp_path: Path) -> None:
    controller, _services, gate = _locked(tmp_path, _Services(wav=None))
    controller.toggle_locked(InsertionContext())
    controller.toggle_locked(InsertionContext())
    assert controller.state is DictationState.IDLE and not gate.held
    controller._microphone.take()
    controller._fail("transcription broke")
    assert not gate.held


def test_closing_the_window_lets_go(tmp_path: Path) -> None:
    controller, _services, gate = _locked(tmp_path)
    controller.toggle_locked(InsertionContext())
    controller.release_microphone()  # what the frame's destroy handler calls
    assert not gate.held


def test_without_a_gate_locked_dictation_is_unchanged() -> None:
    services = _Services()
    controller = DictationController(services)
    controller.toggle_locked(InsertionContext())
    assert controller.state is DictationState.LOCKED_RECORDING
