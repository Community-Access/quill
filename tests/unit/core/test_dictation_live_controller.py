"""The controller's live half (live.py): preview, late punctuation, where the
words go, finishing, muting, "correct that", and the engines' notices."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from quill.core.windows_dictation.controller import DictationController, DictationState
from quill.core.windows_dictation.parser import RecognizedPhrase, words_from_text
from quill.core.windows_dictation.preferences import DictationPreferences


class Doc:
    """A text document with an anchor, like windows_dictation_ports.EditorDocument."""

    def __init__(self, text: str = "") -> None:
        self.text = text
        self.sel = (len(text), len(text))
        self.focused = True
        self.anchors: list[Any] = []

    def unavailable_reason(self, *, writing: bool) -> str:
        return "" if self.focused or not writing else "no focus"

    def anchored_reason(self, _anchor: Any) -> str:
        return ""

    def anchor(self) -> tuple[int, int]:
        return self.sel

    def place_at_anchor(self, anchor: tuple[int, int]) -> str:
        if self.sel == anchor and self.focused:
            return ""
        self.anchors.append(self.sel)
        self.sel = anchor
        return "Written where you started, in Notes."

    def release_anchor(self, anchor: tuple[int, int]) -> None:
        saved = self.anchors.pop()
        shift = self.sel[1] - anchor[1]
        self.sel = (saved[0] + shift, saved[1] + shift) if saved[0] >= anchor[1] else saved

    def context(self) -> tuple[str, str]:
        return self.text[: self.sel[0]][-80:], self.text[self.sel[1] : self.sel[1] + 2]

    def selection(self) -> tuple[int, int]:
        return self.sel

    def select(self, start: int, end: int) -> None:
        self.sel = (start, end)

    def insert(self, text: str) -> tuple[int, int]:
        return self.replace(*self.sel, text)

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        self.text = self.text[:start] + text + self.text[end:]
        self.sel = (start + len(text), start + len(text))
        return start, start + len(text)

    def text_between(self, start: int, end: int) -> str:
        return self.text[max(0, start) : end]

    def remove(self, start: int, end: int) -> None:
        self.text = self.text[:start] + self.text[end:]
        self.sel = (start, start)

    def line_bounds(self) -> tuple[int, int]:
        return 0, len(self.text)

    def last_position(self) -> int:
        return len(self.text)

    def undo(self) -> bool:
        return False


class Feedback:
    def __init__(self) -> None:
        self.said: list[str] = []
        self.quiet: list[str] = []
        self.previews: list[str] = []
        self.shown: list[str] = []
        self.written: list[str] = []

    def has_cue(self, _moment: Any) -> bool:
        return False

    def cue(self, _moment: Any) -> None:
        pass

    def say(self, text: str) -> None:
        self.said.append(text)

    def say_quietly(self, text: str) -> None:
        self.quiet.append(text)

    def read_back(self, text: str) -> None:
        pass

    def show(self, text: str) -> None:
        self.shown.append(text)

    def preview(self, text: str) -> None:
        self.previews.append(text)

    def phrase_written(self, text: str) -> None:
        self.written.append(text)

    def state_changed(self, _state: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass


class Recognizer:
    def __init__(self) -> None:
        self.finishing = 0
        self.discarded = 0
        self.stopped = 0

    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        self.stopped += 1

    def finish(self) -> None:
        self.finishing += 1

    def discard(self) -> None:
        self.discarded += 1


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _controller(doc: Doc | None = None, **preferences: Any):
    doc = doc or Doc()
    feedback = Feedback()
    recognizer = Recognizer()
    prefs = DictationPreferences(
        phrase_feedback="silent", cue_sounds=False, announce=False, **preferences
    )
    holder = {"prefs": prefs}
    controller = DictationController(
        recognizer=lambda _c, _p: recognizer,
        document=doc,
        feedback=feedback,
        preferences=lambda: holder["prefs"],
    )
    clock = Clock()
    controller._init_live(clock)
    controller.start()
    return controller, doc, feedback, recognizer, clock, holder


def _hear(controller: DictationController, text: str, **fields: Any) -> None:
    controller.on_speech_started()
    controller.on_phrase(RecognizedPhrase(words_from_text(text), text=text, **fields))


def test_the_preview_is_shown_never_written_and_cleared_by_the_phrase() -> None:
    controller, doc, feedback, _r, clock, _h = _controller()
    controller.on_speech_started()
    controller.on_partial("can you")
    clock.now += 1
    controller.on_partial("can you send")
    assert feedback.previews == ["can you", "can you send"]
    assert doc.text == ""  # provisional words never reach the document
    controller.on_phrase(RecognizedPhrase(words_from_text("Can you send it?"), text="x"))
    assert feedback.previews[-1] == ""
    assert doc.text == "Can you send it?"


def test_the_preview_can_be_spoken_quietly_or_switched_off() -> None:
    controller, _d, feedback, _r, _c, holder = _controller(preview="speak")
    controller.on_speech_started()
    controller.on_partial("hello there")
    assert feedback.quiet == ["hello there"]
    holder["prefs"] = replace(holder["prefs"], preview="off")
    controller.on_partial("hello there friend")
    assert feedback.previews == ["hello there"]


def test_a_late_question_mark_corrects_the_last_phrase() -> None:
    controller, doc, _f, _r, _c, _h = _controller(engine="nemotron")
    _hear(controller, "Can you send it.")
    _hear(controller, "The meeting moved.", previous_mark="?")
    assert doc.text == "Can you send it? The meeting moved."


def test_a_confirmed_full_stop_is_not_taken_back_by_a_continuation_word() -> None:
    controller, doc, _f, _r, _c, _h = _controller(engine="nemotron")
    _hear(controller, "It moved to Thursday.")
    _hear(controller, "Where did you put the keys?", previous_mark=".")
    assert doc.text == "It moved to Thursday. Where did you put the keys?"


def test_a_phrase_still_goes_where_you_started_after_the_caret_moved() -> None:
    doc = Doc("Start. End.")
    doc.sel = (6, 6)
    controller, doc, feedback, _r, _c, _h = _controller(doc)
    controller.on_speech_started()
    doc.sel = (11, 11)  # the person arrowed to the end while it was recognised
    controller.on_phrase(RecognizedPhrase(words_from_text("middle"), text="middle"))
    assert doc.text == "Start. Middle End."
    assert doc.sel == (18, 18)  # their caret, moved along by what was written
    assert "Written where you started, in Notes." in feedback.said


def test_a_phrase_started_here_is_written_here_after_the_focus_left() -> None:
    controller, doc, feedback, _r, _c, _h = _controller(Doc("Dear Sam"))
    controller.on_speech_started()
    doc.focused = False
    controller.on_phrase(RecognizedPhrase(words_from_text("comma"), text="comma"))
    assert doc.text == "Dear Sam,"
    assert controller.active
    assert any("where you started" in line for line in feedback.said)


def test_stopping_while_speaking_waits_for_the_last_phrase() -> None:
    controller, doc, _f, recognizer, _c, _h = _controller()
    controller.on_speech_started()
    controller.toggle()
    assert recognizer.finishing == 1 and controller.active and controller.finishing
    controller.on_phrase(RecognizedPhrase(words_from_text("last words"), text="x"))
    controller.on_finished()
    assert doc.text == "Last words" and not controller.active
    assert recognizer.stopped == 1


def test_stopping_in_silence_stops_at_once() -> None:
    controller, _d, _f, recognizer, _c, _h = _controller()
    controller.toggle()
    assert recognizer.finishing == 0 and not controller.active


def test_a_recogniser_that_never_finishes_is_stopped_anyway() -> None:
    controller, _d, _f, _r, clock, _h = _controller()
    controller.on_speech_started()
    controller.finish()
    controller.finish_overdue()
    assert controller.active
    clock.now += 10
    controller.finish_overdue()
    assert not controller.active


def test_muted_while_the_reply_is_read_then_listening_again() -> None:
    controller, doc, _f, recognizer, clock, _h = _controller()
    controller.mute_for(5.0)
    assert controller.muted and recognizer.discarded == 1
    _hear(controller, "the reply read back by the speakers")
    assert doc.text == ""
    clock.now += 6
    _hear(controller, "my next question")
    assert doc.text == "My next question"


def test_correct_that_reads_the_guesses_and_choose_swaps_one() -> None:
    controller, doc, feedback, _r, _c, _h = _controller(engine="windows")
    _hear(controller, "write to Ann", alternatives=("right to Ann", "write two Ann"))
    _hear(controller, "correct that")
    assert feedback.said[-1].startswith("1: right to Ann. 2: write two Ann.")
    _hear(controller, "choose one")
    assert doc.text == "right to Ann"
    assert feedback.said[-1] == "Changed to: right to Ann"


def test_correct_that_says_plainly_when_the_engine_has_no_guesses() -> None:
    controller, _d, feedback, _r, _c, _h = _controller()
    _hear(controller, "hello")
    _hear(controller, "correct that")
    assert "only Windows speech recognition offers other guesses" in feedback.said[-1]


def test_a_written_phrase_is_reported_for_talking_to_the_ai() -> None:
    controller, _d, feedback, _r, _c, _h = _controller()
    _hear(controller, "what is the weather")
    assert feedback.written == ["What is the weather"]


def test_engine_notices_are_said_and_fatal_problems_stop() -> None:
    controller, _d, feedback, _r, _c, _h = _controller()
    controller.on_engine_notice("This computer is busy.")
    assert feedback.said[-1] == "This computer is busy."
    controller.on_engine_problem("OpenAI could not be reached.", False)
    assert controller.active
    controller.on_engine_problem("The OpenAI model is no longer available.", True)
    assert not controller.active
    assert controller.state is DictationState.OFF
