"""Dictation session records: insertion context and session metadata (PRD §16, §22).

``InsertionContext`` is the snapshot QUILL captures when recording *begins* so a
transcript produced seconds later can be inserted back into the exact place it was
meant for — or safely deferred to review if the document moved (PRD §16). The wx
shell builds it from the live editor; this module keeps it a plain, picklable,
JSON-serializable record with no wx types so the recovery repository and unit
tests can round-trip it.

``DictationSession`` is the full per-dictation record persisted to the recovery
sidecar (PRD §22.2). The sidecar deliberately stores only the *small* anchor
context needed to resolve insertion, never the surrounding document body.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, replace

from quill.core.speech.dictation.states import DictationMode, DictationState


def new_session_id() -> str:
    """A short, filesystem-safe, collision-resistant session id."""
    return uuid.uuid4().hex


@dataclass(frozen=True, slots=True)
class InsertionContext:
    """Where a transcript should land, captured at recording start (PRD §16).

    Only ``prefix_char`` / ``suffix_char`` (the single characters on either side
    of the caret) are stored from the document body — enough to make spacing
    decisions (PRD §17) and to sanity-check the anchor — never the wider text,
    to honour the privacy rule in §22.2.
    """

    document_id: str = ""
    document_path: str | None = None
    caret: int = 0
    selection_start: int = 0
    selection_end: int = 0
    document_revision: int = 0
    prefix_char: str = ""
    suffix_char: str = ""
    read_only: bool = False
    content_mode: str = ""

    @property
    def has_selection(self) -> bool:
        return self.selection_end > self.selection_start

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "document_path": self.document_path,
            "caret": self.caret,
            "selection_start": self.selection_start,
            "selection_end": self.selection_end,
            "document_revision": self.document_revision,
            "prefix_char": self.prefix_char,
            "suffix_char": self.suffix_char,
            "read_only": self.read_only,
            "content_mode": self.content_mode,
        }

    @classmethod
    def from_dict(cls, data: object) -> InsertionContext:
        if not isinstance(data, dict):
            return cls()
        return cls(
            document_id=str(data.get("document_id", "") or ""),
            document_path=(
                str(data["document_path"]) if data.get("document_path") is not None else None
            ),
            caret=_as_int(data.get("caret")),
            selection_start=_as_int(data.get("selection_start")),
            selection_end=_as_int(data.get("selection_end")),
            document_revision=_as_int(data.get("document_revision")),
            prefix_char=str(data.get("prefix_char", "") or "")[:1],
            suffix_char=str(data.get("suffix_char", "") or "")[:1],
            read_only=bool(data.get("read_only", False)),
            content_mode=str(data.get("content_mode", "") or ""),
        )


@dataclass(slots=True)
class DictationSession:
    """The full lifecycle record for one dictation (PRD §15.2, §25)."""

    session_id: str = field(default_factory=new_session_id)
    mode: DictationMode = DictationMode.HOLD
    state: DictationState = DictationState.IDLE
    context: InsertionContext = field(default_factory=InsertionContext)
    started_at: float = field(default_factory=time.time)
    stopped_at: float | None = None
    audio_path: str | None = None
    transcript_path: str | None = None
    transcript: str | None = None
    audio_state: str = "none"  # none | saved | missing
    transcription_state: str = "pending"  # pending | running | done | empty | failed
    insertion_state: str = "not_started"  # not_started | inserted | deferred | failed
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        """JSON-serializable metadata for the recovery sidecar (PRD §22.2)."""
        return {
            "session_id": self.session_id,
            "mode": self.mode.name.lower(),
            "state": self.state.name,
            "created_at": _iso(self.started_at),
            "stopped_at": _iso(self.stopped_at) if self.stopped_at else None,
            "context": self.context.to_dict(),
            "audio_path": self.audio_path,
            "transcript_path": self.transcript_path,
            "audio_state": self.audio_state,
            "transcription_state": self.transcription_state,
            "insertion_state": self.insertion_state,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: object) -> DictationSession:
        if not isinstance(data, dict):
            return cls()
        mode = DictationMode.LOCKED if data.get("mode") == "locked" else DictationMode.HOLD
        try:
            state = DictationState[str(data.get("state", "IDLE"))]
        except KeyError:
            state = DictationState.IDLE
        return cls(
            session_id=str(data.get("session_id", new_session_id())),
            mode=mode,
            state=state,
            context=InsertionContext.from_dict(data.get("context")),
            started_at=_from_iso(data.get("created_at")),
            stopped_at=_from_iso(data.get("stopped_at")) if data.get("stopped_at") else None,
            audio_path=_opt_str(data.get("audio_path")),
            transcript_path=_opt_str(data.get("transcript_path")),
            audio_state=str(data.get("audio_state", "none") or "none"),
            transcription_state=str(data.get("transcription_state", "pending") or "pending"),
            insertion_state=str(data.get("insertion_state", "not_started") or "not_started"),
            error=_opt_str(data.get("error")),
        )

    def with_state(self, state: DictationState) -> DictationSession:
        """Return a copy with ``state`` updated (the controller mutates in place,
        but tests and the repository find an immutable-style helper convenient)."""
        return replace(self, state=state)


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
    return 0


def _opt_str(value: object) -> str | None:
    return None if value is None else str(value)


def _iso(epoch: float) -> str:
    from datetime import UTC, datetime

    return datetime.fromtimestamp(epoch, tz=UTC).isoformat()


def _from_iso(value: object) -> float:
    if not isinstance(value, str) or not value:
        return time.time()
    from datetime import datetime

    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return time.time()
