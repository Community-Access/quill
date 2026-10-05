"""Dictation's commands, shared by QUILL and QUILL Lite.

Two commands -- start or stop dictation, and Dictation Settings -- and the wx
half of the feature: the adapter that lets the wx-free
:class:`~quill.core.windows_dictation.controller.DictationController` write into
a text control, play a cue, say a sentence, and listen for the wake phrase.

**Both editors mix this in.** What differs between them is a handful of hooks,
each with QUILL Lite's answer as the default and QUILL's in
:mod:`quill.ui.main_frame_windows_dictation`: which control the document is in,
where the settings live, how a sentence is spoken and a cue played, how a modal
dialog is shown, where the user's own words are kept. Everything about what the
commands *do* is here once, so a fix to one editor's dictation is a fix to both
-- and if the QUILL adapter ever grows a command of its own, the capability has
forked.

**One controller in the whole app**, because there is one microphone. It writes
into the document it was last pointed at (where the key was pressed, or the one
in front when the wake phrase was heard), and the key that starts dictation
anywhere stops it everywhere.

**The wake phrase listens only while this program is the active window.** When
another program comes to the front, dictation stops and the microphone closes;
when this one comes back, listening for the wake phrase resumes. Listening in
the background was left out: waking would have to pull the window forward, and a
program that takes focus because it heard its name is the kind of surprise a
screen reader user pays for most.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.core.sound_events import SoundEvent
from quill.core.windows_dictation.controller import (
    DictationController,
    DictationPreferences,
    DictationState,
    Moment,
)
from quill.ui.windows_dictation_hold import DictationHoldMixin
from quill.ui.windows_dictation_ports import EditorDocument as _EditorDocument
from quill.ui.windows_dictation_ports import HostFeedback as _HostFeedback
from quill.ui.windows_dictation_tools import DictationToolsMixin

__all__ = [
    "DICTATION_CUES",
    "WindowsDictationMixin",
    "dictation_active",
    "dictation_standing_by",
]

#: The earcon for each moment. QUILL Lite names the same four in its own module,
#: because the sound audit credits an app only with the cues its own files post.
DICTATION_CUES: dict[Moment, str] = {
    Moment.ON: SoundEvent.WINDOWS_DICTATION_ON,
    Moment.PHRASE: SoundEvent.WINDOWS_DICTATION_PHRASE,
    Moment.OFF: SoundEvent.WINDOWS_DICTATION_OFF,
    Moment.ERROR: SoundEvent.WINDOWS_DICTATION_ERROR,
}

#: The one controller, the host window it writes into, and the top-level
#: windows whose activation it follows.
_controller: DictationController | None = None
_host: Any = None
_watched_tops: set[int] = set()


def dictation_active(host: Any = None) -> bool:
    """Whether dictation is writing -- anywhere, or into *host*'s document."""
    if _controller is None or not _controller.active:
        return False
    return host is None or host is _host


def dictation_standing_by() -> bool:
    """Whether the microphone is open for the wake phrase only."""
    return _controller is not None and _controller.standing_by


class WindowsDictationMixin(DictationToolsMixin, DictationHoldMixin):
    """The dictation commands. Mixed into both editors' document windows."""

    # ------------------------------------------------------------------ #
    # Hooks -- QUILL Lite's answers; QUILL overrides them
    # ------------------------------------------------------------------ #

    def _dictation_control(self):  # noqa: ANN201 - the document's text control
        return self.control

    def _dictation_parent(self):  # noqa: ANN201 - wx.Window
        return self

    def _dictation_top_window(self):  # noqa: ANN201 - the window whose activation matters
        return getattr(getattr(self, "app", None), "shell", None) or self

    def _dictation_current_host(self) -> Any:
        """The document window in front now -- where a wake phrase should write."""
        shell = getattr(getattr(self, "app", None), "shell", None)
        active = shell.GetActiveChild() if shell is not None else None
        return active if isinstance(active, WindowsDictationMixin) else self

    def _dictation_settings(self) -> Any:
        return self.app.settings

    def _dictation_enabled(self) -> bool:
        """Whether dictation exists in this copy -- QUILL Lite's Customize
        Features area. Off means no wake phrase either: a switched-off feature
        that still opened the microphone would be the feature not being off."""
        enabled = getattr(getattr(self, "app", None), "feature_enabled", None)
        return bool(enabled("dictation")) if callable(enabled) else True

    def _dictation_save_settings(self) -> None:
        self.app.save_settings()

    def _dictation_profile_path(self) -> Path:
        """The user's own words and phrases (``dictation.md``)."""
        return Path(self.app.data_dir) / "dictation.md"

    def _dictation_open_file(self, path: Path) -> None:
        """Open *path* for editing, in this editor."""
        self.app.open_path(path)

    def _dictation_say(self, text: str) -> None:
        self._announce(text)

    def _dictation_status(self, text: str) -> None:
        self._set_status_message(text)

    def _dictation_cue(self, event: str) -> None:
        self._cue(event)

    def _dictation_has_cue(self, event: str) -> bool:
        """Whether the loaded pack can play *event* -- QUILL Lite's own seam
        when the window has one, the sound manager's answer otherwise."""
        has_sound = getattr(self, "_has_sound_for", None)
        if callable(has_sound):
            return bool(has_sound(event))
        from quill.ui.sound_manager import has_sound_for

        return bool(has_sound_for(event))

    def _dictation_run_modal(self, dialog: Any, label: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, label))

    def _dictation_after_edit(self) -> None:
        """Anything the host keeps in step with the control after an edit."""

    def _dictation_state_changed(self, state: DictationState) -> None:
        """Refresh whatever mirrors the state -- QUILL Lite's menu check mark and
        the status bar's Dictation cell."""
        del state
        for name in ("_sync_check_items", "_touch_status"):
            refresh = getattr(self, name, None)
            if callable(refresh):
                try:
                    refresh()
                except Exception:  # noqa: BLE001 - a mirror is never worth a session
                    pass

    # ------------------------------------------------------------------ #
    # Commands
    # ------------------------------------------------------------------ #

    def cmd_toggle_dictation(self) -> None:
        """Start dictation here, or stop it wherever it is running. Held down,
        it talks until the key comes up (windows_dictation_hold.py)."""
        if self._dictation_repeat():
            return  # Windows repeating the held key: the press is being followed
        preferences = self._dictation_preferences()
        if preferences.engine == "voice_typing":
            self._dictation_voice_typing()
            return
        controller = self._dictation_controller()
        if controller.active and _host is not self:
            # One session at a time (dict.md 2.8): the microphone follows the
            # key to this document instead of stopping, and says so.
            self._dictation_target(self)
            self._dictation_say(f"Dictation moved to {self._dictation_document_name()}.")
            return
        if not controller.active:
            self._dictation_target(self)
        self._dictation_press(controller)

    def cmd_dictation_settings(self) -> None:
        """Choose the engine, the microphone, the wake phrase and what is heard."""
        from quill.ui.windows_dictation_dialog import (
            EDIT_INSTRUCTIONS,
            EDIT_OPENAI_KEY,
            EDIT_WORDS,
            SHOW_COMMANDS,
            WindowsDictationDialog,
        )

        settings = self._dictation_settings()
        dialog = WindowsDictationDialog(self._dictation_parent(), settings, self._dictation_say)
        saving = (wx.ID_OK, EDIT_WORDS, EDIT_INSTRUCTIONS, EDIT_OPENAI_KEY)
        try:
            answer = self._dictation_run_modal(dialog, "Dictation Settings")
            if answer in saving:
                dialog.apply(settings)
        finally:
            dialog.Destroy()
        if answer == SHOW_COMMANDS:
            self._dictation_show_commands()
            return
        if answer not in saving:
            return
        self._dictation_save_settings()
        self._dictation_status("Dictation settings saved.")
        self._dictation_rearm()
        if answer == EDIT_WORDS:
            self.cmd_dictation_words()
        elif answer == EDIT_INSTRUCTIONS:
            self._dictation_edit_instructions()
        elif answer == EDIT_OPENAI_KEY:
            self._dictation_add_openai_key()

    def _dictation_add_openai_key(self) -> None:
        """The shared Use My Own AI Key window, from Dictation Settings.

        Both editors have it (Alt+F2); dictation adds no second key store.
        """
        own_key = getattr(self, "cmd_ai_own_key", None)
        if callable(own_key):
            own_key()
        else:
            self._dictation_say("Use My Own AI Key is not available here.")

    # ------------------------------------------------------------------ #
    # Plumbing
    # ------------------------------------------------------------------ #

    def dictation_active(self) -> bool:
        """Whether this window's document is being dictated into."""
        return dictation_active(self)

    def dictation_state_text(self) -> str:
        """The status bar's Dictation cell: empty while dictation is off."""
        if _controller is None:
            return ""
        state = _controller.state
        if state is DictationState.STANDBY:
            return "Dictation: waiting for wake phrase"
        if not _controller.active or _host is not self:
            return ""
        if _controller.spelling:
            return "Dictation: spelling"
        return {
            DictationState.STARTING: "Dictation: starting",
            DictationState.LISTENING: "Dictation: listening",
            DictationState.RECOGNIZING: (
                f"Dictation: hearing: {self._dictation_preview_text}"
                if getattr(self, "_dictation_preview_text", "")
                else "Dictation: hearing you"
            ),
            DictationState.PROCESSING: "Dictation: writing",
            DictationState.PAUSED: "Dictation: paused, microphone lost",
        }.get(state, "")

    def _dictation_install(self) -> None:
        """Follow the top-level window's activation, once per window, and start
        listening for the wake phrase if it is switched on."""
        top = self._dictation_top_window()
        if id(top) not in _watched_tops:
            _watched_tops.add(id(top))
            top.Bind(wx.EVT_ACTIVATE, self._on_dictation_top_activate)
        # Escape throws away the phrase being heard (dict.md 2.2). A char hook,
        # so it runs before the control sees the key, and only consumes it when
        # there was something to cancel.
        self._dictation_parent().Bind(wx.EVT_CHAR_HOOK, self._dictation_cancel_key)
        try:
            wx.CallAfter(self._dictation_rearm)
        except Exception:  # noqa: BLE001 - no event loop (tests)
            pass

    def _on_dictation_top_activate(self, event: Any) -> None:
        event.Skip()
        if _controller is None and not event.GetActive():
            return
        if event.GetActive():
            self._dictation_current_host()._dictation_rearm()
            return
        controller = _controller
        if controller is None:
            return
        if controller.active:
            controller.stop("Dictation off, because QUILL is no longer the window in front.")
        controller.disarm()

    def _dictation_feature_changed(self) -> None:
        """Customize Features changed: close everything if dictation went away."""
        if self._dictation_enabled():
            self._dictation_rearm()
        elif _controller is not None:
            _controller.shut_down()

    def _dictation_rearm(self) -> None:
        """Listen for the wake phrase, or stop listening, as the settings say."""
        preferences = self._dictation_preferences()
        if (
            not preferences.wake_enabled
            or preferences.engine == "voice_typing"
            or not self._dictation_enabled()
        ):
            if _controller is not None:
                _controller.disarm()
            return
        top = self._dictation_top_window()
        try:
            if not top.IsActive():
                return
        except Exception:  # noqa: BLE001 - a window mid-construction: try later
            return
        controller = self._dictation_controller()
        if controller.active or controller.standing_by:
            return
        self._dictation_target(self._dictation_current_host())
        controller.arm()

    def _dictation_preferences(self) -> DictationPreferences:
        from quill.core.windows_dictation.profile import rewriter

        try:
            rewrite = rewriter(self._dictation_profile_path())
        except Exception:  # noqa: BLE001 - a broken profile never stops dictation
            rewrite = None
        # Talking to AI (dict.md 6): the AI Conversation window's message box
        # carries its own profile, so it switches by itself while it is the target.
        profile = str(getattr(self._dictation_targeted(), "_quill_dictation_profile", "writing"))
        preferences = DictationPreferences.from_settings(
            self._dictation_settings(), rewrite=rewrite, profile=profile
        )
        if preferences.engine != "openai":
            return preferences
        from dataclasses import replace

        from quill.core.windows_dictation.profile import load

        try:
            words = tuple(load(self._dictation_profile_path()).vocabulary)
        except Exception:  # noqa: BLE001 - no words is a fine answer
            words = ()
        return replace(preferences, keywords=words)

    def _dictation_controller(self) -> DictationController:
        global _controller
        if _controller is None:
            _controller = DictationController(
                recognizer=_make_recognizer,
                document=_EditorDocument(self, self._dictation_control()),
                feedback=_HostFeedback(self),
                preferences=lambda: (_host or self)._dictation_preferences(),
            )
            _controller.on_wake = lambda: self._dictation_target(
                (_host or self)._dictation_current_host()
            )
        return _controller

    def _dictation_target(self, host: Any, control: Any = None) -> None:
        """Point the controller at *host*'s document, or at one of its fields."""
        global _host
        controller = self._dictation_controller()
        control = control if control is not None else host._dictation_control()
        # A field is remembered as the target only while it is one; the
        # document is the default and needs no record.
        host._dictation_targeted_control = None if control is host._dictation_control() else control
        controller.retarget(_EditorDocument(host, control), _HostFeedback(host))
        if host is not _host:
            _host = host
        bound = getattr(control, "_quill_dictation_destroy_bound", False)
        if not bound:
            # The control going away -- the window closed, or plain and rich
            # swapped it for another -- stops dictation at once, rather than at
            # the next phrase: the microphone must not write to nothing.
            control.Bind(wx.EVT_WINDOW_DESTROY, host._on_dictation_control_destroyed)
            try:
                control._quill_dictation_destroy_bound = True
            except Exception:  # noqa: BLE001 - a control that refuses attributes
                pass

    def _on_dictation_control_destroyed(self, event: Any) -> None:
        event.Skip()
        if event.GetEventObject() is not event.GetWindow():
            return  # a child of the control, not the control
        if _controller is not None and _host is self:
            if _controller.active:
                _controller.stop()
            elif _controller.standing_by:
                _controller.disarm()

    def _dictation_voice_typing(self) -> None:
        """Hand over to Windows' own voice typing (Windows+H)."""
        try:
            from quill.platform.windows.dictation import launch_windows_dictation

            launch_windows_dictation()
        except Exception as error:  # noqa: BLE001 - reported, never raised
            self._dictation_say(f"Windows voice typing could not be opened: {error}")
            return
        self._dictation_status("Windows voice typing opened. Windows+H closes it.")

    def _dictation_show_commands(self) -> None:
        from quill.core.speech.dictation_profile import DictationProfile
        from quill.core.windows_dictation.profile import load
        from quill.core.windows_dictation.reference import commands_reference
        from quill.ui.windows_dictation_dialog import DictationCommandsDialog

        preferences = self._dictation_preferences()
        try:
            profile = load(self._dictation_profile_path())
        except Exception:  # noqa: BLE001 - the built-in list is still worth showing
            profile = DictationProfile()
        body = commands_reference(
            dash=preferences.dash,
            wake_phrase=preferences.wake_phrase if preferences.wake_enabled else "",
            stop_phrase=preferences.stop_phrase,
            own_phrases=profile.replacements,
            language=preferences.speech_language,
        )
        dialog = DictationCommandsDialog(self._dictation_parent(), body)
        try:
            self._dictation_run_modal(dialog, "Dictation Commands")
        finally:
            dialog.Destroy()

    def _dictation_edit_instructions(self) -> None:
        """Open My Dictation Instructions, the file Tidy Dictated Text follows."""
        from quill.core.windows_dictation.instructions import (
            ensure_instructions,
            instructions_path,
        )

        try:
            path = ensure_instructions(instructions_path(self._dictation_profile_path()))
        except OSError as error:
            self._dictation_say(f"Your dictation instructions could not be opened: {error}")
            return
        self._dictation_open_file(path)

    def _dictation_edit_words(self) -> None:
        """Open ``dictation.md`` itself, for whoever prefers a file (the words
        window's Open the File button). The window is the front door now."""
        from quill.core.windows_dictation.profile import ensure_file

        try:
            path = ensure_file(self._dictation_profile_path())
        except OSError as error:
            self._dictation_say(f"Your dictation words could not be opened: {error}")
            return
        self._dictation_open_file(path)


def _make_recognizer(controller: DictationController, preferences: DictationPreferences) -> Any:
    """The recogniser the settings chose. Windows speech runs on this thread and
    needs no marshalling; the built-in engines run on a worker and hand every
    result back through ``wx.CallAfter``."""
    if preferences.engine == "windows":
        from quill.platform.windows.sapi_dictation import SapiDictationRecognizer

        return SapiDictationRecognizer(
            controller,
            language=preferences.language,
            pause_ms=int(preferences.pause_seconds * 1000),
            speech_language=preferences.speech_language,
        )
    if preferences.engine == "openai":
        from quill.core.windows_dictation.openai_recognizer import OpenAIDictationRecognizer

        return OpenAIDictationRecognizer(
            controller,
            post=wx.CallAfter,
            model=preferences.openai_model,
            consent=preferences.openai_consent,
            keywords=preferences.keywords,
            pause_seconds=preferences.pause_seconds,
            language=preferences.speech_language,
        )
    from quill.core.windows_dictation.local_recognizer import LocalDictationRecognizer

    return LocalDictationRecognizer(
        controller,
        preferences.engine,
        post=wx.CallAfter,
        pause_seconds=preferences.pause_seconds,
        language=preferences.speech_language,
    )
