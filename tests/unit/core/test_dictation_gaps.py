"""The 2026-10-05 dictation gap plan, wx-free: read-back marks, targets, names,
Markdown and spelling, modes, transcripts, contexts and Dictate Anywhere."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.windows_dictation import (
    Command,
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    anywhere,
    compose,
    contexts,
    instructions,
    parse,
    words_from_text,
)
from quill.core.windows_dictation.options import PAUSE_SECONDS, coerce_pause
from quill.core.windows_dictation.readback import spoken_marks
from quill.core.windows_dictation.targets import (
    find_target,
    match_names,
    number_from,
    unit_bounds,
)
from quill.core.windows_dictation.transcript import transcript_status

# -- the read-back ------------------------------------------------------------ #


@pytest.mark.parametrize(
    ("written", "heard"),
    [
        ("Hello, world.", "Hello comma world period"),
        ("Is it 3.5 or 1,000?", "Is it 3.5 or 1,000 question mark"),
        ("Don't stop -- well-known.", "Don't stop dash well-known period"),
        ('She said "hi".', "She said open quote hi close quote period"),
        ("jo@example.com", "jo at sign example dot com"),
        ("One\n\nTwo\nThree", "One new paragraph Two new line Three"),
        ("Wait...", "Wait ellipsis"),
    ],
)
def test_marks_are_said_by_their_dictation_names(written: str, heard: str) -> None:
    assert spoken_marks(written) == heard


def test_spanish_marks_are_said_in_spanish() -> None:
    assert spoken_marks("Hola, mundo.", "es") == "Hola coma mundo punto"


# -- targets and names ----------------------------------------------------------- #

_TEXT = "The cat sat. The cat ran to the hat! Was it 2 or three?"


def test_the_nearest_match_before_the_cursor_wins() -> None:
    target = find_target(_TEXT, len(_TEXT), ["the", "cat"])
    assert target is not None and (target.start, target.end) == (13, 20)
    assert target.moved(-1) is not None and target.moved(-1).start == 0  # type: ignore[union-attr]


def test_with_nothing_before_the_cursor_the_next_match_wins() -> None:
    target = find_target(_TEXT, 0, ["cat", "ran"])
    assert target is not None and _TEXT[target.start : target.end] == "cat ran"


def test_a_range_runs_through_the_second_words() -> None:
    target = find_target(_TEXT, len(_TEXT), ["the", "cat", "through", "the", "hat"])
    assert target is not None and _TEXT[target.start : target.end] == "The cat ran to the hat"


def test_numbers_match_either_way_and_accents_are_ignored() -> None:
    assert find_target(_TEXT, 0, ["two"]) is not None
    assert find_target(_TEXT, 0, ["3"]) is not None
    assert find_target("Un café negro", 0, ["cafe"]) is not None
    assert find_target(_TEXT, 0, ["dog"]) is None


def test_units() -> None:
    assert _TEXT[slice(*unit_bounds(_TEXT, 20, "sentence"))] == "The cat ran to the hat!"
    assert unit_bounds("a\nbb\nc", 3, "line") == (2, 4)
    assert unit_bounds("one\n\ntwo two\n\nthree", 7, "paragraph") == (5, 12)


def test_names_exact_then_start_then_word_and_never_a_guess() -> None:
    names = ["Sign-off", "Signature", "Address block"]
    assert match_names(names, ["sign", "off"]) == ["Sign-off"]
    assert match_names(names, ["sig"]) == ["Sign-off", "Signature"]
    assert match_names(names, ["address"]) == ["Address block"]
    assert match_names(["sigoff"], ["sig", "off"]) == ["sigoff"]
    assert match_names(names, ["nothing"]) == []


def test_slot_numbers() -> None:
    assert number_from(["three"]) == 3
    assert number_from(["12"]) == 12
    assert number_from(["banana"]) is None


# -- parsing: commands with words, Markdown, spelling ----------------------------- #


def _parse(text: str) -> Any:
    return parse(RecognizedPhrase(words_from_text(text)))


def test_a_command_that_takes_words_keeps_the_whole_phrase_as_a_fallback() -> None:
    parsed = _parse("select the cat")
    assert parsed.command is Command.SELECT_WORDS
    assert parsed.argument == ("the", "cat")
    assert compose(parsed.pieces) == "Select the cat"


def test_whole_phrase_commands_still_win_over_words() -> None:
    assert _parse("select that").command is Command.SELECT
    assert _parse("go to top").command is Command.DOCUMENT_START
    assert _parse("paste clip three").command is Command.PASTE_SLOT


def test_spell_one_word_and_a_sentence_that_only_starts_with_spell() -> None:
    assert compose(_parse("spell bravo alpha delta").pieces) == "bad"
    parsed = _parse("spell it out for me")
    assert parsed.command is None and compose(parsed.pieces) == "Spell it out for me"


def test_line_marks_count_only_at_the_start_of_a_phrase() -> None:
    assert compose(_parse("heading two welcome").pieces) == "## Welcome"
    assert compose(_parse("bullet buy milk").pieces, before="List.") == "\n- Buy milk"
    assert compose(_parse("the heading two lines down").pieces) == "The heading two lines down"


def test_backticks_open_and_close_and_the_pipe_stands_alone() -> None:
    assert compose(_parse("use backtick print backtick now").pieces) == "Use `print` now"
    assert compose(_parse("a vertical bar b").pieces) == "A | b"


def test_spelling_writes_punctuation_and_all_caps() -> None:
    parsed = parse(
        RecognizedPhrase(words_from_text("all caps bravo no caps alpha dot com")),
        spelling=True,
    )
    # "com" is not a letter: a word is spelled out letter by letter.
    assert parsed.pieces[0].text == "Ba."


def test_joined_words_take_no_spaces_and_no_capitals() -> None:
    parsed = _parse("example period com")
    assert compose(parsed.pieces, before="www.", join_words=True) == "example.com"


# -- the controller: modes, the unfinished phrase, transcripts --------------------- #


class _Document:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.sel = (len(text), len(text))

    def unavailable_reason(self, *, writing: bool) -> str:
        return ""

    def context(self) -> tuple[str, str]:
        return self.text[: self.sel[0]], self.text[self.sel[1] : self.sel[1] + 2]

    def selection(self) -> tuple[int, int]:
        return self.sel

    def select(self, start: int, end: int) -> None:
        self.sel = (start, end)

    def insert(self, text: str) -> tuple[int, int]:
        start, end = self.sel
        self.text = self.text[:start] + text + self.text[end:]
        self.sel = (start + len(text), start + len(text))
        return start, start + len(text)

    def text_between(self, start: int, end: int) -> str:
        return self.text[max(0, start) : end]

    def remove(self, start: int, end: int) -> None:
        self.text = self.text[:start] + self.text[end:]
        self.sel = (start, start)

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        self.sel = (start, end)
        return self.insert(text)

    def line_bounds(self) -> tuple[int, int]:
        return 0, len(self.text)

    def last_position(self) -> int:
        return len(self.text)

    def undo(self) -> bool:
        return False


class _Feedback:
    def __init__(self) -> None:
        self.said: list[str] = []
        self.shown: list[str] = []
        self.language = ""

    def has_cue(self, moment: Any) -> bool:
        return False

    def cue(self, moment: Any) -> None:
        pass

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, text: str) -> None:
        self.said.append(text)

    def show(self, text: str) -> None:
        self.shown.append(text)

    def state_changed(self, state: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass

    def set_speech_language(self, language: str) -> None:
        self.language = language


class _Recognizer:
    def start(self, microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass


def _controller(document: _Document, preferences: DictationPreferences | None = None):
    feedback = _Feedback()
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=document,
        feedback=feedback,
        preferences=lambda: preferences or DictationPreferences(phrase_feedback="speech"),
    )
    controller.start()
    return controller, feedback


def _hear(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text), text=text))


def test_all_caps_and_no_space_last_until_turned_off() -> None:
    document = _Document("")
    controller, feedback = _controller(document)
    _hear(controller, "all caps on")
    _hear(controller, "warning")
    _hear(controller, "all caps off")
    assert document.text == "WARNING"
    _hear(controller, "no space on")
    assert controller.mode_text == "no space"
    controller.stop()
    assert controller.mode_text == ""


def test_a_phrase_that_ends_unfinished_runs_on_into_the_next() -> None:
    document = _Document("")
    preferences = DictationPreferences(engine="moonshine", phrase_feedback="silent")
    controller, _feedback = _controller(document, preferences)
    _hear(controller, "This is a very.")
    _hear(controller, "Good test.")
    assert document.text == "This is a very good test."


def test_longer_pauses_are_offered_and_honest_about_seconds() -> None:
    assert PAUSE_SECONDS[coerce_pause("longer")] == 2.0
    assert PAUSE_SECONDS[coerce_pause("longest")] == 3.0


def test_the_language_switch_tells_the_host_and_says_the_language() -> None:
    controller, feedback = _controller(_Document())
    _hear(controller, "switch to spanish")
    assert feedback.language == "es"
    assert "Español." in feedback.said


def test_a_live_transcript_takes_no_commands_and_starts_paragraphs_at_long_pauses() -> None:
    document = _Document("")
    now = {"t": 0.0}
    preferences = DictationPreferences.from_settings(
        type("S", (), {"windows_dictation_transcript_timestamps": True})(), profile="transcript"
    )
    controller, feedback = _controller(document, preferences)
    controller._clock = lambda: now["t"]
    controller._wall = lambda: "10:42"
    controller.begin_transcript()
    _hear(controller, "Good morning.")
    now["t"] = 2.0
    _hear(controller, "scratch that")
    now["t"] = 10.0
    _hear(controller, "Next topic.")
    assert document.text == "[10:42] Good morning. Scratch that.\n\n[10:42] Next topic."
    assert feedback.said == ["Dictation on."]  # nothing per phrase
    assert controller.transcript_words == 6
    controller.stop()
    assert feedback.said[-1] == "Live transcript stopped, 6 words."


def test_transcript_status_counts_minutes_and_words() -> None:
    assert transcript_status(725, 1840) == "Live transcript: 12 minutes, 1,840 words"
    assert transcript_status(30, 1) == "Live transcript: 0 minutes, 1 word"


def test_select_next_with_nothing_selected_writes_the_words() -> None:
    document = _Document("")
    controller, _feedback = _controller(document)
    _hear(controller, "select next")
    assert document.text == "Select next"


# -- contexts, Tidy and OpenAI ---------------------------------------------------- #


def test_contexts_are_kept_per_document_and_pruned(tmp_path: Path) -> None:
    letter = tmp_path / "letter.txt"
    letter.write_text("", encoding="utf-8")
    store = contexts.ContextStore()
    store.set_for_document(letter, "A formal   letter.")
    store.set_for_document(tmp_path / "gone.txt", "Lost.")
    store.save_as("Client letter", "A formal letter.")
    path = contexts.contexts_path(tmp_path / "dictation.md")
    contexts.save(path, store)
    loaded = contexts.load(path)
    assert loaded.for_document(letter) == "A formal letter."
    assert loaded.for_document(tmp_path / "gone.txt") == ""
    assert "Client letter" in loaded.choices() and "Formal letter" in loaded.choices()


def test_tidy_reads_the_context_beside_the_instructions() -> None:
    wrapped = instructions.wrap("hello", "", "A note to a friend.")
    assert "This document is: A note to a friend." in wrapped
    assert instructions.wrap("hello", "") == "hello"


def test_openai_hears_the_context_as_its_prompt(monkeypatch) -> None:
    from quill.core.windows_dictation import openai_transcribe

    captured: dict[str, Any] = {}

    def fake_multipart(fields: list[tuple[str, str]], audio: bytes) -> tuple[bytes, str]:
        captured["fields"] = fields
        raise RuntimeError("stop here")

    monkeypatch.setattr(openai_transcribe, "_multipart", fake_multipart)
    monkeypatch.setattr(openai_transcribe, "wav_bytes", lambda _samples: b"")
    with pytest.raises(RuntimeError):
        openai_transcribe.transcribe_phrase("k", "m", None, prompt="A formal letter.")
    assert ("prompt", "A formal letter.") in captured["fields"]


# -- Dictate Anywhere --------------------------------------------------------------- #


def test_the_handoff_carries_the_settings_once(tmp_path: Path) -> None:
    from quill.core.lite.settings import Settings

    settings = Settings()
    settings.windows_dictation_engine = "whisper"
    anywhere.write_handoff(tmp_path, settings)
    stored = anywhere.take_handoff(tmp_path)
    assert stored is not None and stored["windows_dictation_engine"] == "whisper"
    assert anywhere.take_handoff(tmp_path) is None
    assert anywhere.settings_from(stored).windows_dictation_engine == "whisper"
    assert anywhere.settings_from(None).windows_dictation_phrase_feedback == "sound"


def test_commands_that_read_the_other_programs_text_are_refused() -> None:
    document = _Document("")
    document.external = True  # type: ignore[attr-defined]
    controller, feedback = _controller(document)
    _hear(controller, "select sentence")
    assert anywhere.external_refusal() in feedback.said
    assert Command.SCRATCH in anywhere.EXTERNAL_COMMANDS
