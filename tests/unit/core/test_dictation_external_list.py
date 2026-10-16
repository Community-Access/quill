"""What can I say, in another program (D-7), and the library by voice there (D-8).

QUILL Transcribe's and Inkwell's "What can I say" list is
``commands_reference(external=True)``: every command it lists must be one the
parser understands *and* one the controller lets through in another program,
none it refuses may be listed, and the person's own phrases are there. The
editors' list stays complete.

The D-8 slice: "insert snippet", "insert abbreviation" and "paste clip" work in
another program, typed through the external document as one phrase, and
"scratch that" takes all of it back.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.anywhere import (
    EXTERNAL_COMMANDS,
    SPOKEN_SUMMARY_COMMANDS,
    spoken_summary,
)
from quill.core.windows_dictation.parser import parse
from quill.core.windows_dictation.reference import commands_reference
from quill.core.windows_dictation.vocabulary import COMMAND_HELP, PREFIX_HELP
from quill.core.windows_dictation.vocabulary_types import Command
from quill.ui.windows_dictation_external import ExternalDocument

# -- the list ------------------------------------------------------------------- #

_QUOTED = re.compile(r'"([^"]+)"')


def _listed_phrases(reference: str) -> list[str]:
    """Every quoted phrase on a command row ("say: does")."""
    phrases: list[str] = []
    for line in reference.splitlines():
        said, colon, _does = line.partition(": ")
        if colon and said.startswith('"'):
            phrases.extend(_QUOTED.findall(said))
    return phrases


def test_every_listed_phrase_works_in_another_program() -> None:
    """Parsed as the controller parses it, each is a command it lets through
    in Notepad (EXTERNAL_COMMANDS), not one answered with a refusal."""
    from quill.core.windows_dictation.command_mode import COMMAND_MODE_HELP
    from quill.core.windows_dictation.review_session import REVIEW_HELP

    # Said after the command word only (D-1, and D-2's review): the controller
    # answers those before it parses, in any program (test_dictation_command_mode.py,
    # test_dictation_review.py).
    after_the_word = {
        phrase for entry in (*COMMAND_MODE_HELP, *REVIEW_HELP) for phrase in entry.phrases
    }
    phrases = _listed_phrases(commands_reference(external=True))
    assert len(phrases) >= 20
    assert after_the_word <= set(phrases)
    for phrase in phrases:
        if phrase in after_the_word:
            continue
        sample = {"spell": "bravo alpha", "paste clip": "three", "paste slot": "three"}
        opening = phrase.replace("...", "").strip()
        text = phrase.replace("...", sample.get(opening, "sign off")).strip()
        parsed = parse(RecognizedPhrase(words_from_text(text)))
        if opening == "spell":  # spell one word: the letters are written, no command
            assert "".join(piece.text for piece in parsed.pieces) == "ba"
            continue
        assert parsed.command in EXTERNAL_COMMANDS, (phrase, parsed.command)


def test_no_refused_command_is_listed() -> None:
    reference = commands_reference(external=True)
    for entry in COMMAND_HELP:
        if entry.command not in EXTERNAL_COMMANDS:
            for phrase in entry.phrases:
                assert f'"{phrase}"' not in reference, phrase
    for prefix in PREFIX_HELP:
        if prefix.command not in EXTERNAL_COMMANDS:
            for opening in prefix.prefixes:
                assert f'"{opening} ..."' not in reference, opening


def test_the_insert_commands_are_listed_there() -> None:
    reference = commands_reference(external=True)
    for opening in ('"insert snippet ..."', '"paste clip ..."', '"insert abbreviation ..."'):
        assert opening in reference, opening
    assert "[title]" in reference and "cursor stays at the end" in reference


def test_your_own_phrases_are_listed() -> None:
    reference = commands_reference(external=True, own_phrases=[("my address", "1 Main St")])
    assert "my address: 1 Main St" in reference


def test_the_editors_list_is_still_complete() -> None:
    editors = commands_reference()
    assert '"select that"' in editors and '"select ..."' in editors
    assert "wake phrase" in editors
    assert '"select that"' not in commands_reference(external=True)


def test_the_spoken_summary_names_five_commands_that_work_there() -> None:
    assert len(SPOKEN_SUMMARY_COMMANDS) == 5
    for phrase in SPOKEN_SUMMARY_COMMANDS:
        text = phrase.replace("and its name", "sign off")
        parsed = parse(RecognizedPhrase(words_from_text(text)))
        assert parsed.command in EXTERNAL_COMMANDS or phrase == "new line", phrase
    sentence = spoken_summary("For the full list, open Dictation Commands.")
    assert sentence == (
        "In another program, you can say scratch that, new line, start spelling, "
        "insert snippet and its name, or stop dictation. For the full list, open "
        "Dictation Commands."
    )


# -- the library by voice, in another program ---------------------------------------- #


class _Library:
    def slot_text(self, number: int) -> str | None:
        return {3: "Kind regards"}.get(number, "" if 1 <= number <= 12 else None)

    def snippet_names(self) -> list[str]:
        return ["sign off"]

    def snippet_text(self, name: str) -> tuple[str, int] | None:
        return ("Thanks, [name]", 0) if name == "sign off" else None

    def abbreviation_names(self) -> list[str]:
        return ["addr"]

    def abbreviation_text(self, name: str) -> tuple[str, int] | None:
        return ("1 Main Street", 0) if name == "addr" else None


class _Feedback:
    def __init__(self) -> None:
        self.said: list[str] = []

    def has_cue(self, _m: Any) -> bool:
        return False

    def cue(self, _m: Any) -> None:
        pass

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, _t: str) -> None:
        pass

    def show(self, _t: str) -> None:
        pass

    def state_changed(self, _s: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass

    def library(self) -> _Library:
        return _Library()


class _Recognizer:
    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass


@pytest.fixture()
def notepad() -> tuple[DictationController, list[str], list[int], _Feedback]:
    typed: list[str] = []
    erased: list[int] = []
    document = ExternalDocument(
        problem=lambda: "",
        where=lambda: ("notepad", 1, "edit"),
        type_text=lambda text, *_a: typed.append(text) or True,
        backspace=lambda count: erased.append(count) or True,
    )
    feedback = _Feedback()
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=document,
        feedback=feedback,
        preferences=lambda: DictationPreferences(phrase_feedback="silent"),
    )
    controller.start()
    return controller, typed, erased, feedback


def _say(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text)))


@pytest.mark.parametrize(
    ("said", "written"),
    [
        ("paste clip three", "Kind regards"),
        ("insert snippet sign off", "Thanks, [name]"),
        ("insert abbreviation addr", "1 Main Street"),
    ],
)
def test_the_library_inserts_in_another_program(notepad: Any, said: str, written: str) -> None:
    controller, typed, _erased, feedback = notepad
    _say(controller, said)
    assert typed == [written]
    assert not any("QUILL's own documents" in line for line in feedback.said)


def test_scratch_that_takes_all_of_an_inserted_snippet_back(notepad: Any) -> None:
    controller, typed, erased, _feedback = notepad
    _say(controller, "insert snippet sign off")
    _say(controller, "scratch that")
    assert erased == [len(typed[0])]


def test_reading_commands_are_still_refused_there(notepad: Any) -> None:
    controller, typed, _erased, feedback = notepad
    _say(controller, "copy all")
    assert typed == []
    assert any("QUILL's own documents" in line for line in feedback.said)
    assert Command.COPY_ALL not in EXTERNAL_COMMANDS


def test_the_family_library_drops_the_cursor_and_keeps_blanks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    import quill.core.abbreviations as store
    import quill.core.snippets as snippets
    from quill.ui.windows_dictation_anywhere_library import AnywhereLibrary

    snippet = SimpleNamespace(name="greet", enabled=True, body="Dear ${input:name},${cursor} bye")
    monkeypatch.setattr(
        snippets, "load_snippet_library", lambda: SimpleNamespace(snippets=[snippet])
    )
    entry = SimpleNamespace(abbreviation="sig", expansion="Best,${cursor} Sam")
    monkeypatch.setattr(
        store,
        "load_abbreviation_library",
        lambda: SimpleNamespace(enabled_only=lambda: [entry]),
    )
    library = AnywhereLibrary()
    assert library.snippet_names() == ["greet"]
    text, back = library.snippet_text("greet")  # type: ignore[misc]
    assert back == 0 and "[name]" in text and "${cursor}" not in text
    text, back = library.abbreviation_text("sig")  # type: ignore[misc]
    assert back == 0 and text == "Best, Sam"
