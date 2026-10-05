"""Dictate Anywhere in Quill Inkwell: QUILL's dictation, typed into other programs.

dict.md 3.9 (gap 8, question 9). Inkwell already lives in the tray, already has
system-wide keys and already types into other programs, so it hosts this. It is
opt-in twice over: nothing listens until you choose a **Dictate Anywhere Key**
(File menu, the shared picker, none by default like every Inkwell key), and the
microphone opens only while you are dictating.

Press the key in any program, speak, pause: each phrase is typed where the
cursor is. Press it again, or say "stop dictation", to stop. It is the shared
controller with the same engines, words, punctuation, spelling and modes as
both editors' dictation (``quill/core/windows_dictation``); the port is
:class:`quill.ui.windows_dictation_external.ExternalDocument`.

Its dictation settings are Inkwell's own copy of the editors' (the same names,
cleaned by the same loader), set in **Dictation Settings...** here -- the same
window both editors show -- or handed over by an editor's More Dictation
Settings, **Dictate in Other Programs...**. The read-back defaults to a tone:
the screen reader echoes typed characters itself.

Refused in Safe Mode, which exists to touch nothing.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.sound_events import SoundEvent

__all__ = ["InkwellDictationMixin"]

_CUES = {
    "on": SoundEvent.WINDOWS_DICTATION_ON,
    "phrase": SoundEvent.WINDOWS_DICTATION_PHRASE,
    "off": SoundEvent.WINDOWS_DICTATION_OFF,
    "error": SoundEvent.WINDOWS_DICTATION_ERROR,
}
_READ_BACK_DELAY_MS = 250


class _InkwellFeedback:
    """The feedback port: Inkwell's speech, its status line and the earcons."""

    def __init__(self, frame: Any) -> None:
        self._frame = frame

    def has_cue(self, moment: Any) -> bool:
        from quill.ui.sound_manager import has_sound_for

        return bool(has_sound_for(_CUES[str(moment)]))

    def cue(self, moment: Any) -> None:
        from quill.ui.sound_manager import post_sound

        post_sound(_CUES[str(moment)])

    def say(self, text: str) -> None:
        self._frame._announce(text, force=True)

    def read_back(self, text: str) -> None:
        try:
            wx.CallLater(_READ_BACK_DELAY_MS, self.say, text)
        except Exception:  # noqa: BLE001 - no event loop (tests)
            self.say(text)

    def show(self, text: str) -> None:
        self._frame._set_status(text)

    def state_changed(self, state: Any) -> None:
        self._frame._dictation_anywhere_changed()

    def show_commands(self) -> None:
        wx.CallAfter(self._frame.show_dictation_commands)


class InkwellDictationMixin:
    """On ``QuillInkwellFrame``: the Dictate Anywhere toggle, its settings window."""

    _settings: Any
    _data_dir: Any
    _safe_mode: bool
    frame: Any

    # -- the settings, Inkwell's copy ----------------------------------------- #

    def _anywhere_settings(self) -> Any:
        from quill.core.windows_dictation.anywhere import settings_from

        return settings_from(getattr(self._settings, "dictation", None))

    def _anywhere_preferences(self) -> Any:
        from quill.core.speech.dictation_profile import default_profile_path
        from quill.core.windows_dictation.preferences import DictationPreferences
        from quill.core.windows_dictation.profile import rewriter

        try:
            rewrite = rewriter(default_profile_path())
        except Exception:  # noqa: BLE001 - a broken word list never stops dictation
            rewrite = None
        from dataclasses import replace

        preferences = DictationPreferences.from_settings(self._anywhere_settings(), rewrite=rewrite)
        return replace(preferences, wake_enabled=False, hold_to_talk=False)

    def take_dictation_handoff(self) -> bool:
        """An editor's Dictate in Other Programs: take its settings, once."""
        from quill.core.expansion.settings import save_settings
        from quill.core.windows_dictation.anywhere import take_handoff

        stored = take_handoff(self._data_dir)
        if stored is None:
            return False
        self._settings.dictation = stored
        save_settings(self._data_dir, self._settings)
        key = self._settings.dictate_anywhere_hotkey
        self._announce(  # type: ignore[attr-defined]
            f"Dictate Anywhere is ready with your dictation settings. Press {key} in any "
            "program to start."
            if key
            else "Dictate Anywhere has your dictation settings. Choose its key next."
        )
        if not key:
            wx.CallAfter(self.choose_inkwell_key, "dictate_anywhere_hotkey")  # type: ignore[attr-defined]
        return True

    # -- the commands ---------------------------------------------------------- #

    def _anywhere_controller(self) -> Any:
        controller = getattr(self, "_anywhere", None)
        if controller is None:
            from quill.core.windows_dictation.controller import DictationController
            from quill.ui.windows_dictation_commands import _make_recognizer
            from quill.ui.windows_dictation_external import ExternalDocument

            controller = DictationController(
                recognizer=_make_recognizer,
                document=ExternalDocument(),
                feedback=_InkwellFeedback(self),
                preferences=self._anywhere_preferences,
            )
            self._anywhere = controller
        return controller

    def toggle_dictate_anywhere(self) -> None:
        """The Dictate Anywhere key: start typing what you say, or stop."""
        if self._safe_mode:
            self._announce("Safe Mode: Dictate Anywhere is off.")  # type: ignore[attr-defined]
            return
        controller = self._anywhere_controller()
        if controller.active:
            controller.finish()  # keeps the phrase being spoken
        else:
            controller.start()

    def dictate_anywhere_active(self) -> bool:
        controller = getattr(self, "_anywhere", None)
        return bool(controller is not None and controller.active)

    def _dictation_anywhere_changed(self) -> None:
        item = getattr(self, "_anywhere_item_id", None)
        menu_bar = self.frame.GetMenuBar() if item is not None else None
        if menu_bar is not None:
            found = menu_bar.FindItemById(int(item))
            if found is not None:
                found.Check(self.dictate_anywhere_active())

    def edit_anywhere_settings(self) -> None:
        """Dictation Settings: the window both editors show, over Inkwell's copy."""
        from quill.core.expansion.settings import save_settings
        from quill.core.windows_dictation.anywhere import stored_from
        from quill.ui.windows_dictation_dialog import WindowsDictationDialog

        settings = self._anywhere_settings()
        dialog = WindowsDictationDialog(self.frame, settings, self._announce)  # type: ignore[attr-defined]
        try:
            answer = self._show_modal_dialog(dialog, "Dictation Settings")  # type: ignore[attr-defined]
            if answer == wx.ID_OK:
                dialog.apply(settings)
        finally:
            dialog.Destroy()
        if answer != wx.ID_OK:
            return
        self._settings.dictation = stored_from(settings)
        save_settings(self._data_dir, self._settings)
        self._set_status("Dictation settings saved.")  # type: ignore[attr-defined]

    def show_dictation_commands(self) -> None:
        from quill.core.windows_dictation.reference import commands_reference
        from quill.ui.dictation_lists_dialog import DictationCommandsDialog

        dialog = DictationCommandsDialog(self.frame, commands_reference())
        try:
            self._show_modal_dialog(dialog, "Dictation Commands")  # type: ignore[attr-defined]
        finally:
            dialog.Destroy()

    def _append_dictation_menu(self, menu_bar: Any) -> None:
        """The Dictation menu: the toggle and the settings window."""
        menu = wx.Menu()
        self._anywhere_item_id = wx.NewIdRef()
        settings_id = wx.NewIdRef()
        menu.AppendCheckItem(self._anywhere_item_id, "&Dictate Anywhere\tCtrl+D")
        menu.Append(settings_id, "Dictation &Settings...\tCtrl+Alt+D")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.toggle_dictate_anywhere(), id=self._anywhere_item_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.edit_anywhere_settings(), id=settings_id)
        self._keep_menu_ids(self._anywhere_item_id, settings_id)  # type: ignore[attr-defined]
        menu_bar.Append(menu, "&Dictation")

    def _stop_dictate_anywhere(self) -> None:
        controller = getattr(self, "_anywhere", None)
        if controller is not None:
            controller.shut_down()
