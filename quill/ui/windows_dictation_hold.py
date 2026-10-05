"""Dictation's key, held or tapped, and the live half of a session -- shared by
QUILL and QUILL Lite.

A third mixin under :class:`~quill.ui.windows_dictation_commands.WindowsDictationMixin`
(after :mod:`windows_dictation_tools`), from the 2026-10-05 pass:

* **Hold-to-talk** (dict.md 2.1, VS Code's hold mode): the decision is the
  wx-free :class:`~quill.core.windows_dictation.hold.HoldToTalk`; this asks the
  keyboard whether the dictation key is still down, every few hundredths of a
  second, only while a press is being followed. The key is whatever the
  dictation command is bound to now, so a person who rebinds it keeps the hold.
* **Finishing the last phrase** when dictation stops while you are still
  speaking, with a timer so a recogniser that never answers cannot hold it open.
* **The live preview's** way out: the status bar's Dictation cell, a braille
  display, and -- only when asked for -- quiet speech.
* **Talking to the AI** (dict.md 3.2): a phrase written into the AI
  Conversation window's message box sends it at the pause (or waits for Enter),
  and the microphone is muted while the reply is read aloud.
"""

from __future__ import annotations

import time
from typing import Any

import wx

from quill.core.windows_dictation.hold import HoldAction, HoldToTalk
from quill.core.windows_dictation.live import FINISH_SECONDS

__all__ = ["DictationHoldMixin", "reply_seconds"]

#: How often the key is asked about while a press is followed.
_POLL_MS = 40
#: The one key there is: one hold at a time, app-wide.
_HOLD = HoldToTalk()
#: The words-per-second a reply is assumed to be read at, for muting the
#: microphone while it is read: a brisk screen-reader rate, so a fast listener
#: does not wait long, plus a second for the reader to start.
_READING_WORDS_PER_SECOND = 4.0
_MAX_MUTE_SECONDS = 60.0


def _shared() -> Any:
    from quill.ui import windows_dictation_commands

    return windows_dictation_commands


def reply_seconds(text: str) -> float:
    """Roughly how long a screen reader takes to read *text* aloud."""
    words = len(text.split())
    return min(_MAX_MUTE_SECONDS, 1.0 + words / _READING_WORDS_PER_SECOND)


def _key_code(chord: str) -> int | None:
    """The wx key code of *chord*'s main key ("Ctrl+F11" -> WXK_F11)."""
    key = str(chord or "").split(",")[-1].split("+")[-1].strip()
    if not key:
        return None
    if len(key) == 1:
        return ord(key.upper())
    code = getattr(wx, f"WXK_{key.upper()}", None)
    return int(code) if isinstance(code, int) else None


class DictationHoldMixin:
    """Hold-to-talk, finishing, and the preview's outlets."""

    # -- hooks (QUILL Lite's answers; QUILL overrides where it differs) ------- #

    def _dictation_toggle_chord(self) -> str:
        """The chord the dictation command answers to right now."""
        key_for = getattr(self, "key_for", None)
        if callable(key_for):
            try:
                return str(key_for("cmd_toggle_dictation") or "Ctrl+F11")
            except Exception:  # noqa: BLE001 - the default chord is a fine answer
                pass
        return "Ctrl+F11"

    def _dictation_key_down(self) -> bool:
        """Whether the dictation key is physically held right now."""
        code = _key_code(self._dictation_toggle_chord())
        if code is None:
            return False
        try:
            return bool(wx.GetKeyState(code))
        except Exception:  # noqa: BLE001 - no keyboard state (tests): not held
            return False

    def _dictation_say_quietly(self, text: str) -> None:
        """Speak without cutting across the reader: QUILL Lite's quiet voice."""
        announce = getattr(self, "_announce", None)
        if callable(announce):
            try:
                announce(text, interrupt=False)
            except TypeError:  # a host whose announce has no such option
                announce(text)

    def _dictation_braille(self, text: str) -> None:
        """Write *text* to a braille display, if there is one; never speak it."""
        voice = getattr(getattr(self, "app", None), "voice", None)
        engine = getattr(self, "_announcement_engine", None)
        writer = getattr(voice, "braille", None) or getattr(engine, "braille", None)
        if callable(writer):
            try:
                writer(text)
            except Exception:  # noqa: BLE001 - a display unplugged mid-phrase
                pass

    def _dictation_preview(self, text: str) -> None:
        """The live preview: the status bar's Dictation cell, and braille."""
        self._dictation_preview_text = text
        if text:
            self._dictation_braille(f"Hearing: {text}")
        self._dictation_state_changed(_shared().DictationState.RECOGNIZING)  # type: ignore[attr-defined]

    def _dictation_phrase_written(self, text: str) -> None:
        """A field that sends at the pause (the AI message box) hears about it."""
        del text
        control = self._dictation_targeted()  # type: ignore[attr-defined]
        send = getattr(control, "_quill_dictation_after_phrase", None)
        preferences = self._dictation_preferences()  # type: ignore[attr-defined]
        if callable(send) and preferences.profile == "ai" and preferences.send_after_pause:
            try:
                wx.CallAfter(send)
            except Exception:  # noqa: BLE001 - no event loop (tests): send now
                send()

    # -- the key ---------------------------------------------------------------- #

    def _dictation_repeat(self) -> bool:
        """``True`` for a key repeat of a press already being followed."""
        return _HOLD.watching

    def _dictation_press(self, controller: Any) -> None:
        """Run the dictation key's press against *controller*: start, or stop
        (keeping the last phrase), and follow the key if it is held."""
        _HOLD.hold_enabled = bool(self._dictation_preferences().hold_to_talk)  # type: ignore[attr-defined]
        action = _HOLD.press(
            now=time.monotonic(), active=controller.active, key_down=self._dictation_key_down()
        )
        if action is HoldAction.IGNORE:
            return
        if action is HoldAction.STOP:
            controller.finish()
            self._dictation_watch_finish(controller)
        else:
            controller.start()
        if _HOLD.watching:
            self._dictation_poll_later(controller)

    def _dictation_poll_later(self, controller: Any) -> None:
        try:
            wx.CallLater(_POLL_MS, self._dictation_poll, controller)
        except Exception:  # noqa: BLE001 - no event loop (tests): nothing to follow
            _HOLD.reset()

    def _dictation_poll(self, controller: Any) -> None:
        action = _HOLD.poll(now=time.monotonic(), key_down=self._dictation_key_down())
        if action is HoldAction.WATCH:
            self._dictation_poll_later(controller)
        elif action is HoldAction.RELEASE and controller.active:
            controller.finish()
            self._dictation_watch_finish(controller)

    def _dictation_watch_finish(self, controller: Any) -> None:
        """Stop anyway if the last phrase takes too long to come back."""
        if not getattr(controller, "finishing", False):
            return
        try:
            wx.CallLater(int(FINISH_SECONDS * 1000) + 100, controller.finish_overdue)
        except Exception:  # noqa: BLE001 - no event loop (tests)
            pass

    # -- Talking to the AI -------------------------------------------------------- #

    def _dictation_mute_for_reply(self, text: str, control: Any) -> None:
        """The AI's reply is being read: do not hear it as the next message."""
        controller = _shared()._controller
        if controller is None or not controller.active or _shared()._host is not self:
            return
        if self._dictation_targeted() is not control:  # type: ignore[attr-defined]
            return
        controller.mute_for(reply_seconds(text))
