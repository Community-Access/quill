"""Announcement history (verbosity §24).

Spoken output disappears the instant it is heard. The history keeps the last N
announcements so a user can repeat the last one, review and replay earlier ones,
copy them, ask why they happened, or filter them — recovery, confidence, and
debugging in one place. It is a bounded ring buffer; ``redact_text`` keeps raw
token values (which may hold document content) out of the record by default,
storing only the already-user-facing rendered output.

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from quill.core.verbosity.explain import ExplanationTrace
from quill.core.verbosity.verbs import Severity

if TYPE_CHECKING:
    from quill.core.verbosity.engine import RenderedAnnouncement

__all__ = ["HistoryEntry", "AnnouncementHistory"]


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """One recorded announcement with the fields History and Explain need."""

    timestamp: datetime
    verb_id: str
    trigger: str
    profile: str
    channels: str
    speech: str
    braille: str
    visual: str
    sound_event: str | None
    template_source: str
    severity: Severity
    suppressed: bool
    quiet: bool
    meeting: bool
    trace: ExplanationTrace
    token_values: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_announcement(
        cls,
        rendered: RenderedAnnouncement,
        *,
        timestamp: datetime | None = None,
        token_values: dict[str, Any] | None = None,
        redact: bool = True,
    ) -> HistoryEntry:
        """Build an entry from an engine result; drop token values when redacting."""
        return cls(
            timestamp=timestamp or datetime.now(),
            verb_id=rendered.verb_id,
            trigger=rendered.trace.trigger,
            profile=rendered.profile,
            channels=rendered.trace.channels,
            speech=rendered.speech,
            braille=rendered.braille,
            visual=rendered.visual,
            sound_event=rendered.sound_event,
            template_source=rendered.template_source,
            severity=rendered.severity,
            suppressed=rendered.suppressed,
            quiet=rendered.trace.quiet_affected,
            meeting=rendered.trace.meeting_affected,
            trace=rendered.trace,
            token_values={} if redact else dict(token_values or {}),
        )


class AnnouncementHistory:
    """A bounded, filterable record of recent announcements."""

    def __init__(self, *, max_entries: int = 100, redact_text: bool = True) -> None:
        self._max = max_entries
        self._redact = redact_text
        self._entries: list[HistoryEntry] = []

    @property
    def redact_text(self) -> bool:
        return self._redact

    def record(self, entry: HistoryEntry) -> None:
        """Append an entry, trimming the oldest past ``max_entries``."""
        self._entries.append(entry)
        if len(self._entries) > self._max:
            self._entries.pop(0)

    def record_announcement(
        self, rendered: RenderedAnnouncement, *, token_values: dict[str, Any] | None = None
    ) -> HistoryEntry:
        """Convenience: build an entry from an engine result and record it."""
        entry = HistoryEntry.from_announcement(
            rendered, token_values=token_values, redact=self._redact
        )
        self.record(entry)
        return entry

    def last(self) -> HistoryEntry | None:
        """The most recent entry, or ``None`` when history is empty."""
        return self._entries[-1] if self._entries else None

    def all(self) -> tuple[HistoryEntry, ...]:
        return tuple(self._entries)

    def filter(
        self,
        *,
        verb_id: str | None = None,
        profile: str | None = None,
        severity: Severity | None = None,
        warnings_only: bool = False,
    ) -> tuple[HistoryEntry, ...]:
        """Return entries matching every supplied criterion."""
        result = []
        for entry in self._entries:
            if verb_id is not None and entry.verb_id != verb_id:
                continue
            if profile is not None and entry.profile != profile:
                continue
            if severity is not None and entry.severity is not severity:
                continue
            if warnings_only and not entry.trace.has_warnings:
                continue
            result.append(entry)
        return tuple(result)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
