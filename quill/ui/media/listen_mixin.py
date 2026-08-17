"""Hands-free voice-listening for the Media Player frame (PRD Section 18).

A mixin the player frame inherits so the microphone toggle, background
transcription, audiobook ducking, per-event announcements, and the check-menu
state live outside the frame body (keeping it under the size budget). All the
engine-free logic -- resolving a small Whisper model, parsing a transcript, and
the announce/earcon styling -- is in :mod:`quill.ui.media.voice_capture`; this
mixin is only the wx wiring around it.

The frame supplies ``_player`` (a PlayerPanel), ``_announce`` (from AppShellFrame),
``frame`` (the wx.Frame), and the ``_listen_*`` state initialised in its
``__init__``. Every state transition is announced with a distinct earcon and
interrupt/queue policy, per the Desktop Accessibility guidance.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import wx

# The lead-in delays actual capture until after the spoken "Listening" cue, so a
# screen reader's own announcement is not recorded. The max window is a watchdog
# so a forgotten-open mic can never persist silently.
_CAPTURE_LEAD_MS = 450
_LISTEN_MAX_MS = 20_000
_DUCK_LEVEL = 20


class MediaListenMixin:
    """Push-to-talk voice listening, mixed into the media-player frame."""

    # These attributes are initialised by the frame's __init__.
    _voice_services: Any
    _listening: bool
    _listen_timer: Any
    _listen_menu_item: Any
    _listen_last_toggle: float

    def _on_listen_command(self, _event: Any) -> None:
        """Toggle push-to-talk listening (first press starts, second stops).

        A screen-reader passthrough can double-send the accelerator, so a second
        toggle within 250 ms is ignored (Desktop A11y guidance).
        """
        now = time.monotonic()
        if now - self._listen_last_toggle < 0.25:
            self._sync_listen_check()
            return
        self._listen_last_toggle = now
        if self._listening:
            self._stop_listening()
        else:
            self._start_listening()

    def _start_listening(self) -> None:
        from quill.ui.media.voice_capture import VoiceCommandEvent, build_media_voice_services

        if self._voice_services is None:
            self._voice_services = build_media_voice_services()
        if self._voice_services is None or not self._voice_services.input_available():
            self._voice_event(
                VoiceCommandEvent.MIC_UNAVAILABLE,
                "Voice listening needs a microphone and an installed speech model. "
                "Open QUILL and download a small Whisper model first.",
            )
            return
        # Duck the book before the cue so the earcon is clearly audible and less
        # narration bleeds into the microphone; capture itself starts after the
        # spoken cue so the reader's own "Listening" is not recorded.
        self._player.duck(_DUCK_LEVEL)
        self._listening = True
        self._sync_listen_check()
        self._voice_event(
            VoiceCommandEvent.LISTENING_START,
            "Listening. Press Control Shift L again to stop.",
        )
        wx.CallLater(_CAPTURE_LEAD_MS, self._begin_capture)

    def _begin_capture(self) -> None:
        from quill.ui.media.voice_capture import VoiceCommandEvent

        if not self._listening:  # stopped during the lead-in
            return
        try:
            self._voice_services.start_recording()
        except Exception as error:  # noqa: BLE001 - surfaced as a clean announcement
            self._listening = False
            self._sync_listen_check()
            self._player.unduck()
            self._voice_event(
                VoiceCommandEvent.MIC_UNAVAILABLE, f"Could not start the microphone. {error}"
            )
            return
        if self._listen_timer is None:
            self._listen_timer = wx.Timer(self.frame)
            self.frame.Bind(wx.EVT_TIMER, lambda _e: self._on_listen_timeout(), self._listen_timer)
        self._listen_timer.StartOnce(_LISTEN_MAX_MS)

    def _stop_listening(self) -> None:
        from quill.ui.media.voice_capture import VoiceCommandEvent

        if not self._listening:
            return
        if self._listen_timer is not None:
            self._listen_timer.Stop()
        self._listening = False
        self._sync_listen_check()
        self._voice_event(VoiceCommandEvent.TRANSCRIBING, "Working.")
        services = self._voice_services

        def _work() -> None:
            # GATE-40-OK: voice-command transcription worker; UI via wx.CallAfter.
            try:
                transcript = services.stop_and_transcribe()
            except Exception as error:  # noqa: BLE001
                wx.CallAfter(self._finish_listen, None, str(error))
                return
            wx.CallAfter(self._finish_listen, transcript, "")

        threading.Thread(  # GATE-40-OK: one-shot capture+transcribe; CallAfter result;
            # _on_listen_timeout is the watchdog.
            target=_work,
            daemon=True,
        ).start()

    def _on_listen_timeout(self) -> None:
        if self._listening:
            self._stop_listening()

    def _finish_listen(self, transcript: str | None, error: str) -> None:
        from quill.ui.media.voice_capture import VoiceCommandEvent, dispatch_transcript

        self._player.unduck()
        if error:
            self._voice_event(VoiceCommandEvent.ERROR, "Voice command failed.")
            return
        self._voice_feedback(dispatch_transcript(self, transcript or ""))

    def _voice_feedback(self, feedback: Any) -> None:
        from quill.ui.media.voice_capture import event_style

        force, sound = event_style(feedback.event)
        self._announce(feedback.message, force=force, sound=sound)

    def _voice_event(self, event: Any, message: str) -> None:
        from quill.ui.media.voice_capture import VoiceFeedback

        self._voice_feedback(VoiceFeedback(event, message))

    def _sync_listen_check(self) -> None:
        if self._listen_menu_item is not None:
            self._listen_menu_item.Check(self._listening)
