"""QUILL Transcribe's dictation: the shared controller, locked to one field.

Everything that hears and writes is QUILL's shared dictation
(:mod:`quill.core.windows_dictation`): the same controller, engines, words,
punctuation and commands as both editors and Quill Inkwell. What this mixin
adds is QUILL Transcribe's promise:

* **The field you started in.** The document port is the shared
  :func:`~quill.ui.windows_dictation_external.locked_external_document`, the
  same one Quill Inkwell's Dictate Anywhere uses. If the focus moves, dictation
  pauses and holds the words until you resume
  (:mod:`~quill.core.windows_dictation.target_hold`); Resume, Resume in This
  Field and Discard Held Words are :mod:`quill.ui.dictation_field_hold`'s.
* **Never into a listed program.** The never-type list
  (``windows_dictation_never_type``, :mod:`quill.core.windows_dictation.never_type`)
  is checked at every start, as the password field is.
* **Where the speech goes.** With a cloud engine, the state line and the tray
  name end "Speech goes to OpenAI." (:func:`~quill.core.windows_dictation.engines.cloud_line`).
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

from dataclasses import replace
from typing import Any

import wx

from quill.core.sound_events import SoundEvent
from quill.ui.dictation_field_hold import FieldHoldMixin
from quill.ui.windows_dictation_external import PAUSE_ADVICE, WRITE_FAILURE

__all__ = ["PAUSE_ADVICE", "WRITE_FAILURE", "TranscribeDictationMixin"]

_CUES = {
    "on": SoundEvent.WINDOWS_DICTATION_ON,
    "phrase": SoundEvent.WINDOWS_DICTATION_PHRASE,
    "off": SoundEvent.WINDOWS_DICTATION_OFF,
    "error": SoundEvent.WINDOWS_DICTATION_ERROR,
    "working": SoundEvent.WINDOWS_DICTATION_WORKING,
}
_READ_BACK_DELAY_MS = 250


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
        """Said "what can I say" while dictating: a short spoken answer (D-7).
        The window would take the focus, and that pauses dictation."""
        self.say(self._host.spoken_commands_summary())

    def library(self) -> Any:
        """Snippets, abbreviations and clips by voice: insert only (D-8 slice)."""
        from quill.ui.windows_dictation_anywhere_library import AnywhereLibrary

        return AnywhereLibrary()

    def call_later(self, seconds: float, callback: Any) -> Any:
        """The working tick's clock (working_tick.py): stopped when the wait ends."""
        return wx.CallLater(int(seconds * 1000), callback)

    def set_speech_language(self, language: str) -> None:
        """ "Switch to Spanish" said aloud, or Ctrl+Shift+F11: kept, as in the editors."""
        self._host._save_speech_language(language)


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


class TranscribeDictationMixin(FieldHoldMixin):
    """On ``QuillTranscribeFrame``: start, stop, pause and resume."""

    _settings: Any
    _data_dir: Any
    _safe_mode: bool
    frame: Any

    # -- preferences ---------------------------------------------------------- #

    def _dictation_settings_object(self) -> Any:
        from quill.core.transcribe.settings import TRANSCRIBE_DICTATION_DEFAULTS
        from quill.core.windows_dictation.anywhere import settings_from

        return settings_from({**TRANSCRIBE_DICTATION_DEFAULTS, **self._settings.dictation})

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
        from quill.core.transcribe.parity import PREFERENCES_OFF

        # The documented subset (parity.py): everything else is the editors'.
        preferences = replace(preferences, **dict.fromkeys(PREFERENCES_OFF, False))
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
            from quill.ui.windows_dictation_external import locked_external_document

            document = locked_external_document(
                preferences=self._dictation_preferences,
                never_type=self.never_type_list,
                app="QUILL Transcribe",
                key="start and stop key",
            )
            controller = DictationController(
                recognizer=self._make_chosen_recognizer,
                document=document,
                feedback=_Feedback(self),
                preferences=self._dictation_preferences,
                microphone=self._microphone_gate(),
            )
            self._dictation = controller
        return controller

    @staticmethod
    def _make_chosen_recognizer(controller: Any, preferences: Any) -> Any:
        from quill.ui.windows_dictation_commands import _make_recognizer

        return _ChosenModelOnly(_make_recognizer(controller, preferences), preferences.engine)

    def never_type_list(self) -> list[str]:
        """The programs dictation never types into (D-24), as saved."""
        return list(self._dictation_settings_object().windows_dictation_never_type)

    def dictation_active(self) -> bool:
        controller = getattr(self, "_dictation", None)
        return bool(controller is not None and controller.active)

    # -- FieldHoldMixin's hooks (quill/ui/dictation_field_hold.py) ------------- #

    def _held_controller(self) -> Any:
        return getattr(self, "_dictation", None)

    def _hold_refresh(self) -> None:
        self._dictation_state_changed()

    def _armed(self, what: str, text: str) -> None:
        if what == "insert":
            self._type_recent_phrase(text)  # type: ignore[attr-defined]
        elif what == "start":
            self.start_dictation()
        else:
            super()._armed(what, text)

    # -- the commands ----------------------------------------------------------- #

    def _refusal(self) -> str:
        """Why dictation cannot start at all right now, or ``""``."""
        if self._safe_mode:
            return "Safe Mode is on, so QUILL Transcribe does not listen."
        if not self._own_dictate_anywhere():
            from quill.core.dictation_owner import busy_sentence

            return busy_sentence("inkwell", asker="transcribe")
        busy = self._microphone_gate().busy()  # QUILL or QUILL Lite dictating (D-11)
        if busy:
            return busy
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

    def _arm_start(self) -> None:
        if not self._front_is_own_window():
            self.start_dictation()
            return
        self._arm(here=False)

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

    def _microphone_gate(self) -> Any:
        """The family's one microphone (D-11): held only while dictation listens,
        so QUILL and QUILL Lite can dictate while this waits in the tray."""
        gate = getattr(self, "_microphone", None)
        if gate is None:
            from quill.core.dictation_owner import MicrophoneLock

            gate = MicrophoneLock(
                "transcribe", key=lambda: str(self._settings.dictation_hotkey or "")
            )
            self._microphone = gate
        return gate

    def _release_dictate_anywhere(self) -> None:
        controller = getattr(self, "_dictation", None)
        if controller is not None:
            controller.shut_down()  # closes the recogniser, and lets go of the microphone
        self._cancel_arming(say=False)
        for name in ("_microphone", "_owner_lock"):
            lock = getattr(self, name, None)
            if lock is not None:
                lock.release()

    # -- the language (Ctrl+Shift+F11, the editors' chord) ----------------------- #

    def switch_dictation_language(self) -> None:
        """English to Spanish, or Spanish to English, from now on -- the editors'
        Switch Dictation Language, over QUILL Transcribe's own settings."""
        current = self._dictation_preferences().speech_language
        target = "en" if current == "es" else "es"
        controller = getattr(self, "_dictation", None)
        if controller is not None and controller.active:
            controller.switch_language(target)  # reopens the engine in that language
            return
        self._save_speech_language(target)
        self._announce("Español." if target == "es" else "English.")  # type: ignore[attr-defined]

    def _save_speech_language(self, language: str) -> None:
        """Keep the dictation language, and say if the chosen model cannot do it."""
        from quill.core.windows_dictation.engines import language_model_problem

        language = "es" if language == "es" else "en"
        self._set_dictation_field("windows_dictation_speech_language", language)  # type: ignore[attr-defined]
        label = "Spanish" if language == "es" else "English"
        self._set_status(f"Dictation language: {label}")  # type: ignore[attr-defined]
        problem = language_model_problem(self.chosen_engine(), language)
        if problem:
            self._announce(problem)  # type: ignore[attr-defined]

    # -- what the window shows ------------------------------------------------- #

    def dictation_state_word(self) -> str:
        """Ready, Listening, Paused, Waiting for a field, Off (Safe Mode); and
        while a cloud engine has the speech, "Speech goes to OpenAI." after it."""
        state = self._dictation_state_only()
        controller = getattr(self, "_dictation", None)
        if controller is not None and controller.active:
            from quill.core.windows_dictation.engines import cloud_line

            line = cloud_line(self.engine_in_use())
            if line:
                return f"{state}. {line}"
        return state

    def _dictation_state_only(self) -> str:
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
