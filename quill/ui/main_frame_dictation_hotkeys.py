"""Locked Dictation hotkeys (Ctrl+F9 and family).

Wires the wx-free :class:`~quill.core.speech.dictation.DictationController` to the
live editor: it builds the insertion context from the caret, drives microphone
capture (:class:`~quill.core.speech.capture.MicRecorder`), runs Whisper on a
worker thread, secures audio to the recovery repository before transcribing, and
inserts the transcript as one undoable edit. Key activation is matched against
the *configured* keymap bindings (so every shortcut is remappable) in the
editor's key-down handlers rather than the accelerator table, so Escape can be
consumed only while a session is recording. (Hold-to-Dictate was removed: a held
key repeats and announces itself endlessly; Ctrl+F9 is the toggle.)

Default shortcuts (all remappable in Keyboard settings):

* ``tools.dictation_lock_toggle``    Ctrl+F9         start / finish Locked Dictation
* ``tools.dictation_pause``          Ctrl+Shift+F9   pause / resume Locked Dictation
* ``tools.dictation_status``         Alt+F9          speak the current state
* ``tools.dictation_emergency_stop`` Escape          stop now, keep the speech
* ``tools.dictation_cancel``         Shift+Escape    stop and discard

Escape / Shift+Escape are only consumed while a dictation session is active, so
they behave normally the rest of the time.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DICTATION_COMMANDS: tuple[tuple[str, str], ...] = (
    ("tools.dictation_lock_toggle", "Locked Dictation (start/finish)"),
    ("tools.dictation_pause", "Pause or Resume Dictation"),
    ("tools.dictation_status", "Dictation Status"),
    ("tools.dictation_emergency_stop", "Stop Dictation (keep speech)"),
    ("tools.dictation_cancel", "Cancel Dictation (discard)"),
)


class _LiveDictationServices:
    """``DictationServices`` implementation backed by the MainFrame mixin."""

    def __init__(self, frame: DictationHotkeysMixin) -> None:
        self._frame = frame
        self._recorder: Any = None
        self._repo: Any = None

    def _repository(self) -> Any:
        if self._repo is None:
            from quill.core.speech.dictation import DictationRecoveryRepository

            self._repo = DictationRecoveryRepository()
        return self._repo

    def start_capture(self, session: Any) -> None:
        from quill.core.speech.capture import MicRecorder, list_input_devices
        from quill.core.speech.service import load_input_device

        device = load_input_device()
        try:
            name = next(
                (n for i, n in list_input_devices() if i == device),
                "system default" if device < 0 else f"index {device}",
            )
        except Exception:  # noqa: BLE001 - logging must not block capture
            name = "?"
        logger.info("dictation: capture start, mic index=%s (%s)", device, name)
        recorder = MicRecorder()
        recorder.start(device)  # raises on failure -> MIC_UNAVAILABLE
        self._recorder = recorder

    def stop_capture(self, session: Any) -> Path | None:
        recorder = self._recorder
        self._recorder = None
        if recorder is None:
            logger.info("dictation: stop_capture with no active recorder")
            return None
        try:
            path = recorder.stop()
            try:
                size = Path(path).stat().st_size
            except OSError:
                size = -1
            logger.info("dictation: capture stopped, wav=%s size=%d bytes", path, size)
            if 0 <= size <= 44:  # WAV header only, no audio frames
                logger.warning("dictation: WAV has no audio — check mic selection / OS mic access")
            return path
        except Exception as exc:  # noqa: BLE001 - capture cleanup must not raise over the result
            logger.warning("dictation: stop_capture failed: %s", exc)
            return None

    def pause_capture(self, session: Any) -> None:
        if self._recorder is not None:
            self._recorder.pause()

    def resume_capture(self, session: Any) -> None:
        if self._recorder is not None:
            self._recorder.resume()

    def discard_capture(self, session: Any) -> None:
        recorder = self._recorder
        self._recorder = None
        if recorder is None:
            return
        try:
            path = recorder.stop()
            Path(path).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001 - discarding must never raise
            pass

    def save_audio(self, session: Any, wav_path: Path) -> None:
        try:
            self._repository().save_audio(session, wav_path)
        except Exception:  # noqa: BLE001 - recovery write must not wedge the machine
            pass

    def transcribe(self, session: Any) -> None:
        frame = self._frame
        controller = frame._live_dictation
        provider = frame._dictation_provider()
        installed = provider.list_installed_models()  # type: ignore[attr-defined]
        if not installed:
            controller.transcription_failed(session.session_id, "No speech model installed.")
            return
        model_id = frame._default_model_id(installed)
        audio_path = Path(session.audio_path) if session.audio_path else None
        session_id = session.session_id

        from quill.core.speech.provider import TranscriptionRequest

        request = TranscriptionRequest(source_path=audio_path, model_id=model_id)
        asize = audio_path.stat().st_size if (audio_path and audio_path.exists()) else -1
        logger.info("dictation: transcribe model=%s audio size=%d bytes", model_id, asize)

        import threading

        from quill.core.speech.provider import SpeechError
        from quill.ui.ai_transcribe_dialog import AIProgressDialog

        wx = frame._wx
        cancel = threading.Event()
        progress = AIProgressDialog(
            frame.frame,
            "Transcribing dictation",
            "Transcribing your dictation...",
            on_cancel=cancel.set,
            # Quiet mirroring so a minimized run isn't chatty; the controller's
            # state feedback announces the start and the inserted word count.
            status_fn=frame._set_status_quiet,
        )
        progress.show()

        def _on_progress(fraction: float, message: str) -> None:
            if cancel.is_set():
                raise SpeechError("Transcription cancelled.")
            percent = int(max(0.0, min(1.0, fraction)) * 100)
            progress.set_progress(percent, f"{message} {percent}%")

        def _run() -> None:
            try:
                result = provider.transcribe_file(request, _on_progress)  # type: ignore[attr-defined]
                text = (getattr(result, "full_text", "") or "").strip()
                logger.info("dictation: transcription ok, %d chars: %r", len(text), text[:120])
            except Exception as exc:  # noqa: BLE001 - report failure to the controller
                logger.warning("dictation: transcription failed: %s", exc)
                wx.CallAfter(progress.close)
                wx.CallAfter(controller.transcription_failed, session_id, str(exc))
                return
            wx.CallAfter(progress.close)
            wx.CallAfter(controller.transcription_succeeded, session_id, text)

        threading.Thread(  # GATE-40-OK: dictation transcription worker.
            target=_run, daemon=True
        ).start()

    def insert(self, session: Any, text: str) -> bool:
        frame = self._frame
        editor = getattr(frame, "editor", None)
        if editor is None or frame._document_is_read_only():
            return False  # defer to recovery/review
        full = editor.GetValue()
        ctx = session.context
        start, end = ctx.selection_start, ctx.selection_end
        if not (0 <= start <= end <= len(full)):
            caret = editor.GetInsertionPoint()
            start = end = caret
        frame._atomic_replace(start, end, text)
        frame.document.set_text(editor.GetValue())
        return True

    def feedback(self, event: Any, session: Any) -> None:
        self._frame._dictation_feedback(event, session)

    def now(self) -> float:
        return time.time()


class DictationHotkeysMixin:
    """Ctrl+F9 Locked Dictation and its controls, fully remappable."""

    # Relies on MainFrame helpers: _wx, frame, editor, document, settings,
    # commands, _binding_for, _parse_keybinding, _announce, _set_status,
    # _atomic_replace, _document_is_read_only, _effective_markup_kind,
    # _run_background_task, _speech_provider, _default_model_id,
    # _play_speech_sound.

    _live_dictation: Any = None
    _dictation_services: Any = None
    _dictation_timer: Any = None

    # -- lifecycle --------------------------------------------------------- #

    def _ensure_dictation_controller(self) -> Any:
        if self._live_dictation is None:
            from quill.core.speech.dictation import DictationController

            self._dictation_services = _LiveDictationServices(self)
            self._live_dictation = DictationController(
                self._dictation_services, self._dictation_config()
            )
        return self._live_dictation

    def _dictation_config(self) -> Any:
        """Build the controller policy from user Settings (PRD §10, §20)."""
        from quill.core.speech.dictation.controller import DictationConfig

        settings = self.settings
        return DictationConfig(
            max_locked_seconds=getattr(settings, "dictation_max_locked_seconds", 300.0),
            stop_on_focus_loss=getattr(settings, "dictation_stop_on_focus_loss", True),
            intelligent_spacing=getattr(settings, "dictation_intelligent_spacing", True),
            min_hold_seconds=getattr(settings, "dictation_min_hold_seconds", 0.0),
        )

    def _register_dictation_hotkey_commands(self) -> None:
        handlers = {
            "tools.dictation_lock_toggle": self.toggle_locked_dictation,
            "tools.dictation_pause": self.toggle_dictation_pause,
            "tools.dictation_status": self.speak_dictation_status,
            "tools.dictation_emergency_stop": self.stop_dictation_keep_speech,
            "tools.dictation_cancel": self.cancel_dictation_discard,
        }
        for command_id, title in _DICTATION_COMMANDS:
            self.commands.try_register(
                command_id,
                title,
                handlers[command_id],
                self._binding_for(command_id),
                feature_id="core.dictation",
            )
        # Deferred so the prompt lands after the startup announcements settle.
        try:
            self._wx.CallLater(2000, self.check_dictation_recovery_on_startup)
            self._wx.CallLater(4000, self.prewarm_dictation_model)  # warm model: fast first use
            self._wx.CallLater(4500, self.prewarm_kokoro_model)  # warm Kokoro for fast preview
        except Exception:  # noqa: BLE001 - the startup prompt is best-effort
            pass

    # -- command handlers (also callable from the command palette) --------- #

    def toggle_locked_dictation(self) -> None:
        controller = self._ensure_dictation_controller()
        if not controller.is_busy and not self._dictation_preflight():
            return
        controller.toggle_locked(self._dictation_context())
        self._start_dictation_watchdog()

    def toggle_dictation_pause(self) -> None:
        if self._live_dictation is not None:
            self._live_dictation.toggle_pause()

    def stop_dictation_keep_speech(self) -> None:
        if self._live_dictation is not None:
            self._live_dictation.emergency_stop()

    def cancel_dictation_discard(self) -> None:
        if self._live_dictation is not None:
            self._live_dictation.cancel_and_discard()

    def speak_dictation_status(self) -> None:
        from quill.core.speech.dictation import DictationState

        controller = self._live_dictation
        state = controller.state if controller is not None else DictationState.IDLE
        self._announce(_DICTATION_STATUS_TEXT.get(state, "Dictation is off."), force=True)

    def open_dictation_settings(self) -> None:
        """Edit the dictation knobs (the controller's DictationConfig) in a dialog."""
        from quill.core.settings import save_settings
        from quill.ui.dialog_contract import apply_modal_ids
        from quill.ui.dictation_settings_dialog import DictationSettingsDialog

        wx = self._wx
        panel = DictationSettingsDialog(wx, settings=self.settings)
        dialog = wx.Dialog(self.frame, title="Dictation Settings", style=wx.DEFAULT_DIALOG_STYLE)
        outer = panel.populate(dialog)
        buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        panel.finalize()
        apply_modal_ids(
            dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="&Save",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        try:
            if self._show_modal_dialog(dialog, "Dictation Settings") != wx.ID_OK:
                self._set_status("Dictation settings unchanged")
                return
            result = panel.result
        finally:
            dialog.Destroy()
        if result is None:
            return
        s = self.settings
        s.dictation_max_locked_seconds = result.max_locked_seconds
        s.dictation_min_hold_seconds = result.min_hold_seconds
        s.dictation_stop_on_focus_loss = result.stop_on_focus_loss
        s.dictation_intelligent_spacing = result.intelligent_spacing
        if result.reset_onboarding:
            s.dictation_onboarding_shown = False
        try:
            save_settings(s)
        except Exception:  # noqa: BLE001 - persistence is best-effort
            pass
        self._set_status("Dictation settings saved")

    def open_dictation_history(self) -> None:
        """Review recovered dictations: insert, copy, or discard each (PRD §22.4)."""
        from quill.core.speech.dictation.recovery import DictationRecoveryRepository
        from quill.ui.dictation_history_dialog import DictationHistoryDialog

        dialog = DictationHistoryDialog(
            self.frame,
            repo=DictationRecoveryRepository(),
            on_insert=self._insert_review_text,
            on_copy=self._copy_review_text,
        )
        dialog.show(self._show_modal_dialog)

    def _insert_review_text(self, text: str) -> None:
        editor = self.editor
        editor.WriteText(text)
        self.document.set_text(editor.GetValue())
        self._announce("Dictation transcript inserted. Press Control Z to undo.", force=True)

    def _copy_review_text(self, text: str) -> None:
        wx = self._wx
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
        self._set_status("Dictation transcript copied")

    def check_dictation_recovery_on_startup(self) -> None:
        """Point the user at the review window when dictations are pending (§22.4)."""
        from quill.core.speech.dictation.recovery import DictationRecoveryRepository

        try:
            pending = DictationRecoveryRepository().list_incomplete()
        except Exception:  # noqa: BLE001 - a broken store must not affect startup
            return
        if pending:
            self._announce(
                f"{len(pending)} dictation recording(s) await review. Open Tools, "
                "Speech, Hold and Locked Dictation, Dictation History.",
                force=True,
            )

    # -- preflight + context ---------------------------------------------- #

    def _dictation_preflight(self) -> bool:
        """Confirm capture support and an installed model before recording."""
        from quill.core.speech.capture import capture_available

        if getattr(self, "_safe_mode", False):
            self._announce("Dictation is disabled in Safe Mode.", force=True)
            return False
        if not capture_available():
            self._announce(
                "Dictation needs microphone support (the optional sounddevice package).",
                force=True,
            )
            return False
        provider = self._dictation_provider()
        try:
            if not provider.is_available():  # type: ignore[attr-defined]
                # The engine itself (e.g. the whisper.cpp binary) is missing, so
                # recording would capture audio that can never be transcribed.
                self._announce(
                    "The speech engine isn't set up on this computer, so dictation can't "
                    "run. Open Tools, Speech and Dictation to set it up.",
                    force=True,
                )
                return False
            if not provider.list_installed_models():  # type: ignore[attr-defined]
                self._announce(
                    "No speech model is installed. Open Tools, Speech and Dictation "
                    "to download one.",
                    force=True,
                )
                return False
        except Exception:  # noqa: BLE001 - a provider probe must not block the editor
            return False
        self._maybe_show_dictation_onboarding()
        return True

    def _maybe_show_dictation_onboarding(self) -> None:
        """Speak a one-time first-use hint for dictation, then remember it (§ onboarding)."""
        settings = self.settings
        if getattr(settings, "dictation_onboarding_shown", False):
            return
        self._announce(
            "Dictation ready. Press Control F9 to start a hands-free session, then "
            "Control F9 again or Escape to finish and insert; Shift Escape cancels. "
            "This hint won't show again.",
            force=True,
        )
        settings.dictation_onboarding_shown = True
        try:
            from quill.core.settings import save_settings

            save_settings(settings)
        except Exception:  # noqa: BLE001 - persistence is best-effort
            pass

    def _dictation_context(self) -> Any:
        from quill.core.speech.dictation import InsertionContext

        editor = self.editor
        text = editor.GetValue()
        start, end = editor.GetSelection()
        caret = editor.GetInsertionPoint()
        return InsertionContext(
            document_id=str(id(self.document)),
            document_path=str(self.document.path) if self.document.path else None,
            caret=caret,
            selection_start=start,
            selection_end=end,
            prefix_char=text[caret - 1] if caret > 0 else "",
            suffix_char=text[caret] if caret < len(text) else "",
            read_only=self._document_is_read_only(),
            content_mode=self._effective_markup_kind(),
        )

    # -- key routing (called from the editor key handlers) ----------------- #

    def _dictation_match(
        self, event: Any, binding: str | None, *, ignore_mods: bool = False
    ) -> bool:
        # Key routing for this optional feature must never break normal typing:
        # any failure resolving the binding (e.g. a minimal wx during tests, or a
        # malformed chord) means "no match" so the editor's own handling proceeds.
        try:
            parsed = self._parse_keybinding(binding)
            if parsed is None:
                return False
            flags, key_code = parsed
            if event.GetKeyCode() != key_code:
                return False
            if ignore_mods:
                return True
            wx = self._wx
            return (
                event.ControlDown() == bool(flags & wx.ACCEL_CTRL)
                and event.ShiftDown() == bool(flags & wx.ACCEL_SHIFT)
                and event.AltDown() == bool(flags & wx.ACCEL_ALT)
            )
        except Exception:  # noqa: BLE001 - never let dictation routing break a keystroke
            return False

    def _dictation_handle_key_down(self, event: Any) -> bool:
        """Return True if the key began/affected a dictation session (consumed)."""
        active = self._live_dictation is not None and self._live_dictation.is_busy
        # Escape / Shift+Escape only when a session is active, so normal Escape works.
        if active and self._dictation_match(event, self._binding_for("tools.dictation_cancel")):
            self.cancel_dictation_discard()
            return True
        if active and self._dictation_match(
            event, self._binding_for("tools.dictation_emergency_stop")
        ):
            self.stop_dictation_keep_speech()
            return True
        if self._dictation_match(event, self._binding_for("tools.dictation_lock_toggle")):
            self.toggle_locked_dictation()
            return True
        if self._dictation_match(event, self._binding_for("tools.dictation_pause")):
            self.toggle_dictation_pause()
            return True
        if self._dictation_match(event, self._binding_for("tools.dictation_status")):
            self.speak_dictation_status()
            return True
        return False

    def _dictation_handle_key_up(self, event: Any) -> bool:
        # Hold-to-Dictate was removed (a held key repeats and announces itself
        # endlessly); Locked Dictation (Ctrl+F9) is the toggle. Nothing to do on
        # key-up now.
        return False

    # -- watchdog timer (max duration, missing key-up, focus loss) --------- #

    def _start_dictation_watchdog(self) -> None:
        wx = self._wx
        if self._dictation_timer is None:
            self._dictation_timer = wx.Timer(self.frame)
            self.frame.Bind(wx.EVT_TIMER, self._on_dictation_tick, self._dictation_timer)
        if not self._dictation_timer.IsRunning():
            self._dictation_timer.Start(500)

    def _on_dictation_tick(self, _event: Any) -> None:
        controller = self._live_dictation
        if controller is None or not controller.is_busy:
            if self._dictation_timer is not None and self._dictation_timer.IsRunning():
                self._dictation_timer.Stop()
            return
        controller.tick()  # max-duration enforcement
        # Focus-loss policy: stop and preserve if QUILL is no longer foreground.
        try:
            if controller.is_recording and not self.frame.IsActive():
                controller.on_focus_lost()
        except Exception:  # noqa: BLE001 - foreground probe is best-effort
            pass
        # Missing key-up recovery: if the physical hold key is no longer down.
        from quill.core.speech.dictation import DictationState

        if controller.state is DictationState.HOLD_RECORDING:
            parsed = self._parse_keybinding(self._binding_for("tools.dictation_hold"))
            if parsed is not None:
                try:
                    if not self._wx.GetKeyState(parsed[1]):
                        controller.on_missing_keyup()
                except Exception:  # noqa: BLE001 - key-state probe is best-effort
                    pass

    # -- feedback (earcons + announcements) -------------------------------- #

    def _dictation_feedback(self, event: Any, session: Any) -> None:
        from quill.core.speech.dictation.controller import FeedbackEvent

        earcon, message, status = _DICTATION_FEEDBACK.get(event, ("", "", ""))
        if event is FeedbackEvent.INSERTED and session is not None:
            words = len((session.transcript or "").split())
            message = f"Dictation inserted, {words} words. Press Control Z to undo."
            status = f"Dictation inserted, {words} words"
        if earcon:
            self._play_speech_sound(earcon)
        if status:
            self._set_status(status)
        if message:
            self._announce(message, force=True)


# State -> Alt+F9 status announcement (PRD §18.4).
def _build_status_text() -> dict:
    from quill.core.speech.dictation import DictationState

    return {
        DictationState.IDLE: "Dictation is off.",
        DictationState.HOLD_RECORDING: "Hold-to-dictate is recording.",
        DictationState.LOCKED_RECORDING: "Locked dictation is recording.",
        DictationState.PAUSED: "Dictation is paused.",
        DictationState.TRANSCRIBING: "Dictation is being transcribed.",
        DictationState.REVIEW_REQUIRED: "A transcript is waiting for review.",
    }


def _build_feedback() -> dict:
    from quill.core.speech.dictation.controller import FeedbackEvent

    return {
        FeedbackEvent.HOLD_START: ("transcription_started", "", "Dictating; release to insert"),
        FeedbackEvent.LOCKED_START: (
            "dictation_locked_on",
            "Locked dictation on. Press the lock key again to finish. Escape stops.",
            "Locked dictation - press the lock key to finish; Escape to stop",
        ),
        FeedbackEvent.HOLD_STOP: ("transcription_stopped", "", ""),
        FeedbackEvent.LOCKED_STOP: ("dictation_locked_off", "", ""),
        FeedbackEvent.PAUSED: ("", "Dictation paused.", "Locked dictation paused"),
        FeedbackEvent.RESUMED: ("transcription_started", "Dictation resumed.", ""),
        FeedbackEvent.TRANSCRIBING: (
            "",
            "Transcribing, please wait. The first one loads the model.",
            "Transcribing...",
        ),
        FeedbackEvent.INSERTED: ("transcription_word_inserted", "Dictation inserted.", ""),
        FeedbackEvent.NO_SPEECH: ("", "No speech was recognized.", "No speech recognized"),
        FeedbackEvent.REVIEW: (
            "",
            "Dictation saved for review; it could not be inserted here.",
            "Dictation saved for review",
        ),
        FeedbackEvent.CANCELLED: ("", "Dictation cancelled.", "Dictation cancelled"),
        FeedbackEvent.MAX_TIME: (
            "transcription_stopped",
            "Maximum dictation time reached. Recording stopped and is being transcribed.",
            "",
        ),
        FeedbackEvent.FOCUS_LOST: (
            "transcription_stopped",
            "Dictation stopped because QUILL lost focus.",
            "",
        ),
        FeedbackEvent.MISSING_KEYUP: ("", "", "Dictation stopped"),
        FeedbackEvent.MIC_UNAVAILABLE: (
            "",
            "The microphone could not be opened. Check your input device and "
            "Windows microphone permissions.",
            "Microphone unavailable",
        ),
        FeedbackEvent.BUSY: ("", "The previous dictation is still being transcribed.", ""),
        FeedbackEvent.ERROR: ("", "Dictation failed; the recording was kept for recovery.", ""),
    }


_DICTATION_STATUS_TEXT = _build_status_text()
_DICTATION_FEEDBACK = _build_feedback()
