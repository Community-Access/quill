"""Windows Dictation's wx-free half: parsing, spacing, transactions, states."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.windows_dictation import (
    Command,
    DictationController,
    DictationPreferences,
    DictationState,
    Moment,
    RecognizedPhrase,
    RecognizedWord,
    compose,
    parse,
    words_from_text,
)
from quill.core.windows_dictation.controller import DictationStartError


def _text(spoken: str, before: str = "", after: str = "") -> str:
    parsed = parse(RecognizedPhrase(words_from_text(spoken)))
    assert parsed.command is None
    return compose(parsed.pieces, before=before, after=after)


# -- parsing ---------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("spoken", "expected"),
    [
        ("hello comma world period", "Hello, world."),
        ("is it question mark", "Is it?"),
        ("wow exclamation point", "Wow!"),
        ("wow exclamation mark", "Wow!"),
        ("note colon two things semicolon done", "Note: two things; done"),
        ("she said open quote hi close quote", 'She said "hi"'),
        ("see open parenthesis below close parenthesis", "See (below)"),
        ("item open bracket one close bracket", "Item [one]"),
        ("well hyphen known", "Well-known"),
        ("first line new line second line", "First line\nSecond line"),
        ("end period new paragraph start", "End.\n\nStart"),
        ("tab indented", "\tIndented"),
    ],
)
def test_spoken_punctuation_becomes_text(spoken: str, expected: str) -> None:
    assert _text(spoken) == expected


def test_the_recognisers_own_rendering_is_matched_by_what_was_said() -> None:
    """Windows reports "period" as "." and "new paragraph" as one joined word."""
    words = (
        RecognizedWord("hello", "hello"),
        RecognizedWord("period", "."),
        RecognizedWord("new-paragraph", "new-paragraph"),
        RecognizedWord("welcome", "welcome"),
    )
    parsed = parse(RecognizedPhrase(words))
    assert compose(parsed.pieces) == "Hello.\n\nWelcome"


def test_a_proper_noun_keeps_the_recognisers_capital() -> None:
    words = (
        RecognizedWord("i", "I"),
        RecognizedWord("use", "use"),
        RecognizedWord("windows", "Windows"),
    )
    assert compose(parse(RecognizedPhrase(words)).pieces) == "I use Windows"


def test_a_joined_word_that_is_not_a_command_stays_one_word() -> None:
    words = (RecognizedWord("well-known", "well-known"),)
    assert compose(parse(RecognizedPhrase(words)).pieces, before="a ") == "well-known"


@pytest.mark.parametrize(
    ("spoken", "command"),
    [
        ("scratch that", Command.SCRATCH),
        ("delete that", Command.SCRATCH),
        ("Scratch that.", Command.SCRATCH),
        ("undo that", Command.UNDO),
        ("stop dictation", Command.STOP),
    ],
)
def test_a_whole_phrase_command_is_a_command(spoken: str, command: Command) -> None:
    assert parse(RecognizedPhrase(words_from_text(spoken))).command is command


def test_a_command_inside_a_sentence_is_words() -> None:
    assert _text("delete that line of text") == "Delete that line of text"


def test_literal_writes_the_command_word_itself() -> None:
    assert _text("literal new line of products") == "New line of products"
    assert _text("the literal comma", before="x") == " the comma"
    assert parse(RecognizedPhrase(words_from_text("literal scratch that"))).command is None


def test_literal_before_an_ordinary_word_is_itself_a_word() -> None:
    assert _text("a literal translation") == "A literal translation"


def test_literal_keeps_the_word_even_when_windows_rendered_it() -> None:
    words = (RecognizedWord("literal", "literal"), RecognizedWord("period", "."))
    assert compose(parse(RecognizedPhrase(words)).pieces, before="the word") == " period"


# -- spacing and capitals ---------------------------------------------------- #


def test_a_phrase_after_a_sentence_takes_a_space_and_a_capital() -> None:
    assert _text("next one", before="First one.") == " Next one"


def test_a_phrase_mid_sentence_is_not_capitalised() -> None:
    assert _text("and bought milk", before="I went to the store") == " and bought milk"


def test_no_space_before_a_comma_even_across_phrases() -> None:
    assert _text("comma then", before="Well") == ", then"


def test_no_space_at_the_start_of_a_line() -> None:
    assert _text("new words", before="Line one\n") == "New words"


def test_existing_spaces_are_never_touched() -> None:
    assert _text("period", before="end  ") == "."


def test_a_space_is_added_when_the_caret_sits_against_the_next_word() -> None:
    assert _text("inserted", before="a ", after="b") == "inserted "


def test_a_sentence_ended_inside_a_quote_still_capitalises() -> None:
    assert _text("then", before='He said "no."') == " Then"


# -- the controller -------------------------------------------------------- #


class FakeRecognizer:
    def __init__(self, fail: str = "") -> None:
        self.fail = fail
        self.started_with: str | None = None
        self.stopped = 0

    def start(self, microphone: str) -> None:
        if self.fail:
            raise DictationStartError(self.fail)
        self.started_with = microphone

    def stop(self) -> None:
        self.stopped += 1


class FakeDocument:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.caret = len(text)
        self.reason = ""
        self.undone = 0

    def unavailable_reason(self, *, writing: bool) -> str:
        return self.reason

    def context(self) -> tuple[str, str]:
        return self.text[: self.caret], self.text[self.caret : self.caret + 2]

    def insert(self, text: str) -> tuple[int, int]:
        if self.anchor is not None and self.anchor != self.caret:
            low, high = self.selection()
            self.text = self.text[:low] + self.text[high:]
            self.caret = low
        self.anchor = None
        start = self.caret
        self.text = self.text[:start] + text + self.text[start:]
        self.caret = start + len(text)
        return start, self.caret

    def text_between(self, start: int, end: int) -> str:
        return self.text[start:end]

    def remove(self, start: int, end: int) -> None:
        self.text = self.text[:start] + self.text[end:]
        self.caret = start
        self.anchor = start

    anchor: int | None = None

    def selection(self) -> tuple[int, int]:
        anchor = self.caret if self.anchor is None else self.anchor
        return min(anchor, self.caret), max(anchor, self.caret)

    def select(self, start: int, end: int) -> None:
        self.anchor, self.caret = start, end

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        self.text = self.text[:start] + text + self.text[end:]
        self.caret = start + len(text)
        self.anchor = None
        return start, self.caret

    def line_bounds(self) -> tuple[int, int]:
        start = self.text.rfind("\n", 0, self.caret) + 1
        end = self.text.find("\n", self.caret)
        return start, len(self.text) if end < 0 else end

    def last_position(self) -> int:
        return len(self.text)

    def undo(self) -> bool:
        self.undone += 1
        return True


class FakeFeedback:
    def __init__(self, sounds: bool = True) -> None:
        self.sounds = sounds
        self.cues: list[Moment] = []
        self.said: list[str] = []
        self.states: list[DictationState] = []

    def has_cue(self, moment: Moment) -> bool:
        return self.sounds

    def cue(self, moment: Moment) -> None:
        self.cues.append(moment)

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, text: str) -> None:
        self.said.append(text)

    def show(self, text: str) -> None:
        pass

    def state_changed(self, state: DictationState) -> None:
        self.states.append(state)

    shown_commands = 0

    def show_commands(self) -> None:
        self.shown_commands += 1


def _controller(
    document: FakeDocument | None = None,
    *,
    preferences: DictationPreferences | None = None,
    fail: str = "",
    sounds: bool = True,
) -> tuple[DictationController, FakeRecognizer, FakeDocument, FakeFeedback]:
    recognizer = FakeRecognizer(fail)
    document = document or FakeDocument()
    feedback = FakeFeedback(sounds)
    controller = DictationController(
        recognizer=lambda _c, _p: recognizer,
        document=document,
        feedback=feedback,
        preferences=lambda: preferences or DictationPreferences(),
    )
    return controller, recognizer, document, feedback


def _hear(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text)))


def test_start_then_phrase_then_back_to_listening() -> None:
    controller, recognizer, document, feedback = _controller()
    controller.start()
    assert controller.state is DictationState.LISTENING
    controller.on_speech_started()
    assert controller.state is DictationState.RECOGNIZING
    _hear(controller, "hello")
    assert document.text == "Hello"
    assert controller.state is DictationState.LISTENING
    assert feedback.cues == [Moment.ON, Moment.PHRASE]
    assert DictationState.PROCESSING in feedback.states


def test_the_phrase_cue_follows_the_insert_and_the_words_are_read_back() -> None:
    controller, _, _, feedback = _controller()
    controller.start()
    _hear(controller, "read me back")
    assert feedback.said[-1] == "Read me back"


@pytest.mark.parametrize(
    ("mode", "cue", "spoken"),
    [
        ("sound", True, False),
        ("speech", False, True),
        ("both", True, True),
        ("silent", False, False),
    ],
)
def test_phrase_feedback_modes(mode: str, cue: bool, spoken: bool) -> None:
    controller, _, _, feedback = _controller(preferences=DictationPreferences(phrase_feedback=mode))
    controller.start()
    _hear(controller, "words")
    assert (Moment.PHRASE in feedback.cues) is cue
    assert ("Words" in feedback.said) is spoken


def test_sound_with_no_clip_falls_through_to_speech() -> None:
    controller, _, _, feedback = _controller(
        preferences=DictationPreferences(phrase_feedback="sound"), sounds=False
    )
    controller.start()
    _hear(controller, "words")
    assert "Words" in feedback.said


def test_a_line_break_alone_is_read_back_by_name() -> None:
    controller, _, _, feedback = _controller(FakeDocument("Line."))
    controller.start()
    _hear(controller, "new paragraph")
    assert feedback.said[-1] == "New paragraph"


def test_on_and_off_are_quiet_when_both_switches_are_off() -> None:
    controller, recognizer, _, feedback = _controller(
        preferences=DictationPreferences(cue_sounds=False, announce=False)
    )
    controller.start()
    controller.stop()
    assert feedback.cues == []
    assert feedback.said == []
    assert recognizer.stopped == 1


def test_a_start_failure_speaks_even_with_everything_off() -> None:
    controller, _, _, feedback = _controller(
        preferences=DictationPreferences(
            cue_sounds=False, announce=False, phrase_feedback="silent"
        ),
        fail="No microphone was found.",
    )
    controller.start()
    assert controller.state is DictationState.OFF
    assert feedback.said == ["No microphone was found."]


def test_the_microphone_setting_reaches_the_recogniser() -> None:
    controller, recognizer, _, _ = _controller(preferences=DictationPreferences(microphone="mic-2"))
    controller.start()
    assert recognizer.started_with == "mic-2"


def test_scratch_that_walks_back_one_phrase_at_a_time() -> None:
    controller, _, document, _ = _controller(FakeDocument("Start."))
    controller.start()
    _hear(controller, "one")
    _hear(controller, "two")
    _hear(controller, "scratch that")
    assert document.text == "Start. One"
    _hear(controller, "scratch that")
    assert document.text == "Start."


def test_scratch_that_leaves_an_edited_phrase_alone() -> None:
    controller, _, document, feedback = _controller()
    controller.start()
    _hear(controller, "original words")
    document.text = document.text.replace("words", "work")  # the user typed into it
    _hear(controller, "scratch that")
    assert document.text == "Original work"
    assert "left alone" in feedback.said[-1]


def test_nothing_to_scratch_says_so() -> None:
    controller, _, _, feedback = _controller()
    controller.start()
    _hear(controller, "scratch that")
    assert feedback.said[-1] == "Nothing has been dictated yet."


def test_undo_that_undoes_and_forgets_the_ranges() -> None:
    controller, _, document, _ = _controller()
    controller.start()
    _hear(controller, "text")
    _hear(controller, "undo that")
    assert document.undone == 1
    assert len(controller.history) == 0


def test_stop_dictation_by_voice_closes_the_microphone() -> None:
    controller, recognizer, _, feedback = _controller()
    controller.start()
    _hear(controller, "stop dictation")
    assert controller.state is DictationState.OFF
    assert recognizer.stopped == 1
    assert feedback.cues[-1] is Moment.OFF


def test_a_phrase_that_cannot_be_written_ends_the_session() -> None:
    controller, recognizer, document, feedback = _controller(FakeDocument("Safe"))
    controller.start()
    document.reason = "Dictation stopped because the document no longer has the focus."
    _hear(controller, "lost words")
    assert document.text == "Safe"
    assert controller.state is DictationState.OFF
    assert recognizer.stopped == 1
    assert feedback.cues[-1] is Moment.ERROR


def test_a_recogniser_failure_closes_everything_and_says_why() -> None:
    controller, recognizer, _, feedback = _controller()
    controller.start()
    controller.on_failure("The microphone stopped.")
    assert controller.state is DictationState.OFF
    assert recognizer.stopped == 1
    assert feedback.said[-1] == "The microphone stopped."


def test_an_exception_while_writing_never_escapes() -> None:
    class Broken(FakeDocument):
        def insert(self, text: str) -> tuple[int, int]:
            raise RuntimeError("control gone")

    controller, recognizer, _, _ = _controller(Broken())
    controller.start()
    _hear(controller, "anything")
    assert controller.state is DictationState.OFF
    assert recognizer.stopped == 1


def test_preferences_read_both_editors_settings_by_the_shared_names() -> None:
    class Settings:
        windows_dictation_microphone = "mic"
        windows_dictation_phrase_feedback = "nonsense"
        windows_dictation_cue_sounds = False
        windows_dictation_announce = True

    preferences = DictationPreferences.from_settings(Settings())
    assert preferences.microphone == "mic"
    assert preferences.phrase_feedback == "sound"  # an unknown mode is the default mode
    assert preferences.cue_sounds is False
    defaults: Any = DictationPreferences.from_settings(object())
    assert defaults.phrase_feedback == "both"


# -- commands that edit the document ----------------------------------------- #


def _dictated(text: str = "", *phrases: str, **preferences: Any):
    controller, recognizer, document, feedback = _controller(
        FakeDocument(text), preferences=DictationPreferences(**preferences)
    )
    controller.start()
    for phrase in phrases:
        _hear(controller, phrase)
    return controller, recognizer, document, feedback


def test_select_that_selects_the_last_phrase_without_its_leading_space() -> None:
    _c, _r, document, feedback = _dictated("Start.", "second part", "select that")
    low, high = document.selection()
    assert document.text[low:high] == "Second part"
    assert feedback.said[-1] == "Selected: Second part"


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("capitalize that", "Meeting Notes For Tuesday"),
        ("all caps that", "MEETING NOTES FOR TUESDAY"),
        ("no caps that", "meeting notes for tuesday"),
    ],
)
def test_case_commands_change_the_last_phrase(command: str, expected: str) -> None:
    _c, _r, document, _f = _dictated("", "meeting notes for tuesday", command)
    assert document.text == expected


def test_delete_word_and_delete_sentence() -> None:
    _c, _r, document, _f = _dictated("One two three", "delete word")
    assert document.text == "One two"
    _c, _r, document, _f = _dictated("First sentence. Second one here", "delete sentence")
    assert document.text == "First sentence."


def test_moving_the_cursor_by_voice() -> None:
    controller, _r, document, _f = _dictated("line one" + chr(10) + "line two")
    document.caret = 12
    _hear(controller, "go to beginning of line")
    assert document.caret == 9
    _hear(controller, "go to end of line")
    assert document.caret == len(document.text)
    _hear(controller, "go to top")
    assert document.caret == 0
    _hear(controller, "go to end of document")
    assert document.caret == len(document.text)


def test_read_that_says_the_last_phrase_again() -> None:
    _c, _r, _d, feedback = _dictated("", "hello there", "read that")
    assert feedback.said[-1] == "Hello there"


def test_what_can_i_say_opens_the_list() -> None:
    _c, _r, document, feedback = _dictated("", "what can I say")
    assert feedback.shown_commands == 1
    assert document.text == ""


def test_spelling_mode_writes_letters_until_stopped() -> None:
    _c, _r, document, feedback = _dictated(
        "Call ", "start spelling", "capital bravo alpha delta", "stop spelling", "later"
    )
    assert document.text == "Call Bad later"
    assert "Spelling off." in feedback.said


# -- joining phrases ------------------------------------------------------------ #


def test_a_pause_mid_sentence_does_not_leave_a_full_stop() -> None:
    """An engine that punctuates ends every phrase with a full stop; when the
    next phrase plainly continues, the full stop and the capital come out."""
    _c, _r, document, _f = _dictated("", "I went to the store.", "And bought milk.")
    assert document.text == "I went to the store and bought milk."


def test_a_spoken_period_is_never_taken_back() -> None:
    _c, _r, document, _f = _dictated("", "I went to the store period", "And then home.")
    assert document.text == "I went to the store. And then home."


def test_a_new_sentence_keeps_its_full_stop() -> None:
    _c, _r, document, _f = _dictated("", "It rained.", "We stayed in.")
    assert document.text == "It rained. We stayed in."


def test_new_paragraph_ends_the_sentence_for_an_engine_that_punctuates() -> None:
    blank_line = chr(10) * 2
    _c, _r, document, _f = _dictated("", "hello there new paragraph how are you")
    assert document.text == "Hello there." + blank_line + "How are you"
    _c, _r, document, _f = _dictated("", "hello there new paragraph how are you", engine="windows")
    assert document.text == "Hello there" + blank_line + "How are you"


@pytest.mark.parametrize(
    ("style", "expected"),
    [
        ("em", "this" + chr(0x2014) + "that"),
        ("en", "this " + chr(0x2013) + " that"),
        ("hyphens", "this -- that"),
    ],
)
def test_the_dash_is_written_the_way_the_settings_say(style: str, expected: str) -> None:
    _c, _r, document, _f = _dictated("x ", "this dash that", dash=style)
    assert document.text == "x " + expected


def test_the_users_own_phrases_are_applied() -> None:
    signature = "Jeff" + chr(10) + "Tucson"
    _c, _r, document, _f = _dictated(
        "", "my signature", rewrite=lambda text: text.replace("my signature", signature)
    )
    assert document.text == signature


# -- the wake phrase -------------------------------------------------------------- #


def _standing_by(**preferences: Any):
    controller, recognizer, document, feedback = _controller(
        preferences=DictationPreferences(wake_enabled=True, **preferences)
    )
    controller.arm()
    return controller, recognizer, document, feedback


def test_arming_opens_the_microphone_and_writes_nothing() -> None:
    controller, recognizer, document, _f = _standing_by()
    assert controller.standing_by and recognizer.started_with == ""
    _hear(controller, "what a lovely day it is")
    assert document.text == ""
    assert controller.standing_by


def test_the_wake_phrase_starts_dictation_and_writes_the_rest() -> None:
    controller, _r, document, feedback = _standing_by()
    _hear(controller, "Quill dictate dear Sam comma")
    assert controller.active
    assert document.text == "Dear Sam,"
    assert Moment.ON in feedback.cues


def test_a_near_miss_of_the_wake_phrase_still_wakes() -> None:
    controller, _r, _d, _f = _standing_by()
    _hear(controller, "Quil dictate")
    assert controller.active


def test_the_wake_phrase_only_counts_at_the_start() -> None:
    controller, _r, document, _f = _standing_by()
    _hear(controller, "I asked Quill dictate something")
    assert controller.standing_by and document.text == ""


def test_a_chosen_wake_phrase_replaces_the_default() -> None:
    controller, _r, _d, _f = _standing_by(wake_phrase="Hey editor")
    _hear(controller, "Quill dictate")
    assert controller.standing_by
    _hear(controller, "hey editor")
    assert controller.active


def test_stop_dictation_goes_back_to_waiting_and_disarm_closes_the_microphone() -> None:
    controller, recognizer, _d, feedback = _standing_by()
    _hear(controller, "Quill dictate")
    _hear(controller, "stop dictation")
    assert controller.standing_by
    assert recognizer.stopped == 0
    assert "Say Quill dictate to start again" in feedback.said[-1]
    controller.disarm()
    assert controller.state is DictationState.OFF and recognizer.stopped == 1


def test_arming_does_nothing_when_the_wake_phrase_is_off() -> None:
    controller, recognizer, _d, _f = _controller()
    controller.arm()
    assert controller.state is DictationState.OFF and recognizer.started_with is None


def test_a_poor_wake_phrase_is_refused_with_a_reason() -> None:
    from quill.core.windows_dictation.wake import wake_phrase_problem

    assert "two words" in wake_phrase_problem("Quill")
    assert wake_phrase_problem("Hi yo") != ""
    assert wake_phrase_problem("Quill dictate") == ""


def test_a_chosen_stop_phrase_stops_and_stop_dictation_still_works() -> None:
    controller, recognizer, document, _f = _dictated("", "hello", stop_phrase="that will do")
    _hear(controller, "That will do.")
    assert controller.state is DictationState.OFF and recognizer.stopped == 1
    assert document.text == "Hello"
    controller, recognizer, _d, _f = _dictated("", stop_phrase="that will do")
    _hear(controller, "stop dictation")
    assert controller.state is DictationState.OFF


def test_the_stop_phrase_inside_a_sentence_is_just_words() -> None:
    controller, _r, document, _f = _dictated(
        "", "I said that will do nicely", stop_phrase="that will do"
    )
    assert controller.active
    assert "that will do nicely" in document.text


def test_a_near_miss_of_the_stop_phrase_still_stops() -> None:
    controller, _r, _d, _f = _dictated("", stop_phrase="finish dictating")
    _hear(controller, "finnish dictating")
    assert controller.state is DictationState.OFF


def test_with_the_wake_phrase_on_the_stop_phrase_goes_back_to_waiting() -> None:
    controller, _r, _d, _f = _standing_by(stop_phrase="that will do")
    _hear(controller, "Quill dictate")
    _hear(controller, "that will do")
    assert controller.standing_by


def test_a_poor_stop_phrase_is_refused_with_a_reason() -> None:
    from quill.core.windows_dictation.wake import stop_phrase_problem

    assert "stop phrase" in stop_phrase_problem("stop")
    assert "stop dictation by accident" in stop_phrase_problem("stop")
    assert stop_phrase_problem("that will do") == ""


def test_the_list_names_the_users_stop_phrase() -> None:
    from quill.core.windows_dictation.reference import commands_reference

    assert '"that will do"' in commands_reference(stop_phrase="that will do")
    assert '"stop dictation"' in commands_reference()


def test_the_stop_phrase_round_trips_through_saved_settings() -> None:
    from quill.core.windows_dictation.settings_fields import load_fields

    assert load_fields({})["windows_dictation_stop_phrase"] == "stop dictation"
    loaded = load_fields({"windows_dictation_stop_phrase": "that will do"})
    assert loaded["windows_dictation_stop_phrase"] == "that will do"

    class Settings:
        windows_dictation_stop_phrase = "that will do"

    assert DictationPreferences.from_settings(Settings()).stop_phrase == "that will do"


# -- the published list ------------------------------------------------------------ #


def test_every_phrase_is_in_the_commands_list() -> None:
    from quill.core.windows_dictation.reference import commands_reference
    from quill.core.windows_dictation.vocabulary import COMMAND_HELP, MARKS

    text = commands_reference()
    for mark in MARKS:
        assert " ".join(mark.phrase) in text
    for entry in COMMAND_HELP:
        for phrase in entry.phrases:
            assert phrase in text


def test_the_list_includes_the_users_own_phrases_and_wake_phrase() -> None:
    from quill.core.windows_dictation.reference import commands_reference

    signature = "Jeff" + chr(10) + "Tucson"
    text = commands_reference(wake_phrase="Hey editor", own_phrases=[("sig", signature)])
    assert "Hey editor" in text and "sig: Jeff (new line) Tucson" in text


def test_the_profile_is_reread_only_when_it_changes(tmp_path) -> None:
    from quill.core.windows_dictation import profile

    path = profile.ensure_file(tmp_path / "dictation.md")
    rewrite = profile.rewriter(path)
    assert rewrite is not None
    assert rewrite("my email address please") == "someone@example.com please"
