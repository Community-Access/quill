"""AI activity / audit log (PRD §9, §14 — first-class reviewable surface).

Every gateway tool call, permission decision, and applied patch is recorded here
as a structured, redacted entry so the AI Hub's Activity tab can answer "what did
the AI do, and can I undo the last change?" without exposing document content or
secrets.

This is wx-free core. Entries persist atomically as a bounded JSON list under
``<data>/ai-activity/activity.json`` (newest last). Free-text fields pass through
:func:`quill.stability.redaction.redact_text_for_bundle` before they are stored,
and by default we record *scope*, not raw document content (PRD §9 "scope, not
raw content, by default").
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic
from quill.stability.redaction import redact_text_for_bundle

__all__ = [
    "ActivityEntry",
    "ActivityLog",
    "activity_dir",
]

# Keep the on-disk log bounded; the Activity tab shows the recent tail and the
# full history is intentionally not unbounded (PRD: reviewable, not forensic).
_MAX_ENTRIES = 1000


def activity_dir() -> Path:
    return app_data_dir() / "ai-activity"


def _activity_path() -> Path:
    return activity_dir() / "activity.json"


@dataclass(frozen=True, slots=True)
class ActivityEntry:
    """One recorded AI action.

    ``kind`` mirrors the gateway/event vocabulary (e.g. ``"tool_call_completed"``,
    ``"patch_applied"``, ``"permission_denied"``). ``summary`` is a short,
    already-redacted human sentence. ``detail`` holds non-secret structured
    extras (scope, category, decision). ``undo_label`` is set only on entries
    that produced an undoable editor change, so "Undo last AI change" can find
    the most recent one.
    """

    timestamp: float
    kind: str
    agent_id: str
    harness: str
    summary: str
    detail: dict[str, str] = field(default_factory=dict)
    undo_label: str | None = None

    @classmethod
    def now(
        cls,
        *,
        kind: str,
        agent_id: str,
        harness: str,
        summary: str,
        detail: dict[str, str] | None = None,
        undo_label: str | None = None,
    ) -> ActivityEntry:
        """Build an entry stamped with the current time, redacting free text."""
        return cls(
            timestamp=time.time(),
            kind=kind,
            agent_id=agent_id,
            harness=harness,
            summary=redact_text_for_bundle(summary).strip(),
            detail={k: redact_text_for_bundle(v).strip() for k, v in (detail or {}).items()},
            undo_label=undo_label,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ActivityEntry:
        raw_detail = data.get("detail", {})
        detail = (
            {str(k): str(v) for k, v in raw_detail.items()} if isinstance(raw_detail, dict) else {}
        )
        raw_ts = data.get("timestamp", 0.0)
        timestamp = float(raw_ts) if isinstance(raw_ts, (int, float)) else 0.0
        undo = data.get("undo_label")
        return cls(
            timestamp=timestamp,
            kind=str(data.get("kind", "")),
            agent_id=str(data.get("agent_id", "")),
            harness=str(data.get("harness", "")),
            summary=str(data.get("summary", "")),
            detail=detail,
            undo_label=str(undo) if undo is not None else None,
        )


class ActivityLog:
    """Append-and-read access to the bounded, redacted activity log.

    Reads tolerate a missing or corrupt file (returns empty). Writes are atomic
    and trim the head once the cap is exceeded, so the file never grows without
    bound. A custom ``path`` is accepted for test isolation.
    """

    def __init__(self, path: Path | None = None, *, max_entries: int = _MAX_ENTRIES) -> None:
        self._path = path or _activity_path()
        self._max_entries = max_entries

    @property
    def path(self) -> Path:
        return self._path

    def all(self) -> list[ActivityEntry]:
        """Return every stored entry, oldest first; empty on missing/corrupt."""
        try:
            raw = read_json(self._path, default=[])
        except (ValueError, OSError):
            # A truncated/corrupt log must never crash the Activity tab.
            return []
        if not isinstance(raw, list):
            return []
        entries: list[ActivityEntry] = []
        for item in raw:
            if isinstance(item, dict):
                entries.append(ActivityEntry.from_dict(item))
        return entries

    def recent(self, count: int = 50) -> list[ActivityEntry]:
        """Return the newest ``count`` entries, oldest first within that slice."""
        if count <= 0:
            return []
        return self.all()[-count:]

    def append(self, entry: ActivityEntry) -> None:
        """Append one entry atomically, trimming the head past the cap."""
        entries = self.all()
        entries.append(entry)
        if len(entries) > self._max_entries:
            entries = entries[-self._max_entries :]
        write_json_atomic(self._path, [e.to_dict() for e in entries])

    def last_undoable(self) -> ActivityEntry | None:
        """The most recent entry that produced an undoable change, if any.

        Backs the Hub's "Review / Undo last AI change" affordance.
        """
        for entry in reversed(self.all()):
            if entry.undo_label is not None:
                return entry
        return None
