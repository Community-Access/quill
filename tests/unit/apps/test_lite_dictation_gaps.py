"""The 2026-10-05 dictation gap plan in QUILL Lite, through the handlers and the
voice: punctuation said in the read-back, clips and snippets by voice, words as
targets, Markdown, the language switch, live transcripts, document context and
Dictation Status.

The recogniser is replaced (no microphone); everything after a phrase arrives
is the shipped code -- the shared controller, the composer, the document port
writing into the window's control, and the window's own commands.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.abbreviations import AbbreviationLibrary
from quill.core.windows_dictation import RecognizedPhrase, words_from_text
from quill.ui import windows_dictation_commands as shared


class FakeRecognizer:
    def __init__(self, controller: Any, preferences: Any) -> None:
        self.controller = controller
        self.preferences = preferences
        self.stopped = 0

    def start(self, microphone: str) -> None:
        del microphone

    def stop(self) -> None:
        self.stopped += 1

    def hear(self, text: str) -> None:
        self.controller.on_phrase(RecognizedPhrase(words_from_text(text)))


@pytest.fixture
def recognizers(monkeypatch):
    made: list[FakeRecognizer] = []

    def make(controller: Any, preferences: Any) -> FakeRecognizer:
        recognizer = FakeRecognizer(controller, preferences)
        made.append(recognizer)
        return recognizer

    monkeypatch.setattr(shared, "_make_recognizer", make)
    monkeypatch.setattr(shared, "_controller", None)
    monkeypatch.setattr(shared, "_host", None)
    monkeypatch.setattr(shared, "_watched_tops", set())
    return made


@pytest.fixture
def focused(monkeypatch):
    holder: dict[str, Any] = {"control": None}
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: holder["control"]))
    return holder


def _window(lite_window, focused, text: str = "", cursor: int | None = None):
    win = lite_window(text, cursor=len(text) if cursor is None else cursor)
    win.available_sounds = frozenset(str(event) for event in shared.DICTATION_CUES.values())
    win.app.settings.windows_dictation_phrase_feedback = "speech"
    focused["control"] = win.control
    return win


def _start(win, made):
    win.cmd_toggle_dictation()
    assert win.dictation_active()
    return made[-1]


# -- punctuation in the read-back (dict.md 3.1) ----------------------------- #


def test_the_read_back_says_each_mark_by_name(lite_window, recognizers, focused):
    win = _window(lite_window, focused)
    _start(win, recognizers).hear("hello comma world period")
    assert win.control.GetValue() == "Hello, world."
    assert "Hello comma world period" in win.announcements


def test_the_marks_can_be_left_to_the_screen_reader(lite_window, recognizers, focused):
    win = _window(lite_window, focused)
    win.app.settings.windows_dictation_readback_marks = False
    _start(win, recognizers).hear("hello comma world period")
    assert "Hello, world." in win.announcements


# -- clips, snippets and Copy All by voice (dict.md 3.2) --------------------- #


def test_copy_all_by_voice_runs_the_editors_own_copy_all(
    lite_window, recognizers, focused, monkeypatch
):
    win = _window(lite_window, focused, "Every word here.")
    copied: list[str] = []
    monkeypatch.setattr(win, "_set_clipboard_text", lambda text: copied.append(text) or True)
    _start(win, recognizers).hear("copy all")
    assert copied == ["Every word here."]
    assert any("Copied the whole document" in line for line in win.announcements)


def test_paste_clip_three_writes_that_slot_as_one_phrase(lite_window, recognizers, focused):
    win = _window(lite_window, focused, "Start. ")
    win.app.copy_tray.copy_to(3, "from the tray")
    recognizer = _start(win, recognizers)
    recognizer.hear("paste clip three")
    assert win.control.GetValue() == "Start. from the tray"
    recognizer.hear("scratch that")
    assert win.control.GetValue() == "Start. "


def test_an_empty_slot_is_said_and_nothing_is_written(lite_window, recognizers, focused):
    win = _window(lite_window, focused)
    _start(win, recognizers).hear("paste slot five")
    assert win.control.GetValue() == ""
    assert "Slot 5 is empty." in win.announcements


def test_insert_snippet_by_name_uses_the_snippets_list(lite_window, recognizers, focused):
    win = _window(lite_window, focused)
    library = AbbreviationLibrary(version=1, abbreviations=[])
    library.add("sigoff", "Kind regards,\nJeff")
    win.app.abbreviations = library
    _start(win, recognizers).hear("insert snippet sig off")
    assert win.control.GetValue() == "Kind regards,\nJeff"
    assert "Snippet sigoff" in win.announcements


def test_a_snippet_nobody_has_is_said_and_not_guessed(lite_window, recognizers, focused):
    win = _window(lite_window, focused)
    win.app.abbreviations = AbbreviationLibrary(version=1, abbreviations=[])
    _start(win, recognizers).hear("insert snippet nothing like it")
    assert win.control.GetValue() == ""
    assert "No snippet called nothing like it." in win.announcements


def test_show_clips_opens_the_copy_tray(lite_window, recognizers, focused, monkeypatch):
    win = _window(lite_window, focused)
    opened: list[str] = []
    monkeypatch.setattr(win, "cmd_paste_from_tray", lambda: opened.append("tray"))
    monkeypatch.setattr(wx, "CallAfter", lambda function, *args: function(*args))
    _start(win, recognizers).hear("show clips")
    assert opened == ["tray"]


# -- characters, spelling and Markdown (dict.md 3.3) ------------------------- #


def test_markdown_line_marks_start_a_line(lite_window, recognizers, focused):
    win = _window(lite_window, focused, "Shopping list.")
    recognizer = _start(win, recognizers)
    recognizer.hear("heading two groceries")
    recognizer.hear("bullet milk")
    assert win.control.GetValue() == "Shopping list.\n## Groceries\n- Milk"


def test_spelling_takes_punctuation_and_all_caps(lite_window, recognizers, focused):
    win = _window(lite_window, focused)
    recognizer = _start(win, recognizers)
    recognizer.hear("spell all caps alpha bravo no caps charlie dot delta")
    assert win.control.GetValue() == "ABc.d"


def test_spell_that_replaces_the_last_phrase_with_letters(lite_window, recognizers, focused):
    win = _window(lite_window, focused, "Name: ")
    recognizer = _start(win, recognizers)
    recognizer.hear("shawn")
    recognizer.hear("spell that")
    recognizer.hear("capital sierra echo alpha november")
    assert win.control.GetValue() == "Name: Sean"
    assert not shared._controller.spelling  # one phrase only


def test_caps_on_capitalises_every_word_until_off(lite_window, recognizers, focused):
    win = _window(lite_window, focused, "Title: ")
    recognizer = _start(win, recognizers)
    recognizer.hear("caps on")
    recognizer.hear("the old man and the sea")
    recognizer.hear("caps off")
    assert win.control.GetValue() == "Title: The Old Man And The Sea"
    assert "Caps on." in win.announcements


# -- words as targets (dict.md 3.4) ----------------------------------------- #


def test_select_words_selects_the_nearest_match_before_the_cursor(
    lite_window, recognizers, focused
):
    win = _window(lite_window, focused, "The cat sat. The cat ran.")
    recognizer = _start(win, recognizers)
    recognizer.hear("select the cat")
    assert win.control.GetSelection() == (13, 20)
    assert "Selected: The cat." in win.announcements
    recognizer.hear("a dog")
    assert win.control.GetValue() == "The cat sat. A dog ran."


def test_words_that_are_not_there_are_written_as_text(lite_window, recognizers, focused):
    win = _window(lite_window, focused, "Hello. ")
    _start(win, recognizers).hear("go to the store")
    assert win.control.GetValue() == "Hello. Go to the store"
    assert "Not found, written as text." in win.announcements


def test_go_after_puts_the_cursor_after_the_words(lite_window, recognizers, focused):
    win = _window(lite_window, focused, "One two three.")
    _start(win, recognizers).hear("go after two")
    assert win.control.GetSelection() == (7, 7)


# -- the language, the transcript, the context, the status ------------------- #


def test_switch_dictation_language_when_off_saves_and_says_it(lite_window, recognizers, focused):
    win = _window(lite_window, focused)
    before = win.app.saved_settings
    win.cmd_switch_dictation_language()
    assert win.app.settings.windows_dictation_speech_language == "es"
    assert win.app.saved_settings > before
    assert "Español." in win.announcements
    win.cmd_switch_dictation_language()
    assert win.app.settings.windows_dictation_speech_language == "en"


def test_switching_while_dictating_reopens_the_engine_in_the_new_language(
    lite_window, recognizers, focused
):
    win = _window(lite_window, focused)
    first = _start(win, recognizers)
    win.cmd_switch_dictation_language()
    assert first.stopped == 1
    assert recognizers[-1].preferences.speech_language == "es"
    assert win.dictation_active()


def test_switch_to_spanish_by_voice_and_back(lite_window, recognizers, focused):
    win = _window(lite_window, focused)
    _start(win, recognizers).hear("switch to spanish")
    assert win.app.settings.windows_dictation_speech_language == "es"
    recognizers[-1].hear("cambiar a inglés")
    assert win.app.settings.windows_dictation_speech_language == "en"


def test_live_transcript_writes_quietly_into_a_new_document(
    lite_window, recognizers, focused, monkeypatch
):
    win = _window(lite_window, focused, "My own notes.")
    transcript = lite_window("")
    monkeypatch.setattr(win.app, "new_window", lambda *_a, **_k: transcript)
    win.cmd_live_transcript()
    controller = shared._controller
    assert controller.transcribing
    recognizer = recognizers[-1]
    recognizer.hear("welcome everyone period scratch that")
    assert transcript.control.GetValue() == "Welcome everyone. Scratch that"
    assert win.control.GetValue() == "My own notes."
    assert "Welcome everyone" not in " ".join(transcript.announcements)
    assert "Please record other people only when they have agreed." in win.announcements
    win.cmd_live_transcript()
    assert not controller.transcribing
    assert any("Live transcript stopped, 4 words." in line for line in transcript.announcements)


def test_dictation_context_is_kept_for_the_document(lite_window, recognizers, focused, monkeypatch):
    from quill.ui import dictation_context_dialog

    class FakeContext:
        def __init__(self, _parent: Any, current: str, choices: dict[str, str], **_k: Any):
            self.current = current
            self.choices = choices

        def values(self) -> tuple[str, str]:
            return "A formal letter to a client.", "Client letter"

        def Destroy(self) -> None:  # noqa: N802 - wx API shape
            pass

    monkeypatch.setattr(dictation_context_dialog, "DictationContextDialog", FakeContext)
    win = _window(lite_window, focused)
    win.path = win.app.data_dir / "letter.txt"
    win.path.write_text("", encoding="utf-8")
    monkeypatch.setattr(win, "_dictation_run_modal", lambda _d, _l: wx.ID_OK)
    win.cmd_dictation_context()
    assert win._dictation_document_context() == "A formal letter to a client."
    assert "Dictation context saved for this document." in win.announcements


def test_dictation_status_says_what_dictation_is_doing(lite_window, recognizers, focused):
    win = _window(lite_window, focused)
    win.cmd_dictation_status()
    assert win.announcements[-1].startswith("Dictation is off.")
    _start(win, recognizers).hear("caps on")
    win.cmd_dictation_status()
    assert "Caps on." in win.announcements[-1]
    assert win.announcements[-1].startswith("Dictation on,")
