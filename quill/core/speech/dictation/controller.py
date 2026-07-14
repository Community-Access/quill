"""Dictation state-machine controller (PRD §11, §25, §26).

The wx-free orchestrator for Hold-to-Dictate and Locked Dictation. It owns the
:class:`DictationState`, enforces legal transitions, guarantees the single
recorder invariant, and sequences the protected-transaction lifecycle the PRD
demands (§37): the user explicitly starts; the active state is unmistakable;
there is always a dependable stop; audio is secured before transcription; the
transcript stays tied to its document context; failure recovers rather than
loses; and the machine always returns to a known state.

All side effects — opening the microphone, saving recovery audio, running
Whisper, inserting text, playing earcons/announcements — are delegated to an
injected :class:`DictationServices` bundle so the controller is deterministic and
unit-testable with no microphone, no Whisper, and no ``wx``.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Protocol

from quill.core.speech.dictation.insertion import normalize_for_insertion
from quill.core.speech.dictation.session import DictationSession, InsertionContext
from quill.core.speech.dictation.states import (
    ACTIVE_RECORDING_STATES,
    STOPPABLE_STATES,
    DictationMode,
    DictationState,
    is_valid_transition,
)

logger = logging.getLogger(__name__)


class FeedbackEvent(Enum):
    """Discrete moments the UI turns into an earcon and/or announcement (§18)."""

    HOLD_START = auto()
    HOLD_STOP = auto()
    LOCKED_START = auto()
    LOCKED_STOP = auto()
    PAUSED = auto()
    RESUMED = auto()
    TRANSCRIBING = auto()
    INSERTED = auto()
    NO_SPEECH = auto()
    REVIEW = auto()
    CANCELLED = auto()
    MAX_TIME = auto()
    FOCUS_LOST = auto()
    MISSING_KEYUP = auto()
    MIC_UNAVAILABLE = auto()
    BUSY = auto()
    ERROR = auto()


@dataclass(slots=True)
class DictationConfig:
    """User-tunable policy the controller consults (PRD §10, §20)."""

    max_locked_seconds: float = 300.0  # 5 minutes (PRD §10.5 default)
    stop_on_focus_loss: bool = True  # PRD §10.3 default
    intelligent_spacing: bool = True  # PRD §17
    min_hold_seconds: float = 0.0  # PRD §20.2 "Ignore accidental taps"


class DictationServices(Protocol):
    """Side-effect bundle the wx shell injects (everything the core must not do).

    Implementations marshal to the UI thread as needed. ``transcribe`` is
    fire-and-forget: it kicks off a worker that must eventually call back into
    :meth:`DictationController.transcription_succeeded` or
    :meth:`DictationController.transcription_failed`.
    """

    def start_capture(self, session: DictationSession) -> None:
        """Open the microphone and begin capture. Raise on failure."""

    def stop_capture(self, session: DictationSession) -> Path | None:
        """Stop capture; return the captured WAV path (or None if nothing)."""

    def pause_capture(self, session: DictationSession) -> None: ...

    def resume_capture(self, session: DictationSession) -> None: ...

    def discard_capture(self, session: DictationSession) -> None:
        """Stop capture and drop the audio (cancel path)."""

    def save_audio(self, session: DictationSession, wav_path: Path) -> None:
        """Persist captured audio to recovery storage before transcription."""

    def transcribe(self, session: DictationSession) -> None:
        """Begin background transcription; call back the controller when done."""

    def insert(self, session: DictationSession, text: str) -> bool:
        """Insert ``text`` as one undo action. Return False to defer to review."""

    def feedback(self, event: FeedbackEvent, session: DictationSession | None) -> None:
        """Play the earcon/announcement for ``event`` (never raises)."""

    def now(self) -> float:
        """Monotonic-ish wall clock; injectable so tests control time."""


class DictationController:
    """The dictation state machine (PRD §26, hardened for production §26 notes)."""

    def __init__(
        self,
        services: DictationServices,
        config: DictationConfig | None = None,
    ) -> None:
        self._services = services
        self._config = config if config is not None else DictationConfig()
        self._state = DictationState.IDLE
        self._session: DictationSession | None = None
        self._lock = threading.RLock()

    # -- introspection ----------------------------------------------------- #

    @property
    def state(self) -> DictationState:
        with self._lock:
            return self._state

    @property
    def config(self) -> DictationConfig:
        return self._config

    @config.setter
    def config(self, value: DictationConfig) -> None:
        self._config = value

    @property
    def session(self) -> DictationSession | None:
        with self._lock:
            return self._session

    @property
    def is_recording(self) -> bool:
        """True only while the microphone is live (never a bare global flag)."""
        with self._lock:
            return self._state in ACTIVE_RECORDING_STATES

    @property
    def is_busy(self) -> bool:
        """True when a session is active in any non-idle phase."""
        with self._lock:
            return self._state is not DictationState.IDLE

    # -- public commands (PRD §8 / §26) ------------------------------------ #

    def start_hold(self, context: InsertionContext) -> None:
        """Begin Hold-to-Dictate. A no-op unless idle.

        Auto-repeat key-down events and an overlapping second session both land
        here while non-idle and are silently ignored (PRD §13.1, §33 Hold #2).
        """
        with self._lock:
            if self._state is not DictationState.IDLE:
                return  # auto-repeat / overlap rejection — silent by design
            self._begin_session(DictationMode.HOLD, context)

    def release_hold(self) -> None:
        """End Hold-to-Dictate on key-up. Ignored if no hold is active."""
        with self._lock:
            if self._state is not DictationState.HOLD_RECORDING:
                return
            if self._hold_too_short():
                # Accidental tap (PRD §20.2): drop without transcribing.
                self._discard("hold tap below minimum duration")
                return
            self._finish(FeedbackEvent.HOLD_STOP)

    def toggle_locked(self, context: InsertionContext) -> None:
        """Start Locked Dictation when idle, or finish it when active (PRD §9.2)."""
        with self._lock:
            if self._state is DictationState.IDLE:
                self._begin_session(DictationMode.LOCKED, context)
                return
            if self._state in {DictationState.LOCKED_RECORDING, DictationState.PAUSED}:
                self._finish(FeedbackEvent.LOCKED_STOP)
                return
            if self._state is DictationState.HOLD_RECORDING:
                # PRD §12: Ctrl+F9 during a held session is ignored (no promotion
                # in the first release); the hold owns the session.
                return
            # Busy transcribing/inserting: report rather than start a second one.
            self._services.feedback(FeedbackEvent.BUSY, self._session)

    def emergency_stop(self) -> None:
        """Escape: stop recording immediately but keep the speech (PRD §9.2)."""
        with self._lock:
            if self._state not in STOPPABLE_STATES:
                return
            stop_event = (
                FeedbackEvent.LOCKED_STOP
                if self._mode is DictationMode.LOCKED
                else FeedbackEvent.HOLD_STOP
            )
            self._finish(stop_event)

    def cancel_and_discard(self) -> None:
        """Shift+Escape: stop and throw the audio away (PRD §8, §12)."""
        with self._lock:
            if self._state not in STOPPABLE_STATES:
                return
            self._discard("user cancelled")

    def toggle_pause(self) -> None:
        """Pause/resume a locked session (PRD §9.2 Pause and Resume)."""
        with self._lock:
            session = self._session
            if session is None:
                return
            if self._state is DictationState.LOCKED_RECORDING:
                self._safe(lambda: self._services.pause_capture(session), "pause_capture")
                self._set_state(DictationState.PAUSED)
                self._services.feedback(FeedbackEvent.PAUSED, session)
            elif self._state is DictationState.PAUSED:
                self._safe(lambda: self._services.resume_capture(session), "resume_capture")
                self._set_state(DictationState.LOCKED_RECORDING)
                self._services.feedback(FeedbackEvent.RESUMED, session)

    # -- watchdog / environment hooks (PRD §10, §13.3) --------------------- #

    def tick(self) -> None:
        """Enforce the maximum locked-recording duration (PRD §10.5).

        Call periodically from the UI's existing timer. Hold sessions are bounded
        by the physical key, so only locked recording is time-limited here.
        """
        with self._lock:
            if self._state is not DictationState.LOCKED_RECORDING:
                return
            session = self._session
            if session is None or self._config.max_locked_seconds <= 0:
                return
            if self._services.now() - session.started_at >= self._config.max_locked_seconds:
                self._services.feedback(FeedbackEvent.MAX_TIME, session)
                self._finish(FeedbackEvent.LOCKED_STOP)

    def on_focus_lost(self) -> None:
        """Stop and preserve speech when QUILL loses focus (PRD §10.3 default)."""
        with self._lock:
            if self._state not in STOPPABLE_STATES:
                return
            if not self._config.stop_on_focus_loss:
                return
            self._services.feedback(FeedbackEvent.FOCUS_LOST, self._session)
            self._finish(
                FeedbackEvent.LOCKED_STOP
                if self._mode is DictationMode.LOCKED
                else FeedbackEvent.HOLD_STOP
            )

    def on_missing_keyup(self) -> None:
        """Recover when a Hold key-up was never delivered (PRD §13.3, mandatory)."""
        with self._lock:
            if self._state is not DictationState.HOLD_RECORDING:
                return
            logger.warning("dictation: recovered a missing key-up; treating as release")
            self._services.feedback(FeedbackEvent.MISSING_KEYUP, self._session)
            self._finish(FeedbackEvent.HOLD_STOP)

    # -- transcription callbacks (from the worker thread) ------------------ #

    def transcription_succeeded(self, session_id: str, text: str) -> None:
        """Worker reported a transcript. Insert it or defer to review."""
        with self._lock:
            session = self._session
            if session is None or session.session_id != session_id:
                return  # a stale/cancelled session — ignore
            if self._state is not DictationState.TRANSCRIBING:
                return
            cleaned = (text or "").strip()
            if not cleaned:
                session.transcription_state = "empty"
                self._services.feedback(FeedbackEvent.NO_SPEECH, session)
                self._complete(DictationState.COMPLETED)
                return
            session.transcript = cleaned
            session.transcription_state = "done"
            self._set_state(DictationState.INSERTING)
            insert_text = normalize_for_insertion(
                cleaned,
                prefix_char=session.context.prefix_char,
                suffix_char=session.context.suffix_char,
                intelligent_spacing=self._config.intelligent_spacing,
            )
            inserted = self._safe(
                lambda: self._services.insert(session, insert_text),
                "insert",
                default=False,
            )
            if inserted:
                session.insertion_state = "inserted"
                self._services.feedback(FeedbackEvent.INSERTED, session)
                self._complete(DictationState.COMPLETED)
            else:
                session.insertion_state = "deferred"
                self._services.feedback(FeedbackEvent.REVIEW, session)
                self._set_state(DictationState.REVIEW_REQUIRED)
                self._idle_after_review()

    def transcription_failed(self, session_id: str, error: str) -> None:
        """Worker reported a failure. Preserve audio; never insert error text."""
        with self._lock:
            session = self._session
            if session is None or session.session_id != session_id:
                return
            session.transcription_state = "failed"
            session.error = error
            self._services.feedback(FeedbackEvent.ERROR, session)
            self._fail(error)

    # -- internals --------------------------------------------------------- #

    @property
    def _mode(self) -> DictationMode | None:
        return self._session.mode if self._session is not None else None

    def _begin_session(self, mode: DictationMode, context: InsertionContext) -> None:
        self._set_state(DictationState.VALIDATING)
        if context.read_only:
            # PRD §16.5 / §9.1: never record into a target that cannot accept text.
            self._services.feedback(FeedbackEvent.MIC_UNAVAILABLE, None)
            self._set_state(DictationState.IDLE)
            return
        session = DictationSession(mode=mode, context=context)
        session.started_at = self._services.now()
        self._session = session
        self._set_state(DictationState.STARTING)
        try:
            self._services.start_capture(session)
        except Exception as exc:  # noqa: BLE001 - any capture failure is non-fatal
            logger.warning("dictation: could not start capture: %s", exc)
            self._services.feedback(FeedbackEvent.MIC_UNAVAILABLE, session)
            self._session = None
            self._set_state(DictationState.IDLE)
            return
        recording = (
            DictationState.LOCKED_RECORDING
            if mode is DictationMode.LOCKED
            else DictationState.HOLD_RECORDING
        )
        self._set_state(recording)
        self._services.feedback(
            FeedbackEvent.LOCKED_START
            if mode is DictationMode.LOCKED
            else FeedbackEvent.HOLD_START,
            session,
        )

    def _finish(self, stop_event: FeedbackEvent) -> None:
        """Stop capture, secure audio, then start transcription (PRD §14.2)."""
        session = self._session
        if session is None:
            self._set_state(DictationState.IDLE)
            return
        self._set_state(DictationState.STOPPING)
        session.stopped_at = self._services.now()
        wav = self._safe(lambda: self._services.stop_capture(session), "stop_capture", default=None)
        # Stop tone only after capture has ended so it cannot enter the recording.
        self._services.feedback(stop_event, session)
        self._set_state(DictationState.SAVING_AUDIO)
        if wav is None:
            session.audio_state = "missing"
            self._services.feedback(FeedbackEvent.NO_SPEECH, session)
            self._complete(DictationState.COMPLETED)
            return
        self._safe(lambda: self._services.save_audio(session, wav), "save_audio")
        self._set_state(DictationState.TRANSCRIBING)
        session.transcription_state = "running"
        self._services.feedback(FeedbackEvent.TRANSCRIBING, session)
        self._safe(lambda: self._services.transcribe(session), "transcribe")

    def _discard(self, reason: str) -> None:
        session = self._session
        logger.info("dictation: discarding session (%s)", reason)
        if session is not None:
            self._safe(lambda: self._services.discard_capture(session), "discard_capture")
        self._set_state(DictationState.CANCELLED)
        if session is not None:
            self._services.feedback(FeedbackEvent.CANCELLED, session)
        self._complete(DictationState.CANCELLED)

    def _complete(self, terminal: DictationState) -> None:
        self._set_state(terminal)
        self._session = None
        self._set_state(DictationState.IDLE)

    def _idle_after_review(self) -> None:
        # The transcript is held for the user's review UI; the controller itself
        # returns to idle so a new dictation can start (PRD §16.3). The pending
        # transcript lives in the recovery sidecar, not in the controller.
        self._session = None
        self._set_state(DictationState.IDLE)

    def _fail(self, error: str) -> None:
        logger.warning("dictation: session failed: %s", error)
        self._set_state(DictationState.FAILED)
        # Audio is preserved in recovery; surface for review rather than losing it.
        self._set_state(DictationState.RECOVERING)
        self._session = None
        self._set_state(DictationState.IDLE)

    def _hold_too_short(self) -> bool:
        session = self._session
        if session is None or self._config.min_hold_seconds <= 0:
            return False
        return (self._services.now() - session.started_at) < self._config.min_hold_seconds

    def _set_state(self, target: DictationState) -> None:
        current = self._state
        if not is_valid_transition(current, target):
            # An illegal transition is a programming error; log loudly but do not
            # crash the editor — force the machine to a safe known state.
            logger.error("dictation: illegal transition %s -> %s", current.name, target.name)
        self._state = target
        if self._session is not None:
            self._session.state = target

    def _safe(self, fn, label: str, default=None):  # type: ignore[no-untyped-def]
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - a service fault must not wedge state
            logger.warning("dictation: %s failed: %s", label, exc)
            return default
