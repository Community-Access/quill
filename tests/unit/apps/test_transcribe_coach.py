"""QUILL Transcribe's Practice Dictation, recognition test, tutorials and
profiles (D-25, D-23), with the shared controller over a fake desktop.

The Practice window is built for real (in memory, never shown to a person and
sent no input); the recogniser is a stand-in, so no microphone opens and
nothing is typed into any other program.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import wx

from quill.apps import transcribe_coach, transcribe_dictation
from quill.apps.transcribe_coach import ProfileDialog, TranscribeCoachMixin, _LessonHost
from quill.apps.transcribe_commands import TranscribeCommandsMixin
from quill.apps.transcribe_dictation import TranscribeDictationMixin, _Feedback
from quill.apps.transcribe_practice import TITLE, PracticeDictationFrame, PracticeFieldDocument
from quill.core.dictation_owner import MicrophoneLock, OwnerLock
from quill.core.transcribe import models, surface_help
from quill.core.transcribe.practice import SENTENCES, next_sentence, score
from quill.core.transcribe.settings import TranscribeSettings
from quill.core.transcribe.tutorials import CATALOGUE, LOCAL_COMMANDS, key_for, method_for
from quill.core.windows_dictation import DictationController, RecognizedPhrase, words_from_text
from quill.core.windows_dictation.target_lock import LockedTarget
from quill.core.windows_dictation.word_errors import word_errors
from quill.ui.windows_dictation_external import ExternalDocument
from tests.wx_session import shared_wx_app

_ROOT = Path(__file__).resolve().parents[3]


class _World:
    def __init__(self) -> None:
        self.field: Any = ("notepad", 1, "edit-1")
        self.typed: list[str] = []

    def type_text(self, text: str) -> bool:
        self.typed.append(text)
        return True


class _Recognizer:
    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass


class Host(TranscribeDictationMixin, TranscribeCommandsMixin, TranscribeCoachMixin):
    def __init__(self, data_dir: Path) -> None:
        self.frame = wx.Frame(None)  # never shown; a parent for the profile window
        self._settings = TranscribeSettings(dictation={"windows_dictation_engine": "windows"})
        self._data_dir = data_dir
        self._safe_mode = False
        self._engine_override = ""
        self.said: list[str] = []
        self.status: list[str] = []
        self.modal: Any = None
        self.world = _World()
        self._owner_lock = OwnerLock("transcribe", folder=data_dir / "ipc")
        self._microphone = MicrophoneLock("transcribe")
        inner = ExternalDocument(
            problem=lambda: "", where=lambda: self.world.field, type_text=self.world.type_text
        )
        self._dictation_document = LockedTarget(inner, where=lambda: self.world.field)
        self._dictation = DictationController(
            recognizer=lambda _c, _p: _Recognizer(),
            document=self._dictation_document,
            feedback=_Feedback(self),
            preferences=lambda: replace(self._dictation_preferences(), phrase_feedback="silent"),
            microphone=self._microphone,
        )

    def _announce(self, text: str, *, force: bool = False, sound: str = "") -> None:
        self.said.append(text)

    def _set_status(self, text: str) -> None:
        self.status.append(text)

    def _show_modal_dialog(self, dialog: Any, label: str) -> int:
        return int(self.modal(dialog, label))

    def _braille_state_change(self) -> None:
        pass

    def hear(self, text: str) -> None:
        self._dictation.on_phrase(RecognizedPhrase(words_from_text(text)))


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App.Get() or shared_wx_app()
    yield app


@pytest.fixture()
def host(wx_app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(models, "start_problem", lambda *_a, **_k: "")
    monkeypatch.setattr(
        transcribe_dictation.TranscribeDictationMixin, "_front_is_own_window", lambda _s: False
    )
    monkeypatch.setattr(transcribe_coach.wx, "CallLater", _now)
    made = Host(tmp_path)
    yield made
    window = made._practice_window()
    if window is not None:
        window.Destroy()
    made._release_dictate_anywhere()
    made.frame.Destroy()


def _now(_ms: int, fn: Any, *args: Any) -> None:
    fn(*args)


# -- the Practice window ------------------------------------------------------------ #


def test_practice_dictates_into_its_own_field_and_never_another_program(host: Host) -> None:
    host.open_practice()
    window = host._practice_window()
    assert isinstance(window, PracticeDictationFrame) and window.GetTitle() == TITLE
    host.practice_start_or_stop()
    assert host._practicing()
    assert window.start.GetLabel() == "Stop Dictation &Here"
    host.hear("this is my first dictation")
    assert window.field.GetValue() == "This is my first dictation"
    assert host.world.typed == []
    host.practice_start_or_stop()
    assert not host.dictation_active()
    # Stopped by any route, dictation goes back to the field it is locked to.
    assert host._dictation.document is host._dictation_document
    assert window.start.GetLabel() == "Start Dictation &Here"


def test_practice_starts_only_after_the_same_refusals_as_any_start(host: Host) -> None:
    host._safe_mode = True
    host.practice_start_or_stop()
    assert not host.dictation_active()
    assert "Safe Mode" in host.said[-1]
    assert host._dictation.document is host._dictation_document


def test_practice_will_not_take_a_session_running_in_another_program(host: Host) -> None:
    host.start_dictation()
    host.open_practice()
    host.practice_start_or_stop()
    assert host._dictation.document is host._dictation_document
    assert "another program" in host.said[-1]


def test_closing_the_window_stops_practice_and_restores_the_field(host: Host) -> None:
    host.practice_start_or_stop()  # opens the window when it is not open
    window = host._practice_window()
    assert host._practicing()

    class _Close:
        skipped = False

        def Skip(self) -> None:  # noqa: N802
            self.skipped = True

    event = _Close()
    host._on_practice_close(event)
    assert event.skipped and not host.dictation_active()
    assert host._dictation.document is host._dictation_document
    window.Destroy()


def test_read_this_sentence_scores_the_first_phrase_and_says_it_once(host: Host) -> None:
    host.open_practice()
    window = host._practice_window()
    window.field.ChangeValue("old words")
    host.practice_read_sentence()
    assert window.field.GetValue() == ""  # cleared, so only the sentence counts
    assert host._practicing()
    host.hear("the quick brown fox jumps over the lazy dog")
    assert window.result.GetValue() == "All 9 words right. Recognition is working well."
    assert host.said[-1] == window.result.GetValue()
    host.hear("and more")  # the test is over: nothing else is scored
    assert host.said.count(window.result.GetValue()) == 1


def test_score_the_field_and_next_sentence(host: Host) -> None:
    host.open_practice()
    window = host._practice_window()
    window.field.ChangeValue("the quick brown fox jumped over the dog")
    host.practice_score_field()
    assert window.result.GetValue().startswith("78 percent right: 2 differences in 9 words.")
    assert "jumps, lazy" in window.result.GetValue()
    host.practice_next_sentence()
    assert window.sentence.GetValue() == SENTENCES[1]


def test_the_practice_field_is_plain_text(host: Host) -> None:
    host.open_practice()
    document = PracticeFieldDocument(host._practice_window().field)
    assert document.formatting() == ""
    assert document.unavailable_reason(writing=True) == ""


# -- the score ------------------------------------------------------------------------ #


def test_the_score_uses_the_benchmarks_scorer_and_ignores_case_and_marks() -> None:
    assert word_errors(["a", "b", "c"], ["a", "c"]) == 1
    assert score("Can you call me back?", "can you call me back").errors == 0
    weak = score("Please send the report to Maria", "please end the sport")
    assert weak.percent < 80 and "slower" in weak.sentence()
    assert score("", "anything").sentence() == "There was no sentence to compare with."
    assert next_sentence(SENTENCES[-1]) == SENTENCES[0]
    assert next_sentence("not one of them") == SENTENCES[0]


# -- profiles ---------------------------------------------------------------------------- #


def test_switching_by_voice_is_kept_and_shown(host: Host) -> None:
    host.start_dictation()
    host.hear("quill email mode")
    assert host._settings.dictation["windows_dictation_profile"] == "email"
    assert host.dictation_profile_name() == "Email"
    assert "Email profile." in host.said


def test_lock_profile_from_the_menu_stops_voice_switching(host: Host) -> None:
    host.toggle_profile_lock()
    assert host.profile_locked() and host.said[-1] == "Profile locked."
    host.start_dictation()
    host.hear("quill chat mode")
    assert host.dictation_profile_name() == "Standard"
    assert "Lock Profile is on" in host.said[-1]
    host.toggle_profile_lock()
    assert not host.profile_locked()


def test_the_profile_window_chooses_and_locks(host: Host) -> None:
    def answer(dialog: ProfileDialog, label: str) -> int:
        assert label == "Dictation Profile" and dialog.chosen() == "standard"
        dialog.list.SetSelection(3)  # Markdown
        dialog._describe()
        assert "Markdown marks" in dialog.about.GetValue()
        dialog.lock.SetValue(True)
        return wx.ID_OK

    host.modal = answer
    host.choose_dictation_profile()
    assert host.dictation_profile_name() == "Markdown"
    assert host.profile_locked()
    assert host.said[-1] == "Markdown profile."


def test_cancelling_the_profile_window_changes_nothing(host: Host) -> None:
    host.modal = lambda _dialog, _label: wx.ID_CANCEL
    host.choose_dictation_profile()
    assert host.dictation_profile_name() == "Standard"
    assert host.said == []


# -- tutorials ------------------------------------------------------------------------- #


def test_five_lessons_and_every_command_a_step_names_runs_here() -> None:
    from quill.apps.transcribe import QuillTranscribeFrame

    assert CATALOGUE.problems() == []
    assert len(CATALOGUE.tutorials) == 5
    for tutorial in CATALOGUE.tutorials:
        for step in tutorial.steps:
            if step.command:
                method = method_for(step.command)
                assert method and callable(getattr(QuillTranscribeFrame, method, None)), (
                    step.command
                )
                assert key_for(step.command), step.command


def test_the_lesson_host_resolves_and_runs_commands(host: Host) -> None:
    lessons = _LessonHost(host)
    assert lessons.commands.get("transcribe.practice") == host.open_practice
    assert lessons.commands.get("nothing.here") is None
    assert lessons._binding_for("transcribe.practice") == "Ctrl+Shift+P"
    lessons.commands.run("transcribe.practice")
    assert host._practice_window() is not None


def test_the_menu_shows_the_keys_the_lessons_teach() -> None:
    menus = (_ROOT / "quill" / "apps" / "transcribe_menus.py").read_text(encoding="utf-8")
    for command_id, (method, key) in LOCAL_COMMANDS.items():
        if command_id == "transcribe.practice_start":
            continue  # the Practice window's own key, in its accelerator table
        assert f"\\t{key}" in menus and f"host.{method}" in menus, command_id
    practice = (_ROOT / "quill" / "apps" / "transcribe_practice.py").read_text(encoding="utf-8")
    assert "wx.WXK_F11" in practice


# -- F1, reachability ------------------------------------------------------------------- #


def test_every_new_window_has_authored_f1_help() -> None:
    for title in ("Practice Dictation", "Dictation Profile", "QUILL Transcribe Tutorials"):
        assert surface_help.is_known_title(title), title


def test_every_control_in_the_new_windows_carries_inline_help() -> None:
    for name in ("transcribe_practice.py", "transcribe_coach.py"):
        tree = ast.parse((_ROOT / "quill" / "apps" / name).read_text(encoding="utf-8"))
        made = {
            node.targets[0].attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Attribute)
            and isinstance(node.value, ast.Call)
            and getattr(node.value.func, "attr", "") in ("TextCtrl", "ListBox", "CheckBox")
        }
        source = (_ROOT / "quill" / "apps" / name).read_text(encoding="utf-8")
        for attribute in made:
            assert f"self.{attribute}.SetHelpText(" in source, (name, attribute)


def test_the_practice_window_is_reached_from_the_app() -> None:
    frame = (_ROOT / "quill" / "apps" / "transcribe.py").read_text(encoding="utf-8")
    assert "TranscribeCoachMixin" in frame
    coach = (_ROOT / "quill" / "apps" / "transcribe_coach.py").read_text(encoding="utf-8")
    assert "from quill.apps.transcribe_practice import PracticeDictationFrame" in coach


def test_dictation_status_names_a_profile_other_than_standard(host: Host) -> None:
    assert "profile" not in host.dictation_status_sentence()
    host._save_dictation_profile("coding")
    assert host.dictation_status_sentence().endswith("Coding profile.")
