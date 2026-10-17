"""Spoken prompts for snippet blanks (D-8) and reading back more (D-18).

D-8's acceptance criteria, run through the shared controller with the external
document QUILL Transcribe and Inkwell type through (an injector that records
every keystroke, standing in for Edge):

* "QUILL insert snippet bug report" asks for each blank and types the filled
  text as one phrase;
* "scratch that" removes all of it.

D-18: "read that" says the whole of the last insertion, not just a snippet's
name, and "read last sentence", "read last paragraph" and "read selection" read
the editors' own text; in another program they are refused, because nothing
there can be read. Nothing here needs a microphone or touches a real window.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import pytest

from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.snippet_fill import CANCELLED, SnippetFill
from quill.ui.windows_dictation_external import ExternalDocument

BUG_REPORT = (
    "## Summary\n${input:summary}\n\n"
    "Screen reader: ${choice:NVDA|JAWS|Narrator}\n"
    "Date: ${date}\n${cursor}"
)


class _Library:
    def __init__(self, *, with_body: bool = True) -> None:
        if not with_body:
            self.snippet_body = None  # type: ignore[assignment]

    def snippet_names(self) -> list[str]:
        return ["bug report", "sign off"]

    def snippet_body(self, name: str) -> str | None:
        return {"bug report": BUG_REPORT, "sign off": "Thanks"}.get(name)

    def snippet_text(self, name: str) -> tuple[str, int] | None:
        return {"bug report": ("[summary]", 0), "sign off": ("Thanks", 0)}.get(name)


class _Feedback:
    def __init__(self, library: _Library) -> None:
        self._library = library
        self.said: list[str] = []
        self.read: list[str] = []

    def has_cue(self, _m: Any) -> bool:
        return False

    def cue(self, _m: Any) -> None:
        pass

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, text: str) -> None:
        self.read.append(text)

    def show(self, _t: str) -> None:
        pass

    def state_changed(self, _s: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass

    def library(self) -> _Library:
        return self._library


class _Recognizer:
    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass


class _Editor:
    """An editor's document: text, a cursor and a selection."""

    def __init__(self, text: str = "", selection: tuple[int, int] | None = None) -> None:
        self.text = text
        self.sel = selection or (len(text), len(text))

    def unavailable_reason(self, *, writing: bool) -> str:
        return ""

    def context(self) -> tuple[str, str]:
        return self.text[: self.sel[0]], self.text[self.sel[1] :]

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
        return self.text[start:end]

    def remove(self, start: int, end: int) -> None:
        self.text = self.text[:start] + self.text[end:]

    def last_position(self) -> int:
        return len(self.text)


def _controller(
    document: Any, library: _Library | None = None, **preferences: Any
) -> tuple[DictationController, _Feedback]:
    feedback = _Feedback(library or _Library())
    settings = DictationPreferences(phrase_feedback="silent", announce=False, **preferences)
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=document,
        feedback=feedback,
        preferences=lambda: settings,
    )
    controller.start()
    return controller, feedback


def _hear(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text)))


@pytest.fixture()
def edge() -> tuple[DictationController, list[str], list[int], _Feedback]:
    typed: list[str] = []
    erased: list[int] = []
    document = ExternalDocument(
        problem=lambda: "",
        where=lambda: ("msedge", 1, "edit"),
        type_text=lambda text, *_a: typed.append(text) or True,
        backspace=lambda count: erased.append(count) or True,
    )
    controller, feedback = _controller(document, command_prefix_required=True)
    return controller, typed, erased, feedback


# -- D-8 ------------------------------------------------------------------------ #


def test_quill_insert_snippet_asks_for_each_blank_and_types_once(edge: Any) -> None:
    controller, typed, _erased, feedback = edge
    _hear(controller, "QUILL insert snippet bug report")
    assert typed == []
    assert feedback.said[-1] == ("Snippet bug report, 2 blanks. Say cancel to stop. Summary?")
    _hear(controller, "the reader skips headings comma badly")
    assert typed == []  # an answer is never typed on its own
    assert feedback.said[-1] == "Choose NVDA, JAWS or Narrator."
    _hear(controller, "JAWS")
    today = datetime.now().strftime("%Y-%m-%d")
    assert typed == [
        f"## Summary\nThe reader skips headings, badly\n\nScreen reader: JAWS\nDate: {today}\n"
    ]  # one phrase; the cursor mark dropped in another program


def test_scratch_that_removes_all_of_the_filled_snippet(edge: Any) -> None:
    controller, typed, erased, _feedback = edge
    _hear(controller, "QUILL insert snippet bug report")
    _hear(controller, "a summary")
    _hear(controller, "choose two")
    assert len(typed) == 1
    _hear(controller, "QUILL scratch that")
    assert erased == [len(typed[0])]


def test_cancel_types_nothing(edge: Any) -> None:
    controller, typed, _erased, feedback = edge
    _hear(controller, "QUILL insert snippet bug report")
    _hear(controller, "a summary")
    _hear(controller, "cancel")
    assert typed == [] and feedback.said[-1] == CANCELLED
    assert not controller.filling_snippet


def test_scratch_that_asks_the_blank_before_again(edge: Any) -> None:
    controller, typed, _erased, feedback = edge
    _hear(controller, "QUILL insert snippet bug report")
    _hear(controller, "wrong summary")
    _hear(controller, "QUILL scratch that")
    assert feedback.said[-1] == "Summary?"
    _hear(controller, "right summary")
    _hear(controller, "skip")
    assert "Right summary" in typed[0] and "Screen reader: \n" in typed[0]


def test_a_choice_that_is_not_offered_is_asked_again(edge: Any) -> None:
    controller, typed, _erased, feedback = edge
    _hear(controller, "QUILL insert snippet bug report")
    _hear(controller, "s")
    _hear(controller, "voiceover")
    assert typed == []
    assert feedback.said[-1] == "Say one of NVDA, JAWS or Narrator, or choose and a number."
    _hear(controller, "number three")
    assert "Screen reader: Narrator" in typed[0]


def test_stopping_dictation_stops_the_snippet(edge: Any) -> None:
    controller, typed, _erased, _feedback = edge
    _hear(controller, "QUILL insert snippet bug report")
    controller.stop()
    assert not controller.filling_snippet and typed == []


def test_a_snippet_with_no_blanks_goes_straight_in(edge: Any) -> None:
    controller, typed, _erased, _feedback = edge
    _hear(controller, "QUILL insert snippet sign off")
    assert typed == ["Thanks"]


def test_a_library_without_bodies_keeps_the_written_blanks() -> None:
    typed: list[str] = []
    document = ExternalDocument(
        problem=lambda: "",
        where=lambda: ("notepad", 1, "edit"),
        type_text=lambda text, *_a: typed.append(text) or True,
    )
    controller, _feedback = _controller(document, _Library(with_body=False))
    _hear(controller, "insert snippet bug report")
    assert typed == ["[summary]"]


def test_in_an_editor_the_cursor_goes_where_the_snippet_puts_it() -> None:
    document = _Editor()
    controller, _feedback = _controller(document)
    _hear(controller, "insert snippet bug report")
    _hear(controller, "summary text")
    _hear(controller, "choose one")
    assert document.text.startswith("## Summary\nSummary text\n\nScreen reader: NVDA\nDate: ")
    assert document.sel == (len(document.text), len(document.text))  # ${cursor} is last


def test_the_fill_model_counts_and_renders() -> None:
    fill = SnippetFill.start("x", "${input:first_name} ${choice:a|b} ${cursor}!", external=True)
    assert fill is not None and len(fill.fields) == 2
    assert fill.prompt() == "First name?"
    assert fill.answer(["sam"], "Sam") == ""
    assert fill.answer(["b"], "B") == ""
    assert fill.done and fill.render() == ("Sam b !", 0)
    assert SnippetFill.start("x", "plain ${date}", external=True) is None
    assert SnippetFill.start("x", "${input:}", external=True) is None  # unreadable: old path


# -- D-18 ------------------------------------------------------------------------- #


def test_read_that_says_the_whole_of_an_inserted_snippet(edge: Any) -> None:
    controller, typed, _erased, feedback = edge
    _hear(controller, "QUILL insert snippet sign off")
    _hear(controller, "QUILL read that")
    assert feedback.said[-1] == "Thanks"


def test_read_that_after_a_filled_snippet_reads_every_line() -> None:
    document = _Editor()
    controller, feedback = _controller(document)
    _hear(controller, "insert snippet bug report")
    _hear(controller, "it crashed")
    _hear(controller, "choose one")
    _hear(controller, "read that")
    said = feedback.said[-1]
    assert said.startswith("hash sign hash sign Summary new line It crashed new paragraph")
    assert "Screen reader colon NVDA" in said


@pytest.mark.parametrize(
    ("said", "text", "selection", "heard"),
    [
        ("read last sentence", "First one. Second one. ", None, "Second one period"),
        ("read last paragraph", "Old.\n\nNew para here. More", None, "New para here period More"),
        ("read selection", "Pick these words now", (5, 16), "these words"),
        ("read selection", "Nothing chosen", None, "Nothing is selected."),
        ("read last sentence", "", None, "There is no sentence here."),
    ],
)
def test_the_editors_text_is_read_back(
    said: str, text: str, selection: tuple[int, int] | None, heard: str
) -> None:
    document = _Editor(text, selection)
    controller, feedback = _controller(document)
    _hear(controller, said)
    assert feedback.said[-1] == heard
    assert document.text == text  # reading writes nothing


def test_reading_the_document_is_refused_in_another_program(edge: Any) -> None:
    controller, typed, _erased, feedback = edge
    _hear(controller, "QUILL read last sentence")
    assert typed == []
    assert re.search("QUILL's own documents", feedback.said[-1])
