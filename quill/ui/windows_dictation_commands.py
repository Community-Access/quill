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

**One controller in the whole app.** There is one microphone. It writes into
whichever document it was last pointed at: the one the key was pressed in, or
the one in front when the wake phrase was heard. The key that starts dictation
anywhere stops it everywhere, so "press it again to stop" is true whichever
window you pressed it in.

**The wake phrase listens only while this program is the active window.** When
another program comes to the front, dictation stops and the microphone closes;
when this one comes back, listening for the wake phrase resumes. Listening in
the background was considered and left out: waking would have to pull the
window forward to write anywhere, and a program that takes focus from what
somebody is doing because it heard its name is the kind of surprise a screen
reader user pays for most.
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

#: How much text in front of the caret the spacing rules look at. A sentence is
#: plenty; the whole document would be a copy of it across the wx boundary for
#: every phrase.
_CONTEXT_CHARS = 80

#: How long after a phrase is written its words are read back -- long enough
#: for the editor's own reaction to the edit to have been said first.
_READ_BACK_DELAY_MS = 250

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


def _alive(window: Any) -> bool:
    """Whether *window* still exists. A destroyed wx object is falsy."""
    try:
        being_deleted = getattr(window, "IsBeingDeleted", None)
        return bool(window) and not (callable(being_deleted) and being_deleted())
    except Exception:  # noqa: BLE001 - a dead wx object raises on any call
        return False


class _EditorDocument:
    """The document port: one text control, reached through its host."""

    def __init__(self, host: Any, control: Any) -> None:
        self._host = host
        self._control = control

    def unavailable_reason(self, *, writing: bool) -> str:
        control = self._control
        if not _alive(control) or control is not self._host._dictation_control():
            return "Dictation stopped: the document it was writing into has closed or changed."
        if not control.IsEditable():
            return "This document is read-only, so dictation has nowhere to write."
        if writing and wx.Window.FindFocus() is not control:
            return "Dictation stopped because the document no longer has the focus."
        return ""

    def context(self) -> tuple[str, str]:
        control = self._control
        start, end = control.GetSelection()
        before = control.GetRange(max(0, start - _CONTEXT_CHARS), start)
        after = control.GetRange(end, min(end + 2, control.GetLastPosition()))
        return before, after

    def selection(self) -> tuple[int, int]:
        start, end = self._control.GetSelection()
        return int(start), int(end)

    def select(self, start: int, end: int) -> None:
        self._control.SetSelection(start, end)

    def insert(self, text: str) -> tuple[int, int]:
        control = self._control
        start, end = control.GetSelection()
        if end > start:
            # Removed first and written second, rather than trusting WriteText to
            # replace a selection: the rich edit control does and the Scintilla
            # one QUILL can also use does not.
            control.Remove(start, end)
            control.SetInsertionPoint(start)
        control.WriteText(text)
        self._host._dictation_after_edit()
        return start, control.GetInsertionPoint()

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        control = self._control
        control.Remove(start, end)
        control.SetInsertionPoint(start)
        control.WriteText(text)
        self._host._dictation_after_edit()
        return start, control.GetInsertionPoint()

    def text_between(self, start: int, end: int) -> str:
        return str(self._control.GetRange(max(0, start), end))

    def remove(self, start: int, end: int) -> None:
        self._control.Remove(start, end)
        self._control.SetInsertionPoint(start)
        self._host._dictation_after_edit()

    def line_bounds(self) -> tuple[int, int]:
        control = self._control
        caret = control.GetInsertionPoint()
        last = control.GetLastPosition()
        before = control.GetRange(max(0, caret - 4000), caret)
        after = control.GetRange(caret, min(last, caret + 4000))
        start = caret - (len(before) - (before.rfind("\n") + 1))
        newline = after.find("\n")
        end = caret + (newline if newline >= 0 else len(after))
        return start, end

    def last_position(self) -> int:
        return int(self._control.GetLastPosition())

    def undo(self) -> bool:
        control = self._control
        if not control.CanUndo():
            return False
        control.Undo()
        self._host._dictation_after_edit()
        return True


class _HostFeedback:
    """The feedback port: the host's own cues, speech and status line."""

    def __init__(self, host: Any) -> None:
        self._host = host
        self._pending: list[str] = []
        self._timer: Any = None

    def has_cue(self, moment: Moment) -> bool:
        try:
            return bool(self._host._dictation_has_cue(DICTATION_CUES[moment]))
        except Exception:  # noqa: BLE001 - no sound stack is an answer
            return False

    def cue(self, moment: Moment) -> None:
        try:
            self._host._dictation_cue(DICTATION_CUES[moment])
        except Exception:  # noqa: BLE001 - a cue must never break dictation
            pass

    def say(self, text: str) -> None:
        try:
            self._host._dictation_say(text)
        except Exception:  # noqa: BLE001 - a closing window cannot speak; never crash
            pass

    def read_back(self, text: str) -> None:
        """Say what a phrase wrote, a moment after it was written.

        Reported unreliable when it was spoken at once (2026-09-25). Inserting
        text into a focused edit control is itself something a screen reader
        may react to -- the caret moved, the line changed, the editor's own
        caret cues fire off the same text event -- and a sentence handed over in
        the same instant raced all of that, so sometimes it was heard and
        sometimes it was cut off by whatever the reader said next. Speaking it
        after the edit has settled lets it arrive last and interrupt the rest.

        Phrases that land while one is still waiting are joined rather than
        dropped, so quick speech is read back whole, once.
        """
        self._pending.append(text)
        if self._timer is not None:
            return
        try:
            self._timer = wx.CallLater(_READ_BACK_DELAY_MS, self._speak_pending)
        except Exception:  # noqa: BLE001 - no event loop (tests): say it now
            self._speak_pending()

    def _speak_pending(self) -> None:
        self._timer = None
        text, self._pending = " ".join(self._pending).strip(), []
        if text:
            self.say(text)

    def show(self, text: str) -> None:
        try:
            self._host._dictation_status(text)
        except Exception:  # noqa: BLE001 - the status line is a record, not a need
            pass

    def state_changed(self, state: DictationState) -> None:
        from quill.ui.windows_dictation_silence import note_activity

        note_activity(state, lambda: _controller)
        self._host._dictation_state_changed(state)

    def show_commands(self) -> None:
        # After the phrase has been handled, not in the middle of it: the list is
        # a modal window, and a modal window opened inside a recogniser callback
        # would hold that callback open until it closed.
        try:
            wx.CallAfter(self._host._dictation_show_commands)
        except Exception:  # noqa: BLE001 - no event loop (tests)
            self._host._dictation_show_commands()


class WindowsDictationMixin:
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
        """Start dictation here, or stop it wherever it is running."""
        preferences = self._dictation_preferences()
        if preferences.engine == "voice_typing":
            self._dictation_voice_typing()
            return
        controller = self._dictation_controller()
        if not controller.active:
            self._dictation_target(self)
        controller.toggle()

    def cmd_dictation_settings(self) -> None:
        """Choose the engine, the microphone, the wake phrase and what is heard."""
        from quill.ui.windows_dictation_dialog import (
            EDIT_WORDS,
            SHOW_COMMANDS,
            WindowsDictationDialog,
        )

        settings = self._dictation_settings()
        dialog = WindowsDictationDialog(self._dictation_parent(), settings, self._dictation_say)
        try:
            answer = self._dictation_run_modal(dialog, "Dictation Settings")
            if answer in (wx.ID_OK, EDIT_WORDS):
                dialog.apply(settings)
        finally:
            dialog.Destroy()
        if answer == SHOW_COMMANDS:
            self._dictation_show_commands()
            return
        if answer not in (wx.ID_OK, EDIT_WORDS):
            return
        self._dictation_save_settings()
        self._dictation_status("Dictation settings saved.")
        self._dictation_rearm()
        if answer == EDIT_WORDS:
            self._dictation_edit_words()

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
            DictationState.RECOGNIZING: "Dictation: hearing you",
            DictationState.PROCESSING: "Dictation: writing",
        }.get(state, "")

    def _dictation_install(self) -> None:
        """Follow the top-level window's activation, once per window, and start
        listening for the wake phrase if it is switched on."""
        top = self._dictation_top_window()
        if id(top) not in _watched_tops:
            _watched_tops.add(id(top))
            top.Bind(wx.EVT_ACTIVATE, self._on_dictation_top_activate)
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
        return DictationPreferences.from_settings(self._dictation_settings(), rewrite=rewrite)

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

    def _dictation_target(self, host: Any) -> None:
        """Point the controller at *host*'s document."""
        global _host
        controller = self._dictation_controller()
        control = host._dictation_control()
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
        )
        dialog = DictationCommandsDialog(self._dictation_parent(), body)
        try:
            self._dictation_run_modal(dialog, "Dictation Commands")
        finally:
            dialog.Destroy()

    def _dictation_edit_words(self) -> None:
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
        )
    from quill.core.windows_dictation.local_recognizer import LocalDictationRecognizer

    return LocalDictationRecognizer(
        controller, preferences.engine, post=wx.CallAfter, pause_seconds=preferences.pause_seconds
    )
