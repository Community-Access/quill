"""QUILL Transcribe's dictation: the shared controller, locked to one field.

Everything that hears and writes is QUILL's shared dictation
(:mod:`quill.core.windows_dictation`): the same controller, engines, words,
punctuation and commands as both editors and Quill Inkwell. What this mixin
adds is QUILL Transcribe's promise:

* **The field you started in.** The document port is the shared
  :class:`~quill.ui.windows_dictation_external.ExternalDocument` wrapped in a
  :class:`~quill.core.windows_dictation.target_lock.LockedTarget`. If the focus
  moves, dictation pauses and holds the words until you resume
  (:mod:`~quill.core.windows_dictation.target_hold`).
* **The model you chose.** :func:`quill.core.transcribe.models.start_problem`
  is asked before the microphone opens, and a downloaded model that will not
  load stops the start instead of quietly giving way to another
  (:class:`_ChosenModelOnly`). Using the built-in model for one session is a
  separate command, said out loud.
* **One owner.** QUILL Transcribe holds the Dictate Anywhere owner lock
  (:mod:`quill.core.dictation_owner`) while it runs; Inkwell passes its key on.
* **Starting from the tray** arms dictation: it begins in the next program you
  return to (:mod:`quill.core.transcribe.arming`).

Refused in Safe Mode, which exists to touch nothing.
"""

from __future__ import annotations

import os
from dataclasses import replace
from typing import Any

import wx

from quill.core.sound_events import SoundEvent

__all__ = ["TranscribeDictationMixin"]

_CUES = {
    "on": SoundEvent.WINDOWS_DICTATION_ON,
    "phrase": SoundEvent.WINDOWS_DICTATION_PHRASE,
    "off": SoundEvent.WINDOWS_DICTATION_OFF,
    "error": SoundEvent.WINDOWS_DICTATION_ERROR,
}
_READ_BACK_DELAY_MS = 250
_ARM_POLL_MS = 250

#: What the person is told to do when dictation pauses.
PAUSE_ADVICE = (
    "Go back and choose Resume, choose Resume in This Field to write here, or "
    "Discard Held Words. Both are in the tray menu and the Dictation menu."
)
#: Said when typing failed part-way: never "done".
WRITE_FAILURE = (
    "Dictation stopped: Windows did not take all of that phrase, so part of it "
    "may be missing. Check the field before you carry on."
)


class _Feedback:
    """The feedback port: QUILL Transcribe's speech, its window, the earcons."""

    def __init__(self, host: Any) -> None:
        self._host = host

    def has_cue(self, moment: Any) -> bool:
        from quill.ui.sound_manager import has_sound_for

        return bool(has_sound_for(_CUES[str(moment)]))

    def cue(self, moment: Any) -> None:
        from quill.ui.sound_manager import post_sound

        post_sound(_CUES[str(moment)])

    def say(self, text: str) -> None:
        self._host._announce(text, force=True)

    def read_back(self, text: str) -> None:
        try:
            wx.CallLater(_READ_BACK_DELAY_MS, self.say, text)
        except Exception:  # noqa: BLE001 - no event loop (tests)
            self.say(text)

    def show(self, text: str) -> None:
        self._host._show_dictation_message(text)

    def preview(self, text: str) -> None:
        self._host._set_status(f"Hearing: {text}" if text else "")

    def state_changed(self, state: Any) -> None:
        self._host._dictation_state_changed()

    def show_commands(self) -> None:
        wx.CallAfter(self._host.show_dictation_commands)


class _ChosenModelOnly:
    """The recogniser the settings chose, and only that one.

    The shared local recogniser gives way to the built-in engine when a
    downloaded model will not load, and says so. QUILL Transcribe does not
    switch models on its own (spec 7.5), so a give-way stops the start here.
    """

    def __init__(self, inner: Any, engine: str) -> None:
        self._inner = inner
        self._engine = engine

    def start(self, microphone: str) -> None:
        from quill.core.transcribe.models import model_name
        from quill.core.windows_dictation.controller import DictationStartError

        self._inner.start(microphone)
        if str(getattr(self._inner, "fallback_notice", "") or ""):
            try:
                self._inner.stop()
            except Exception:  # noqa: BLE001 - it is being thrown away either way
                pass
            raise DictationStartError(
                f"{model_name(self._engine)} could not be loaded, so nothing is listening. "
                "Download it again in the Model Library, choose another model, or "
                "choose Use the Built-in Model This Time."
            )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class TranscribeDictationMixin:
    """On ``QuillTranscribeFrame``: start, stop, pause and resume."""

    _settings: Any
    _data_dir: Any
    _safe_mode: bool
    frame: Any

    # -- preferences ---------------------------------------------------------- #

    def _dictation_settings_object(self) -> Any:
        from quill.core.windows_dictation.anywhere import settings_from

        return settings_from(self._settings.dictation)

    def _dictation_preferences(self) -> Any:
        """The shared preferences, as Dictate Anywhere uses them, with this
        session's built-in-model choice if the person made one."""
        from quill.core.speech.dictation_profile import default_profile_path
        from quill.core.windows_dictation.preferences import DictationPreferences
        from quill.core.windows_dictation.profile import rewriter

        try:
            rewrite = rewriter(default_profile_path())
        except Exception:  # noqa: BLE001 - a broken word list never stops dictation
            rewrite = None
        preferences = DictationPreferences.from_settings(
            self._dictation_settings_object(), rewrite=rewrite
        )
        preferences = replace(preferences, wake_enabled=False, hold_to_talk=False)
        override = getattr(self, "_engine_override", "")
        return replace(preferences, engine=override) if override else preferences

    def chosen_engine(self) -> str:
        """The model the person chose (not this session's stand-in)."""
        return str(self._dictation_settings_object().windows_dictation_engine)

    def engine_in_use(self) -> str:
        return str(getattr(self, "_engine_override", "") or self.chosen_engine())

    # -- the controller ------------------------------------------------------- #

    def _controller(self) -> Any:
        controller = getattr(self, "_dictation", None)
        if controller is None:
            from quill.core.windows_dictation.controller import DictationController
            from quill.core.windows_dictation.target_lock import LockedTarget
            from quill.ui.windows_dictation_external import (
                ExternalDocument,
                focus_identity,
                foreground_problem,
                hush_unless_spoken,
            )

            def problem() -> str:
                return foreground_problem(app="QUILL Transcribe", key="start and stop key")

            document = LockedTarget(
                ExternalDocument(
                    problem=problem, hush=hush_unless_spoken(self._dictation_preferences)
                ),
                where=focus_identity,
                advice=PAUSE_ADVICE,
            )
            document.write_failure = WRITE_FAILURE  # type: ignore[attr-defined]
            controller = DictationController(
                recognizer=self._make_chosen_recognizer,
                document=document,
                feedback=_Feedback(self),
                preferences=self._dictation_preferences,
            )
            self._dictation = controller
        return controller

    @staticmethod
    def _make_chosen_recognizer(controller: Any, preferences: Any) -> Any:
        from quill.ui.windows_dictation_commands import _make_recognizer

        return _ChosenModelOnly(_make_recognizer(controller, preferences), preferences.engine)

    def dictation_active(self) -> bool:
        controller = getattr(self, "_dictation", None)
        return bool(controller is not None and controller.active)

    def dictation_paused(self) -> bool:
        controller = getattr(self, "_dictation", None)
        return bool(controller is not None and controller.paused_for_target)

    # -- the commands ----------------------------------------------------------- #

    def _refusal(self) -> str:
        """Why dictation cannot start at all right now, or ``""``."""
        if self._safe_mode:
            return "Safe Mode is on, so QUILL Transcribe does not listen."
        if not self._own_dictate_anywhere():
            return (
                "Quill Inkwell is dictating right now. Stop it there, and QUILL "
                "Transcribe takes over."
            )
        from quill.core.transcribe.models import start_problem

        preferences = self._dictation_preferences()
        return start_problem(
            preferences.engine,
            preferences.speech_language,
            openai_consent=preferences.openai_consent,
        )

    def toggle_dictation(self) -> None:
        """The start and stop key, pressed in the field to dictate into."""
        if self._cancel_arming():
            return
        controller = self._controller()
        if controller.active:
            controller.finish()  # keeps the phrase being spoken
            return
        self.start_dictation()

    def start_dictation(self) -> None:
        refusal = self._refusal()
        if refusal:
            self._dictation_refused(refusal)
            return
        self._controller().start()

    def stop_dictation(self) -> None:
        if self._cancel_arming():
            return
        controller = getattr(self, "_dictation", None)
        if controller is None or not controller.active:
            self._announce("Dictation is already off.")  # type: ignore[attr-defined]
            return
        controller.finish()

    def start_or_stop_from_here(self) -> None:
        """The tray menu and the window's button: stop, or arm a start."""
        if self._cancel_arming():
            return
        if self.dictation_active():
            self.stop_dictation()
            return
        refusal = self._refusal()
        if refusal:
            self._dictation_refused(refusal)
            return
        self._arm_start()

    def resume_dictation(self) -> None:
        if not self.dictation_paused():
            self._announce("Dictation is not paused.")  # type: ignore[attr-defined]
            return
        self._controller().resume_held()

    def resume_in_this_field(self) -> None:
        if not self.dictation_paused():
            self._announce("Dictation is not paused.")  # type: ignore[attr-defined]
            return
        if self._front_is_own_window():
            self._arm(here=True)
            return
        self._controller().resume_held(here=True)

    def discard_held_words(self) -> None:
        if not self.dictation_paused():
            self._announce("Dictation is not paused, so nothing is held.")  # type: ignore[attr-defined]
            return
        self._controller().discard_held()

    def use_built_in_model_once(self) -> None:
        """Start this one session on the built-in model, on purpose."""
        from quill.core.transcribe.models import FALLBACK_ENGINE, model_name

        if self.dictation_active():
            self._announce("Stop dictation first; the model is chosen when it starts.")  # type: ignore[attr-defined]
            return
        if self.chosen_engine() == FALLBACK_ENGINE:
            self._announce(f"{model_name(FALLBACK_ENGINE)} is already your model.")  # type: ignore[attr-defined]
            return
        self._engine_override = FALLBACK_ENGINE
        self._announce(  # type: ignore[attr-defined]
            f"This session uses {model_name(FALLBACK_ENGINE)}, the built-in model. "
            f"Your chosen model is still {model_name(self.chosen_engine())}."
        )
        self.start_or_stop_from_here()

    def _dictation_refused(self, sentence: str) -> None:
        self._last_refusal = sentence
        self._show_dictation_message(sentence)
        self._announce(sentence, force=True, sound=SoundEvent.WINDOWS_DICTATION_ERROR)  # type: ignore[attr-defined]
        self._dictation_state_changed()

    # -- arming: the tray and the window ---------------------------------------- #

    def _front_is_own_window(self) -> bool:
        try:
            from quill.platform.windows.foreground import foreground_window_info

            return int(foreground_window_info().process_id) == os.getpid()
        except Exception:  # noqa: BLE001 - not Windows: treat as our own
            return True

    def _arm_start(self) -> None:
        if not self._front_is_own_window():
            self.start_dictation()
            return
        self._arm(here=False)

    def _arm(self, *, here: bool) -> None:
        from quill.core.transcribe.arming import ARM_SECONDS

        self._armed_for = "resume" if here else "start"
        self._armed_ticks = int(ARM_SECONDS * 1000 / _ARM_POLL_MS)
        timer = getattr(self, "_arm_timer", None)
        if timer is None:
            timer = wx.Timer(self.frame)
            self.frame.Bind(wx.EVT_TIMER, self._on_arm_tick, timer)
            self._arm_timer = timer
        timer.Start(_ARM_POLL_MS)
        verb = "resumes" if here else "starts"
        self._announce(  # type: ignore[attr-defined]
            f"Switch to the field you want. Dictation {verb} there. Choose the same "
            "command again to cancel."
        )
        self._dictation_state_changed()

    def _cancel_arming(self, *, say: bool = True, refresh: bool = True) -> bool:
        if not getattr(self, "_armed_for", ""):
            return False
        self._armed_for = ""
        timer = getattr(self, "_arm_timer", None)
        if timer is not None:
            timer.Stop()
        if say:
            self._announce("Cancelled; dictation did not start.")  # type: ignore[attr-defined]
        if refresh:
            self._dictation_state_changed()
        return True

    def dictation_armed(self) -> bool:
        return bool(getattr(self, "_armed_for", ""))

    def _on_arm_tick(self, _event: Any) -> None:
        from quill.core.transcribe.arming import ready_to_start

        self._armed_ticks -= 1
        try:
            from quill.platform.windows.foreground import foreground_window_info

            window = foreground_window_info()
            ready = ready_to_start(
                hwnd=window.hwnd,
                process_id=window.process_id,
                window_class=window.window_class,
                own_process=os.getpid(),
            )
        except Exception:  # noqa: BLE001 - not Windows: nothing will come forward
            ready = False
        if ready:
            what = self._armed_for
            self._cancel_arming(say=False, refresh=False)  # the start refreshes
            if what == "resume":
                self._controller().resume_held(here=True)
            else:
                self.start_dictation()
            return
        if self._armed_ticks <= 0:
            self._cancel_arming(say=False)
            self._announce("No other program came forward, so dictation did not start.")  # type: ignore[attr-defined]

    # -- one owner ---------------------------------------------------------- #

    def _own_dictate_anywhere(self) -> bool:
        """Hold the owner lock, taking it now if Inkwell has let go."""
        lock = getattr(self, "_owner_lock", None)
        if lock is None:
            from quill.core.dictation_owner import OwnerLock

            lock = OwnerLock("transcribe")
            self._owner_lock = lock
        return bool(lock.claim())

    def _answer_owner_requests(self) -> None:
        """Requests passed on by Inkwell (its Dictate Anywhere key, pressed in
        the field to dictate into), answered as if our own key was pressed."""
        from quill.core.dictation_owner import take_requests

        if self._safe_mode or not self._own_dictate_anywhere():
            return
        for request in take_requests():
            if request.command == "toggle":
                self.toggle_dictation()
            elif request.command == "start" and not self.dictation_active():
                self.start_dictation()
            elif request.command == "stop":
                self.stop_dictation()
            elif request.command == "show":
                self._restore_from_tray()  # type: ignore[attr-defined]

    def _release_dictate_anywhere(self) -> None:
        controller = getattr(self, "_dictation", None)
        if controller is not None:
            controller.shut_down()
        self._cancel_arming(say=False)
        lock = getattr(self, "_owner_lock", None)
        if lock is not None:
            lock.release()

    # -- what the window shows ------------------------------------------------- #

    def dictation_state_word(self) -> str:
        """Ready, Listening, Paused, Waiting for a field, Off (Safe Mode)."""
        from quill.core.windows_dictation.ports import DictationState

        if self._safe_mode:
            return "Off (Safe Mode)"
        if self.dictation_armed():
            return "Waiting for you to switch to a field"
        controller = getattr(self, "_dictation", None)
        if controller is None:
            return "Ready"
        state = controller.state
        if controller.paused_for_target:
            held = controller.held_count
            return f"Paused, {held} phrase{'s' if held != 1 else ''} held"
        if state is DictationState.PAUSED:
            return "Paused, waiting for the microphone"
        if state is DictationState.STARTING:
            return "Starting"
        if state is DictationState.RECOGNIZING:
            return "Hearing you"
        if state in (DictationState.LISTENING, DictationState.PROCESSING):
            return "Listening"
        return "Ready"

    def _dictation_state_changed(self) -> None:
        controller = getattr(self, "_dictation", None)
        if controller is not None and not controller.active and not self.dictation_armed():
            self._engine_override = ""  # a stand-in model lasts one session
        refresh = getattr(self, "_refresh_view", None)
        if callable(refresh):
            refresh()

    def _show_dictation_message(self, text: str) -> None:
        self._last_message = text
        self._set_status(text)  # type: ignore[attr-defined]
        refresh = getattr(self, "_refresh_view", None)
        if callable(refresh):
            refresh()

    def show_dictation_commands(self) -> None:
        from quill.core.windows_dictation.reference import commands_reference
        from quill.ui.dictation_lists_dialog import DictationCommandsDialog

        dialog = DictationCommandsDialog(self.frame, commands_reference())
        try:
            self._show_modal_dialog(dialog, "Dictation Commands")  # type: ignore[attr-defined]
        finally:
            dialog.Destroy()
