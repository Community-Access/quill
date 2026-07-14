"""The verbosity runtime controller (verbosity sub-PR 1.5 wiring).

One wx-free object that the editor shell holds to make the verbosity system live.
It owns the engine, the Quiet/Meeting controllers, the undo stack, the
announcement history, mastery, and Safe Mode, and exposes the handful of methods
the UI calls: process an announcement (applying mode suppression and recording
history), toggle the modes, undo a transition, answer the status-query commands,
and render the status-bar mode badge. Keeping this wx-free means the whole
integration is unit-testable without a display; ``main_frame`` routes its single
announce choke-point through :meth:`process` rather than editing call sites one
by one.
"""

from __future__ import annotations

from typing import Any

from quill.core.verbosity.engine import VerbosityEngine
from quill.core.verbosity.history import AnnouncementHistory
from quill.core.verbosity.mastery import MasteryTracker
from quill.core.verbosity.meeting import MeetingMode
from quill.core.verbosity.profiles import DEFAULT_PROFILE, VerbosityProfile, active_profile
from quill.core.verbosity.quiet import QuietMode, VerbosityUndoStack
from quill.core.verbosity.registry import VerbRegistry, default_registry
from quill.core.verbosity.safe_mode import VerbositySafeMode
from quill.core.verbosity.throttle import AnnouncementThrottle, config_from_settings

__all__ = ["AnnouncementOutcome", "VerbosityController"]


class AnnouncementOutcome:
    """What :meth:`VerbosityController.process` decided for one announcement.

    ``speech`` is the text the shell should actually speak ("" when suppressed);
    ``visual`` is always the full text for the status bar (the visual floor).
    """

    __slots__ = ("speech", "visual", "suppressed", "sound_event")

    def __init__(self, speech: str, visual: str, suppressed: bool, sound_event: str | None) -> None:
        self.speech = speech
        self.visual = visual
        self.suppressed = suppressed
        self.sound_event = sound_event


class VerbosityController:
    """Live verbosity state for the editor shell."""

    def __init__(
        self,
        *,
        profile: VerbosityProfile = DEFAULT_PROFILE,
        registry: VerbRegistry | None = None,
        history_enabled: bool = True,
        history_limit: int = 100,
        mastery_enabled: bool = True,
    ) -> None:
        self._registry = registry or default_registry()
        self._engine = VerbosityEngine(self._registry, profile)
        self.quiet = QuietMode()
        self.meeting = MeetingMode()
        self.undo_stack = VerbosityUndoStack()
        self.history = AnnouncementHistory(max_entries=history_limit)
        self._history_enabled = history_enabled
        self.mastery = MasteryTracker(enabled=mastery_enabled)
        self.safe_mode = VerbositySafeMode()
        # Anti-spam for the spoken channel (repetition collapse + budget). Visual
        # output is never throttled, so nothing is hidden on the status bar.
        self.throttle = AnnouncementThrottle()

    # -- configuration ------------------------------------------------------

    @property
    def profile(self) -> VerbosityProfile:
        return self._engine.profile

    def set_profile(self, profile: VerbosityProfile) -> None:
        self._engine.set_profile(profile)

    def apply_settings(self, settings: Any) -> None:
        """Adopt the legacy ``announcement_verbosity`` knob as the active profile."""
        self.set_profile(active_profile(settings))
        self._history_enabled = bool(getattr(settings, "verbosity_history_enabled", True))
        self.throttle.set_config(config_from_settings(settings))

    # -- the announce choke-point ------------------------------------------

    def process(
        self,
        message: str,
        *,
        verb_id: str = "_legacy",
        ctx: dict[str, Any] | None = None,
        chord: str | None = None,
        trigger: str | None = None,
        record: bool = True,
    ) -> AnnouncementOutcome:
        """Run one announcement through the engine under the current modes.

        Returns the speech the shell should speak (empty when Quiet/Meeting or the
        profile suppresses it) and the full visual text for the status bar.
        """
        context = ctx if ctx is not None else {"message": message}
        result = self._engine.speak(
            verb_id,
            context,
            quiet=self.quiet.is_active,
            meeting=self.meeting.is_active,
            chord=chord,
            trigger=trigger,
        )
        # The legacy passthrough renders to the original message; for an unmapped
        # verb the engine already falls back to _legacy.
        visual = result.visual or message
        speech = result.speech if result.speech else ("" if result.suppressed else "")
        if verb_id == "_legacy" and not result.suppressed:
            speech = message
        # Anti-spam the spoken channel only — the status bar always gets `visual`.
        throttled = bool(speech) and not self.throttle.admit(speech).speak
        if throttled:
            speech = ""
        if self._history_enabled and record:
            self.history.record_announcement(result)
        return AnnouncementOutcome(
            speech=speech,
            visual=visual,
            suppressed=result.suppressed or throttled,
            sound_event=result.sound_event,
        )

    # -- mode toggles (return the spoken transition) ------------------------

    def toggle_quiet(self) -> str:
        was = self.quiet.is_active
        message = self.quiet.toggle()

        def _restore() -> None:
            self._restore_quiet(was)

        self.undo_stack.push(message, _restore)
        return message

    def _restore_quiet(self, active: bool) -> None:
        if active:
            self.quiet.enter()
        else:
            self.quiet.exit()

    def toggle_meeting(self) -> str:
        was = self.meeting.is_active
        message = self.meeting.toggle()

        def _restore() -> None:
            self._restore_meeting(was)

        self.undo_stack.push(message, _restore)
        return message

    def _restore_meeting(self, active: bool) -> None:
        if active:
            self.meeting.enter()
        else:
            self.meeting.exit()

    def undo(self) -> str:
        return self.undo_stack.undo()

    # -- status queries (§18-§20) ------------------------------------------

    def where_am_i(
        self, *, line: int | None = None, total: int | None = None, column: int | None = None
    ) -> str:
        parts: list[str] = []
        if line is not None:
            parts.append(f"Line {line}" + (f" of {total}" if total else ""))
        if column is not None:
            parts.append(f"column {column}")
        return ", ".join(parts) if parts else "Position unknown"

    def what_changed(self) -> str:
        last = self.history.last()
        return last.visual if last is not None else "Nothing recent"

    def speak_status(self, status_text: str) -> str:
        return status_text or "Status bar empty"

    # -- status-bar badge ---------------------------------------------------

    def status_badge(self) -> str:
        """Return the mode badge for the status bar, e.g. ``[Q]``, ``[M]``, or ``""``."""
        badges = []
        if self.quiet.is_active:
            badges.append("[Q]")
        if self.meeting.is_active:
            badges.append("[M]")
        return " ".join(badges)
