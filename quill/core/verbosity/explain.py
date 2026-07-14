"""The "Why did QUILL say that?" explanation trace (verbosity §25).

Every announcement the engine produces carries an :class:`ExplanationTrace` that
records exactly how it was decided: which verb fired, the trigger, the active
profile and channels, where the template came from, the per-channel output, what
(if anything) was suppressed and why. The trace renders to plain copyable text
for the History "Explain" command.

Pure and wx-free; depends on nothing else in the package, so the engine can
import it freely.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ExplanationTrace"]


@dataclass(frozen=True, slots=True)
class ExplanationTrace:
    """A full account of how one announcement was produced."""

    verb_id: str
    trigger: str
    profile: str
    channels: str
    template_source: str
    speech: str
    braille: str
    visual: str
    sound_event: str | None
    suppressed_reason: str
    quiet_affected: bool
    meeting_affected: bool
    per_verb_override: bool
    per_chord_override: bool
    qvp_source: str | None
    sound_suppressed: bool
    routine_hidden: bool
    has_warnings: bool

    def to_text(self) -> str:
        """Render the trace as plain, copyable, screen-reader-friendly text."""
        lines = [
            f"Verb: {self.verb_id}",
            f"Trigger: {self.trigger}",
            f"Profile: {self.profile}",
            f"Channels: {self.channels}",
            f"Template source: {self.template_source}",
        ]
        if self.speech:
            lines.append(f"Speech output: {self.speech}")
        if self.braille:
            lines.append(f"Braille output: {self.braille}")
        lines.append(f"Visual output: {self.visual}")
        if self.sound_event and not self.sound_suppressed:
            lines.append(f"Sound: {self.sound_event}")
        if self.suppressed_reason:
            lines.append(f"Suppressed: {self.suppressed_reason}")
        if self.quiet_affected:
            lines.append("Quiet Mode: affected this announcement")
        if self.meeting_affected:
            lines.append("Meeting Mode: affected this announcement")
        if self.per_verb_override:
            lines.append("Override: a per-verb template applied")
        if self.per_chord_override:
            lines.append("Override: a per-chord template applied")
        if self.qvp_source:
            lines.append(f"Pack: template from {self.qvp_source}")
        if self.has_warnings:
            lines.append("Validation: this template has warnings")
        return "\n".join(lines)
