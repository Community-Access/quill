"""QUILL Transcribe: hold to talk, the wake phrase, braille and Dictation Status
(D-9 and D-6, 2026-10-15).

The real mixins over the stand-in host of ``test_transcribe_app.py``: the shared
controller, locked to a fake desktop, so nothing is typed into a real program,
no microphone opens and no key is registered with Windows. The start and stop
key's state is a flag the test sets, never the real keyboard.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from quill.apps import transcribe_dictation, transcribe_talk
from quill.core.transcribe import models
from quill.core.windows_dictation import DictationPreferences, RecognizedPhrase, words_from_text
from tests.unit.apps.test_transcribe_app import Host


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class _Braille:
    def __init__(self) -> None:
        self.cells: list[str] = []

    def braille(self, text: str) -> str:
        self.cells.append(text)
        return ""


@pytest.fixture()
def host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(models, "start_problem", lambda *_a, **_k: "")
    monkeypatch.setattr(
        transcribe_dictation.TranscribeDictationMixin, "_front_is_own_window", lambda _s: False
    )
    clock = _Clock()
    monkeypatch.setattr(transcribe_talk, "_clock", clock)
    polls: list[Any] = []
    monkeypatch.setattr(transcribe_talk.wx, "CallLater", lambda _ms, run, *a: polls.append(run))
    made = Host(tmp_path)
    made.clock = clock
    made.polls = polls
    made.key = {"down": False}
    made._start_key_down = lambda: made.key["down"]
    made._announcement_engine = _Braille()
    yield made
    made._release_dictate_anywhere()


def _phrase(text: str) -> RecognizedPhrase:
    return RecognizedPhrase(words_from_text(text))


def _hold_on(host: Any) -> None:
    host._settings.dictation["windows_dictation_hold_to_talk"] = True


# -- holding the start and stop key (D-9) --------------------------------------- #


def test_holding_the_key_talks_and_letting_go_types_then_stops(host: Any) -> None:
    _hold_on(host)
    host.key["down"] = True
    host.toggle_dictation()
    assert host.dictation_active()
    gate = host._talk_gate(host._dictation)  # what the recogniser reports to
    gate.on_phrase(_phrase("hello there"))
    assert host.world.typed == []  # never while the key (and its Alt) is down
    host.toggle_dictation()  # Windows repeating the held key: ignored
    assert host.dictation_active()
    host.clock.now += 1.0
    host.key["down"] = False
    host._poll_start_key()
    assert host.world.typed == ["edit-1:Hello there"]
    assert not host.dictation_active()


def test_a_quick_press_still_turns_dictation_on_and_leaves_it_on(host: Any) -> None:
    _hold_on(host)
    host.key["down"] = True
    host.toggle_dictation()
    host.clock.now += 0.1
    host.key["down"] = False
    host._poll_start_key()
    assert host.dictation_active()
    host.hear("one")
    assert host.world.typed == ["edit-1:One"]


def test_with_the_setting_off_a_long_press_is_a_plain_toggle(host: Any) -> None:
    host.key["down"] = True
    host.toggle_dictation()
    gate = host._talk_gate(host._dictation)
    gate.on_phrase(_phrase("kept"))
    host.clock.now += 2.0
    host.key["down"] = False
    host._poll_start_key()
    assert host.dictation_active()  # the key does not stop it on release
    assert host.world.typed == ["edit-1:Kept"]  # but what waited is typed


def test_the_press_that_stops_lets_the_last_phrase_through(host: Any) -> None:
    _hold_on(host)
    host.toggle_dictation()  # on, by a tap
    host.key["down"] = True
    gate = host._talk_gate(host._dictation)
    host.toggle_dictation()  # the stopping press, still held
    gate.on_phrase(_phrase("last words"))  # the phrase finish() waits for
    assert gate.waiting == 0


def test_the_key_is_followed_only_while_it_is_down(host: Any) -> None:
    _hold_on(host)
    host.key["down"] = True
    host.toggle_dictation()
    assert host.polls  # asked again in a moment
    host.polls.clear()
    host._poll_start_key()  # still down
    assert host.polls
    host.polls.clear()
    host.key["down"] = False
    host.clock.now += 0.1
    host._poll_start_key()
    assert host.polls == []  # let go: nothing more is asked


def test_a_press_from_the_tray_or_inkwell_is_a_plain_toggle(host: Any) -> None:
    _hold_on(host)
    host.toggle_dictation()  # the key is not down: not followed
    assert host.dictation_active() and host.polls == []
    host.toggle_dictation()
    assert not host.dictation_active()


def test_closing_throws_away_words_waiting_for_the_key(host: Any) -> None:
    host.key["down"] = True
    host.toggle_dictation()
    gate = host._talk_gate(host._dictation)
    gate.on_phrase(_phrase("never"))
    host._release_dictate_anywhere()
    assert gate.waiting == 0 and host.world.typed == []


def test_the_recogniser_reports_through_the_key_gate(
    host: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.ui.windows_dictation_commands as shared

    seen: list[Any] = []
    monkeypatch.setattr(
        shared, "_make_recognizer", lambda controller, _p: seen.append(controller) or object()
    )
    host._make_chosen_recognizer(host._dictation, DictationPreferences())
    assert seen and seen[0] is host._key_gate
    assert seen[0].active is host._dictation.active  # everything else passes through


def test_the_virtual_key_is_the_chords_last_key() -> None:
    from quill.ui.tray_hotkey import virtual_key

    assert virtual_key("Alt+Shift+F9") == 0x78
    assert virtual_key("Ctrl+Alt+PageDown") == 0x22
    assert virtual_key("Ctrl+Alt+K") == ord("K")
    assert virtual_key("Alt+Shift+\\") is not None
    assert virtual_key("") is None and virtual_key("Ctrl+Alt+Nonsense") is None


# -- the wake phrase (D-9) ---------------------------------------------------------- #


def _wake_on(host: Any) -> None:
    host._settings.dictation["windows_dictation_wake_enabled"] = True
    host._dictation._preferences = lambda: DictationPreferences(
        phrase_feedback="silent", wake_enabled=True
    )
    host._wake_front_allows = lambda: True


def test_the_wake_phrase_is_off_until_turned_on(host: Any) -> None:
    host._wake_front_allows = lambda: True
    host._keep_wake_standby()
    assert not host._dictation.standing_by
    assert host.recognizers == []  # no microphone opened


def test_with_the_wake_phrase_on_it_listens_and_says_so_in_the_state(host: Any) -> None:
    _wake_on(host)
    host._keep_wake_standby()
    assert host._dictation.standing_by
    assert host.dictation_state_word() == "Listening for your wake phrase"
    transcribe_dictation._Feedback(host).state_changed(None)  # the controller's port
    assert host._announcement_engine.cells == ["Dictation: Listening for your wake phrase"]


def test_nothing_is_written_until_the_wake_phrase_then_the_rest_is(host: Any) -> None:
    _wake_on(host)
    host._keep_wake_standby()
    host.hear("good morning everybody")
    assert host.world.typed == [] and host._dictation.standing_by
    host.hear("quill dictate dear Sam")
    assert host.dictation_active()
    assert host.world.typed == ["edit-1:Dear Sam"]


def test_stopping_goes_back_to_listening_for_the_wake_phrase(host: Any) -> None:
    _wake_on(host)
    host._keep_wake_standby()
    host.hear("quill dictate")
    host.stop_dictation()
    assert host._dictation.standing_by
    assert "Say Quill dictate to start again." in host.feedback.said[-1]


def test_it_stops_listening_where_dictation_would_not_type(host: Any) -> None:
    _wake_on(host)
    host._keep_wake_standby()
    host._wake_front_allows = lambda: False  # QUILL Transcribe, QUILL, or a listed program
    host._keep_wake_standby()
    assert not host._dictation.standing_by
    assert not host._dictation.microphone_open


def test_it_stops_listening_when_turned_off_and_in_safe_mode(host: Any) -> None:
    _wake_on(host)
    host._keep_wake_standby()
    host._settings.dictation["windows_dictation_wake_enabled"] = False
    host._keep_wake_standby()
    assert not host._dictation.standing_by
    _wake_on(host)
    host._safe_mode = True
    host._keep_wake_standby()
    assert not host._dictation.standing_by


def test_the_wake_front_check_refuses_own_window_quill_and_listed_programs(
    host: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    pytest.importorskip("ctypes.wintypes")
    from quill.platform.windows import foreground, text_target

    window = foreground.ForegroundWindow(hwnd=5, process_name="notepad.exe", process_id=1)
    monkeypatch.setattr(foreground, "foreground_window_info", lambda: window)
    monkeypatch.setattr(text_target, "window_handles_own_expansion", lambda _h: False)
    assert host._wake_front_allows()
    monkeypatch.setattr(
        foreground, "foreground_window_info", lambda: replace(window, process_id=os.getpid())
    )
    assert not host._wake_front_allows()
    monkeypatch.setattr(
        foreground, "foreground_window_info", lambda: replace(window, process_name="KeePass.exe")
    )
    assert not host._wake_front_allows()  # on the never-type list by default
    monkeypatch.setattr(foreground, "foreground_window_info", lambda: window)
    monkeypatch.setattr(text_target, "window_handles_own_expansion", lambda _h: True)
    assert not host._wake_front_allows()  # a QUILL or QUILL Lite window


def test_switching_the_wake_phrase_on_says_so_once(host: Any) -> None:
    _wake_on(host)
    host._wake_settings_changed(before=False)
    assert host.said[-1] == transcribe_talk.WAKE_ON
    host._wake_settings_changed(before=True)
    assert host.said.count(transcribe_talk.WAKE_ON) == 1


# -- braille and Dictation Status (D-6) --------------------------------------------- #


def test_the_words_heard_so_far_go_to_braille_not_speech(host: Any) -> None:
    feedback = transcribe_dictation._Feedback(host)
    feedback.preview("dear sa")
    assert host._announcement_engine.cells == ["Hearing: dear sa"]
    assert host.said == []
    feedback.preview("")  # cleared: nothing written to the display
    assert host._announcement_engine.cells == ["Hearing: dear sa"]


def test_braille_follows_the_announcement_braille_setting(host: Any) -> None:
    host.settings = type("S", (), {"announcement_braille": False})()
    transcribe_dictation._Feedback(host).preview("dear")
    assert host._announcement_engine.cells == []


def test_unspoken_state_changes_go_to_braille(host: Any) -> None:
    host.command_key_pressed()  # one command armed: shown, not said
    transcribe_dictation._Feedback(host).state_changed(None)  # the controller's port
    assert "Dictation: Waiting for a command" in host._announcement_engine.cells
    host._announcement_engine.cells.clear()
    host.start_dictation()
    host._braille_state_change()  # nothing new: nothing written
    assert host._announcement_engine.cells == []


def test_preview_speech_only_when_the_setting_says_speak(host: Any) -> None:
    feedback = transcribe_dictation._Feedback(host)
    feedback.say_quietly("dear Sam")
    assert host.said == ["dear Sam"]


def test_dictation_status_is_one_sentence(host: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    host.speak_dictation_status()
    assert host.said[-1].startswith("Dictation is off, using ")
    host.start_dictation()
    host.world.field = ("mail", 2, "edit-9")
    host.hear("one")
    host.hear("two")

    class _Doc:
        def locked_window(self) -> int:
            return 42

    host._dictation_document = _Doc()
    from quill.platform.windows import foreground

    monkeypatch.setattr(foreground, "window_process_name", lambda _h: "OUTLOOK.EXE")
    host.speak_dictation_status()
    sentence = host.said[-1]
    assert sentence.startswith("Dictation is paused in OUTLOOK, using ")
    assert sentence.endswith(", with 2 phrases held.")
    assert sentence.count(".") == 1


def test_dictation_status_is_the_editors_alt_f9() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.transcribe.parity import DIVERGENCES, SHARED_COMMANDS

    assert SHARED_COMMANDS["tools.dictation_status"] == "speak_dictation_status"
    assert "tools.dictation_status" not in DIVERGENCES
    assert DEFAULT_KEYMAP["tools.dictation_status"] == "Alt+F9"


# -- the three optional keys (D-6) -------------------------------------------------- #


def test_none_of_the_new_keys_is_registered_until_chosen(host: Any) -> None:
    host._settings.dictation_hotkey = ""
    assert host._start_transcribe_keys() == ""
    assert host.frame.hotkeys == {}
    for field in ("status_hotkey", "resume_hotkey", "discard_hotkey"):
        assert getattr(host._settings, field) == ""
        assert host.optional_key(field) == ""


def test_chosen_keys_are_registered_at_launch_and_released(host: Any) -> None:
    host._settings.dictation_hotkey = ""
    host._settings.status_hotkey = "Ctrl+Alt+PageUp"
    host._settings.resume_hotkey = "Ctrl+Alt+PageDown"
    host._settings.discard_hotkey = "Alt+Shift+PageDown"
    assert host._start_transcribe_keys() == ""
    assert len(host.frame.hotkeys) == 3
    assert host.optional_key("resume_hotkey") == "Ctrl+Alt+PageDown"
    host._release_transcribe_keys()
    assert host.frame.hotkeys == {}


def test_a_refused_key_is_explained(host: Any) -> None:
    host._settings.dictation_hotkey = ""
    host._settings.status_hotkey = "Ctrl+Alt+PageUp"
    host.frame.refused = True
    notice = host._start_transcribe_keys()
    assert "Your Dictation Status Key, Ctrl+Alt+PageUp, is not working" in notice


def test_choosing_a_key_goes_through_the_family_picker_with_its_conflicts(
    host: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.ui.show_hide_key_picker as picker
    from quill.core.transcribe.settings import load_settings

    host._settings.command_hotkey = "Ctrl+Alt+PageDown"
    seen: dict[str, Any] = {}

    def fake(_host: Any, _wx: Any, **kwargs: Any) -> None:
        seen.update(kwargs)
        assert kwargs["replace"]("Ctrl+Alt+PageUp")
        kwargs["save"]("Ctrl+Alt+PageUp")

    monkeypatch.setattr(picker, "run_system_key_command", fake)
    host.choose_optional_key("discard_hotkey")
    assert seen["app_id"] == "transcribe" and seen["caption"] == "Discard Held Words Key"
    assert seen["own"]["Command Key"] == "Ctrl+Alt+PageDown"  # its siblings are refused
    assert "Discard Held Words Key" not in seen["own"]
    assert load_settings(host._data_dir).discard_hotkey == "Ctrl+Alt+PageUp"
    assert host.optional_key("discard_hotkey") == "Ctrl+Alt+PageUp"


def test_the_keys_run_the_windows_own_commands(host: Any) -> None:
    from quill.apps.transcribe_keys import OPTIONAL_KEYS

    methods = {row[4] for row in OPTIONAL_KEYS.values()}
    assert methods == {"speak_dictation_status", "resume_dictation", "discard_held_words"}
    host.resume_dictation()
    assert host.said[-1] == "Dictation is not paused."
    host.discard_held_words()
    assert host.said[-1] == "Dictation is not paused, so nothing is held."


def test_resume_and_discard_from_the_other_program(host: Any) -> None:
    """D-6: Resume and Discard from wherever the person is, without the window."""
    host.start_dictation()
    host.world.field = ("mail", 2, "edit-9")
    host.hear("one")
    host.world.field = ("notepad", 1, "edit-1")
    host.resume_dictation()  # what the Resume key runs
    assert host.world.typed == ["edit-1:One"]
    host.world.field = ("mail", 2, "edit-9")
    host.hear("two")
    host.discard_held_words()  # what the Discard key runs
    assert host._dictation.held_count == 0
