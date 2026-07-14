"""The central verbosity routing engine (verbosity §7-§13, §28).

:class:`VerbosityEngine.speak` is the one decision point every announcement
flows through. Given a verb id and a context dict it decides: which template
applies (per-chord override > per-verb override > QVP > default), which channels
fire (always including the visual floor), whether the active profile or Quiet /
Meeting mode suppresses speech or sound, and which sound event (if any) plays. It
returns a :class:`RenderedAnnouncement` with the per-channel text and an
:class:`ExplanationTrace` for History and "Why did QUILL say that?".

The engine is pure and wx-free: it computes *what* should be announced; the UI
layer decides how to deliver it. Later sub-PRs migrate live call sites onto it;
:func:`speak_legacy_text` is the no-op passthrough that lets existing
string-based announce paths route through the engine without changing what the
user hears.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quill.core.verbosity.channels import Channel, route_channels
from quill.core.verbosity.explain import ExplanationTrace
from quill.core.verbosity.parser import render_template, validate
from quill.core.verbosity.profiles import NORMAL, SoundPolicy, VerbosityProfile
from quill.core.verbosity.registry import VerbRegistry, default_registry
from quill.core.verbosity.verbs import Severity, VerbSpec

__all__ = ["RenderedAnnouncement", "VerbosityEngine", "speak_legacy_text"]

_LEGACY_VERB_ID = "_legacy"


@dataclass(frozen=True, slots=True)
class RenderedAnnouncement:
    """The fully-decided output of one :meth:`VerbosityEngine.speak` call."""

    verb_id: str
    speech: str
    braille: str
    visual: str
    sound_event: str | None
    channels: Channel
    profile: str
    severity: Severity
    template_source: str
    suppressed: bool
    trace: ExplanationTrace


@dataclass(frozen=True, slots=True)
class _TemplateChoice:
    template: str
    source: str  # "default" | "per_verb" | "per_chord" | "qvp"
    qvp_name: str | None


class VerbosityEngine:
    """Routes announcements through profile, channel, and override decisions."""

    def __init__(
        self,
        registry: VerbRegistry | None = None,
        profile: VerbosityProfile = NORMAL,
        *,
        per_verb_templates: dict[str, str] | None = None,
        per_chord_templates: dict[str, str] | None = None,
        qvp_templates: dict[str, str] | None = None,
        qvp_name: str | None = None,
    ) -> None:
        self._registry = registry or default_registry()
        self._profile = profile
        self._per_verb = per_verb_templates or {}
        self._per_chord = per_chord_templates or {}
        self._qvp = qvp_templates or {}
        self._qvp_name = qvp_name

    @property
    def profile(self) -> VerbosityProfile:
        return self._profile

    def set_profile(self, profile: VerbosityProfile) -> None:
        self._profile = profile

    def _resolve_template(self, verb: VerbSpec, chord: str | None) -> _TemplateChoice:
        if chord is not None and chord in self._per_chord:
            return _TemplateChoice(self._per_chord[chord], "per_chord", None)
        if verb.id in self._per_verb:
            return _TemplateChoice(self._per_verb[verb.id], "per_verb", None)
        if verb.id in self._qvp:
            return _TemplateChoice(self._qvp[verb.id], "qvp", self._qvp_name)
        return _TemplateChoice(verb.default_template, "default", None)

    def _effective_channels(self, quiet: bool, meeting: bool) -> Channel:
        channels = self._profile.channels
        if meeting:
            channels &= ~Channel.SOUND
        if quiet:
            channels &= ~(Channel.SPEECH | Channel.SOUND)
        return route_channels(channels)

    def _sound_event(self, verb: VerbSpec, channels: Channel) -> tuple[str | None, bool]:
        """Return (sound_event, suppressed). Honors the profile sound policy."""
        if Channel.SOUND not in channels:
            return None, True
        if self._profile.sound_policy == SoundPolicy.OFF:
            return None, True
        if (
            self._profile.sound_policy == SoundPolicy.ERRORS_ONLY
            and verb.severity is not Severity.ERROR
        ):
            return None, True
        return f"verbosity.{verb.id}", False

    def speak(
        self,
        verb_id: str,
        ctx: dict[str, Any] | None = None,
        *,
        quiet: bool = False,
        meeting: bool = False,
        chord: str | None = None,
        trigger: str | None = None,
    ) -> RenderedAnnouncement:
        """Decide and render the announcement for ``verb_id`` under ``ctx``."""
        context = ctx or {}
        verb = self._registry.get(verb_id) or self._registry.get(_LEGACY_VERB_ID)
        assert verb is not None  # the legacy verb is always registered
        choice = self._resolve_template(verb, chord)
        channels = self._effective_channels(quiet, meeting)

        rendered = render_template(choice.template, context, verb.supported_tokens)
        report = validate(choice.template, verb)

        # Expert and Quiet suppress routine confirmations; errors always speak.
        routine_hidden = self._profile.suppress_routine and verb.severity is Severity.ROUTINE
        speech_on = Channel.SPEECH in channels and not routine_hidden
        sound_event, sound_suppressed = self._sound_event(verb, channels)
        if routine_hidden:
            sound_event, sound_suppressed = None, True

        speech = rendered if speech_on else ""
        braille = rendered if Channel.BRAILLE in channels else ""
        visual = rendered  # the always-on floor

        suppressed_reason = ""
        if routine_hidden:
            suppressed_reason = f"Routine confirmation hidden by {self._profile.name} profile"
        elif quiet and Channel.SPEECH not in channels:
            suppressed_reason = "Speech hidden by Quiet Mode"

        trace = ExplanationTrace(
            verb_id=verb.id,
            trigger=trigger or chord or "",
            profile=self._profile.name,
            channels=self._channel_names(channels),
            template_source=self._source_label(choice),
            speech=speech,
            braille=braille,
            visual=visual,
            sound_event=sound_event,
            suppressed_reason=suppressed_reason,
            quiet_affected=quiet,
            meeting_affected=meeting,
            per_verb_override=choice.source == "per_verb",
            per_chord_override=choice.source == "per_chord",
            qvp_source=choice.qvp_name if choice.source == "qvp" else None,
            sound_suppressed=sound_suppressed,
            routine_hidden=routine_hidden,
            has_warnings=bool(report.warnings),
        )
        return RenderedAnnouncement(
            verb_id=verb.id,
            speech=speech,
            braille=braille,
            visual=visual,
            sound_event=sound_event,
            channels=channels,
            profile=self._profile.name,
            severity=verb.severity,
            template_source=self._source_label(choice),
            suppressed=routine_hidden or (quiet and Channel.SPEECH not in channels),
            trace=trace,
        )

    @staticmethod
    def _channel_names(channels: Channel) -> str:
        names = [
            channel.name.lower()
            for channel in (Channel.SPEECH, Channel.BRAILLE, Channel.SOUND, Channel.VISUAL)
            if channel in channels and channel.name is not None
        ]
        return ", ".join(names)

    @staticmethod
    def _source_label(choice: _TemplateChoice) -> str:
        if choice.source == "qvp" and choice.qvp_name:
            return f"QVP {choice.qvp_name}"
        return {
            "default": "default",
            "per_verb": "per-verb override",
            "per_chord": "per-chord override",
            "qvp": "QVP pack",
        }[choice.source]


# A single default engine backs the legacy passthrough so existing string-based
# announce paths can route through the engine with no behavior change.
_DEFAULT_ENGINE = VerbosityEngine()


def speak_legacy_text(message: str) -> str:
    """Route a legacy announcement string through the engine, returning speech.

    For the ``_legacy`` verb under the default profile this returns ``message``
    unchanged — a no-op passthrough that makes :meth:`VerbosityEngine.speak`
    reachable from existing call sites without altering what the user hears.
    """
    result = _DEFAULT_ENGINE.speak(_LEGACY_VERB_ID, {"message": message})
    return result.speech or message
