"""One microphone in the family (D-11), and the working tick (D-17).

The microphone lock is a real operating-system file lock in a temporary folder:
two locks in one process collide exactly as two programs do, which is what lets
these tests say "two starts give one owner and one recogniser". The tick runs
against a fake clock and a fake ``call_later``, so nothing waits.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from quill.core.dictation_owner import (
    APP_NAMES,
    MicrophoneLock,
    OwnerLock,
    busy_sentence,
    microphone_holder,
)
from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.controller import DictationStartError
from quill.core.windows_dictation.ports import DictationState, Moment
from quill.core.windows_dictation.working_tick import STILL_WORKING

# -- the stand-ins --------------------------------------------------------------- #


class _Document:
    def __init__(self) -> None:
        self.text = ""

    def unavailable_reason(self, *, writing: bool) -> str:
        return ""

    def context(self) -> tuple[str, str]:
        return self.text, ""

    def selection(self) -> tuple[int, int]:
        return len(self.text), len(self.text)

    def select(self, start: int, end: int) -> None:
        pass

    def insert(self, text: str) -> tuple[int, int]:
        start = len(self.text)
        self.text += text
        return start, len(self.text)

    def text_between(self, start: int, end: int) -> str:
        return self.text[start:end]

    def remove(self, start: int, end: int) -> None:
        self.text = self.text[:start] + self.text[end:]

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        self.text = self.text[:start] + text + self.text[end:]
        return start, start + len(text)

    def line_bounds(self) -> tuple[int, int]:
        return 0, len(self.text)

    def last_position(self) -> int:
        return len(self.text)

    def undo(self) -> bool:
        return False


class _Handle:
    def __init__(self, seconds: float, callback: Callable[[], None]) -> None:
        self.seconds = seconds
        self.callback = callback
        self.stopped = False

    def Stop(self) -> None:  # noqa: N802 - wx.CallLater's shape
        self.stopped = True


class _Feedback:
    def __init__(self, *, clip: bool = True) -> None:
        self.clip = clip
        self.cues: list[Moment] = []
        self.said: list[str] = []
        self.shown: list[str] = []
        self.pending: list[_Handle] = []

    def has_cue(self, moment: Moment) -> bool:
        return self.clip

    def cue(self, moment: Moment) -> None:
        self.cues.append(moment)

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, text: str) -> None:
        pass

    def show(self, text: str) -> None:
        self.shown.append(text)

    def state_changed(self, state: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass

    def call_later(self, seconds: float, callback: Callable[[], None]) -> _Handle:
        handle = _Handle(seconds, callback)
        self.pending.append(handle)
        return handle


class _Recognizer:
    def __init__(self, made: list[_Recognizer], *, fail: str = "") -> None:
        self.started = 0
        self.stopped = 0
        self.fail = fail
        made.append(self)

    def start(self, microphone: str) -> None:
        if self.fail:
            raise DictationStartError(self.fail)
        self.started += 1

    def stop(self) -> None:
        self.stopped += 1


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _controller(
    made: list[_Recognizer],
    *,
    gate: Any = None,
    feedback: _Feedback | None = None,
    fail: str = "",
    **preferences: Any,
) -> DictationController:
    preferences.setdefault("phrase_feedback", "silent")
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(made, fail=fail),
        document=_Document(),
        feedback=feedback or _Feedback(),
        preferences=lambda: DictationPreferences(**preferences),
        microphone=gate,
    )
    return controller


# -- the lock -------------------------------------------------------------------- #


def test_the_microphone_has_one_holder_and_its_note_names_it(tmp_path: Path) -> None:
    lite = MicrophoneLock("lite", folder=tmp_path, key="Ctrl+F11")
    transcribe = MicrophoneLock("transcribe", folder=tmp_path)
    assert microphone_holder(folder=tmp_path) is None
    assert lite.take() == ""
    assert microphone_holder(folder=tmp_path) == "lite"
    assert transcribe.take() == (
        "QUILL Lite is dictating. Press Ctrl+F11 in QUILL Lite to stop it, then try again."
    )
    lite.release()
    assert microphone_holder(folder=tmp_path) is None
    assert transcribe.take() == ""
    transcribe.release()


def test_the_microphone_lock_is_not_the_owner_lock(tmp_path: Path) -> None:
    """QUILL Transcribe holds the owner lock all the time it runs; the editors
    must still be able to dictate while it waits in the tray."""
    owner = OwnerLock("transcribe", folder=tmp_path)
    assert owner.claim()
    assert MicrophoneLock("quill", folder=tmp_path).take() == ""
    owner.release()


def test_a_note_left_behind_by_a_crash_holds_nothing(tmp_path: Path) -> None:
    (tmp_path / "dictation-microphone.json").write_text('{"app": "lite"}', encoding="utf-8")
    assert microphone_holder(folder=tmp_path) is None
    assert MicrophoneLock("quill", folder=tmp_path).take() == ""


def test_an_unknown_app_cannot_hold_the_microphone(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        MicrophoneLock("radio", folder=tmp_path)


@pytest.mark.parametrize(
    ("holder", "asker", "key", "where", "sentence"),
    [
        (
            "lite",
            "transcribe",
            "Ctrl+F11",
            "",
            "QUILL Lite is dictating. Press Ctrl+F11 in QUILL Lite to stop it, then try again.",
        ),
        (
            "quill",
            "lite",
            "Ctrl+F11",
            "",
            "QUILL is dictating. Press Ctrl+F11 in QUILL to stop it, then try again.",
        ),
        (
            "quill",
            "quill",
            "Ctrl+F9",
            "same",
            "QUILL is already dictating. Press Ctrl+F9 to stop it, then try again.",
        ),
        (
            "lite",
            "lite",
            "Ctrl+F11",
            "other",
            "QUILL Lite is dictating in another window. Press Ctrl+F11 there to stop it, "
            "then try again.",
        ),
        (
            "transcribe",
            "quill",
            "Alt+Shift+\\",
            "",
            "QUILL Transcribe is listening. Press Alt+Shift+Backslash to stop it, then try again.",
        ),
        (
            "transcribe",
            "lite",
            "",
            "",
            "QUILL Transcribe is listening. Stop it from its tray icon, then try again.",
        ),
        (
            "inkwell",
            "transcribe",
            "",
            "",
            "Quill Inkwell is dictating. Stop it there, then try again.",
        ),
        ("", "quill", "", "", "Another program is dictating. Stop it there, then try again."),
    ],
)
def test_each_refusal_names_who_is_listening_and_the_key_that_stops_it(
    holder: str, asker: str, key: str, where: str, sentence: str
) -> None:
    assert (
        busy_sentence(
            holder,
            asker=asker,
            key=key,
            same_process=where == "same",
            other_window=where == "other",
        )
        == sentence
    )


def test_the_holders_live_key_is_what_the_refusal_names(tmp_path: Path) -> None:
    """The key is asked at the moment the lock is taken, so a rebinding counts."""
    bound = {"key": "Ctrl+F11"}
    lite = MicrophoneLock("lite", folder=tmp_path, key=lambda: bound["key"])
    bound["key"] = "Ctrl+Alt+F11"
    assert lite.take() == ""
    assert MicrophoneLock("transcribe", folder=tmp_path).take() == (
        "QUILL Lite is dictating. Press Ctrl+Alt+F11 in QUILL Lite to stop it, then try again."
    )
    lite.release()


def test_every_app_that_can_listen_has_a_name() -> None:
    from quill.core.dictation_owner import MICROPHONE_APPS

    assert set(APP_NAMES) == set(MICROPHONE_APPS)


# -- the controller ---------------------------------------------------------------- #


def test_two_starts_give_one_owner_and_one_recognizer(tmp_path: Path) -> None:
    """Transcribe PRD 15.2: two clients start at once; one owner, one
    recogniser, and a clear response to the second."""
    made: list[_Recognizer] = []
    lite_feedback, transcribe_feedback = _Feedback(), _Feedback()
    lite = _controller(
        made, gate=MicrophoneLock("lite", folder=tmp_path, key="Ctrl+F11"), feedback=lite_feedback
    )
    transcribe = _controller(
        made,
        gate=MicrophoneLock("transcribe", folder=tmp_path),
        feedback=transcribe_feedback,
    )
    lite.start()
    transcribe.start()
    assert lite.active and not transcribe.active
    assert len(made) == 1 and made[0].started == 1
    assert microphone_holder(folder=tmp_path) == "lite"
    assert transcribe_feedback.said == [
        "QUILL Lite is dictating. Press Ctrl+F11 in QUILL Lite to stop it, then try again."
    ]
    assert Moment.ERROR in transcribe_feedback.cues
    lite.stop()
    transcribe.start()
    assert transcribe.active and len(made) == 2
    assert microphone_holder(folder=tmp_path) == "transcribe"
    transcribe.shut_down()


def test_stopping_lets_go_of_the_microphone(tmp_path: Path) -> None:
    made: list[_Recognizer] = []
    gate = MicrophoneLock("quill", folder=tmp_path)
    controller = _controller(made, gate=gate)
    controller.start()
    assert gate.held
    controller.stop()
    assert not gate.held and made[0].stopped == 1


def test_an_engine_that_fails_twice_lets_go_of_the_microphone(tmp_path: Path) -> None:
    made: list[_Recognizer] = []
    gate = MicrophoneLock("lite", folder=tmp_path)
    controller = _controller(made, gate=gate)
    controller.start()
    controller.on_failure("the engine stopped")  # restarted silently, once
    assert gate.held and controller.active
    controller.on_failure("the engine stopped")
    assert not controller.active and not gate.held


def test_a_recognizer_that_will_not_start_lets_go(tmp_path: Path) -> None:
    made: list[_Recognizer] = []
    gate = MicrophoneLock("lite", folder=tmp_path)
    controller = _controller(made, gate=gate, fail="No microphone.")
    controller.start()
    assert not controller.active and not gate.held


def test_closing_the_window_lets_go(tmp_path: Path) -> None:
    made: list[_Recognizer] = []
    gate = MicrophoneLock("quill", folder=tmp_path)
    controller = _controller(made, gate=gate)
    controller.start()
    controller.shut_down()
    assert not gate.held and microphone_holder(folder=tmp_path) is None


def test_the_wake_phrase_says_once_that_another_program_has_the_microphone(
    tmp_path: Path,
) -> None:
    """Arming for the wake phrase is not a key press, so a refusal there plays no
    error tone -- but the person switched the wake phrase on, and one that is
    silently not listened for reads as "it never hears me" (2026-10-26). Said
    once, shown every time; the next time the window comes forward it tries
    again."""
    held = MicrophoneLock("transcribe", folder=tmp_path)
    assert held.take() == ""
    made: list[_Recognizer] = []
    feedback = _Feedback()
    controller = _controller(
        made,
        gate=MicrophoneLock("lite", folder=tmp_path),
        feedback=feedback,
        wake_enabled=True,
    )
    controller.arm()
    assert not controller.standing_by and made == []
    assert len(feedback.said) == 1
    assert feedback.said[0].startswith("The wake phrase is not being listened for. ")
    assert "QUILL Transcribe" in feedback.said[0]
    assert Moment.ERROR not in feedback.cues
    controller.arm()  # the window came forward again: shown, not said again
    assert len(feedback.said) == 1 and len(feedback.shown) == 2
    held.release()
    controller.arm()
    assert controller.standing_by
    controller.disarm()


def test_without_a_gate_nothing_changes() -> None:
    made: list[_Recognizer] = []
    controller = _controller(made)
    controller.start()
    assert controller.active


# -- the working tick --------------------------------------------------------------- #


def _ticking(
    *, clip: bool = True, on: bool = True, heard: str = "sound"
) -> tuple[DictationController, _Feedback, _Clock]:
    made: list[_Recognizer] = []
    feedback = _Feedback(clip=clip)
    controller = _controller(
        made, feedback=feedback, working_tick=on, announce=False, phrase_feedback=heard
    )
    clock = _Clock()
    controller._clock = clock
    controller.start()
    feedback.cues.clear()
    return controller, feedback, clock


def _run_until(feedback: _Feedback, clock: _Clock, seconds: float) -> None:
    """Fire every scheduled callback whose time has come, up to *seconds* on."""
    end = clock.now + seconds
    while feedback.pending:
        handle = feedback.pending.pop(0)
        if handle.stopped:
            continue
        if clock.now + handle.seconds > end + 1e-9:
            feedback.pending.insert(0, handle)
            clock.now = end
            return
        clock.now += handle.seconds
        handle.callback()
    clock.now = end


def _hear(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text)))


def test_no_tick_when_the_phrase_arrives_within_a_second() -> None:
    controller, feedback, clock = _ticking()
    controller.on_speech_started()
    controller.on_phrase_decoding()
    clock.now += 0.6
    _hear(controller, "quick")
    assert all(handle.stopped for handle in feedback.pending)
    _run_until(feedback, clock, 5)
    assert Moment.WORKING not in feedback.cues and STILL_WORKING not in feedback.said


def test_a_slow_phrase_ticks_once_a_second_until_the_text_arrives() -> None:
    controller, feedback, clock = _ticking()
    controller.on_speech_started()
    controller.on_phrase_decoding()
    _run_until(feedback, clock, 3.5)
    assert feedback.cues.count(Moment.WORKING) == 3  # at 1, 2 and 3 seconds
    assert STILL_WORKING not in feedback.said
    _hear(controller, "at last")
    _run_until(feedback, clock, 5)
    assert feedback.cues.count(Moment.WORKING) == 3


def test_after_four_seconds_it_says_so_once_a_session() -> None:
    controller, feedback, clock = _ticking()
    controller.on_speech_started()
    controller.on_phrase_decoding()
    _run_until(feedback, clock, 6.5)
    assert feedback.said.count(STILL_WORKING) == 1
    _hear(controller, "one")
    controller.on_speech_started()
    controller.on_phrase_decoding()
    _run_until(feedback, clock, 6.5)
    assert feedback.said.count(STILL_WORKING) == 1  # the second long wait only ticks
    _hear(controller, "two")
    controller.stop()
    controller.start()
    controller.on_speech_started()
    controller.on_phrase_decoding()
    _run_until(feedback, clock, 4.5)
    assert feedback.said.count(STILL_WORKING) == 2  # a new session explains it again


def test_stopping_or_failing_ends_the_tick() -> None:
    controller, feedback, clock = _ticking()
    controller.on_speech_started()
    controller.on_phrase_decoding()
    _run_until(feedback, clock, 1.5)
    assert feedback.cues.count(Moment.WORKING) == 1
    controller.stop()
    _run_until(feedback, clock, 5)
    assert feedback.cues.count(Moment.WORKING) == 1
    controller.start()
    controller.on_speech_started()
    controller.on_phrase_decoding()
    controller.on_failure("gone")  # restarted silently: the wait it was in is over
    _run_until(feedback, clock, 5)
    assert feedback.cues.count(Moment.WORKING) == 1


def test_the_setting_off_means_silence() -> None:
    controller, feedback, clock = _ticking(on=False)
    controller.on_speech_started()
    controller.on_phrase_decoding()
    _run_until(feedback, clock, 6)
    assert Moment.WORKING not in feedback.cues and STILL_WORKING not in feedback.said


def _two_slow_waits(controller: DictationController, feedback: _Feedback, clock: _Clock) -> None:
    for word in ("one", "two"):
        controller.on_speech_started()
        controller.on_phrase_decoding()
        _run_until(feedback, clock, 6)
        _hear(controller, word)


def test_with_no_tick_in_the_pack_it_speaks_at_four_seconds_each_wait() -> None:
    """A sound moment with no clip speaks: at four seconds, once per wait, and
    never a word a second (A2)."""
    controller, feedback, clock = _ticking(clip=False)
    controller.on_speech_started()
    controller.on_phrase_decoding()
    _run_until(feedback, clock, 3.5)
    assert feedback.said.count(STILL_WORKING) == 0
    _run_until(feedback, clock, 4.5)
    assert feedback.said.count(STILL_WORKING) == 1
    _hear(controller, "one")
    controller.on_speech_started()
    controller.on_phrase_decoding()
    _run_until(feedback, clock, 6)
    assert feedback.said.count(STILL_WORKING) == 2
    assert Moment.WORKING not in feedback.cues


@pytest.mark.parametrize("heard", ["sound", "both"])
def test_sound_and_both_tick(heard: str) -> None:
    controller, feedback, clock = _ticking(heard=heard)
    _two_slow_waits(controller, feedback, clock)
    assert feedback.cues.count(Moment.WORKING) >= 8
    assert feedback.said.count(STILL_WORKING) == 1  # once a session, with the tick


def test_words_only_means_no_tick_and_the_sentence_each_wait() -> None:
    """phrase_feedback is the cap (A1): speech only never gets a sound."""
    controller, feedback, clock = _ticking(heard="speech")
    _two_slow_waits(controller, feedback, clock)
    assert Moment.WORKING not in feedback.cues
    assert feedback.said.count(STILL_WORKING) == 2


def test_silent_phrase_feedback_means_silence_even_with_the_tick_on() -> None:
    controller, feedback, clock = _ticking(heard="silent")
    _two_slow_waits(controller, feedback, clock)
    assert Moment.WORKING not in feedback.cues and STILL_WORKING not in feedback.said


def test_text_arriving_before_four_seconds_drops_the_sentence() -> None:
    """A3: the sentence is never said once its wait is over."""
    controller, feedback, clock = _ticking(heard="speech")
    controller.on_speech_started()
    controller.on_phrase_decoding()
    _run_until(feedback, clock, 3.9)
    _hear(controller, "in time")
    _run_until(feedback, clock, 5)
    assert STILL_WORKING not in feedback.said


def test_a_phrase_decoded_while_dictation_is_off_never_ticks() -> None:
    controller, feedback, clock = _ticking()
    controller.stop()
    controller.on_phrase_decoding()
    assert feedback.pending == [] or all(handle.stopped for handle in feedback.pending)
    _run_until(feedback, clock, 5)
    assert Moment.WORKING not in feedback.cues


def test_a_host_without_a_clock_gets_no_tick() -> None:
    class _NoClock(_Feedback):
        call_later = None  # type: ignore[assignment]

    made: list[_Recognizer] = []
    feedback = _NoClock()
    controller = _controller(made, feedback=feedback, working_tick=True)
    controller.start()
    controller.on_speech_started()
    controller.on_phrase_decoding()
    assert Moment.WORKING not in feedback.cues
    assert controller.state is DictationState.RECOGNIZING
