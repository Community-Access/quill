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
:func:`quill.ui.windows_dictation_external.locked_external_document`, the one
QUILL Transcribe uses.

**The field you started in** (D-15, 2026-10-13). Until then Inkwell followed
the focus and typed into whatever field you landed in. Now, as in QUILL
Transcribe, a focus move pauses dictation and holds the words; **Resume**,
**Resume in This Field** and **Discard Held Words** are in the Dictation menu
and, while paused, the tray menu (:mod:`quill.ui.dictation_field_hold`, shared
with QUILL Transcribe). Stopping while paused says how many phrases were not
written. The never-type list (D-24) is checked at every start.

Its dictation settings are Inkwell's own copy of the editors' (the same names,
cleaned by the same loader), set in **Dictation Settings...** here -- the same
window both editors show -- or handed over by an editor's More Dictation
Settings, **Dictate in Other Programs...**. The read-back defaults to a tone:
the screen reader echoes typed characters itself.

Refused in Safe Mode, which exists to touch nothing.

**One owner** (2026-10-11): while QUILL Transcribe runs it owns Dictate Anywhere,
and Inkwell's key is passed on to it rather than opening a second microphone
(:mod:`quill.core.dictation_owner`). Inkwell holds the owner lock only for the
length of its own session.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.sound_events import SoundEvent
from quill.ui.dictation_field_hold import FieldHoldMixin

__all__ = ["InkwellDictationMixin"]

_CUES = {
    "on": SoundEvent.WINDOWS_DICTATION_ON,
    "phrase": SoundEvent.WINDOWS_DICTATION_PHRASE,
    "off": SoundEvent.WINDOWS_DICTATION_OFF,
    "error": SoundEvent.WINDOWS_DICTATION_ERROR,
    "working": SoundEvent.WINDOWS_DICTATION_WORKING,
    "command_on": SoundEvent.WINDOWS_DICTATION_COMMAND_ON,
    "command_off": SoundEvent.WINDOWS_DICTATION_COMMAND_OFF,
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

    def library(self) -> Any:
        """Snippets, abbreviations and clips by voice: insert only (D-8 slice)."""
        from quill.ui.windows_dictation_anywhere_library import AnywhereLibrary

        return AnywhereLibrary()

    def call_later(self, seconds: float, callback: Any) -> Any:
        """The working tick's clock (working_tick.py), if it is switched on."""
        return wx.CallLater(int(seconds * 1000), callback)


class InkwellDictationMixin(FieldHoldMixin):
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
            from quill.core.dictation_owner import MicrophoneLock
            from quill.core.windows_dictation.controller import DictationController
            from quill.ui.windows_dictation_commands import _make_recognizer
            from quill.ui.windows_dictation_external import locked_external_document

            controller = DictationController(
                recognizer=_make_recognizer,
                document=locked_external_document(
                    preferences=self._anywhere_preferences, never_type=self.never_type_list
                ),
                feedback=_InkwellFeedback(self),
                preferences=self._anywhere_preferences,
                microphone=MicrophoneLock("inkwell"),  # one microphone in the family (D-11)
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
            return
        if self._passed_to_transcribe():
            return
        controller.start()
        if not controller.active:
            self._release_anywhere_owner()

    # -- one owner (quill/core/dictation_owner.py) ----------------------------- #

    def _passed_to_transcribe(self) -> bool:
        """QUILL Transcribe owns Dictate Anywhere while it runs: pass the key on.

        Otherwise Inkwell takes the owner lock for this one session, so QUILL
        Transcribe cannot start a second microphone while Inkwell is listening.
        """
        from quill.core.dictation_owner import OwnerLock, send_request

        lock = getattr(self, "_anywhere_owner", None)
        if lock is None:
            lock = OwnerLock("inkwell")
            self._anywhere_owner = lock
        if lock.claim():
            return False
        if send_request("toggle", sender="inkwell"):
            self._set_status("Dictate Anywhere passed to QUILL Transcribe.")  # type: ignore[attr-defined]
        else:
            self._announce("QUILL Transcribe is dictating, and could not be reached.")  # type: ignore[attr-defined]
        return True

    def _release_anywhere_owner(self) -> None:
        lock = getattr(self, "_anywhere_owner", None)
        if lock is not None:
            lock.release()

    def never_type_list(self) -> list[str]:
        """The programs dictation never types into (D-24), as saved."""
        return list(self._anywhere_settings().windows_dictation_never_type)

    def dictate_anywhere_active(self) -> bool:
        controller = getattr(self, "_anywhere", None)
        return bool(controller is not None and controller.active)

    # -- FieldHoldMixin's hooks (quill/ui/dictation_field_hold.py) ------------- #

    def _held_controller(self) -> Any:
        return getattr(self, "_anywhere", None)

    def _hold_refresh(self) -> None:
        self._dictation_anywhere_changed()

    def _dictation_anywhere_changed(self) -> None:
        active = self.dictate_anywhere_active()
        if not active:
            self._release_anywhere_owner()  # the session is over: QUILL Transcribe may own it
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            item = getattr(self, "_anywhere_item_id", None)
            found = menu_bar.FindItemById(int(item)) if item is not None else None
            if found is not None:
                found.Check(active)
            for item_id in getattr(self, "_held_item_ids", ()):
                held = menu_bar.FindItemById(int(item_id))
                if held is not None:
                    held.Enable(self.dictation_paused())
        self._refresh_tray_name(active)

    def _refresh_tray_name(self, active: bool) -> None:
        """The tray icon's name: what Dictate Anywhere is doing, and, with a
        cloud engine, where the speech goes (D-24)."""
        icon = getattr(self, "_tray_icon", None)
        if icon is None:
            return
        name = "Quill Inkwell"
        if active:
            from quill.core.windows_dictation.engines import cloud_line

            name += " - Dictate Anywhere paused" if self.dictation_paused() else " - Dictating"
            line = cloud_line(self._anywhere_preferences().engine)
            if line:
                name += f". {line}"
        art = getattr(self, "_app_icon", None) or wx.ArtProvider.GetIcon(
            wx.ART_INFORMATION, wx.ART_OTHER, (16, 16)
        )
        try:
            icon.SetIcon(art, name)
        except Exception:  # noqa: BLE001 - a tooltip is never worth a failure
            pass

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

        # Only what works in another program (D-7), as in QUILL Transcribe.
        dialog = DictationCommandsDialog(self.frame, commands_reference(external=True))
        try:
            self._show_modal_dialog(dialog, "Dictation Commands")  # type: ignore[attr-defined]
        finally:
            dialog.Destroy()

    def _append_dictation_menu(self, menu_bar: Any) -> None:
        """The Dictation menu: the toggle, the three paused commands on QUILL
        Transcribe's keys for them (rule 2), and the settings window."""
        menu = wx.Menu()
        self._anywhere_item_id = wx.NewIdRef()
        settings_id = wx.NewIdRef()
        menu.AppendCheckItem(self._anywhere_item_id, "&Dictate Anywhere\tCtrl+D")
        held = (
            ("&Resume\tCtrl+R", self.resume_dictation),
            ("Resume in &This Field\tCtrl+Shift+R", self.resume_in_this_field),
            ("Discard &Held Words\tCtrl+Shift+D", self.discard_held_words),
        )
        self._held_item_ids: list[Any] = []
        for label, handler in held:
            item_id = wx.NewIdRef()
            menu.Append(item_id, label)
            menu.Enable(item_id, False)  # nothing is held until dictation pauses
            self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=item_id)
            self._held_item_ids.append(item_id)
        menu.AppendSeparator()
        menu.Append(settings_id, "Dictation &Settings...\tCtrl+Alt+D")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.toggle_dictate_anywhere(), id=self._anywhere_item_id
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.edit_anywhere_settings(), id=settings_id)
        self._keep_menu_ids(self._anywhere_item_id, settings_id, *self._held_item_ids)  # type: ignore[attr-defined]
        menu_bar.Append(menu, "&Dictation")

    def _append_held_tray_rows(self, menu: Any) -> None:
        """While Dictate Anywhere is paused for its field: the three commands,
        bound on the tray menu itself (#1465)."""
        if not self.dictation_paused():
            return
        # QUILL Transcribe's words. Only Resume's letter differs: R is Quill
        # Radio's in the sibling rows this tray also carries (GATE-14).
        rows = (
            ("Res&ume", self.resume_dictation),
            ("Resume in This &Field", self.resume_in_this_field),
            ("&Discard Held Words", self.discard_held_words),
        )
        menu.AppendSeparator()
        for label, handler in rows:
            item_id = wx.NewIdRef()
            menu.Append(item_id, label)
            menu.Bind(wx.EVT_MENU, lambda _e, run=handler: wx.CallAfter(run), id=item_id)
            self._keep_menu_ids(item_id)  # type: ignore[attr-defined]

    def _stop_dictate_anywhere(self) -> None:
        # A pending Resume in This Field must not fire on a stopped session.
        self._cancel_arming(say=False)
        controller = getattr(self, "_anywhere", None)
        if controller is not None:
            controller.shut_down()
        self._release_anywhere_owner()
