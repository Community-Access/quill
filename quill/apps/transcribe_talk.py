"""QUILL Transcribe: holding the key to talk, the wake phrase, and feedback
where you are working (D-9 and D-6, 2026-10-15).

Until now both of the editors' hands-free ways in were switched off here
(``transcribe/parity.py`` ``PREFERENCES_OFF``). This mixin gives them back,
under the editors' own settings and with the editors' behaviour:

* **Hold the dictation key to talk** (More Dictation Settings, off by
  default). The start and stop key is followed while it is down, exactly as
  the editors follow Ctrl+F11 (:class:`~quill.core.windows_dictation.hold.HoldToTalk`):
  a quick press turns dictation on and off; with the setting on, holding it
  talks until it comes up. Windows reports the press of a registered key and
  never the release, so the release is read by asking Windows whether that one
  key is still down (:mod:`quill.platform.windows.key_state`) every
  :data:`_POLL_MS` milliseconds while a press is followed -- no keyboard hook.
  Because the key has Ctrl or Alt in it, phrases said while it is down wait
  (:class:`~quill.core.transcribe.talk.KeyHeldGate`) and are typed the moment it
  comes up, never while a modifier would turn the letters into shortcuts.
* **The wake phrase** (Dictation Settings, off by default). The microphone
  waits for it while another program is in front -- never while QUILL
  Transcribe's own window, a QUILL or QUILL Lite window, or a program on the
  never-type list is -- and the state line and tray name say "Listening for your
  wake phrase". As in the editors, nothing heard is written, kept or sent
  anywhere until the phrase is heard (:mod:`quill.core.windows_dictation.wake`).
* **Braille** (D-6). The words heard so far ("Hearing: ...") and the state
  changes dictation does not say aloud -- command mode, waiting for a command,
  listening for the wake phrase -- go to a braille display only, so a braille
  user in Outlook sees them. Spoken only when the preview setting says "speak".
* **Dictation Status** (D-6): the editors' Alt+F9 in the window, and an
  optional system-wide key (``transcribe_keys.py``), say one sentence: the
  state, the program, the model and what is held.
"""

from __future__ import annotations

import os
import time
from typing import Any

import wx

from quill.core.windows_dictation.hold import HoldAction, HoldToTalk

__all__ = ["TranscribeTalkMixin"]

#: How often the start and stop key is asked about while a press is followed.
_POLL_MS = 40
#: The clock the hold is timed with (a test sets its own).
_clock = time.monotonic
#: State lines dictation shows without saying (GATE-13): these, and the change
#: back from one of them, go to a braille display.
_UNSPOKEN_STATES = ("Command mode", "Waiting for a command", "Listening for your wake phrase")
#: Dictation Settings' F1 help in QUILL Transcribe, where the wake phrase and
#: the held key work in other programs rather than in an editor's window.
HELP_FOR = {
    "wake": (
        "Start dictation by saying the wake phrase instead of pressing a key. While "
        "this is on, the microphone stays open whenever another program is in front, "
        "and the state line and the tray say Listening for your wake phrase. Nothing "
        "it hears is written, kept or sent anywhere until it hears the wake phrase. It "
        "does not listen while QUILL Transcribe, QUILL or QUILL Lite is in front, or a "
        "program on the never-type list. Off unless you turn it on."
    ),
    "hold": (
        "Left off, the start and stop key starts dictating with one press and stops "
        "with the next. Turned on, you can also hold it while you talk, and dictation "
        "stops when you let go, keeping your last phrase. What you say while the key "
        "is down is typed when it comes up. A quick press still turns it on and off."
    ),
}
#: Said when the wake phrase is switched on.
WAKE_ON = (
    "Listening for your wake phrase whenever another program is in front. "
    "Nothing is written until it hears it."
)


class TranscribeTalkMixin:
    """On ``QuillTranscribeFrame``, beside ``TranscribeDictationMixin``."""

    _settings: Any
    _safe_mode: bool

    # -- holding the start and stop key ----------------------------------------- #

    def _talk_hold(self) -> HoldToTalk:
        hold = getattr(self, "_hold_to_talk", None)
        if hold is None:
            hold = HoldToTalk()
            self._hold_to_talk = hold
        return hold

    def _start_key_down(self) -> bool:
        """Whether the start and stop key is physically held right now."""
        from quill.platform.windows.key_state import key_is_down
        from quill.ui.tray_hotkey import virtual_key

        code = virtual_key(self.dictation_key())  # type: ignore[attr-defined]
        return bool(code) and key_is_down(int(code or 0))

    def _key_repeat(self) -> bool:
        """``True`` for Windows repeating a key already being followed."""
        return self._talk_hold().watching

    def _press_start_key(self, controller: Any) -> None:
        """The start and stop key went down: start, or stop keeping the last
        phrase, and follow the key while it is held."""
        hold = self._talk_hold()
        hold.hold_enabled = bool(self._dictation_preferences().hold_to_talk)  # type: ignore[attr-defined]
        action = hold.press(
            now=_clock(), active=bool(controller.active), key_down=self._start_key_down()
        )
        # A press that stops lets the last phrase through at once: it is the
        # one finish() is waiting for, and a stop is a tap, not a hold.
        self._stopping_press = action is HoldAction.STOP
        if action is HoldAction.STOP:
            controller.finish()
        else:
            self.start_dictation()  # type: ignore[attr-defined]
        if hold.watching:
            self._follow_start_key()

    def _follow_start_key(self) -> None:
        try:
            wx.CallLater(_POLL_MS, self._poll_start_key)
        except Exception:  # noqa: BLE001 - no event loop (tests): nothing to follow
            self._talk_hold().reset()
            self._release_waiting_phrases()

    def _poll_start_key(self) -> None:
        action = self._talk_hold().poll(now=_clock(), key_down=self._start_key_down())
        if action is HoldAction.WATCH:
            self._follow_start_key()
            return
        self._release_waiting_phrases()  # the key is up: what was said is typed now
        controller = getattr(self, "_dictation", None)
        if action is HoldAction.RELEASE and controller is not None and controller.active:
            controller.finish()  # keeps the phrase still being spoken

    def _talk_gate(self, controller: Any) -> Any:
        """What the recogniser reports to: the controller, with phrases held
        back while the start and stop key is down."""
        from quill.core.transcribe.talk import KeyHeldGate

        def held() -> bool:
            return self._talk_hold().watching and not getattr(self, "_stopping_press", False)

        gate = KeyHeldGate(controller, held=held)
        self._key_gate = gate
        return gate

    def _release_waiting_phrases(self) -> None:
        gate = getattr(self, "_key_gate", None)
        if gate is not None:
            gate.release()

    # -- the wake phrase --------------------------------------------------------- #

    def _wake_front_allows(self) -> bool:
        """Another program is in front, not a QUILL window, not on the never-type list."""
        try:
            from quill.platform.windows.foreground import foreground_window_info
            from quill.platform.windows.text_target import window_handles_own_expansion
        except Exception:  # noqa: BLE001 - not Windows
            return False
        from quill.core.windows_dictation.never_type import is_listed

        window = foreground_window_info()
        if not window.hwnd or window.process_id == os.getpid():
            return False
        if is_listed(window.process_name, self.never_type_list()):  # type: ignore[attr-defined]
            return False
        return not window_handles_own_expansion(window.hwnd)

    def _keep_wake_standby(self) -> None:
        """Wait for the wake phrase, or stop waiting, as the settings and the
        program in front say. Run on the window's timer and after a change."""
        from quill.core.transcribe.talk import standby_wanted

        controller = getattr(self, "_dictation", None)
        if controller is not None and (controller.active or controller.finishing):
            return
        if self.dictation_armed():  # type: ignore[attr-defined]
            return
        preferences = self._dictation_preferences()  # type: ignore[attr-defined]
        if not preferences.wake_enabled:
            if controller is not None and controller.standing_by:
                controller.disarm()
                self._dictation_state_changed()  # type: ignore[attr-defined]
            return
        wanted = standby_wanted(
            wake_enabled=True,
            refused=bool(self._refusal()),  # type: ignore[attr-defined]
            front_allows=self._wake_front_allows(),
        )
        if controller is not None and controller.standing_by:
            if not wanted:
                controller.disarm()
            return
        if not wanted or getattr(self, "_wake_gave_up", False):
            return
        controller = self._controller()  # type: ignore[attr-defined]
        controller.arm()
        if not controller.standing_by and not self._microphone_gate().busy():  # type: ignore[attr-defined]
            # The recogniser would not open, and the controller said why once;
            # not again every tick. Saving Dictation Settings tries again.
            self._wake_gave_up = True

    def _wake_settings_changed(self, before: bool) -> None:
        """Dictation Settings was saved: try the wake phrase afresh, and say so
        when it was just switched on."""
        self._wake_gave_up = False
        now = bool(self._dictation_preferences().wake_enabled)  # type: ignore[attr-defined]
        self._keep_wake_standby()
        if now and not before:
            self._announce(WAKE_ON)  # type: ignore[attr-defined]

    # -- braille (D-6) ------------------------------------------------------------ #

    def _braille_dictation(self, text: str) -> None:
        """Write *text* to a braille display, if there is one; never speak it."""
        if not text or not bool(
            getattr(getattr(self, "settings", None), "announcement_braille", True)
        ):
            return
        engine = getattr(self, "_announcement_engine", None)
        writer = getattr(engine, "braille", None)
        if callable(writer):
            try:
                writer(text)
            except Exception:  # noqa: BLE001 - a display unplugged mid-phrase
                pass

    def _braille_state_change(self) -> None:
        """A state change dictation does not say aloud goes to braille."""
        state = self._dictation_state_only()  # type: ignore[attr-defined]
        if state == "Hearing you":
            state = "Listening"
        before = getattr(self, "_brailled_state", "")
        if state == before:
            return
        self._brailled_state = state
        if state in _UNSPOKEN_STATES or before in _UNSPOKEN_STATES:
            if state != "Ready":
                self._braille_dictation(f"Dictation: {state}")

    # -- Dictation Status (D-6) ---------------------------------------------------- #

    def _dictation_program(self) -> str:
        """The program the session is locked to ("notepad"), or ""."""
        document = getattr(self, "_dictation_document", None)
        locked = getattr(document, "locked_window", None)
        hwnd = locked() if callable(locked) else 0
        if not hwnd:
            return ""
        try:
            from quill.platform.windows.foreground import window_process_name
        except Exception:  # noqa: BLE001 - not Windows
            return ""
        from quill.core.windows_dictation.never_type import friendly_name, normalise_image_name

        raw = window_process_name(hwnd)
        name = friendly_name(raw)
        if name == normalise_image_name(raw):
            name = raw  # not a program with a known name: as Windows spells the file
        return name[:-4] if name.lower().endswith(".exe") else name

    def dictation_status_sentence(self) -> str:
        from quill.core.transcribe.models import model_name
        from quill.core.transcribe.talk import status_sentence

        controller = getattr(self, "_dictation", None)
        live = controller is not None and controller.active
        sentence = status_sentence(
            state=self._dictation_state_only(),  # type: ignore[attr-defined]
            program=self._dictation_program() if live else "",
            model=model_name(self.engine_in_use()),  # type: ignore[attr-defined]
            held=int(controller.held_count) if controller is not None else 0,
        )
        profile = getattr(self, "dictation_profile_name", None)
        name = str(profile()) if callable(profile) else "Standard"
        return sentence if name == "Standard" else f"{sentence} {name} profile."  # D-23

    def speak_dictation_status(self) -> None:
        """Alt+F9 in the window, or the Dictation Status key from anywhere."""
        self._announce(self.dictation_status_sentence(), force=True)  # type: ignore[attr-defined]
