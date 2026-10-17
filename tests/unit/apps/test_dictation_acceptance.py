"""Dictation acceptance, the automated part (todo D.2), in QUILL and QUILL Lite.

Each test runs twice, once per editor, through the editor's own handler
(``cmd_toggle_dictation``) and its own hooks: QUILL Lite's real window mixins
(the ``lite_window`` fixture), and QUILL's real adapter
(:class:`~quill.ui.main_frame_windows_dictation.WindowsDictationCommandsMixin`)
on a stand-in frame that answers the few questions MainFrame answers, with
QUILL's own ``copy_all``. Between the phrase and the document everything is
the shipped code: the shared controller, the parser, the composer, the
document and feedback ports (``quill/ui/windows_dictation_ports.py``) and each
editor's library of clips and snippets.

Nothing here opens a microphone or touches a real window: the recogniser is a
fake that hands over the words a test names, the text control is the suite's
``FakeControl``, and the focus is patched. Dictating into another program is
the external port with typing and backspaces faked.

What this does not cover, on purpose: how accurately or how quickly any
engine hears (the benchmarks, todo C.15), and whether a screen reader echoes
the read-back (todo C.20). The coverage table is section 35 of
``docs/design/2026-10-05-dictation-plan-and-status.md``.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import wx

from quill.core.abbreviations import AbbreviationLibrary
from quill.core.copy_tray import CopyTray
from quill.core.snippets import Snippet
from quill.core.windows_dictation import RecognizedPhrase, words_from_text
from quill.core.windows_dictation.vocabulary import MARKS
from quill.ui import windows_dictation_commands as shared
from tests.unit.apps.conftest import FakeControl

EDITORS = ("quill", "lite")

#: Copy Tray slot numbers as people say them.
_NUMBER_WORDS = (
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
)


# -- the fakes ------------------------------------------------------------- #


class FakeRecognizer:
    """Hands the controller the words a test names, as an engine would."""

    def __init__(self, controller: Any) -> None:
        self.controller = controller

    def start(self, microphone: str) -> None:
        del microphone

    def stop(self) -> None:
        pass

    def hear(self, text: str) -> None:
        self.controller.on_phrase(RecognizedPhrase(words_from_text(text)))


@pytest.fixture
def recognizers(monkeypatch):
    made: list[FakeRecognizer] = []

    def make(controller: Any, preferences: Any) -> FakeRecognizer:
        del preferences
        made.append(FakeRecognizer(controller))
        return made[-1]

    monkeypatch.setattr(shared, "_make_recognizer", make)
    monkeypatch.setattr(shared, "_controller", None)
    monkeypatch.setattr(shared, "_host", None)
    monkeypatch.setattr(shared, "_watched_tops", set())
    return made


def _quill_frame_class() -> type:
    """QUILL's adapter on a stand-in for MainFrame: the adapter's hooks are the
    shipped ones, and so is ``copy_all``; below them, what MainFrame owns."""
    from quill.ui.main_frame import MainFrame
    from quill.ui.main_frame_windows_dictation import WindowsDictationCommandsMixin

    class QuillFrame(WindowsDictationCommandsMixin):
        copy_all = MainFrame.copy_all

        def __init__(self, text: str, tmp_path: Path) -> None:
            from quill.core.settings import Settings

            self.editor = FakeControl(text, len(text))
            self.control = self.editor  # the name the tests share with QUILL Lite
            self.frame = SimpleNamespace(GetMenuBar=lambda: None)
            self.settings = Settings()
            self.document = SimpleNamespace(path=None)
            self.announcements: list[str] = []
            self.status: list[str] = []
            self.clipboard: list[str] = []
            self.opened: list[str] = []
            self._tmp = tmp_path
            self._copy_tray_instance = CopyTray(tmp_path)
            self._snippet_library = SimpleNamespace(snippets=[])
            self._abbreviation_library = AbbreviationLibrary(version=1, abbreviations=[])

        # What MainFrame answers.
        def _announce(self, text: str, force: bool = False) -> None:
            del force
            self.announcements.append(text)

        def _set_status(self, text: str) -> None:
            self.status.append(text)

        def _set_status_quiet(self, text: str) -> None:
            self.status.append(text)

        def _play_speech_sound(self, event: str) -> None:
            del event

        def _has_sound_for(self, event: str) -> bool:
            del event
            return False

        def _copy_to_clipboard(self, text: str) -> bool:
            self.clipboard.append(text)
            return True

        def _tray(self) -> CopyTray:
            return self._copy_tray_instance

        def open_copy_tray(self) -> None:
            self.opened.append("copy tray")

        def insert_snippet(self) -> None:
            self.opened.append("snippets")

        def _get_clipboard_text_for_abbreviation(self) -> str:
            return ""

        def _binding_for(self, command_id: str) -> str:
            del command_id
            return ""

        def _current_editor_mode(self) -> str:
            return "plain"

        def _active_markup_surface(self) -> str:
            return ""

        # The words file: the test's folder, never the person's own.
        def _dictation_profile_path(self) -> Path:
            return self._tmp / "dictation.md"

    return QuillFrame


class Editor:
    """One editor, dictating: its window, its fake engine, and the shared words."""

    def __init__(self, name: str, win: Any, made: list[FakeRecognizer]) -> None:
        self.name = name
        self.win = win
        self._made = made

    @property
    def text(self) -> str:
        return str(self.win.control.GetValue())

    @property
    def said(self) -> list[str]:
        return list(self.win.announcements)

    def selection(self) -> tuple[int, int]:
        return tuple(self.win.control.GetSelection())  # type: ignore[return-value]

    def selected(self) -> str:
        start, end = self.selection()
        return self.text[start:end]

    def start(self) -> Editor:
        self.win.cmd_toggle_dictation()
        assert self.win.dictation_active(), self.said
        return self

    def hear(self, *phrases: str) -> Editor:
        for phrase in phrases:
            self._made[-1].hear(phrase)
        return self

    def clipboard(self) -> list[str]:
        return list(self.win.clipboard)

    def put_in_slot(self, number: int, text: str) -> None:
        tray = self.win._tray() if self.name == "quill" else self.win.app.copy_tray
        tray.copy_to(number, text)

    def add_named_text(self, name: str, body: str) -> None:
        """A snippet in QUILL's snippet library; in QUILL Lite, whose Snippets
        gallery is its abbreviation library, an abbreviation."""
        if self.name == "quill":
            snippets = self.win._snippet_library.snippets
            snippets.append(Snippet(str(len(snippets) + 1), name, f";{len(snippets)}", body))
        else:
            self.win.app.abbreviations.add(name, body)

    def add_abbreviation(self, name: str, body: str) -> None:
        if self.name == "quill":
            self.win._abbreviation_library.add(name, body)
        else:
            self.win.app.abbreviations.add(name, body)


@pytest.fixture
def focused(monkeypatch):
    holder: dict[str, Any] = {"control": None}
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: holder["control"]))
    return holder


@pytest.fixture(params=EDITORS)
def editor(request, lite_window, recognizers, focused, tmp_path, monkeypatch):
    """``editor("text")`` -> an :class:`Editor` with the caret at the end."""

    def make(text: str = "") -> Editor:
        if request.param == "quill":
            win = _quill_frame_class()(text, tmp_path)
        else:
            win = lite_window(text, cursor=len(text))
            win.available_sounds = frozenset(str(event) for event in shared.DICTATION_CUES.values())
            win.app.abbreviations = AbbreviationLibrary(version=1, abbreviations=[])
            win.clipboard = []
            monkeypatch.setattr(
                win, "_set_clipboard_text", lambda copied: win.clipboard.append(copied) or True
            )
        win._dictation_settings().windows_dictation_phrase_feedback = "speech"
        focused["control"] = win.control
        return Editor(request.param, win, recognizers)

    return make


# -- inserting before and after a spoken phrase ------------------------------ #


def test_go_to_then_dictate_inserts_before_the_words(editor) -> None:
    session = editor("Meet me on Friday.").start()
    session.hear("go to friday")
    assert session.selection() == (11, 11)
    assert "Before Friday." in session.said
    session.hear("next")
    assert session.text == "Meet me on next Friday."


def test_go_after_then_dictate_inserts_after_the_words(editor) -> None:
    session = editor("Meet me on Friday.").start()
    session.hear("go after meet me")
    assert session.selection() == (7, 7)
    assert "After Meet me." in session.said
    session.hear("at noon")
    assert session.text == "Meet me at noon on Friday."


def test_go_before_is_another_name_for_go_to(editor) -> None:
    session = editor("One two three.").start()
    session.hear("go before three")
    assert session.selection() == (8, 8)


def test_words_that_are_not_there_are_written_not_lost(editor) -> None:
    session = editor("Hello. ").start()
    session.hear("go after the store")
    assert session.text == "Hello. Go after the store"
    assert "Not found, written as text." in session.said
    session.hear("scratch that")
    assert session.text == "Hello. "


# -- repeated matches -------------------------------------------------------- #


def test_the_nearest_match_before_the_cursor_then_previous_and_next(editor) -> None:
    text = "The cat sat. The cat ran. The cat slept."
    session = editor(text).start()
    session.hear("select the cat")
    assert session.selection() == (26, 33)
    session.hear("select previous")
    assert session.selection() == (13, 20)
    session.hear("select previous")
    assert session.selection() == (0, 7)
    session.hear("select previous")
    assert session.said[-1] == "None before that."
    assert session.selection() == (0, 7)
    session.hear("select next")
    assert session.selection() == (13, 20)
    session.hear("select again")
    assert session.selection() == (26, 33)
    session.hear("select again")
    assert session.said[-1] == "No more."


def test_a_far_match_says_its_line(editor) -> None:
    text = "Remember the milk.\none\ntwo\nthree\nfour\nEnd."
    session = editor(text).start()
    session.hear("select milk")
    assert session.selected() == "milk"
    assert "Selected: milk, line 1." in session.said


def test_go_to_on_a_repeated_word_then_previous_moves_back(editor) -> None:
    session = editor("Red, red, red.").start()
    session.hear("go to red")
    assert session.selection() == (10, 10)
    session.hear("select previous")
    assert session.selection() == (5, 5)


# -- selection by words ------------------------------------------------------ #


def test_select_words_then_the_next_phrase_replaces_them(editor) -> None:
    session = editor("The quick brown fox.").start()
    session.hear("select quick brown")
    assert session.selected() == "quick brown"
    assert "Selected: quick brown." in session.said
    session.hear("slow red")
    assert session.text == "The slow red fox."


def test_select_a_range_through_other_words(editor) -> None:
    session = editor("Dear Sam, the meeting moved to Tuesday at ten.").start()
    session.hear("select the meeting through tuesday")
    assert session.selected() == "the meeting moved to Tuesday"


def test_select_a_number_said_either_way(editor) -> None:
    session = editor("Room 3 is free.").start()
    session.hear("select three")
    assert session.selected() == "3"


def test_correct_words_replaces_them_with_the_next_phrase(editor) -> None:
    session = editor("I met Ann today.").start()
    session.hear("correct ann")
    assert "Correcting Ann. Say the new words." in session.said
    session.hear("Anne")  # an engine writes a name with its capital
    assert session.text == "I met Anne today."


def test_select_sentence_line_and_paragraph(editor) -> None:
    session = editor("First line.\nSecond one. Third one.").start()
    session.hear("select sentence")
    assert session.selected() == "Third one."
    session.hear("select line")
    assert session.selected() == "Second one. Third one."
    session.hear("select paragraph")
    assert session.selected() == "First line.\nSecond one. Third one."


# -- Copy All and copy that ---------------------------------------------------- #


def test_copy_all_puts_the_whole_document_on_the_clipboard(editor) -> None:
    session = editor("Every word here.\nAnd here.").start()
    session.hear("copy all")
    assert session.clipboard() == ["Every word here.\nAnd here."]
    assert session.text == "Every word here.\nAnd here."  # nothing typed, nothing selected
    assert session.selection() == (26, 26)


def test_copy_everything_and_copy_document_are_the_same_command(editor) -> None:
    session = editor("Short.").start()
    session.hear("copy everything", "copy document")
    assert session.clipboard() == ["Short.", "Short."]


def test_copy_all_in_an_empty_document_copies_nothing(editor) -> None:
    session = editor("").start()
    session.hear("copy all")
    assert session.clipboard() == []


def test_copy_that_copies_only_the_last_phrase(editor) -> None:
    session = editor("").start()
    session.hear("first part period", "second part")
    session.hear("copy that")
    assert session.clipboard() == ["Second part"]
    assert "Copied: Second part" in session.said


# -- removing only the last dictated phrase ------------------------------------- #


def test_scratch_that_removes_only_the_last_phrase_then_the_one_before(editor) -> None:
    session = editor("Kept.").start()
    session.hear("first phrase period", "second phrase period")
    assert session.text == "Kept. First phrase. Second phrase."
    session.hear("scratch that")
    assert session.text == "Kept. First phrase."
    assert "Scratched: Second phrase." in session.said
    session.hear("delete that")
    assert session.text == "Kept."
    session.hear("scratch that")
    assert session.text == "Kept."  # the typed text is never taken
    assert session.said[-1] == "Nothing has been dictated yet."


def test_a_phrase_typed_into_since_is_left_alone(editor) -> None:
    session = editor("").start()
    session.hear("hello there")
    session.win.control.Replace(0, 5, "Howdy")  # the person typed over part of it
    session.hear("scratch that")
    assert session.text == "Howdy there"
    assert "That phrase has changed since it was dictated, so it was left alone." in session.said


def test_scratch_that_after_replacing_a_selection_takes_out_the_new_words(editor) -> None:
    session = editor("The quick brown fox.").start()
    session.hear("select quick", "slow")
    assert session.text == "The slow brown fox."
    session.hear("scratch that")
    assert "slow" not in session.text and "brown fox." in session.text


# -- all twelve clips ------------------------------------------------------------ #


@pytest.mark.parametrize("number", range(1, 13))
def test_every_copy_tray_slot_pastes_by_voice(editor, number: int) -> None:
    session = editor("Start. ")
    for slot in range(1, 13):
        session.put_in_slot(slot, f"clip {slot}")
    session.start().hear(f"paste clip {_NUMBER_WORDS[number - 1]}")
    assert session.text == f"Start. clip {number}"
    assert f"Pasted slot {number}" in session.said
    session.hear("scratch that")
    assert session.text == "Start. "


def test_all_twelve_slots_in_one_session_and_as_digits(editor) -> None:
    session = editor("")
    for slot in range(1, 13):
        session.put_in_slot(slot, f"<{slot}>")
    session.start()
    for slot in range(1, 13):
        session.hear(f"paste slot {slot}")
    assert session.text.replace(" ", "") == "".join(f"<{slot}>" for slot in range(1, 13))


def test_a_slot_that_does_not_exist_or_is_empty_is_said(editor) -> None:
    session = editor("").start()
    session.hear("paste clip thirteen")
    assert "Say a slot number, like paste clip three." in session.said
    session.hear("paste clip four")
    assert "Slot 4 is empty." in session.said
    assert session.text == ""


# -- named text with spaces -------------------------------------------------------- #


def test_named_text_with_spaces_is_found_by_its_spoken_words(editor) -> None:
    session = editor("")
    session.add_named_text("sign off", "Kind regards,\nJeff")
    session.start().hear("insert snippet sign off")
    assert session.text == "Kind regards,\nJeff"
    assert "Snippet sign off" in session.said
    session.hear("scratch that")
    assert session.text == ""


def test_a_name_said_as_separate_words_finds_a_joined_name(editor) -> None:
    session = editor("")
    session.add_named_text("sigoff", "Thanks")
    session.start().hear("insert snippet sig off")
    assert session.text == "Thanks"


def test_two_names_that_both_match_are_counted_not_guessed(editor) -> None:
    session = editor("")
    session.add_named_text("sign off", "A")
    session.add_named_text("sign in", "B")
    session.start().hear("insert snippet sign")
    assert "2 snippets match sign." in session.said
    assert session.text == ""


def test_an_abbreviation_with_spaces_in_its_name_expands_by_voice(editor) -> None:
    session = editor("")
    session.add_abbreviation("home address", "1 Main Street")
    session.start().hear("insert abbreviation home address")
    assert session.text == "1 Main Street"
    assert "Abbreviation home address" in session.said


# -- every capitalization mode ------------------------------------------------------ #


def test_caps_on_capitalises_each_word_until_caps_off(editor) -> None:
    session = editor("").start()
    session.hear("caps on", "the old man and the sea", "caps off", "period then more")
    assert session.text.startswith("The Old Man And The Sea. Then more")
    assert "Caps on." in session.said and "Caps off." in session.said


def test_capitals_on_and_off_are_the_same_mode(editor) -> None:
    session = editor("").start()
    session.hear("capitals on")
    assert shared._controller.mode_text == "caps"
    session.hear("capitals off")
    assert shared._controller.mode_text == ""


def test_all_caps_on_writes_capitals_until_all_caps_off(editor) -> None:
    session = editor("").start()
    session.hear("all caps on", "warning", "all caps off", "be careful")
    assert session.text == "WARNING be careful"


def test_capitalize_uppercase_and_lowercase_that(editor) -> None:
    session = editor("").start()
    session.hear("meeting notes", "capitalize that")
    assert session.text == "Meeting Notes"
    session.hear("all caps that")
    assert session.text == "MEETING NOTES"
    session.hear("no caps that")
    assert session.text == "meeting notes"
    session.hear("cap that")
    assert session.text == "Meeting Notes"
    session.hear("uppercase that", "lowercase that")
    assert session.text == "meeting notes"


def test_capital_all_caps_and_no_caps_while_spelling(editor) -> None:
    session = editor("").start()
    session.hear("start spelling", "capital alpha bravo", "all caps charlie delta no caps echo")
    session.hear("stop spelling")
    assert session.text == "AbCDe"


def test_the_modes_end_when_dictation_stops(editor) -> None:
    session = editor("").start()
    session.hear("all caps on", "no space on")
    controller = shared._controller
    assert controller.mode_text == "all caps, no space"
    session.win.cmd_toggle_dictation()
    assert controller.mode_text == ""


# -- an email address, character by character ---------------------------------------- #


def test_an_email_address_spelled_character_by_character(editor) -> None:
    session = editor("Write to").start()
    session.hear("start spelling")
    session.hear("jay dot sierra mike india tango hotel")
    session.hear("at sign echo x-ray dot charlie oscar")
    session.hear("stop spelling")
    assert session.text == "Write to j.smith@ex.co"


def test_an_email_address_one_character_a_phrase(editor) -> None:
    """Spelled phrases join with no space (fixed 2026-10-17: each pause used to
    put a space in the address)."""
    session = editor("").start()
    session.hear("start spelling")
    for phrase in ("juliet", "oscar", "at sign", "echo", "x-ray", "dot", "charlie", "oscar"):
        session.hear(phrase)
    session.hear("stop spelling")
    assert session.text == "jo@ex.co"
    session.hear("is my address")
    assert session.text == "jo@ex.co is my address"


def test_space_while_spelling_is_the_only_way_to_a_space(editor) -> None:
    session = editor("").start()
    session.hear("start spelling", "capital alpha", "space", "capital bravo")
    assert session.text == "A B"


def test_a_whole_word_while_spelling_is_left_out_not_guessed(editor) -> None:
    session = editor("").start()
    session.hear("start spelling", "jay dot smith at sign example dot com")
    # Only letters, digits and marks are written; "smith" is not a letter, so
    # the address is spelled out (the guide's example says so since 2026-10-17).
    assert session.text == "j.@."


def test_spell_one_address_without_spelling_mode(editor) -> None:
    session = editor("").start()
    session.hear("spell alpha bravo at sign charlie dot delta")
    assert session.text == "ab@c.d"


def test_scratch_that_while_spelling_takes_back_one_phrase(editor) -> None:
    session = editor("").start()
    session.hear("start spelling", "alpha bravo", "charlie", "scratch that", "delta")
    session.hear("stop spelling")
    assert session.text == "abd"


# -- the Markdown punctuation vocabulary ----------------------------------------------- #

_MARKDOWN_GROUPS = ("Markdown and code", "Starting a line (say these first)")
_MARKDOWN_MARKS = [mark for mark in MARKS if mark.group in _MARKDOWN_GROUPS]


@pytest.mark.parametrize("mark", _MARKDOWN_MARKS, ids=lambda mark: " ".join(mark.phrase))
def test_each_markdown_word_writes_its_mark(editor, mark) -> None:
    session = editor("Text.").start()
    session.hear(" ".join(mark.phrase) + " word")
    assert mark.text.strip() in session.text, session.text


def test_a_markdown_note_dictated_line_by_line(editor) -> None:
    session = editor("").start()
    session.hear("heading one shopping")
    session.hear("bullet milk")
    session.hear("bullet bread")
    session.hear("numbered item call the bank")
    session.hear("block quote be kind")
    session.hear("new line use backtick print backtick here")
    assert session.text == (
        "# Shopping\n- Milk\n- Bread\n1. Call the bank\n> Be kind\nUse `print` here"
    )


def test_heading_one_to_six(editor) -> None:
    session = editor("").start()
    for level, word in enumerate(("one", "two", "three", "four", "five", "six"), 1):
        session.hear(f"heading {word} part {word}")
        assert session.text.splitlines()[-1] == "#" * level + f" Part {word}"


def test_a_markdown_word_inside_a_sentence_is_words(editor) -> None:
    session = editor("").start()
    session.hear("the heading two lines down")
    assert session.text == "The heading two lines down"


def test_markdown_symbols_and_brackets(editor) -> None:
    session = editor("").start()
    session.hear("open bracket link close bracket open paren page close paren")
    session.hear("new line a vertical bar b")
    session.hear("new line two asterisk three and snake underscore case")
    text = session.text
    assert "[Link](page)" in text  # fixed 2026-10-17: it was "[Link] (page)"
    assert "A | b" in text
    # An asterisk and an underscore join the words either side of them.
    assert text.endswith("Two*three and snake_case")


def test_a_markdown_link_across_two_phrases(editor) -> None:
    session = editor("See").start()
    session.hear("open bracket the guide close bracket")
    session.hear("open paren page close paren")
    assert session.text == "See [the guide](page)"


def test_literal_writes_a_markdown_word_as_a_word(editor) -> None:
    session = editor("").start()
    session.hear("literal bullet points")
    assert session.text == "Bullet points"


# -- the documented limits in another program (insert only) ---------------------------- #


class _OtherProgram:
    """Dictating into another program: the shipped external port, with typing,
    backspaces and the focus faked, and the family's own library (clips from
    the Copy Tray file, snippets and abbreviations) read from a test folder."""

    def __init__(self, tmp_path: Path, monkeypatch: Any) -> None:
        from quill.core import paths
        from quill.core.windows_dictation import DictationController, DictationPreferences
        from quill.ui import windows_dictation_anywhere_library as anywhere_library
        from quill.ui.windows_dictation_external import ExternalDocument

        monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
        self.tray = CopyTray(tmp_path)
        self.snippets: list[Snippet] = []
        monkeypatch.setattr(
            anywhere_library.AnywhereLibrary, "_snippets", lambda _self: self.snippets
        )
        self.typed: list[str] = []
        self.said: list[str] = []
        document = ExternalDocument(
            problem=lambda: "",
            where=lambda: ("notepad", "Edit"),
            type_text=lambda text, *_hush: self.typed.append(text) or True,
            backspace=lambda count: self.typed.append(f"<{count} backspaces>") or True,
        )
        library = anywhere_library.AnywhereLibrary()
        feedback = SimpleNamespace(
            has_cue=lambda _moment: False,
            cue=lambda _moment: None,
            say=self.said.append,
            read_back=self.said.append,
            show=lambda _text: None,
            state_changed=lambda _state: None,
            show_commands=lambda: None,
            library=lambda: library,
        )
        self.controller = DictationController(
            recognizer=lambda _c, _p: FakeRecognizer(None),
            document=document,
            feedback=feedback,
            preferences=lambda: DictationPreferences(phrase_feedback="speech"),
        )
        self.controller.start()

    def hear(self, *phrases: str) -> None:
        for phrase in phrases:
            self.controller.on_phrase(RecognizedPhrase(words_from_text(phrase)))


@pytest.fixture
def other_program(tmp_path, monkeypatch) -> _OtherProgram:
    return _OtherProgram(tmp_path, monkeypatch)


_READS_THE_TEXT = (
    "select the cat",
    "go to the cat",
    "go after the cat",
    "select the cat through the hat",
    "select again",
    "select sentence",
    "select line",
    "select paragraph",
    "go to start of paragraph",
    "copy all",
    "copy that",
    "show clips",
    "show snippets",
    "spell that",
    "read last sentence",
    "read selection",
)


@pytest.mark.parametrize("phrase", _READS_THE_TEXT)
def test_a_command_that_reads_the_other_programs_text_is_refused(
    other_program: _OtherProgram, phrase: str
) -> None:
    from quill.core.windows_dictation.anywhere import external_refusal

    other_program.hear("hello")
    typed = list(other_program.typed)
    other_program.hear(phrase)
    assert other_program.typed == typed  # nothing typed, nothing taken back
    assert other_program.said[-1] == external_refusal()


def test_dictated_words_punctuation_and_scratch_that_work_there(
    other_program: _OtherProgram,
) -> None:
    other_program.hear("dear Sam comma", "thanks period", "scratch that")
    assert other_program.typed == ["Dear Sam,", " thanks.", "<8 backspaces>"]


def test_clips_go_in_there_and_scratch_that_takes_them_back(
    other_program: _OtherProgram,
) -> None:
    for slot in range(1, 13):
        other_program.tray.copy_to(slot, f"clip {slot}")
    other_program.hear("paste clip twelve")
    assert other_program.typed == ["clip 12"]
    other_program.hear("scratch that")
    assert other_program.typed[-1] == "<7 backspaces>"


def test_a_snippets_cursor_mark_is_dropped_there(other_program: _OtherProgram) -> None:
    """Documented limit: the cursor cannot be moved back inside another
    program's text without reading it, so it stays at the end."""
    other_program.snippets.append(Snippet("1", "sign off", ";so", "Thanks,${cursor} Jeff"))
    other_program.hear("insert snippet sign off")
    assert other_program.typed == ["Thanks, Jeff"]


def test_modes_and_spelling_work_there(other_program: _OtherProgram) -> None:
    other_program.hear("all caps on", "note", "all caps off")
    other_program.hear("start spelling", "jay", "oscar", "stop spelling")
    assert other_program.typed == ["NOTE", " j", "o"]
