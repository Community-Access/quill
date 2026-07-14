from __future__ import annotations

from pathlib import Path

from quill.core.speech.dictation.controller import (
    DictationConfig,
    DictationController,
    FeedbackEvent,
)
from quill.core.speech.dictation.session import DictationSession, InsertionContext
from quill.core.speech.dictation.states import DictationState


class FakeServices:
    """A scripted DictationServices double; records calls and drives time."""

    def __init__(self, *, wav: Path | None = Path("capture.wav"), insert_ok: bool = True) -> None:
        self.time = 1000.0
        self.wav = wav
        self.insert_ok = insert_ok
        self.events: list[FeedbackEvent] = []
        self.started = 0
        self.stopped = 0
        self.discarded = 0
        self.saved: list[Path] = []
        self.transcribed: list[DictationSession] = []
        self.inserted_text: list[str] = []
        self.paused = 0
        self.resumed = 0
        self.fail_start = False

    def start_capture(self, session: DictationSession) -> None:
        if self.fail_start:
            raise RuntimeError("mic busy")
        self.started += 1

    def stop_capture(self, session: DictationSession) -> Path | None:
        self.stopped += 1
        return self.wav

    def pause_capture(self, session: DictationSession) -> None:
        self.paused += 1

    def resume_capture(self, session: DictationSession) -> None:
        self.resumed += 1

    def discard_capture(self, session: DictationSession) -> None:
        self.discarded += 1

    def save_audio(self, session: DictationSession, wav_path: Path) -> None:
        self.saved.append(wav_path)

    def transcribe(self, session: DictationSession) -> None:
        self.transcribed.append(session)

    def insert(self, session: DictationSession, text: str) -> bool:
        self.inserted_text.append(text)
        return self.insert_ok

    def feedback(self, event: FeedbackEvent, session: DictationSession | None) -> None:
        self.events.append(event)

    def now(self) -> float:
        return self.time


def _ctx(**kw: object) -> InsertionContext:
    return InsertionContext(**kw)  # type: ignore[arg-type]


# -- Hold-to-Dictate -------------------------------------------------------- #


def test_hold_records_then_inserts_one_transcript() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.start_hold(_ctx(prefix_char="e"))
    assert ctrl.state is DictationState.HOLD_RECORDING
    assert svc.started == 1
    assert FeedbackEvent.HOLD_START in svc.events

    ctrl.release_hold()
    assert ctrl.state is DictationState.TRANSCRIBING
    assert svc.stopped == 1
    assert svc.saved  # audio secured before transcription
    session = svc.transcribed[-1]

    ctrl.transcription_succeeded(session.session_id, "hello world")
    assert ctrl.state is DictationState.IDLE
    assert svc.inserted_text == [" hello world "]
    assert FeedbackEvent.INSERTED in svc.events


def test_autorepeat_keydown_does_not_restart_recording() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.start_hold(_ctx())
    ctrl.start_hold(_ctx())  # auto-repeat
    ctrl.start_hold(_ctx())  # auto-repeat
    assert svc.started == 1  # exactly one recording


def test_release_without_hold_is_ignored() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.release_hold()  # no active hold
    assert ctrl.state is DictationState.IDLE
    assert svc.stopped == 0


def test_mic_failure_returns_to_idle_without_recording_state() -> None:
    svc = FakeServices()
    svc.fail_start = True
    ctrl = DictationController(svc)
    ctrl.start_hold(_ctx())
    assert ctrl.state is DictationState.IDLE
    assert FeedbackEvent.MIC_UNAVAILABLE in svc.events


def test_read_only_target_never_records() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.start_hold(_ctx(read_only=True))
    assert ctrl.state is DictationState.IDLE
    assert svc.started == 0


def test_min_hold_duration_drops_accidental_tap() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc, DictationConfig(min_hold_seconds=0.5))
    ctrl.start_hold(_ctx())
    # Released immediately (no time advance) -> below minimum -> discarded.
    ctrl.release_hold()
    assert ctrl.state is DictationState.IDLE
    assert svc.transcribed == []
    assert svc.discarded == 1


def test_empty_transcript_is_not_inserted() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.start_hold(_ctx())
    ctrl.release_hold()
    session = svc.transcribed[-1]
    ctrl.transcription_succeeded(session.session_id, "   ")
    assert ctrl.state is DictationState.IDLE
    assert svc.inserted_text == []
    assert FeedbackEvent.NO_SPEECH in svc.events


def test_deferred_insertion_goes_to_review_then_idle() -> None:
    svc = FakeServices(insert_ok=False)
    ctrl = DictationController(svc)
    ctrl.start_hold(_ctx())
    ctrl.release_hold()
    session = svc.transcribed[-1]
    ctrl.transcription_succeeded(session.session_id, "draft text")
    assert FeedbackEvent.REVIEW in svc.events
    assert ctrl.state is DictationState.IDLE  # controller frees up for a new session


def test_transcription_failure_preserves_and_recovers() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.start_hold(_ctx())
    ctrl.release_hold()
    session = svc.transcribed[-1]
    ctrl.transcription_failed(session.session_id, "model missing")
    assert ctrl.state is DictationState.IDLE
    assert FeedbackEvent.ERROR in svc.events
    assert svc.saved  # audio still secured


def test_stale_transcription_callback_is_ignored() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.start_hold(_ctx())
    ctrl.release_hold()
    ctrl.transcription_succeeded("not-the-session", "garbage")
    assert svc.inserted_text == []


# -- Locked Dictation ------------------------------------------------------- #


def test_locked_toggle_starts_and_finishes() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.toggle_locked(_ctx())
    assert ctrl.state is DictationState.LOCKED_RECORDING
    assert FeedbackEvent.LOCKED_START in svc.events
    ctrl.toggle_locked(_ctx())
    assert ctrl.state is DictationState.TRANSCRIBING
    assert FeedbackEvent.LOCKED_STOP in svc.events


def test_emergency_stop_keeps_speech() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.toggle_locked(_ctx())
    ctrl.emergency_stop()
    assert ctrl.state is DictationState.TRANSCRIBING
    assert svc.transcribed  # speech preserved, not discarded
    assert svc.discarded == 0


def test_cancel_and_discard_drops_audio() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.toggle_locked(_ctx())
    ctrl.cancel_and_discard()
    assert ctrl.state is DictationState.IDLE
    assert svc.discarded == 1
    assert svc.transcribed == []
    assert FeedbackEvent.CANCELLED in svc.events


def test_pause_and_resume_locked_session() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.toggle_locked(_ctx())
    ctrl.toggle_pause()
    assert ctrl.state is DictationState.PAUSED
    assert svc.paused == 1
    ctrl.toggle_pause()
    assert ctrl.state is DictationState.LOCKED_RECORDING
    assert svc.resumed == 1


def test_max_duration_auto_stops_locked() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc, DictationConfig(max_locked_seconds=300.0))
    ctrl.toggle_locked(_ctx())
    svc.time += 301.0
    ctrl.tick()
    assert ctrl.state is DictationState.TRANSCRIBING
    assert FeedbackEvent.MAX_TIME in svc.events


def test_tick_does_not_stop_before_limit() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc, DictationConfig(max_locked_seconds=300.0))
    ctrl.toggle_locked(_ctx())
    svc.time += 100.0
    ctrl.tick()
    assert ctrl.state is DictationState.LOCKED_RECORDING


def test_focus_loss_stops_and_preserves_when_enabled() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc, DictationConfig(stop_on_focus_loss=True))
    ctrl.toggle_locked(_ctx())
    ctrl.on_focus_lost()
    assert ctrl.state is DictationState.TRANSCRIBING
    assert FeedbackEvent.FOCUS_LOST in svc.events


def test_focus_loss_ignored_when_background_allowed() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc, DictationConfig(stop_on_focus_loss=False))
    ctrl.toggle_locked(_ctx())
    ctrl.on_focus_lost()
    assert ctrl.state is DictationState.LOCKED_RECORDING


def test_missing_keyup_recovers_hold() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.start_hold(_ctx())
    ctrl.on_missing_keyup()
    assert ctrl.state is DictationState.TRANSCRIBING
    assert FeedbackEvent.MISSING_KEYUP in svc.events


def test_ctrl_f9_during_hold_does_not_create_second_session() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.start_hold(_ctx())
    ctrl.toggle_locked(_ctx())  # PRD §12: ignored while holding
    assert ctrl.state is DictationState.HOLD_RECORDING
    assert svc.started == 1


def test_toggle_locked_while_transcribing_reports_busy() -> None:
    svc = FakeServices()
    ctrl = DictationController(svc)
    ctrl.toggle_locked(_ctx())
    ctrl.toggle_locked(_ctx())  # now TRANSCRIBING
    assert ctrl.state is DictationState.TRANSCRIBING
    svc.events.clear()
    ctrl.toggle_locked(_ctx())  # busy
    assert FeedbackEvent.BUSY in svc.events
