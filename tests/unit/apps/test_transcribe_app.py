"""QUILL Transcribe's commands, with the wx window taken out.

The commands under test are the real mixins (dictation, keys, commands), composed
onto a host whose frame, announcer and dialogs record instead of showing
anything -- the same approach as QUILL Lite's window tests (conftest.py there).
The dictation controller is the shared one, locked to a fake desktop, so
nothing is typed and no microphone opens. No window is shown and no key is
registered with Windows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.apps import transcribe_dialogs, transcribe_dictation
from quill.apps.transcribe_commands import TranscribeCommandsMixin
from quill.apps.transcribe_dictation import TranscribeDictationMixin, _ChosenModelOnly
from quill.apps.transcribe_keys import TranscribeKeysMixin
from quill.apps.transcribe_recent import TranscribeRecentMixin
from quill.core.dictation_owner import MicrophoneLock, OwnerLock
from quill.core.transcribe import models
from quill.core.transcribe.settings import TranscribeSettings, load_settings
from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.controller import DictationStartError
from quill.core.windows_dictation.target_lock import LockedTarget
from quill.ui.windows_dictation_external import ExternalDocument

# -- the stand-ins ----------------------------------------------------------------- #


class _Frame:
    def __init__(self) -> None:
        self.hotkeys: dict[int, tuple[int, int]] = {}
        self.refused = False

    def RegisterHotKey(self, hotkey_id: int, mods: int, key: int) -> bool:  # noqa: N802
        if self.refused:
            return False
        self.hotkeys[hotkey_id] = (mods, key)
        return True

    def UnregisterHotKey(self, hotkey_id: int) -> bool:  # noqa: N802
        self.hotkeys.pop(hotkey_id, None)
        return True

    def Bind(self, *_args: Any, **_kwargs: Any) -> None:  # noqa: N802
        pass

    def GetMenuBar(self) -> None:  # noqa: N802
        return None


class _Timer:
    def __init__(self) -> None:
        self.running = False

    def Start(self, _ms: int) -> None:  # noqa: N802
        self.running = True

    def Stop(self) -> None:  # noqa: N802
        self.running = False


class _World:
    def __init__(self) -> None:
        self.field: Any = ("notepad", 1, "edit-1")
        self.typed: list[str] = []

    def type_text(self, text: str) -> bool:
        self.typed.append(f"{self.field[2]}:{text}")
        return True


class _Feedback:
    def __init__(self) -> None:
        self.said: list[str] = []

    def has_cue(self, _moment: Any) -> bool:
        return False

    def cue(self, _moment: Any) -> None:
        pass

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, _text: str) -> None:
        pass

    def show(self, _text: str) -> None:
        pass

    def state_changed(self, _state: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass


class _Recognizer:
    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass


class Host(
    TranscribeDictationMixin, TranscribeKeysMixin, TranscribeCommandsMixin, TranscribeRecentMixin
):
    def __init__(self, data_dir: Path) -> None:
        self.frame = _Frame()
        self._settings = TranscribeSettings(dictation={"windows_dictation_engine": "windows"})
        self._data_dir = data_dir
        self._safe_mode = False
        self._engine_override = ""
        self.said: list[str] = []
        self.status: list[str] = []
        self.boxes: list[str] = []
        self.box_answer: int = 0
        self.modal: Any = None
        self.restored = False
        self.world = _World()
        self.feedback = _Feedback()
        self._owner_lock = OwnerLock("transcribe", folder=data_dir / "ipc")
        # The family's folder, which the suite gives each test (tests/conftest.py),
        # so QUILL Lite's real window below meets the same lock.
        self._microphone = MicrophoneLock(
            "transcribe", key=lambda: str(self._settings.dictation_hotkey or "")
        )
        self._arm_timer = _Timer()
        inner = ExternalDocument(
            problem=lambda: "", where=lambda: self.world.field, type_text=self.world.type_text
        )
        self.recognizers: list[_Recognizer] = []

        def recognizer(_c: Any, _p: Any) -> _Recognizer:
            self.recognizers.append(_Recognizer())
            return self.recognizers[-1]

        self._dictation = DictationController(
            recognizer=recognizer,
            document=LockedTarget(inner, where=lambda: self.world.field),
            feedback=self.feedback,
            preferences=lambda: DictationPreferences(phrase_feedback="silent"),
            microphone=self._microphone,
        )

    def _announce(self, text: str, *, force: bool = False, sound: str = "") -> None:
        self.said.append(text)

    def _set_status(self, text: str) -> None:
        self.status.append(text)

    def _show_modal_dialog(self, dialog: Any, label: str) -> int:
        return int(self.modal(dialog, label))

    def _show_message_box(self, text: str, _caption: str, *_a: Any, **_k: Any) -> int:
        self.boxes.append(text)
        return self.box_answer

    def _restore_from_tray(self) -> None:
        self.restored = True

    def _keep_menu_ids(self, *_refs: Any) -> None:
        pass

    def _release_tray_hotkey(self) -> None:
        pass

    def _start_show_hide_key(self, _app: str) -> None:
        pass

    def hear(self, text: str) -> None:
        self._dictation.on_phrase(RecognizedPhrase(words_from_text(text)))


@pytest.fixture()
def host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Host:
    monkeypatch.setattr(models, "start_problem", lambda *_a, **_k: "")
    monkeypatch.setattr(
        transcribe_dictation.TranscribeDictationMixin, "_front_is_own_window", lambda _s: False
    )
    made = Host(tmp_path)
    yield made
    made._release_dictate_anywhere()


# -- start, stop, toggle --------------------------------------------------------- #


def test_the_key_starts_in_the_field_in_front_and_stops_again(host: Host) -> None:
    host.toggle_dictation()
    assert host.dictation_active()
    host.hear("hello there")
    assert host.world.typed == ["edit-1:Hello there"]
    host.toggle_dictation()
    assert not host.dictation_active()


def test_a_repeated_start_opens_nothing_twice(host: Host) -> None:
    host.start_dictation()
    host.start_dictation()
    assert host._dictation.active
    assert host.feedback.said.count("Dictation on.") <= 1


def test_stop_when_off_says_so(host: Host) -> None:
    host.stop_dictation()
    assert host.said[-1] == "Dictation is already off."


def test_safe_mode_refuses_to_listen(host: Host) -> None:
    host._safe_mode = True
    host.toggle_dictation()
    assert not host.dictation_active()
    assert "Safe Mode" in host.said[-1]


def test_a_missing_model_is_refused_by_name_and_never_swapped(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(models, "start_problem", lambda *_a, **_k: "Whisper small is not here.")
    host.toggle_dictation()
    assert not host.dictation_active()
    assert host.said[-1] == "Whisper small is not here."
    assert host._last_refusal == "Whisper small is not here."


def test_while_inkwell_dictates_transcribe_waits_its_turn(host: Host, tmp_path: Path) -> None:
    host._owner_lock.release()
    inkwell = OwnerLock("inkwell", folder=tmp_path / "ipc")
    assert inkwell.claim()
    host.toggle_dictation()
    assert not host.dictation_active()
    assert "Quill Inkwell is dictating" in host.said[-1]
    inkwell.release()
    host.toggle_dictation()
    assert host.dictation_active()


def test_transcribe_and_inkwell_never_both_own_dictate_anywhere(host: Host, tmp_path: Path) -> None:
    host.start_dictation()
    assert host._owner_lock.held
    assert not OwnerLock("inkwell", folder=tmp_path / "ipc").claim()


# -- the tray and the window arm a start ------------------------------------------- #


def test_from_the_window_dictation_waits_for_another_program(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Host, "_front_is_own_window", lambda _s: True)
    host.start_or_stop_from_here()
    assert host.dictation_armed() and not host.dictation_active()
    assert host._arm_timer.running
    assert host.said[-1].startswith("Switch to the field you want.")
    monkeypatch.setattr(
        "quill.platform.windows.foreground.foreground_window_info",
        lambda: type("W", (), {"hwnd": 9, "process_id": 4242, "window_class": "Notepad"})(),
    )
    host._on_arm_tick(None)
    assert host.dictation_active() and not host.dictation_armed()


def test_the_taskbar_is_never_where_an_armed_start_begins(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Host, "_front_is_own_window", lambda _s: True)
    host.start_or_stop_from_here()
    monkeypatch.setattr(
        "quill.platform.windows.foreground.foreground_window_info",
        lambda: type("W", (), {"hwnd": 9, "process_id": 77, "window_class": "Shell_TrayWnd"})(),
    )
    host._on_arm_tick(None)
    assert host.dictation_armed() and not host.dictation_active()


def test_choosing_the_command_again_cancels_the_wait(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Host, "_front_is_own_window", lambda _s: True)
    host.start_or_stop_from_here()
    host.start_or_stop_from_here()
    assert not host.dictation_armed() and not host._arm_timer.running
    assert host.said[-1] == "Cancelled; dictation did not start."


def test_an_armed_start_gives_up_and_says_so(host: Host, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Host, "_front_is_own_window", lambda _s: True)
    host.start_or_stop_from_here()
    host._armed_ticks = 1
    monkeypatch.setattr(
        "quill.platform.windows.foreground.foreground_window_info",
        lambda: type("W", (), {"hwnd": 0, "process_id": 0, "window_class": ""})(),
    )
    host._on_arm_tick(None)
    assert not host.dictation_armed()
    assert "did not start" in host.said[-1]


def test_from_another_program_the_tray_starts_at_once(host: Host) -> None:
    host.start_or_stop_from_here()
    assert host.dictation_active()
    host.start_or_stop_from_here()
    assert not host.dictation_active()


# -- pause, resume, discard ------------------------------------------------------- #


def test_moving_pauses_and_resume_writes_back_where_it_started(host: Host) -> None:
    host.start_dictation()
    host.world.field = ("mail", 2, "edit-9")
    host.hear("one")
    assert host.dictation_paused()
    assert host.dictation_state_word() == "Paused, 1 phrase held"
    host.world.field = ("notepad", 1, "edit-1")
    host.resume_dictation()
    assert host.world.typed == ["edit-1:One"]
    assert not host.dictation_paused()


def test_resume_in_this_field_writes_where_you_are(host: Host) -> None:
    host.start_dictation()
    host.world.field = ("mail", 2, "edit-9")
    host.hear("one")
    host.resume_in_this_field()
    assert host.world.typed == ["edit-9:One"]


def test_resume_in_this_field_from_the_window_waits_for_the_field(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    host.start_dictation()
    host.world.field = ("mail", 2, "edit-9")
    host.hear("one")
    monkeypatch.setattr(Host, "_front_is_own_window", lambda _s: True)
    host.resume_in_this_field()
    assert host.dictation_armed() and host.world.typed == []
    monkeypatch.setattr(
        "quill.platform.windows.foreground.foreground_window_info",
        lambda: type("W", (), {"hwnd": 9, "process_id": 4242, "window_class": "Edit"})(),
    )
    host._on_arm_tick(None)
    assert host.world.typed == ["edit-9:One"]


def test_discard_drops_the_held_words(host: Host) -> None:
    host.start_dictation()
    host.world.field = ("mail", 2, "edit-9")
    host.hear("one")
    host.discard_held_words()
    assert host._dictation.held_count == 0 and host.dictation_paused()


def test_pause_commands_when_not_paused_say_so(host: Host) -> None:
    host.resume_dictation()
    host.resume_in_this_field()
    host.discard_held_words()
    assert host.said == [
        "Dictation is not paused.",
        "Dictation is not paused.",
        "Dictation is not paused, so nothing is held.",
    ]


# -- the model --------------------------------------------------------------------- #


def test_the_built_in_model_is_used_only_when_asked_and_only_once(host: Host) -> None:
    host.use_built_in_model_once()
    assert host.engine_in_use() == models.FALLBACK_ENGINE
    assert host.chosen_engine() == "windows"
    assert "Your chosen model is still" in host.said[0]
    assert host.dictation_active()
    host.stop_dictation()
    host._dictation_state_changed()
    assert host.engine_in_use() == "windows"


def test_the_built_in_model_cannot_be_swapped_in_mid_session(host: Host) -> None:
    host.start_dictation()
    host.use_built_in_model_once()
    assert host.said[-1].startswith("Stop dictation first")


def test_a_model_that_will_not_load_stops_the_start() -> None:
    class Gives:
        fallback_notice = "Whisper small could not be loaded"
        stopped = False

        def start(self, _mic: str) -> None:
            pass

        def stop(self) -> None:
            Gives.stopped = True

    wrapped = _ChosenModelOnly(Gives(), "whisper_small")
    with pytest.raises(DictationStartError, match="nothing is listening"):
        wrapped.start("")
    assert Gives.stopped


def test_a_model_that_loads_is_passed_through() -> None:
    class Fine:
        fallback_notice = ""
        extra = "yes"

        def start(self, _mic: str) -> None:
            pass

    wrapped = _ChosenModelOnly(Fine(), "moonshine")
    wrapped.start("")
    assert wrapped.extra == "yes"


def test_choose_model_keeps_the_choice(host: Host, monkeypatch: pytest.MonkeyPatch) -> None:
    class Dialog:
        def __init__(self, *_a: Any, **_k: Any) -> None:
            self.chosen = "whisper"

        def Destroy(self) -> None:  # noqa: N802
            pass

    import wx

    monkeypatch.setattr(transcribe_dialogs, "ChooseModelDialog", Dialog)
    host.modal = lambda _d, _l: wx.ID_OK
    host.choose_model()
    assert host.chosen_engine() == "whisper"
    assert load_settings(host._data_dir).dictation["windows_dictation_engine"] == "whisper"
    assert host.said[-1] == "Model: Whisper."


def test_choosing_openai_asks_first_and_no_keeps_the_old_model(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    host.box_answer = wx.NO
    host._use_model("openai")
    assert host.chosen_engine() == "windows"
    assert "OpenAI dictation sends what you say to OpenAI" in host.boxes[-1]
    host.box_answer = wx.YES
    host._use_model("openai")
    assert host.chosen_engine() == "openai"
    assert host._settings.dictation["windows_dictation_openai_consent"] is True


def test_the_model_library_is_closed_in_safe_mode(host: Host) -> None:
    host._safe_mode = True
    host.open_model_library()
    assert host.said[-1] == "Safe Mode is on, so models cannot be downloaded."


def test_the_model_library_choice_becomes_the_model(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.ui.dictation_models_dialog as library

    monkeypatch.setattr(library, "open_speech_models", lambda *_a, **_k: "whisper")
    host.open_model_library()
    assert host.chosen_engine() == "whisper"


def test_choose_microphone_saves_it(host: Host, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(transcribe_dialogs, "choose_microphone", lambda _h, _c: "Headset")
    host.choose_microphone()
    assert host._settings.dictation["windows_dictation_microphone"] == "Headset"
    assert host.said[-1] == "Microphone: Headset."


def test_dictation_settings_are_the_shared_window_over_our_copy(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    import quill.ui.windows_dictation_dialog as shared

    seen: dict[str, Any] = {}

    class Dialog:
        def __init__(
            self, _parent: Any, settings: Any, _announce: Any, *, help_for: Any = None
        ) -> None:
            self.settings = settings
            seen["help_for"] = help_for

        def apply(self, settings: Any) -> None:
            settings.windows_dictation_remove_fillers = True

        def Destroy(self) -> None:  # noqa: N802
            pass

    monkeypatch.setattr(shared, "WindowsDictationDialog", Dialog)
    host.modal = lambda _d, _l: wx.ID_OK
    host.edit_dictation_settings()
    assert host._settings.dictation["windows_dictation_remove_fillers"] is True
    assert host.status[-1] == "Dictation settings saved."
    # The wake phrase and the held key, worded for other programs (D-9).
    assert "another program is in front" in seen["help_for"]["wake"]
    assert "start and stop key" in seen["help_for"]["hold"]


# -- keys ---------------------------------------------------------------------------- #


def test_the_default_key_is_registered_at_launch(host: Host) -> None:
    """Alt+Shift+\\ from the start (owner, 2026-10-12)."""
    host._settings.dictation_hotkey = TranscribeSettings().dictation_hotkey
    assert host._start_transcribe_keys() == ""
    assert host.dictation_key() == "Alt+Shift+\\"


def test_an_emptied_key_registers_nothing(host: Host) -> None:
    host._settings.dictation_hotkey = ""
    assert host._start_transcribe_keys() == ""
    assert host.frame.hotkeys == {}


def test_a_saved_key_is_registered_at_launch(host: Host) -> None:
    host._settings.dictation_hotkey = "Ctrl+Alt+PageDown"
    assert host._start_transcribe_keys() == ""
    assert host.dictation_key() == "Ctrl+Alt+PageDown"
    host._release_transcribe_keys()
    assert host.frame.hotkeys == {}


def test_a_key_windows_refuses_is_explained_without_guessing_who(host: Host) -> None:
    host._settings.dictation_hotkey = "Ctrl+Alt+PageDown"
    host.frame.refused = True
    notice = host._start_transcribe_keys()
    assert "another program is using it" in notice and host.dictation_key() == ""


def test_safe_mode_registers_no_key(host: Host) -> None:
    host._safe_mode = True
    host._settings.dictation_hotkey = "Ctrl+Alt+PageDown"
    host._start_transcribe_keys()
    assert host.frame.hotkeys == {}


def test_choosing_the_key_goes_through_the_family_picker(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.ui.show_hide_key_picker as picker

    seen: dict[str, Any] = {}

    def fake(_host: Any, _wx: Any, **kwargs: Any) -> None:
        seen.update(kwargs)
        assert kwargs["replace"]("Ctrl+Alt+PageDown")
        kwargs["save"]("Ctrl+Alt+PageDown")

    monkeypatch.setattr(picker, "run_system_key_command", fake)
    host.choose_dictation_key()
    assert seen["app_id"] == "transcribe"
    assert load_settings(host._data_dir).dictation_hotkey == "Ctrl+Alt+PageDown"
    assert host.dictation_key() == "Ctrl+Alt+PageDown"


# -- requests passed on by Inkwell --------------------------------------------------- #


def test_inkwells_key_press_is_answered_as_our_own(host: Host, tmp_path: Path) -> None:
    import quill.core.dictation_owner as owner
    from quill.core.dictation_owner import send_request, take_requests

    original = take_requests
    owner_folder = tmp_path / "ipc"
    host._own_dictate_anywhere()
    send_request("toggle", sender="inkwell", folder=owner_folder)
    send_request("show", sender="inkwell", folder=owner_folder)
    owner.take_requests = lambda **_k: original(folder=owner_folder)  # type: ignore[assignment]
    try:
        host._answer_owner_requests()
    finally:
        owner.take_requests = original  # type: ignore[assignment]
    assert host.dictation_active() and host.restored


# -- setup, options, hand-over -------------------------------------------------------- #


def test_setup_skip_changes_nothing_but_is_remembered(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    class Dialog:
        command = ""

        def __init__(self, *_a: Any, **_k: Any) -> None:
            self.at_login = type("C", (), {"GetValue": lambda _s: True})()

        def chosen_microphone(self) -> str:
            return "Headset"

        def chosen_engine(self) -> str:
            return "whisper"

        def chosen_key(self) -> str:
            return "Ctrl+Alt+PageDown"

        def chosen_command_key(self) -> str:
            return self.command

        def Destroy(self) -> None:  # noqa: N802
            pass

    monkeypatch.setattr(transcribe_dialogs, "SetupDialog", Dialog)
    monkeypatch.setattr(host, "launch_at_startup_enabled", lambda: False)
    host.modal = lambda _d, _l: wx.ID_CANCEL
    host.open_setup()
    assert host._settings.setup_done and host.chosen_engine() == "windows"
    assert host.frame.hotkeys == {}
    assert "Setup skipped" in host.said[-1]


def test_setup_finish_keeps_every_choice(host: Host, monkeypatch: pytest.MonkeyPatch) -> None:
    import wx

    class Dialog:
        command = ""

        def __init__(self, *_a: Any, **_k: Any) -> None:
            self.at_login = type("C", (), {"GetValue": lambda _s: True})()

        def chosen_microphone(self) -> str:
            return "Headset"

        def chosen_engine(self) -> str:
            return "whisper"

        def chosen_key(self) -> str:
            return "Ctrl+Alt+PageDown"

        def chosen_command_key(self) -> str:
            return self.command

        def Destroy(self) -> None:  # noqa: N802
            pass

    startup: list[bool] = []
    monkeypatch.setattr(transcribe_dialogs, "SetupDialog", Dialog)
    monkeypatch.setattr(host, "launch_at_startup_enabled", lambda: False)
    monkeypatch.setattr(host, "set_launch_at_startup", lambda on, **_k: startup.append(on))
    host.modal = lambda _d, _l: wx.ID_OK
    host.open_setup()
    saved = load_settings(host._data_dir)
    assert saved.setup_done and saved.dictation_hotkey == "Ctrl+Alt+PageDown"
    assert saved.dictation["windows_dictation_microphone"] == "Headset"
    assert saved.dictation["windows_dictation_engine"] == "whisper"
    assert host.dictation_key() == "Ctrl+Alt+PageDown" and startup == [True]
    assert (
        host.said[-1]
        == "Ready. Model: Whisper. To dictate, press Ctrl+Alt+PageDown in the field you want."
    )


def test_setup_offers_the_command_key_beside_the_start_key(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-1: empty by default, offered in setup with Record Key, registered on Finish."""
    import wx

    class Dialog:
        command = "Ctrl+Alt+PageUp"

        def __init__(self, *_a: Any, **kwargs: Any) -> None:
            assert kwargs["command_key"] == ""  # empty until chosen
            self.at_login = type("C", (), {"GetValue": lambda _s: False})()

        def chosen_microphone(self) -> str:
            return ""

        def chosen_engine(self) -> str:
            return "windows"

        def chosen_key(self) -> str:
            return "Ctrl+Alt+PageDown"

        def chosen_command_key(self) -> str:
            return self.command

        def Destroy(self) -> None:  # noqa: N802
            pass

    assert TranscribeSettings().command_hotkey == ""
    monkeypatch.setattr(transcribe_dialogs, "SetupDialog", Dialog)
    monkeypatch.setattr(host, "launch_at_startup_enabled", lambda: False)
    host.modal = lambda _d, _l: wx.ID_OK
    host.open_setup()
    assert load_settings(host._data_dir).command_hotkey == "Ctrl+Alt+PageUp"
    assert host.command_key() == "Ctrl+Alt+PageUp"
    assert len(host.frame.hotkeys) == 2
    assert host.said[-1].endswith("For a command, press Ctrl+Alt+PageUp first.")


def test_the_command_key_is_registered_at_launch_and_released(host: Host) -> None:
    host._settings.dictation_hotkey = ""
    host._settings.command_hotkey = "Ctrl+Alt+PageUp"
    assert host._start_transcribe_keys() == ""
    assert host.command_key() == "Ctrl+Alt+PageUp"
    host._release_transcribe_keys()
    assert host.frame.hotkeys == {}


def test_a_command_key_windows_refuses_is_explained(host: Host) -> None:
    host._settings.dictation_hotkey = ""
    host._settings.command_hotkey = "Ctrl+Alt+PageUp"
    host.frame.refused = True
    assert "Your Command Key, Ctrl+Alt+PageUp, is not working" in host._start_transcribe_keys()


def test_choosing_the_command_key_goes_through_the_family_picker(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.ui.show_hide_key_picker as picker

    seen: dict[str, Any] = {}

    def fake(_host: Any, _wx: Any, **kwargs: Any) -> None:
        seen.update(kwargs)
        assert kwargs["replace"]("Ctrl+Alt+PageUp")
        kwargs["save"]("Ctrl+Alt+PageUp")

    monkeypatch.setattr(picker, "run_system_key_command", fake)
    host.choose_command_key()
    assert seen["caption"] == "Command Key"
    assert "start and stop key" in seen["own"]
    assert load_settings(host._data_dir).command_hotkey == "Ctrl+Alt+PageUp"


def test_the_command_key_starts_dictation_with_one_command_armed(host: Host) -> None:
    host.command_key_pressed()
    controller = host._dictation
    assert controller.active and controller.command_mode_text == "Waiting for a command"
    assert host.dictation_state_word() == "Waiting for a command"
    host.hear("all caps on")
    assert host.world.typed == []  # a command: nothing typed
    host.command_key_pressed()
    host.command_key_pressed()
    assert host.dictation_state_word() == "Command mode"
    host.hear("pancakes")
    assert host.world.typed == []  # not a command, and in command mode: never typed
    host.command_key_pressed()  # back to dictation
    host.hear("pancakes")
    assert host.world.typed == ["edit-1:PANCAKES"]  # all caps on, from the first command


def test_speak_a_command_from_the_window_is_the_editors_f11(host: Host) -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.transcribe.parity import SHARED_COMMANDS

    assert SHARED_COMMANDS["tools.windows_dictation_command"] == "speak_a_command"
    assert DEFAULT_KEYMAP["tools.windows_dictation_command"] == "F11"
    host.speak_a_command()
    assert host._dictation.command_mode_text == "Waiting for a command"
    host.toggle_dictation()  # stop
    host.toggle_dictation()  # a plain start arms nothing
    assert host._dictation.command_mode_text == ""


def test_set_option_saves(host: Host) -> None:
    host.set_option("start_in_tray", True)
    assert load_settings(host._data_dir).start_in_tray


def test_launch_at_startup_says_the_outcome(host: Host, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.platform.windows import transcribe_startup

    calls: list[bool] = []
    monkeypatch.setattr(transcribe_startup, "set_launch_at_startup", calls.append)
    host.set_launch_at_startup(True)
    assert calls == [True]
    assert host.said[-1] == "QUILL Transcribe will start with Windows, in the tray."


def test_an_editors_settings_are_taken_once(host: Host) -> None:
    from quill.core.windows_dictation.anywhere import write_handoff
    from quill.core.windows_dictation.settings_fields import DictationSettings

    write_handoff(host._data_dir, DictationSettings(windows_dictation_engine="whisper"))
    assert host.take_dictation_handoff()
    assert host.chosen_engine() == "whisper"
    assert not host.take_dictation_handoff()


def test_the_state_word_follows_the_session(host: Host) -> None:
    assert host.dictation_state_word() == "Ready"
    host.start_dictation()
    assert host.dictation_state_word() == "Listening"
    host._safe_mode = True
    assert host.dictation_state_word() == "Off (Safe Mode)"


def test_releasing_closes_the_microphone_and_lets_go_of_the_lock(
    host: Host, tmp_path: Path
) -> None:
    host.start_dictation()
    host._release_dictate_anywhere()
    assert not host._dictation.microphone_open
    assert OwnerLock("inkwell", folder=tmp_path / "ipc").claim()


# -- Quill Inkwell defers --------------------------------------------------------- #


class _InkwellHost:
    """Inkwell's real Dictate Anywhere mixin, with its controller faked."""

    def __init__(self) -> None:
        from quill.apps.inkwell_dictation import InkwellDictationMixin

        self.mixin = InkwellDictationMixin
        self._safe_mode = False
        self.status: list[str] = []
        self.said: list[str] = []
        self.started = 0

        outer = self

        class _Controller:
            active = False

            def start(self) -> None:
                outer.started += 1
                self.active = True

        self._anywhere = _Controller()


def _inkwell_toggle(host: Any) -> None:
    from quill.apps.inkwell_dictation import InkwellDictationMixin

    class Bound(InkwellDictationMixin):
        pass

    bound = Bound()
    bound.__dict__.update(host.__dict__)
    bound._set_status = host.status.append  # type: ignore[attr-defined]
    bound._announce = lambda text, **_k: host.said.append(text)  # type: ignore[attr-defined]
    bound._anywhere_controller = lambda: host._anywhere  # type: ignore[method-assign]
    bound.toggle_dictate_anywhere()
    host.__dict__.update({k: v for k, v in bound.__dict__.items() if k == "_anywhere_owner"})


def test_inkwell_passes_its_key_to_transcribe_while_transcribe_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.dictation_owner import take_requests

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    transcribe = OwnerLock("transcribe")
    assert transcribe.claim()
    try:
        inkwell = _InkwellHost()
        _inkwell_toggle(inkwell)
        assert inkwell.started == 0  # no second microphone
        assert inkwell.status == ["Dictate Anywhere passed to QUILL Transcribe."]
        assert [(r.command, r.sender) for r in take_requests()] == [("toggle", "inkwell")]
    finally:
        transcribe.release()


def test_inkwell_dictates_itself_when_transcribe_is_not_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    inkwell = _InkwellHost()
    _inkwell_toggle(inkwell)
    assert inkwell.started == 1
    assert not OwnerLock("transcribe").claim()  # Inkwell holds it for its session
    inkwell._anywhere_owner.release()


# -- one microphone in the family (D-11) ------------------------------------------ #


class _LiteRecognizer:
    def __init__(self) -> None:
        self.stopped = 0

    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        self.stopped += 1


@pytest.fixture()
def lite_dictation(lite_window, monkeypatch: pytest.MonkeyPatch):
    """A real QUILL Lite window, dictating through the shared commands."""
    import wx

    from quill.ui import windows_dictation_commands as shared

    made: list[_LiteRecognizer] = []

    def make(_controller: Any, _preferences: Any) -> _LiteRecognizer:
        made.append(_LiteRecognizer())
        return made[-1]

    monkeypatch.setattr(shared, "_make_recognizer", make)
    monkeypatch.setattr(shared, "_controller", None)
    monkeypatch.setattr(shared, "_host", None)
    monkeypatch.setattr(shared, "_watched_tops", set())
    win = lite_window("")
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: win.control))
    yield win, made
    if shared._controller is not None:
        shared._controller.shut_down()


def test_two_programs_starting_give_one_owner_and_one_recognizer(
    host: Host, lite_dictation: Any
) -> None:
    """Transcribe PRD 15.2: QUILL Lite's Ctrl+F11 and QUILL Transcribe's key,
    one after the other: one microphone, one recogniser, and the second is
    told who has it."""
    from quill.core.dictation_owner import microphone_holder

    win, lite_made = lite_dictation
    win.cmd_toggle_dictation()
    assert win.dictation_active() and len(lite_made) == 1
    host.toggle_dictation()
    assert not host.dictation_active() and host.recognizers == []
    assert host.said[-1] == (
        "QUILL Lite is dictating. Press Ctrl+F11 in QUILL Lite to stop it, then try again."
    )
    assert microphone_holder() == "lite"
    win.cmd_toggle_dictation()  # QUILL Lite stops, and lets go
    host.toggle_dictation()
    assert host.dictation_active() and len(host.recognizers) == 1
    assert microphone_holder() == "transcribe"


def test_ctrl_f11_while_transcribe_listens_opens_no_second_recognizer(
    host: Host, lite_dictation: Any
) -> None:
    win, lite_made = lite_dictation
    host.toggle_dictation()
    assert host.dictation_active()
    win.cmd_toggle_dictation()
    assert not win.dictation_active() and lite_made == []
    assert (
        "QUILL Transcribe is listening. Press Alt+Shift+Backslash to stop it, then try again."
    ) in win.announcements
    host.toggle_dictation()  # stopped: QUILL Lite may dictate now
    win.cmd_toggle_dictation()
    assert win.dictation_active() and len(lite_made) == 1


def test_arming_from_the_window_is_refused_while_an_editor_dictates(host: Host) -> None:
    editor = MicrophoneLock("quill", key="Ctrl+F11")
    assert editor.take() == ""
    try:
        host.start_or_stop_from_here()
        assert not host.dictation_armed()
        assert host._last_refusal == (
            "QUILL is dictating. Press Ctrl+F11 in QUILL to stop it, then try again."
        )
    finally:
        editor.release()


def test_transcribe_lets_go_of_the_microphone_when_it_stops(host: Host) -> None:
    host.toggle_dictation()
    assert host._microphone.held
    host.toggle_dictation()
    assert not host._microphone.held
    assert MicrophoneLock("lite").take() == ""


def test_quill_lite_claims_its_window_as_quill_does(monkeypatch: pytest.MonkeyPatch) -> None:
    """QUILL Transcribe and Inkwell refuse to type into a claimed window, with
    the sentence that points to Ctrl+F11 (windows_dictation_external.py)."""
    from quill.apps.lite_shell import QuillLiteShell
    from quill.platform.windows import text_target

    claimed: list[int] = []
    monkeypatch.setattr(text_target, "claim_own_expansion", claimed.append)

    class _Shell:
        def GetHandle(self) -> int:  # noqa: N802
            return 4242

    QuillLiteShell._claim_own_dictation(_Shell())  # type: ignore[arg-type]
    assert claimed == [4242]


def test_a_claimed_window_is_refused_with_the_ctrl_f11_sentence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from quill.platform.windows import foreground, text_target
    from quill.ui.windows_dictation_external import foreground_problem

    monkeypatch.setattr(
        foreground,
        "foreground_window_info",
        lambda: SimpleNamespace(
            hwnd=4242, process_id=1, process_name="quill.exe", window_class="MDIFrame"
        ),
    )
    monkeypatch.setattr(text_target, "window_handles_own_expansion", lambda hwnd: hwnd == 4242)
    assert (
        foreground_problem(app="QUILL Transcribe", key="start and stop key")
        == "This is a QUILL window: press Ctrl+F11 to dictate here."
    )


# -- the editors' keys (D-14) ------------------------------------------------------ #


def test_switch_language_is_kept_and_said(host: Host) -> None:
    host.switch_dictation_language()
    assert host._settings.dictation["windows_dictation_speech_language"] == "es"
    assert host.said[-1] == "Español."
    assert load_settings(host._data_dir).dictation["windows_dictation_speech_language"] == "es"
    host.switch_dictation_language()
    assert host._settings.dictation["windows_dictation_speech_language"] == "en"
    assert host.said[-1] == "English."


def test_switch_language_while_dictating_goes_through_the_controller(host: Host) -> None:
    from quill.apps.transcribe_dictation import _Feedback as RealFeedback

    host._dictation._feedback = RealFeedback(host)  # the real port: it saves the choice
    host.toggle_dictation()
    host.switch_dictation_language()
    assert host._settings.dictation["windows_dictation_speech_language"] == "es"
    assert host.dictation_active()


def test_my_words_is_the_editors_window_over_the_same_list(
    host: Host, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.ui.dictation_words_dialog as words
    from quill.core.speech.dictation_profile import default_profile_path

    opened: list[Any] = []

    class _Dialog:
        def __init__(self, parent: Any, path: Path, *, say: Any) -> None:
            opened.append(path)

        def Destroy(self) -> None:  # noqa: N802
            pass

    monkeypatch.setattr(words, "DictationWordsDialog", _Dialog)
    host.modal = lambda _dialog, label: opened.append(label) or 0
    host.edit_dictation_words()
    assert opened == [default_profile_path(), "My Words and Phrases"]


def test_the_working_tick_is_on_by_default_here_and_off_in_the_editors(host: Host) -> None:
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings as QuillSettings

    assert host._dictation_preferences().working_tick is True
    assert QuillSettings().windows_dictation_working_tick is False
    assert LiteSettings().windows_dictation_working_tick is False
    host._settings.dictation = {"windows_dictation_working_tick": False}
    assert host._dictation_preferences().working_tick is False  # the person's choice wins


# -- Recent Phrases (D-5 slice) and What can I say (D-7) ---------------------------- #


class _Chosen:
    """Stands in for RecentPhrasesDialog: answers with a phrase and a verb."""

    verb = "insert"

    def __init__(self, _parent: Any, phrases: list[str]) -> None:
        self.phrases = phrases
        self.chosen = phrases[0]

    def Destroy(self) -> None:  # noqa: N802
        pass


@pytest.fixture()
def recent(host: Host, monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    import quill.ui.windows_dictation_dialog as dialogs

    shown: list[Any] = []

    class Dialog(_Chosen):
        def __init__(self, parent: Any, phrases: list[str]) -> None:
            super().__init__(parent, phrases)
            shown.append(self)

    monkeypatch.setattr(dialogs, "RecentPhrasesDialog", Dialog)
    host.modal = lambda _dialog, _label: 5100  # wx.ID_OK
    host.world.field = ("notepad", 1, "edit-1")
    inner = ExternalDocument(
        problem=lambda: "", where=lambda: host.world.field, type_text=host.world.type_text
    )
    host._recent_target = lambda: LockedTarget(inner, where=lambda: host.world.field)  # type: ignore[method-assign]
    return shown


def test_recent_phrases_with_nothing_dictated_says_so(host: Host, recent: list[Any]) -> None:
    host.show_recent_phrases()
    assert recent == [] and host.said[-1] == "Nothing has been dictated yet this session."


def test_recent_phrases_lists_this_runs_phrases_newest_first(host: Host, recent: list[Any]) -> None:
    host.toggle_dictation()
    host.hear("first one")
    host.hear("second one")
    host.toggle_dictation()
    host.show_recent_phrases()
    assert recent[0].phrases[:2] == ["second one", "First one"]  # as written


def test_insert_again_types_into_the_program_in_front(host: Host, recent: list[Any]) -> None:
    host.toggle_dictation()
    host.hear("kind regards")
    host.toggle_dictation()
    host.world.typed.clear()
    host.show_recent_phrases()
    assert host.world.typed == ["edit-1:Kind regards"]
    assert host.status[-1] == "Typed: Kind regards"


def test_insert_again_from_the_window_waits_for_the_field(
    host: Host, recent: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    host.toggle_dictation()
    host.hear("kind regards")
    host.toggle_dictation()
    host.world.typed.clear()
    monkeypatch.setattr(TranscribeDictationMixin, "_front_is_own_window", lambda _s: True)
    host.show_recent_phrases()
    assert host.world.typed == []
    assert host.said[-1] == "Switch to the field you want. The phrase is typed there."
    assert not host.dictation_armed()  # waiting to type, not to start dictation
    monkeypatch.setattr("quill.core.transcribe.arming.ready_to_start", lambda **_k: True)
    from types import SimpleNamespace

    import quill.platform.windows.foreground as foreground

    monkeypatch.setattr(
        foreground,
        "foreground_window_info",
        lambda: SimpleNamespace(
            hwnd=1, process_id=2, process_name="notepad.exe", window_class="Notepad"
        ),
    )
    host._on_arm_tick(None)
    assert host.world.typed == ["edit-1:Kind regards"]


def test_insert_again_is_refused_where_dictation_would_be(host: Host, recent: list[Any]) -> None:
    host.toggle_dictation()
    host.hear("secret")
    host.toggle_dictation()
    host.world.typed.clear()
    inner = ExternalDocument(
        problem=lambda: "That is a password field, so nothing is typed there.",
        where=lambda: host.world.field,
        type_text=host.world.type_text,
    )
    host._recent_target = lambda: LockedTarget(inner, where=lambda: host.world.field)  # type: ignore[method-assign]
    host.show_recent_phrases()
    assert host.world.typed == []
    assert host.said[-1] == "That is a password field, so nothing is typed there."


def test_copy_puts_the_phrase_on_the_clipboard(
    host: Host, recent: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.ui.windows_dictation_tools as tools

    copied: list[str] = []
    monkeypatch.setattr(
        tools, "copy_phrase", lambda text, say: (copied.append(text), say("Copied: " + text))
    )
    _Chosen.verb = "copy"
    try:
        host.toggle_dictation()
        host.hear("call me")
        host.toggle_dictation()
        host.show_recent_phrases()
    finally:
        _Chosen.verb = "insert"
    assert copied == ["Call me"] and host.said[-1] == "Copied: Call me"


def test_what_can_i_say_while_dictating_is_spoken_and_takes_no_focus(host: Host) -> None:
    from quill.apps.transcribe_dictation import _Feedback as RealFeedback

    opened: list[str] = []
    host.show_dictation_commands = lambda: opened.append("window")  # type: ignore[method-assign]
    RealFeedback(host).show_commands()
    assert opened == []
    # Strict mode is on here by default (D-1), so the commands carry the word.
    assert host.said[-1].startswith(
        "In another program, you can say QUILL scratch that, new line, QUILL start spelling,"
    )
    assert "or stop dictation." in host.said[-1]
    assert host.said[-1].endswith(
        "For the full list, open Dictation Commands from the Dictation menu."
    )


def test_the_full_list_is_what_works_there_with_your_own_phrases(
    host: Host, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from types import SimpleNamespace

    import quill.core.windows_dictation.profile as profile

    monkeypatch.setattr(
        profile, "load", lambda _path: SimpleNamespace(replacements=[("my address", "1 Main St")])
    )
    text = host._external_reference()
    assert "my address: 1 Main St" in text
    assert '"select that"' not in text and '"insert snippet ..."' in text
