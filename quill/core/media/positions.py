"""Where you stopped listening -- portably, and ready to sync.

Resume already worked, within one machine. This module exists because of the
two words that qualifies: **one machine**.

The old store (``speech/listening_positions.py``, now a thin wrapper over this)
keyed a position by ``f"{path.resolve()}|{size}"``. That is a perfectly good
key right up until you own a second computer: ``D:\\Audio\\book.mp3`` and
``/home/you/Audio/book.mp3`` are the same audiobook and will never agree on a
key, and a Windows-to-macOS pair cannot even agree on the separator. A position
keyed by an absolute path is a position that can only ever live on the machine
that made it.

So identity here is **derived from the file's contents**, not its location:
size plus a digest of its first and last 64 KB. Cheap (128 KB read, not the
whole file), stable across machines and operating systems, and different for a
different recording of the same title -- which is what you want, because your
place in one narrator's reading says nothing about another's.

**Why the record carries a timestamp.** Merging two positions is not "keep the
larger one". If you deliberately jumped back twenty minutes to re-hear
something and then opened the book on your laptop, the furthest position is
precisely the wrong answer. The most *recent* one is what you meant, so
:func:`merge_positions` is last-write-wins on ``updated_at`` -- and says so
when the two disagreed, rather than silently discarding a position.

This is shaped for :mod:`quill.core.sync`: :class:`PositionStore`
satisfies its ``RecordStore`` protocol and :func:`merge_positions` satisfies
its ``MergeFn``, so wiring a transport later is adapter work rather than a
rewrite. Nothing here touches the network.

A listening position is **not a cache.** It is the least reproducible thing in
the media stack: lose it and there is no way to recompute where somebody was in
a thirty-hour book. It is classified as content in the persistence audit for
exactly that reason.

wx-free, strict-typed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

#: How much of each end of the file feeds the identity digest. Enough that two
#: different recordings never collide; small enough that identifying a 500 MB
#: audiobook is a couple of reads rather than a full scan.
_SAMPLE_BYTES = 64 * 1024

_FILE_NAME = "listening_positions.json"

#: Positions are small and a listener's library is finite, but the store should
#: not grow without bound for someone who opens thousands of files.
MAX_ENTRIES = 500

#: Below this, "resume" is indistinguishable from "start again" and offering it
#: is noise.
MIN_RESUME_MS = 10_000


def media_identity(path: Path) -> str:
    """A machine-independent identity for a media file.

    ``size-<digest>``, where the digest covers the first and last
    :data:`_SAMPLE_BYTES`. The size alone would collide often enough to matter
    across a large library; the ends alone would not distinguish two files
    padded from the same source. Together they are effectively unique and cost
    two seeks.

    Returns ``""`` when the file cannot be read, which every caller treats as
    "no identity, so no saved position" rather than as an error -- a resume
    position is never worth an exception.
    """
    try:
        size = path.stat().st_size
    except OSError:
        return ""
    digest = hashlib.sha256()
    digest.update(str(size).encode("ascii"))
    try:
        with path.open("rb") as handle:
            digest.update(handle.read(_SAMPLE_BYTES))
            if size > _SAMPLE_BYTES * 2:
                handle.seek(-_SAMPLE_BYTES, 2)
                digest.update(handle.read(_SAMPLE_BYTES))
    except OSError:
        return ""
    return f"{size}-{digest.hexdigest()[:32]}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class ListeningPosition:
    """One remembered playhead, and enough context to merge and report it."""

    media_id: str
    position_ms: int
    #: UTC ISO. The merge key -- see the module docstring on why this is the
    #: tiebreaker rather than the larger position.
    updated_at: str
    #: Length, when known. Lets a report say "2 hours into 11" rather than a
    #: bare number, and lets a caller ignore a position past the end.
    duration_ms: int = 0
    #: The filename as it was on the machine that saved it. Human-readable
    #: only: never part of the identity, because it differs between machines.
    label: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "media_id": self.media_id,
            "position_ms": self.position_ms,
            "updated_at": self.updated_at,
            "duration_ms": self.duration_ms,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: object) -> ListeningPosition | None:
        if not isinstance(data, dict):
            return None
        media_id = str(data.get("media_id", "")).strip()
        if not media_id:
            return None
        return cls(
            media_id=media_id,
            position_ms=max(0, _as_int(data.get("position_ms"))),
            updated_at=str(data.get("updated_at", "")),
            duration_ms=max(0, _as_int(data.get("duration_ms"))),
            label=str(data.get("label", "")),
        )


def _as_int(value: object) -> int:
    """Whatever the file held, as a non-negative-able int (0 when it is junk)."""
    if isinstance(value, bool):  # bool is an int; a flag here is junk, not 1
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, (float, str)):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0
    return 0


def merge_positions(local: dict | None, remote: dict) -> tuple[dict, list[object]]:
    """Combine two versions of one position. A QuillSync ``MergeFn``.

    Last write wins, by ``updated_at``. A conflict is reported only when the
    two are meaningfully apart -- reopening a book on a second machine and
    finding the position a few seconds off is not something to tell anybody
    about, but "these two machines disagree by an hour" is.

    Ties, and records with no timestamp at all, resolve to the remote, matching
    ``default_merge`` so behaviour is predictable when data is incomplete.
    """
    from quill.core.sync.protocol import Conflict

    if local is None:
        return remote, []

    local_at = str(local.get("updated_at", ""))
    remote_at = str(remote.get("updated_at", ""))
    winner = local if local_at > remote_at else remote

    local_ms = max(0, _as_int(local.get("position_ms")))
    remote_ms = max(0, _as_int(remote.get("position_ms")))
    conflicts: list[object] = []
    if abs(local_ms - remote_ms) >= CONFLICT_GAP_MS:
        conflicts.append(
            Conflict(
                entity_id=str(remote.get("media_id", "")),
                field="position_ms",
                local=_spoken(local_ms),
                remote=_spoken(remote_ms),
                merged=_spoken(max(0, _as_int(winner.get("position_ms")))),
                message=(
                    "Two devices remembered different places in "
                    f"{remote.get('label') or 'this recording'}. "
                    "The most recent one was kept."
                ),
            )
        )
    return winner, conflicts


#: How far apart two positions must be before the difference is worth
#: mentioning. Five minutes: below that it is the same place.
CONFLICT_GAP_MS = 5 * 60 * 1000


def _spoken(position_ms: int) -> str:
    """A duration as words, for a conflict a screen reader will read aloud."""
    from quill.core.media.timecode import format_spoken

    return format_spoken(position_ms)


class PositionStore:
    """The remembered positions, and a QuillSync ``RecordStore`` over them.

    ``get_record`` / ``put_record`` / ``delete_record`` are the sync contract;
    the ``*_for`` helpers are what the players call. Both act on the same file,
    so a synced position is immediately the one that resumes.
    """

    def __init__(self, data_dir: Path) -> None:
        self._path = data_dir / _FILE_NAME

    # -- the players' half --------------------------------------------------

    def position_for(self, media: Path) -> int:
        """The saved position for *media*, or 0 when there is none.

        Falls back to the legacy absolute-path key so an upgrade does not lose
        anybody's place; the next save re-files it under the portable one.
        """
        entries = self._read()
        media_id = media_identity(media)
        record = entries.get(media_id) if media_id else None
        if record is None:
            record = entries.get(_legacy_key(media))
        if isinstance(record, dict):
            position = ListeningPosition.from_dict(record)
            return position.position_ms if position is not None else 0
        # The pre-1.0 store held a bare millisecond count against the path key,
        # with no timestamp and no length. Read it, so an upgrade does not
        # reset anybody's place; the next save re-files it as a full record.
        return max(0, _as_int(record)) if record is not None else 0

    def remember(self, media: Path, position_ms: int, *, duration_ms: int = 0) -> None:
        """Record where playback reached. Best-effort; never raises.

        A position under :data:`MIN_RESUME_MS` clears the entry instead of
        storing it: "three seconds in" is the start, and offering to resume
        there is noise the listener has to dismiss.
        """
        media_id = media_identity(media)
        if not media_id:
            return
        entries = self._read()
        entries.pop(_legacy_key(media), None)
        if position_ms < MIN_RESUME_MS:
            entries.pop(media_id, None)
        else:
            entries[media_id] = ListeningPosition(
                media_id=media_id,
                position_ms=max(0, int(position_ms)),
                updated_at=_now(),
                duration_ms=max(0, int(duration_ms)),
                label=media.name,
            ).to_dict()
        self._write(entries)

    def forget(self, media: Path) -> None:
        """Drop the position for *media* (finished, or started again)."""
        entries = self._read()
        media_id = media_identity(media)
        changed = bool(entries.pop(_legacy_key(media), None))
        if media_id and entries.pop(media_id, None) is not None:
            changed = True
        if changed:
            self._write(entries)

    # -- the QuillSync RecordStore contract ---------------------------------

    def get_record(self, entity_id: str) -> dict | None:
        record = self._read().get(entity_id)
        return record if isinstance(record, dict) else None

    def put_record(self, entity_id: str, record: dict) -> None:
        entries = self._read()
        entries[entity_id] = dict(record)
        self._write(entries)

    def delete_record(self, entity_id: str) -> None:
        entries = self._read()
        if entries.pop(entity_id, None) is not None:
            self._write(entries)

    def entity_ids(self) -> list[str]:
        """Every position's id, for an adapter enumerating what to push."""
        return list(self._read())

    # -- disk ----------------------------------------------------------------

    def _read(self) -> dict[str, object]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return raw if isinstance(raw, dict) else {}

    def _write(self, entries: dict[str, object]) -> None:
        from quill.core.storage import write_json_atomic

        while len(entries) > MAX_ENTRIES:
            entries.pop(next(iter(entries)))
        try:
            write_json_atomic(self._path, entries)
        except OSError:
            pass


def _legacy_key(media: Path) -> str:
    """The pre-portable key: absolute path plus size.

    Read for migration only, never written. Kept because dropping it would
    silently reset every listener's place on upgrade, which is the one failure
    this whole module exists to prevent.
    """
    try:
        size = media.stat().st_size
    except OSError:
        size = 0
    try:
        return f"{media.resolve()}|{size}"
    except OSError:
        return f"{media}|{size}"


__all__ = [
    "CONFLICT_GAP_MS",
    "MAX_ENTRIES",
    "MIN_RESUME_MS",
    "ListeningPosition",
    "PositionStore",
    "media_identity",
    "merge_positions",
]
