"""Replace, change, delete by paragraph, a second opinion, kept revisions (D-19),
and correcting in another program on the session's own words (D-10).

Against the shared controller with fakes only: an editor-like document, and the
external document QUILL Transcribe and Inkwell type through, whose injector and
focus are stand-ins. The external document has no way to read the other
program at all -- it is handed a typist, a backspacer and a focus identity --
so every edit here is proved to be made from what dictation itself typed.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Any

import pytest

from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.anywhere import EXTERNAL_COMMANDS
from quill.core.windows_dictation.corrections import (
    BEFORE_CORRECTION,
    fit_to,
    keep_revision,
    phrase_from_entry,
    previous_paragraph_start,
    second_engine,
    split_replacement,
)
from quill.core.windows_dictation.external_edits import (
    EXTERNAL_EDIT_COMMANDS,
    MOVED_SINCE,
    TYPED_SINCE,
    OwnWordsGuard,
    autocorrect_refusal,
    edit_problem,
)
from quill.core.windows_dictation.parser import parse
from quill.core.windows_dictation.reference import commands_reference
from quill.core.windows_dictation.target_lock import LockedTarget
from quill.core.windows_dictation.vocabulary_types import Command
from quill.ui.windows_dictation_external import ExternalDocument

# -- the stand-ins --------------------------------------------------------------- #


class _Document:
    """An editor's text control: the caret can be put anywhere."""

    def __init__(self, text: str = "") -> None:
        self.text = text
        self.caret = len(text)

    def unavailable_reason(self, *, writing: bool) -> str:
        return ""

    def context(self) -> tuple[str, str]:
        return self.text[: self.caret], self.text[self.caret :]

    def selection(self) -> tuple[int, int]:
        return self.caret, self.caret

    def select(self, start: int, end: int) -> None:
        self.caret = end

    def insert(self, text: str) -> tuple[int, int]:
        start = self.caret
        self.text = self.text[:start] + text + self.text[start:]
        self.caret = start + len(text)
        return start, self.caret

    def text_between(self, start: int, end: int) -> str:
        return self.text[max(0, start) : end]

    def remove(self, start: int, end: int) -> None:
        self.text = self.text[:start] + self.text[end:]
        self.caret = start

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        self.text = self.text[:start] + text + self.text[end:]
        self.caret = start + len(text)
        return start, start + len(text)

    def line_bounds(self) -> tuple[int, int]:
        return 0, len(self.text)

    def last_position(self) -> int:
        return len(self.text)

    def undo(self) -> bool:
        return False


class _Feedback:
    def __init__(self) -> None:
        self.said: list[str] = []

    def has_cue(self, moment: Any) -> bool:
        return False

    def cue(self, moment: Any) -> None:
        pass

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, text: str) -> None:
        pass

    def show(self, text: str) -> None:
        pass

    def state_changed(self, state: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass


class _Recognizer:
    def __init__(self) -> None:
        self.asked: list[tuple[Any, str, Callable[[str], None]]] = []

    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass

    def second_opinion(self, samples: Any, engine: str, done: Callable[[str], None]) -> None:
        self.asked.append((samples, engine, done))


def _controller(
    document: Any, recognizer: _Recognizer | None = None, **preferences: Any
) -> tuple[DictationController, _Feedback]:
    feedback = _Feedback()
    settings = DictationPreferences(phrase_feedback="silent", announce=False, **preferences)
    controller = DictationController(
        recognizer=lambda _c, _p: recognizer or _Recognizer(),
        document=document,
        feedback=feedback,
        preferences=lambda: settings,
    )
    controller.start()
    feedback.said.clear()
    return controller, feedback


def _say(controller: DictationController, text: str, audio: Any = None) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text), text=text, audio=audio))


# -- the grammar ----------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("said", "command"),
    [
        ("replace Tuesday with Wednesday", Command.REPLACE_WORDS),
        ("change that to see you Friday", Command.CHANGE_THAT),
        ("delete previous paragraph", Command.DELETE_PARAGRAPH),
        ("delete last paragraph", Command.DELETE_PARAGRAPH),
        ("delete that", Command.SCRATCH),
    ],
)
def test_the_phrases_are_in_the_one_table(said: str, command: Command) -> None:
    assert parse(RecognizedPhrase(words_from_text(said))).command is command


def test_split_replacement_finds_the_words_and_the_new_text() -> None:
    parsed = parse(RecognizedPhrase(words_from_text("replace the cat with the big dog")))
    assert split_replacement(parsed) == (("the", "cat"), "the big dog")
    parsed = parse(RecognizedPhrase(words_from_text("replace the battery soon")))
    assert split_replacement(parsed) is None
    parsed = parse(RecognizedPhrase(words_from_text("replace it with")))
    assert split_replacement(parsed) is None


def test_fit_to_keeps_the_capital_and_the_closing_mark() -> None:
    assert fit_to("see you friday", "See you Thursday.") == "See you friday."
    assert fit_to("Wednesday.", "Tuesday") == "Wednesday"
    assert fit_to("wednesday", "tuesday") == "wednesday"


def test_previous_paragraph_start() -> None:
    assert previous_paragraph_start("One.\n\nTwo three.") == len("One.")
    assert previous_paragraph_start("One.\n\nTwo.\n\n") == len("One.")
    assert previous_paragraph_start("Only one.") == 0


def test_revisions_are_labelled_and_the_label_is_never_inserted() -> None:
    recent: deque[str] = deque(["See you Thursday."], maxlen=20)
    keep_revision(recent, " See you Thursday.", " See you Friday.")
    assert list(recent) == ["See you Friday.", f"See you Thursday. ({BEFORE_CORRECTION})"]
    assert phrase_from_entry(recent[1]) == "See you Thursday."
    assert phrase_from_entry("Plain words") == "Plain words"


def test_the_second_engine_is_the_other_built_in_one() -> None:
    assert second_engine("moonshine", "en") == "whisper"
    assert second_engine("whisper", "en") == "moonshine"
    assert second_engine("windows", "en") == ""
    assert second_engine("whisper", "es") == ""


# -- in QUILL's own documents ------------------------------------------------------------ #


def test_replace_x_with_y_finds_the_nearest_before_the_cursor() -> None:
    document = _Document("Meet on Tuesday. Not Tuesday next week.")
    document.caret = len("Meet on Tuesday.")
    controller, feedback = _controller(document)
    _say(controller, "replace Tuesday with Wednesday")
    assert document.text == "Meet on Wednesday. Not Tuesday next week."
    assert document.caret == len("Meet on Wednesday.")
    assert feedback.said[-1] == "Replaced Tuesday with Wednesday."
    assert f"Tuesday ({BEFORE_CORRECTION})" in controller.recent


def test_replace_inside_the_last_phrase_keeps_scratch_that_right() -> None:
    document = _Document()
    controller, _feedback = _controller(document)
    _say(controller, "see you on Tuesday")
    _say(controller, "replace Tuesday with Wednesday")
    assert document.text == "See you on Wednesday"
    assert controller.recent[0] == "See you on Wednesday"
    assert controller.recent[1] == f"See you on Tuesday ({BEFORE_CORRECTION})"
    _say(controller, "scratch that")
    assert document.text == ""


def test_replace_not_found_is_written_bare_and_nothing_after_the_word() -> None:
    document = _Document("Hello.")
    controller, feedback = _controller(document)
    _say(controller, "replace the filter with a new one")
    assert "filter" in document.text and "Not found, written as text." in feedback.said
    document = _Document("Hello.")
    controller, feedback = _controller(document)
    _say(controller, "quill replace the filter with a new one")
    assert document.text == "Hello." and feedback.said[-1] == "Not found."


def test_strict_mode_writes_a_bare_replace_and_the_command_word_runs_it() -> None:
    document = _Document("Meet on Tuesday.")
    controller, _feedback = _controller(document, command_prefix_required=True)
    _say(controller, "replace Tuesday with Wednesday")
    assert "Tuesday." in document.text and "Replace" in document.text
    document = _Document("Meet on Tuesday.")
    controller, _feedback = _controller(document, command_prefix_required=True)
    _say(controller, "quill replace Tuesday with Wednesday")
    assert document.text == "Meet on Wednesday."


def test_change_that_to_replaces_the_last_phrase_and_keeps_the_original() -> None:
    document = _Document()
    controller, feedback = _controller(document)
    _say(controller, "see you Thursday.")
    _say(controller, "quill change that to see you Friday")
    assert document.text == "See you Friday."
    assert feedback.said[-1] == "Changed to: See you Friday."
    assert controller.recent[1] == f"See you Thursday. ({BEFORE_CORRECTION})"


def test_delete_previous_paragraph() -> None:
    document = _Document("First one.\n\nSecond one is long.")
    controller, feedback = _controller(document)
    _say(controller, "delete previous paragraph")
    assert document.text == "First one."
    assert feedback.said[-1].startswith("Deleted the paragraph:")
    _say(controller, "delete last paragraph")
    assert document.text == ""
    _say(controller, "delete previous paragraph")
    assert feedback.said[-1] == "No paragraph before the cursor."


# -- a second opinion and kept revisions ----------------------------------------------------- #


def test_correct_that_asks_the_other_engine_and_choose_two_takes_it() -> None:
    document = _Document()
    recognizer = _Recognizer()
    controller, feedback = _controller(document, recognizer)
    _say(controller, "the whether is nice", audio="samples")
    _say(controller, "quill correct that")
    assert feedback.said[-1] == "Listening again with Whisper."
    samples, engine, done = recognizer.asked[0]
    assert (samples, engine) == ("samples", "whisper")
    done("The weather is nice")
    assert feedback.said[-1] == (
        "1: The whether is nice. 2: The weather is nice. Say choose and the number."
    )
    _say(controller, "choose two")
    assert document.text == "The weather is nice"
    assert controller.recent[1] == f"The whether is nice ({BEFORE_CORRECTION})"


def test_a_late_second_opinion_about_an_older_phrase_is_dropped() -> None:
    document = _Document()
    recognizer = _Recognizer()
    controller, feedback = _controller(document, recognizer)
    _say(controller, "first phrase", audio="one")
    _say(controller, "correct that")
    _say(controller, "second phrase", audio="two")
    said = list(feedback.said)
    recognizer.asked[0][2]("something else")
    assert feedback.said == said


def test_the_same_answer_is_said_and_nothing_is_offered() -> None:
    document = _Document()
    recognizer = _Recognizer()
    controller, feedback = _controller(document, recognizer)
    _say(controller, "hello there", audio="a")
    _say(controller, "correct that")
    recognizer.asked[0][2]("Hello there.")
    assert feedback.said[-1].startswith("The other engine heard the same: Hello there.")


def test_without_audio_correct_that_says_the_engine_gives_one_answer() -> None:
    controller, feedback = _controller(_Document())
    _say(controller, "hello there")
    _say(controller, "correct that")
    assert "one answer" in feedback.said[-1]


# -- in another program, on the session's own words (D-10) -------------------------------------- #


class _Typist:
    """The keystroke path: what was typed and erased. There is no read."""

    def __init__(self) -> None:
        self.typed: list[str] = []
        self.erased: list[int] = []

    def type_text(self, text: str, *_args: Any) -> bool:
        self.typed.append(text)
        return True

    def backspace(self, count: int) -> bool:
        self.erased.append(count)
        return True


def _external(
    *,
    where: Callable[[], Any] = lambda: ("notepad", 1, "edit"),
    last_input: Callable[[], int | None] | None = None,
    program: str = "notepad.exe",
    **preferences: Any,
) -> tuple[DictationController, _Typist, _Feedback]:
    typist = _Typist()
    document = ExternalDocument(
        problem=lambda: "",
        where=where,
        type_text=typist.type_text,
        backspace=typist.backspace,
        last_input=last_input,
        program=lambda: program,
    )
    controller, feedback = _controller(document, **preferences)
    return controller, typist, feedback


def test_every_edit_command_is_let_through_in_another_program() -> None:
    assert EXTERNAL_EDIT_COMMANDS - {Command.SCRATCH} <= EXTERNAL_COMMANDS
    listed = commands_reference(external=True)
    for phrase in ('"replace ..."', '"change that to ..."', '"delete previous paragraph"'):
        assert phrase in listed


def test_replace_in_another_program_retypes_from_the_words_on() -> None:
    controller, typist, feedback = _external()
    _say(controller, "see you on Tuesday at noon")
    _say(controller, "quill replace Tuesday with Wednesday")
    assert typist.erased == [len("Tuesday at noon")]
    assert typist.typed[-1] == "Wednesday at noon"
    assert feedback.said[-1] == "Replaced Tuesday with Wednesday."


def test_replace_in_another_program_looks_only_in_the_last_phrase() -> None:
    controller, typist, feedback = _external()
    _say(controller, "Tuesday is fine")
    _say(controller, "see you then")
    _say(controller, "quill replace Tuesday with Wednesday")
    assert typist.erased == [] and feedback.said[-1] == "Not found."


def test_caps_change_and_delete_work_on_own_words() -> None:
    controller, typist, _feedback = _external()
    _say(controller, "dear sam")
    _say(controller, "quill uppercase that")
    assert typist.erased == [len("Dear sam")] and typist.typed[-1] == "DEAR SAM"
    _say(controller, "quill change that to dear Sally")
    assert typist.typed[-1] == "ear Sally"  # retyped only from where it differs
    _say(controller, "next sentence. And another")
    _say(controller, "quill delete last sentence")
    assert typist.erased[-1] == len(" And another")


def test_an_edit_after_the_focus_moved_is_refused_and_nothing_is_sent() -> None:
    place = {"field": ("notepad", 1, "edit")}
    controller, typist, feedback = _external(where=lambda: place["field"])
    _say(controller, "hello there")
    place["field"] = ("word", 2, "doc")
    for said in ("quill uppercase that", "quill change that to hi", "quill scratch that"):
        _say(controller, said)
        assert feedback.said[-1] == MOVED_SINCE
    assert typist.erased == []


def test_an_edit_after_the_person_typed_is_refused() -> None:
    clock = {"tick": 1000}
    controller, typist, feedback = _external(last_input=lambda: clock["tick"])
    _say(controller, "hello there")
    clock["tick"] += 5000  # a key, five seconds later
    _say(controller, "quill replace there with world")
    assert feedback.said[-1] == TYPED_SINCE and typist.erased == []


def test_word_refuses_retyping_but_scratch_still_works() -> None:
    controller, typist, feedback = _external(program="WINWORD.EXE")
    _say(controller, "hello there")
    _say(controller, "quill capitalize that")
    assert feedback.said[-1] == autocorrect_refusal("winword.exe") and typist.erased == []
    _say(controller, "quill scratch that")
    assert typist.erased == [len("Hello there")]


def test_the_field_lock_refuses_an_edit_in_another_field() -> None:
    typist = _Typist()
    inner = ExternalDocument(problem=lambda: "", where=lambda: 1, type_text=typist.type_text)
    place = {"now": 1}
    locked = LockedTarget(inner, where=lambda: place["now"])
    assert locked.relock() == ""
    locked.insert("Hello")
    assert locked.edit_problem(Command.CHANGE_THAT) == ""
    place["now"] = 2
    assert locked.edit_problem(Command.CHANGE_THAT) == MOVED_SINCE


def test_the_rules_alone() -> None:
    assert edit_problem(moved=False, typed=False, program="notepad.exe") == ""
    assert edit_problem(moved=True, typed=True) == MOVED_SINCE
    assert edit_problem(moved=False, typed=True) == TYPED_SINCE
    assert edit_problem(moved=False, typed=False, program="outlook.exe") == ""  # scratch
    assert "Outlook" in edit_problem(
        moved=False, typed=False, program="outlook.exe", command=Command.CHOOSE_2
    )
    ticks = iter([100, 250, 900])
    guard = OwnWordsGuard(lambda: next(ticks))
    assert guard.typed_since() is False  # nothing typed by dictation yet
    guard.wrote()  # 100
    assert guard.typed_since() is False  # 250: dictation's own keys settling
    assert guard.typed_since() is True  # 900: somebody else's
    assert OwnWordsGuard(lambda: None).typed_since() is False


def test_correct_that_and_choose_retype_only_the_phrase_in_another_program() -> None:
    controller, typist, feedback = _external(engine="windows")
    _say(controller, "Dear Sam, ")
    phrase = RecognizedPhrase(
        words_from_text("the whether is nice"),
        text="the whether is nice",
        alternatives=("the weather is nice", "the feather is nice"),
    )
    controller.on_phrase(phrase)
    assert typist.typed == ["Dear Sam,", " the whether is nice"]
    _say(controller, "quill correct that")
    assert feedback.said[-1].startswith("1: the weather is nice.")
    _say(controller, "quill choose one")
    # Only the last phrase is taken back and retyped: never the words before it.
    assert typist.erased == [len(" the whether is nice")]
    assert typist.typed[-1] == " the weather is nice"
    assert controller.recent[1] == f"the whether is nice ({BEFORE_CORRECTION})"


def test_outlook_refuses_choose_and_caps_but_deletes_still_work() -> None:
    controller, typist, feedback = _external(program="OUTLOOK.EXE")
    _say(controller, "first sentence. second one")
    for said in ("quill uppercase that", "quill lowercase that", "quill choose two"):
        _say(controller, said)
        assert feedback.said[-1] == autocorrect_refusal("outlook.exe")
    assert typist.erased == []
    _say(controller, "quill delete last sentence")
    assert typist.erased == [len(" Second one")]


def test_the_worker_decodes_again_on_its_own_thread_and_posts_the_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import threading

    from quill.core.windows_dictation import recognizer_worker

    calls: list[tuple[str, Any, str]] = []

    class _Engines:
        def transcribe(self, engine: str, samples: Any, language: str) -> str:
            calls.append((engine, samples, language))
            if samples == "bad":
                raise RuntimeError("the model would not load")
            return "the weather is nice"

    monkeypatch.setattr(recognizer_worker, "_lr", lambda: _Engines())
    answers: list[str] = []
    done = threading.Event()

    class _Worker(recognizer_worker.WorkerMixin):
        _language = "en"

        def _post(self, function: Callable[..., None], *args: Any) -> None:
            function(*args)
            done.set()

    worker = _Worker()
    worker.second_opinion("samples", "whisper", answers.append)
    assert done.wait(5)
    assert answers == ["the weather is nice"]
    assert calls == [("whisper", "samples", "en")]
    done.clear()
    worker.second_opinion("bad", "whisper", answers.append)
    assert done.wait(5)
    assert answers[-1] == ""  # no second opinion is an answer too
