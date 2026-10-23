"""Tools > Dictation in QUILL Lite, through the handlers the menu binds.

The recogniser is replaced: nothing here opens a microphone. What is exercised
is everything after Windows hands over a phrase -- the shared controller, the
real composer, the document port writing into the window's control, and the
cues and speech the window actually makes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import wx

from quill.core.sound_events import SoundEvent
from quill.core.windows_dictation import RecognizedPhrase, words_from_text
from quill.core.windows_dictation.controller import DictationStartError
from quill.ui import windows_dictation_commands as shared


class FakeRecognizer:
    def __init__(self, controller: Any, *, fail: str = "") -> None:
        self.controller = controller
        self.fail = fail
        self.microphone: str | None = None
        self.stopped = 0

    def start(self, microphone: str) -> None:
        if self.fail:
            raise DictationStartError(self.fail)
        self.microphone = microphone

    def stop(self) -> None:
        self.stopped += 1

    def hear(self, text: str) -> None:
        self.controller.on_phrase(RecognizedPhrase(words_from_text(text)))


@pytest.fixture
def recognizers(monkeypatch):
    made: list[FakeRecognizer] = []
    made_preferences: list[Any] = []
    failure = {"message": ""}

    def make(controller: Any, preferences: Any) -> FakeRecognizer:
        made_preferences.append(preferences)
        recognizer = FakeRecognizer(controller, fail=failure["message"])
        made.append(recognizer)
        return recognizer

    monkeypatch.setattr(shared, "_make_recognizer", make)
    monkeypatch.setattr(shared, "_controller", None)
    monkeypatch.setattr(shared, "_host", None)
    monkeypatch.setattr(shared, "_watched_tops", set())
    made_failure = failure
    return made, made_failure


@pytest.fixture
def focused(monkeypatch):
    """Put the focus on whichever control the test names."""
    holder: dict[str, Any] = {"control": None}
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: holder["control"]))
    return holder


def _window(lite_window, focused, text: str = "", cursor: int | None = None):
    win = lite_window(text, cursor=len(text) if cursor is None else cursor)
    win.available_sounds = frozenset(str(event) for event in shared.DICTATION_CUES.values())
    focused["control"] = win.control
    return win


def test_dictation_on_writes_each_phrase_and_reads_it_back(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    win.app.settings.windows_dictation_phrase_feedback = "both"

    win.cmd_toggle_dictation()

    assert win.dictation_active()
    assert SoundEvent.WINDOWS_DICTATION_ON in win.cues
    assert "Dictation on." in win.announcements
    made[0].hear("hello everyone period new paragraph welcome back")
    assert win.control.GetValue() == "Hello everyone.\n\nWelcome back"
    assert SoundEvent.WINDOWS_DICTATION_PHRASE in win.cues
    # The read-back: the words that went in, not a count and not "inserted" --
    # and the marks by name (dict.md 3.1), whatever the reader's punctuation level.
    assert "Hello everyone period new paragraph Welcome back" in win.announcements


def test_the_next_phrase_joins_the_last_with_one_space(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused, "Dear Sam")
    win.cmd_toggle_dictation()
    made[0].hear("comma")
    made[0].hear("thank you for the letter period")
    assert win.control.GetValue() == "Dear Sam, thank you for the letter."


def test_sound_only_feedback_does_not_read_back(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    win.app.settings.windows_dictation_phrase_feedback = "sound"
    win.cmd_toggle_dictation()
    made[0].hear("quiet words")
    assert "Quiet words" not in win.announcements
    assert SoundEvent.WINDOWS_DICTATION_PHRASE in win.cues


def test_scratch_that_removes_exactly_the_last_phrase(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused, "Kept.")
    win.cmd_toggle_dictation()
    made[0].hear("first try")
    made[0].hear("scratch that")
    assert win.control.GetValue() == "Kept."
    assert any(line.startswith("Scratched") for line in win.announcements)


def test_pressing_it_again_stops_and_closes_the_recogniser(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    win.cmd_toggle_dictation()
    win.cmd_toggle_dictation()
    assert not win.dictation_active()
    assert made[0].stopped == 1
    assert SoundEvent.WINDOWS_DICTATION_OFF in win.cues
    assert "Dictation off." in win.announcements


def test_the_chosen_microphone_is_the_one_opened(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    win.app.settings.windows_dictation_microphone = "token-for-headset"
    win.cmd_toggle_dictation()
    assert made[0].microphone == "token-for-headset"


def test_a_start_failure_is_spoken_and_leaves_it_off(lite_window, recognizers, focused):
    _, failure = recognizers
    failure["message"] = "No microphone was found. Connect one and try again."
    win = _window(lite_window, focused)
    win.cmd_toggle_dictation()
    assert not win.dictation_active()
    assert "No microphone was found. Connect one and try again." in win.announcements
    assert SoundEvent.WINDOWS_DICTATION_ERROR in win.cues


def test_a_phrase_heard_after_focus_left_is_not_written(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused, "Safe.")
    win.cmd_toggle_dictation()
    focused["control"] = object()  # a dialog, another window, another program
    made[0].hear("this must go nowhere")
    assert win.control.GetValue() == "Safe."
    assert not win.dictation_active()
    assert made[0].stopped == 1
    assert any("no longer has the focus" in line for line in win.announcements)


class _FakeSettingsDialog:
    answer = wx.ID_CANCEL

    def __init__(self, parent: Any, settings: Any, announce: Any = None, **kwargs: Any) -> None:
        self.settings = settings
        self.destroyed = False
        self.my_words = kwargs.get("my_words")  # the command word may not be one (D-1)

    def apply(self, settings: Any) -> None:
        settings.windows_dictation_microphone = "chosen"
        settings.windows_dictation_phrase_feedback = "speech"

    def Destroy(self) -> None:  # noqa: N802 - wx API shape
        self.destroyed = True


@pytest.fixture
def settings_dialog(monkeypatch):
    from quill.ui import windows_dictation_dialog

    monkeypatch.setattr(windows_dictation_dialog, "WindowsDictationDialog", _FakeSettingsDialog)
    monkeypatch.setattr(
        shared.WindowsDictationMixin,
        "_dictation_run_modal",
        lambda self, dialog, label: _FakeSettingsDialog.answer,
    )
    return _FakeSettingsDialog


def test_dictation_settings_saves_what_ok_chose(lite_window, settings_dialog, focused):
    settings_dialog.answer = wx.ID_OK
    win = _window(lite_window, focused)
    before = win.app.saved_settings
    win.cmd_dictation_settings()
    assert win.app.settings.windows_dictation_microphone == "chosen"
    assert win.app.settings.windows_dictation_phrase_feedback == "speech"
    assert win.app.saved_settings == before + 1


def test_dictation_settings_cancel_changes_nothing(lite_window, settings_dialog, focused):
    settings_dialog.answer = wx.ID_CANCEL
    win = _window(lite_window, focused)
    before = win.app.saved_settings
    win.cmd_dictation_settings()
    assert win.app.settings.windows_dictation_microphone == ""
    assert win.app.saved_settings == before


def test_the_commands_button_opens_the_list(lite_window, settings_dialog, focused, monkeypatch):
    from quill.ui import windows_dictation_dialog as dialogs

    shown: list[str] = []

    class FakeList:
        def __init__(self, _parent: Any, body: str) -> None:
            shown.append(body)

        def Destroy(self) -> None:  # noqa: N802 - wx API shape
            pass

    monkeypatch.setattr(dialogs, "DictationCommandsDialog", FakeList)
    settings_dialog.answer = dialogs.SHOW_COMMANDS
    win = _window(lite_window, focused)
    win.cmd_dictation_settings()
    assert shown and "scratch that" in shown[0]


class _WordsWindow:
    """Stands in for DictationWordsDialog: records how it was opened."""

    opened: list[dict[str, Any]] = []

    def __init__(
        self, parent: Any, path: Path, *, say: Any, open_file: Any = None, shared: Any = None
    ) -> None:
        _WordsWindow.opened.append({
            "parent": parent,
            "path": path,
            "say": say,
            "open": open_file,
            "shared": shared,
        })

    def ShowModal(self) -> int:  # noqa: N802 - wx API shape
        return wx.ID_CANCEL

    def Destroy(self) -> None:  # noqa: N802 - wx API shape
        pass


@pytest.fixture
def words_window(monkeypatch):
    from quill.ui import dictation_words_dialog as module

    _WordsWindow.opened = []
    monkeypatch.setattr(module, "DictationWordsDialog", _WordsWindow)
    return _WordsWindow.opened


def test_the_words_button_saves_and_opens_the_words_window(
    lite_window, settings_dialog, focused, words_window
):
    """dict.md 5: the button opens a window that edits the file, not the file."""
    from quill.ui import windows_dictation_dialog as dialogs

    settings_dialog.answer = dialogs.EDIT_WORDS
    win = _window(lite_window, focused)
    before = win.app.saved_settings
    win.cmd_dictation_settings()
    assert win.app.saved_settings == before + 1
    assert words_window and words_window[-1]["path"] == win.app.data_dir / "dictation.md"
    assert win.app.opened == []  # nothing opened as a document


def test_my_words_and_phrases_is_its_own_command(lite_window, focused, words_window):
    win = _window(lite_window, focused)
    win.cmd_dictation_words()
    assert words_window[-1]["path"] == win.app.data_dir / "dictation.md"
    # The window's Open the File button is the old door, still there.
    words_window[-1]["open"](win.app.data_dir / "dictation.md")
    assert win.app.opened[-1][0][0] == win.app.data_dir / "dictation.md"


def test_a_correction_added_through_the_model_is_heard(lite_window, recognizers, focused):
    """A correction is a replacement at recognition time: no new runtime path."""
    from quill.core.windows_dictation.words_file import Entry, WordsFile, save_words

    made, _ = recognizers
    win = _window(lite_window, focused)
    words = WordsFile()
    words.add(Entry("correction", "quill light", "QUILL Lite"))
    save_words(win.app.data_dir / "dictation.md", words)
    win.cmd_toggle_dictation()
    made[0].hear("I write in quill light")
    assert win.control.GetValue() == "I write in QUILL Lite"


def test_my_words_offers_the_shared_list_and_a_word_added_here_reaches_transcribe(
    lite_window, recognizers, focused, words_window, quill_data_dir
):
    """dict.md D-12: with "Use the shared word list" checked, QUILL Lite edits and
    dictates with the one ``dictation.md`` QUILL Transcribe reads per phrase."""
    from quill.core.speech.dictation_profile import default_profile_path
    from quill.core.windows_dictation.profile import rewriter
    from quill.core.windows_dictation.words_file import Entry, load_words, save_words

    made, _ = recognizers
    win = _window(lite_window, focused)
    win.cmd_dictation_words()
    shared = words_window[-1]["shared"]
    assert shared is not None and not shared.is_on()
    assert win._dictation_profile_path() == win.app.data_dir / "dictation.md"

    before = win.app.saved_settings
    shared.set_on(True)
    assert win.app.settings.share_quill_dictation_words is True
    assert win.app.saved_settings == before + 1
    assert win._dictation_profile_path() == default_profile_path()

    words = load_words(win._dictation_profile_path())
    words.add(Entry("correction", "doctor oh conk woe", "Dr Okonkwo"))
    save_words(win._dictation_profile_path(), words)
    # What QUILL Transcribe runs on its next phrase (transcribe_dictation.py).
    assert rewriter(default_profile_path())("ask doctor oh conk woe") == "ask Dr Okonkwo"
    win.cmd_toggle_dictation()
    made[0].hear("ask doctor oh conk woe")
    assert win.control.GetValue() == "Ask Dr Okonkwo"  # the composer capitalizes


def test_a_portable_quill_lite_keeps_its_own_word_list(
    lite_window, focused, words_window, monkeypatch
):
    import quill.core.lite.paths as lite_paths

    monkeypatch.setattr(lite_paths, "_portable_root", lambda: win.app.data_dir)
    win = _window(lite_window, focused)
    win.app.settings.share_quill_dictation_words = True  # carried over from elsewhere
    win.cmd_dictation_words()
    assert words_window[-1]["shared"] is None
    assert win._dictation_profile_path() == win.app.data_dir / "dictation.md"


def test_windows_voice_typing_hands_over_and_opens_no_microphone(
    lite_window, recognizers, focused, monkeypatch
):
    import quill.platform.windows.dictation as windows_dictation

    made, _ = recognizers
    launched: list[bool] = []
    monkeypatch.setattr(
        windows_dictation, "launch_windows_dictation", lambda: launched.append(True)
    )
    win = _window(lite_window, focused)
    win.app.settings.windows_dictation_engine = "voice_typing"
    win.cmd_toggle_dictation()
    assert launched == [True]
    assert made == []


def test_the_status_cell_follows_the_state(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    assert win.dictation_state_text() == ""
    win.cmd_toggle_dictation()
    assert win.dictation_state_text() == "Dictation: listening"
    made[0].hear("start spelling")
    assert win.dictation_state_text() == "Dictation: spelling"


def test_my_own_phrases_are_used_while_dictating(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    (win.app.data_dir / "dictation.md").write_text(
        "## Replacements" + chr(10) + "my town => Tucson, Arizona" + chr(10), encoding="utf-8"
    )
    win.cmd_toggle_dictation()
    made[0].hear("I live in my town")
    assert win.control.GetValue() == "I live in Tucson, Arizona"


# -- Recent Phrases (dict.md 3.3) --------------------------------------------- #


class _RecentWindow:
    """Stands in for RecentPhrasesDialog: answers with a chosen phrase and a verb."""

    answer: tuple[str | None, str] = (None, "insert")
    shown: list[list[str]] = []

    chosen_row = None

    def __init__(self, _parent: Any, phrases: list[str], **_kept: Any) -> None:
        _RecentWindow.shown.append(list(phrases))
        self.chosen, self.verb = _RecentWindow.answer

    def Destroy(self) -> None:  # noqa: N802 - wx API shape
        pass


@pytest.fixture
def recent_window(monkeypatch):
    from quill.ui import windows_dictation_dialog as dialogs

    _RecentWindow.shown = []
    _RecentWindow.answer = (None, "insert")
    monkeypatch.setattr(dialogs, "RecentPhrasesDialog", _RecentWindow)
    monkeypatch.setattr(shared, "_dictation_run_modal_answer", wx.ID_OK, raising=False)
    return _RecentWindow


def test_recent_phrases_with_nothing_said_yet(lite_window, focused, recent_window):
    win = _window(lite_window, focused)
    win.cmd_dictation_recent()
    assert recent_window.shown == []
    assert "Nothing has been dictated yet this session." in win.announcements


def test_recent_phrases_lists_newest_first_and_inserts_again(
    lite_window, recognizers, focused, recent_window, monkeypatch
):
    made, _ = recognizers
    win = _window(lite_window, focused)
    win.cmd_toggle_dictation()
    made[0].hear("first phrase")
    made[0].hear("second phrase")
    win.cmd_toggle_dictation()  # off; the list survives the session ending
    monkeypatch.setattr(win, "_dictation_run_modal", lambda _d, _l: wx.ID_OK)
    recent_window.answer = ("First phrase", "insert")
    win.control.SetSelection(0, 0)
    win.cmd_dictation_recent()
    assert [p.lower() for p in recent_window.shown[0]] == ["second phrase", "first phrase"]
    assert win.control.GetValue().startswith("First phrase")
    assert "Inserted: First phrase" in win.announcements


def test_recent_phrases_copy_puts_it_on_the_clipboard(
    lite_window, recognizers, focused, recent_window, monkeypatch
):
    made, _ = recognizers
    win = _window(lite_window, focused)
    win.cmd_toggle_dictation()
    made[0].hear("keep this")
    monkeypatch.setattr(win, "_dictation_run_modal", lambda _d, _l: wx.ID_OK)
    copied: list[str] = []

    class _Clipboard:
        def Open(self) -> bool:  # noqa: N802
            return True

        def SetData(self, data: Any) -> None:  # noqa: N802
            copied.append(data.GetText())

        def Close(self) -> None:  # noqa: N802
            pass

    monkeypatch.setattr(wx, "TheClipboard", _Clipboard())
    recent_window.answer = ("Keep this", "copy")
    before = win.control.GetValue()
    win.cmd_dictation_recent()
    assert copied == ["Keep this"]
    assert win.control.GetValue() == before
    assert "Copied: Keep this" in win.announcements


# -- Escape cancels the phrase being heard (dict.md 2.2) ---------------------- #


class _Key:
    def __init__(self, code: int) -> None:
        self.code = code
        self.skipped = False

    def GetKeyCode(self) -> int:  # noqa: N802
        return self.code

    def Skip(self, skip: bool = True) -> None:  # noqa: N802
        self.skipped = skip


def test_escape_throws_away_the_phrase_being_heard(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    win.cmd_toggle_dictation()
    made[0].controller.on_speech_started()
    assert win.dictation_state_text() == "Dictation: hearing you"
    key = _Key(wx.WXK_ESCAPE)
    win._dictation_cancel_key(key)
    assert key.skipped is False  # consumed
    assert "Cancelled." in win.announcements
    assert win.dictation_state_text() == "Dictation: listening"
    made[0].hear("the words that were being heard")
    assert win.control.GetValue() == ""
    made[0].controller.on_speech_started()
    made[0].hear("the next thing")
    assert win.control.GetValue() == "The next thing"


def test_escape_passes_through_when_nothing_is_being_heard(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)
    key = _Key(wx.WXK_ESCAPE)
    win._dictation_cancel_key(key)
    assert key.skipped is True  # dictation off: not ours
    win.cmd_toggle_dictation()
    key = _Key(wx.WXK_ESCAPE)
    win._dictation_cancel_key(key)
    assert key.skipped is True  # listening, nothing heard: not ours either
    assert "Cancelled." not in win.announcements
    other = _Key(wx.WXK_F2)
    win._dictation_cancel_key(other)
    assert other.skipped is True


# -- One Ctrl+Z per phrase (dict.md 2.5) --------------------------------------- #


def test_a_phrase_over_a_selection_is_one_undo_step(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused, "keep THIS keep")
    win.control.SetSelection(5, 9)
    win.cmd_toggle_dictation()
    made[0].hear("that")
    assert win.control.GetValue() == "keep that keep"
    win.control.Undo()
    assert win.control.GetValue() == "keep THIS keep"


# -- Read-only documents (dict.md 2.6) ---------------------------------------- #


def test_a_read_only_document_refuses_before_the_microphone_opens(
    lite_window, recognizers, focused, monkeypatch
):
    made, _ = recognizers
    win = _window(lite_window, focused)
    monkeypatch.setattr(win.control, "IsEditable", lambda: False)
    win.cmd_toggle_dictation()
    assert made == []  # no recogniser was even made
    assert not win.dictation_active()
    assert "This document is read-only, so dictation cannot write here." in win.announcements


# -- One session at a time (dict.md 2.8) -------------------------------------- #


def test_ctrl_f11_in_a_second_document_moves_dictation_there(lite_window, recognizers, focused):
    made, _ = recognizers
    first = _window(lite_window, focused)
    second = lite_window("")
    second.available_sounds = first.available_sounds
    first.cmd_toggle_dictation()
    made[0].hear("in the first")
    focused["control"] = second.control
    second.cmd_toggle_dictation()
    assert first.dictation_active() is False
    assert second.dictation_active() is True
    assert any(a.startswith("Dictation moved to ") for a in second.announcements)
    assert len(made) == 1  # the same microphone, not a second one
    made[0].hear("and now the second")
    assert first.control.GetValue() == "In the first"
    assert second.control.GetValue() == "And now the second"


# -- Dictate into any text field (dict.md 3.1) -------------------------------- #


def test_ctrl_f11_in_a_one_line_field_dictates_there(lite_window, recognizers, focused):
    made, _ = recognizers
    win = _window(lite_window, focused)

    class _OneLine(type(win.control)):  # the fixture's own control, made one-line
        def IsMultiLine(self) -> bool:  # noqa: N802
            return False

    field = _OneLine("")
    focused["control"] = field
    win.cmd_dictation_into(field)
    assert win.dictation_active()
    made[0].hear("hello new paragraph world")
    assert field.GetValue().lower() == "hello world"  # a paragraph break is a space in a box
    assert win.control.GetValue() == ""
    win.cmd_dictation_into(field)  # again: off
    assert not win.dictation_active()


# -- The microphone watchdog, as the window shows it (dict.md 2.3) ------------ #


def test_the_status_cell_says_paused_while_the_microphone_is_gone(
    lite_window, recognizers, focused
):
    made, _ = recognizers
    win = _window(lite_window, focused)
    win.cmd_toggle_dictation()
    made[0].controller.on_microphone_lost()
    assert win.dictation_state_text() == "Dictation: paused, microphone lost"
    assert win.dictation_active()  # the menu mark stays on
    made[0].controller.on_microphone_back()
    assert win.dictation_state_text() == "Dictation: listening"


def test_the_working_tick_plays_in_quill_lite_when_switched_on(
    lite_window, recognizers, focused, monkeypatch
) -> None:
    """D-17 through the shared code: off by default, and when chosen, the
    window's own cue after a second of waiting for a phrase."""
    from quill.ui.windows_dictation_ports import HostFeedback

    later: list[Any] = []

    class _Handle:
        def Stop(self) -> None:  # noqa: N802
            pass

    def call_later(_self: Any, seconds: float, callback: Any) -> _Handle:
        later.append(callback)
        return _Handle()

    monkeypatch.setattr(HostFeedback, "call_later", call_later)
    made, _ = recognizers
    win = _window(lite_window, focused)
    assert win.app.settings.windows_dictation_working_tick is False
    win.app.settings.windows_dictation_working_tick = True
    win.cmd_toggle_dictation()
    controller = made[0].controller
    controller.on_speech_started()
    controller.on_phrase_decoding()
    assert later, "the tick's first wait was not scheduled"
    later.pop(0)()
    assert SoundEvent.WINDOWS_DICTATION_WORKING in win.cues
    made[0].hear("there it is")
    assert win.control.GetValue() == "There it is"


# -- the command word and Speak a Command (D-1, 2026-10-15) ------------------------- #


def test_speak_a_command_starts_dictation_and_takes_one_command(
    lite_window, recognizers, focused, monkeypatch
) -> None:
    """F11 in QUILL Lite, through the shared handler QUILL runs too: off, it
    starts dictation here with one command armed; the next phrase is a command
    and is never written; twice, command mode, shown in the status cell."""
    from quill.apps.lite_window_dictation import dictation_cell
    from quill.ui.windows_dictation_ports import HostFeedback

    monkeypatch.setattr(HostFeedback, "call_later", lambda _s, _sec, _cb: None)
    made, _ = recognizers
    win = _window(lite_window, focused, "Kept.")
    win.cmd_dictation_command()
    assert win.dictation_active()
    assert SoundEvent.WINDOWS_DICTATION_COMMAND_ON in win.cues
    assert dictation_cell(win) == "Waiting for a command"
    made[0].hear("pancakes")  # not a command: nothing written
    assert win.control.GetValue() == "Kept."
    assert any(line.startswith("Not a command.") for line in win.announcements)
    win.cmd_dictation_command()
    win.cmd_dictation_command()
    assert dictation_cell(win) == "Command mode"
    win.cmd_dictation_command()
    assert SoundEvent.WINDOWS_DICTATION_COMMAND_OFF in win.cues
    assert dictation_cell(win) == "Listening"


def test_the_command_word_works_in_quill_lite(lite_window, recognizers, focused) -> None:
    made, _ = recognizers
    win = _window(lite_window, focused, "Kept.")
    win.cmd_toggle_dictation()
    made[0].hear("first try")
    made[0].hear("quill scratch that")
    assert win.control.GetValue() == "Kept."
    made[0].hear("literal quill is open")
    assert "QUILL is open" in win.control.GetValue()


def test_a_saved_switch_offers_the_old_models_files(
    lite_window, settings_dialog, focused, monkeypatch
):
    """The offer comes after OK saved the switch, never from inside Speech
    Models: cancelling Dictation Settings must not leave a deleted model saved."""
    import quill.ui.dictation_models_dialog as library

    offered: list[tuple[str, str, bool]] = []
    monkeypatch.setattr(
        library,
        "offer_to_remove_replaced",
        lambda _p, old, new, _say, in_use=False: offered.append((old, new, in_use)),
    )

    def switch(self, settings):
        settings.windows_dictation_engine = "parakeet"

    monkeypatch.setattr(settings_dialog, "apply", switch)
    win = _window(lite_window, focused)
    win.app.settings.windows_dictation_engine = "whisper_small"
    settings_dialog.answer = wx.ID_OK
    win.cmd_dictation_settings()
    assert offered == [("whisper_small", "parakeet", False)]
    offered.clear()
    for answer in (wx.ID_CANCEL, shared_dialogs().EDIT_WORDS):
        settings_dialog.answer = answer  # not ahead of a window the person asked for
        monkeypatch.setattr(win, "cmd_dictation_words", lambda: None)
        win.cmd_dictation_settings()
    assert offered == []


def shared_dialogs():
    from quill.ui import windows_dictation_dialog

    return windows_dictation_dialog
