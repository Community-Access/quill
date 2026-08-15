"""Where you stopped, for anything Quill Radio plays that has an end.

A live station has no position worth remembering: you tune in and you are where
everyone else is. A **recording** is the opposite -- a four-hour LibriVox
chapter, an Old Time Radio episode, a podcast -- and losing your place in one is
the difference between a library and a shelf you cannot reach.

Separate from :mod:`quill.core.media.positions`, which Quill Cast and the Media
Player use, because that store keys on a *file*: it hashes a path's name and size
to survive the file moving. Nothing Quill Radio plays here is a file. These are
keyed on the stream URL, which is the only stable identity a streamed recording
has, and normalised so a URL that picks up a session token or arrives over a
different scheme still finds its place.

Design notes worth keeping:

* **A position under :data:`MIN_RESUME_MS` is not a position.** "Four seconds in"
  is the beginning, and offering to resume there is a prompt the listener has to
  dismiss for no gain. Saving one *clears* the entry instead.
* **Finishing clears it too.** Within :data:`END_MARGIN_MS` of the end counts as
  done, so replaying a finished episode starts at the start rather than at the
  closing credits.
* **Failure is never fatal.** An unwritable profile, a corrupt file, a disk that
  filled: all of them degrade to "no saved position", never to an exception
  reaching the player.

wx-free, strict-typed, and pure apart from the one file it owns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Only for the annotation: importing the sync protocol at runtime
    # would make a position store depend on the sync framework, and
    # positions work perfectly well with no sync at all.
    from quill.core.sync.protocol import Conflict

import logging
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_LOG = logging.getLogger(__name__)

_FILE_NAME = "radio-resume.json"

#: Below this, you are at the beginning and there is nothing to resume.
MIN_RESUME_MS = 30_000

#: Within this of the end, you have finished it.
END_MARGIN_MS = 20_000

#: How many positions to keep. Old entries fall off the end rather than the file
#: growing forever; 500 recordings is far more than anyone has in flight.
MAX_ENTRIES = 500

#: Query parameters that identify a *session* rather than the recording. An
#: Archive or CDN URL that gains one of these must still match the entry saved
#: before it did, or the position silently never comes back.
_VOLATILE_PARAMS = frozenset({
    "token",
    "jwt",
    "jwt_auth",
    "sig",
    "signature",
    "expires",
    "expiry",
    "session",
    "sessionid",
    "sid",
    "key",
    "auth",
    "hash",
    "st",
    "e",
    "aw_0_1st.playerid",
    "aw_0_1st.skey",
    "rti",
    "streamid",
})


@dataclass(frozen=True, slots=True)
class ResumePoint:
    """A remembered position in one recording."""

    position_ms: int
    duration_ms: int = 0
    saved_at: float = 0.0
    #: What it is called, and where to get it again. Added so an unfinished
    #: recording can be *listed* rather than only recognised when the same
    #: stream happens to be opened again -- the key is a normalised identity
    #: and cannot be played, so without these a saved position is invisible.
    #: Absent on entries written before this existed, which is why every
    #: listing skips a row that has no url.
    label: str = ""
    url: str = ""

    @property
    def fraction(self) -> float:
        return (self.position_ms / self.duration_ms) if self.duration_ms > 0 else 0.0


def stream_identity(url: str) -> str:
    """A stable key for a stream URL (pure).

    Scheme and case are dropped, and query parameters that identify a session
    rather than the recording are stripped, so the same episode fetched twice --
    over http once and https the next time, with a fresh CDN token each time --
    resolves to one entry. Everything else in the query is kept, because for
    plenty of services it *is* the identity.
    """
    cleaned = (url or "").strip()
    if not cleaned:
        return ""
    parsed = urllib.parse.urlsplit(cleaned)
    kept = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _VOLATILE_PARAMS
    ]
    host = (parsed.hostname or "").lower()
    if parsed.port and parsed.port not in (80, 443):
        host = f"{host}:{parsed.port}"
    return urllib.parse.urlunsplit(("", host, parsed.path, urllib.parse.urlencode(kept), ""))


def spoken_resume(position_ms: int) -> str:
    """ "Resuming at 12 minutes 8 seconds." in words (pure).

    Words, not a clock reading: "12:08" spoken aloud is an ambiguous pair of
    numbers, which is the same reason ``bounded_playback_ui.spoken_duration``
    exists.
    """
    seconds = max(0, position_ms // 1000)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'' if hours == 1 else 's'}")
    if minutes:
        parts.append(f"{minutes} minute{'' if minutes == 1 else 's'}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'' if seconds == 1 else 's'}")
    return " ".join(parts)


class ResumeStore:
    """The remembered positions for streamed recordings."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._dir = data_dir

    def _path(self) -> Path:
        return (self._dir or app_data_dir()) / _FILE_NAME

    def _read(self) -> dict:
        try:
            data = read_json(self._path(), {})
        except OSError:
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self, entries: dict) -> None:
        try:
            write_json_atomic(self._path(), entries)
        except (OSError, TypeError, ValueError) as error:  # pragma: no cover
            _LOG.debug("resume store write failed: %s", error)

    def position_for(self, url: str) -> ResumePoint | None:
        """Where this recording was left, or ``None``."""
        key = stream_identity(url)
        if not key:
            return None
        record = self._read().get(key)
        if not isinstance(record, dict):
            return None
        position = int(record.get("position_ms") or 0)
        if position < MIN_RESUME_MS:
            return None
        return ResumePoint(
            position_ms=position,
            duration_ms=int(record.get("duration_ms") or 0),
            saved_at=float(record.get("saved_at") or 0.0),
            label=str(record.get("label") or ""),
            url=str(record.get("url") or ""),
        )

    def remember(
        self, url: str, position_ms: int, *, duration_ms: int = 0, label: str = ""
    ) -> None:
        """Record where playback reached. Best effort; never raises.

        Clears the entry rather than saving one when you are at the beginning or
        have reached the end -- both of those are "start from the top next
        time", and storing them would mean a resume prompt that is never right.
        """
        key = stream_identity(url)
        if not key:
            return
        entries = self._read()
        finished = duration_ms > 0 and position_ms >= duration_ms - END_MARGIN_MS
        if position_ms < MIN_RESUME_MS or finished:
            if entries.pop(key, None) is not None:
                self._write(entries)
            return
        stored = entries.get(key)
        previous: dict = stored if isinstance(stored, dict) else {}
        entries[key] = {
            "position_ms": int(position_ms),
            "duration_ms": int(duration_ms),
            "saved_at": time.time(),
            # Kept so the recording can be listed and replayed later. A caller
            # that does not know the title must not erase one already stored:
            # positions are saved every few seconds, and the save that happens
            # to come from a place with no title would otherwise blank it.
            "label": str(label or previous.get("label") or ""),
            "url": (url or "").strip(),
        }
        if len(entries) > MAX_ENTRIES:
            # Oldest first; a dict of 500 is small enough to sort outright.
            ordered = sorted(
                entries.items(), key=lambda row: float((row[1] or {}).get("saved_at") or 0.0)
            )
            entries = dict(ordered[-MAX_ENTRIES:])
        self._write(entries)

    def forget(self, url: str) -> None:
        """Drop this recording's position -- what "start from the beginning" does."""
        key = stream_identity(url)
        entries = self._read()
        if key and entries.pop(key, None) is not None:
            self._write(entries)

    def clear(self) -> None:
        """Forget every position (a settings-level reset)."""
        self._write({})

    def count(self) -> int:
        """How many recordings have a saved position (diagnostics)."""
        return len(self._read())

    # -- the QuillSync RecordStore contract ---------------------------------
    #
    # A second store to sync, not a second copy of the first: these are keyed on
    # a normalised stream identity and the media store is keyed on a file's
    # contents, and no key can mean both. So each syncs as its own entity type
    # over its own commit log, sharing one vault key and one remote folder --
    # which is what settles the question the plan left open.

    def get_record(self, entity_id: str) -> dict | None:
        record = self._read().get(entity_id)
        return dict(record) if isinstance(record, dict) else None

    def put_record(self, entity_id: str, record: dict) -> None:
        entries = self._read()
        entries[entity_id] = dict(record)
        self._write(entries)

    def delete_record(self, entity_id: str) -> None:
        entries = self._read()
        if entries.pop(entity_id, None) is not None:
            self._write(entries)

    def entity_ids(self) -> list[str]:
        """Every saved position's key, for an adapter enumerating what to push."""
        return list(self._read())

    def unfinished(self) -> list[ResumePoint]:
        """Every recording with a place to go back to, most recent first.

        The listing half of this store, and the reason ``label`` and ``url``
        are kept: the key is a normalised identity that deliberately cannot be
        turned back into a playable address, so an entry without them can be
        *recognised* when the same stream is opened again but can never be
        offered. Those rows are skipped rather than listed as something that
        would fail when chosen.
        """
        rows: list[ResumePoint] = []
        for record in self._read().values():
            if not isinstance(record, dict):
                continue
            url = str(record.get("url") or "")
            position = int(record.get("position_ms") or 0)
            if not url or position < MIN_RESUME_MS:
                continue
            rows.append(
                ResumePoint(
                    position_ms=position,
                    duration_ms=int(record.get("duration_ms") or 0),
                    saved_at=float(record.get("saved_at") or 0.0),
                    label=str(record.get("label") or ""),
                    url=url,
                )
            )
        return sorted(rows, key=lambda row: row.saved_at, reverse=True)


def merge_resume_points(local: dict | None, remote: dict) -> tuple[dict, list[Conflict]]:
    """Combine two machines' memories of one recording. A QuillSync ``MergeFn``.

    Most recent save wins, by ``saved_at``, matching the media position store's
    policy so "your place follows you" behaves the same whatever you were
    listening to. A real disagreement -- more than
    :data:`CONFLICT_GAP_MS` apart -- is surfaced in words rather than resolved in
    silence, because losing an hour of a fourteen-hour book to a stale save on
    another machine is exactly the thing sync is supposed not to do.

    A label the winner lacks is taken from the loser: only one machine may have
    known what the recording was called, and forgetting it would leave a row
    that cannot be listed.
    """
    from quill.core.sync.protocol import Conflict

    if local is None:
        return dict(remote), []

    local_at = float(local.get("saved_at") or 0.0)
    remote_at = float(remote.get("saved_at") or 0.0)
    local_wins = local_at > remote_at
    winner = dict(local if local_wins else remote)
    loser = remote if local_wins else local
    if not winner.get("label") and loser.get("label"):
        winner["label"] = loser["label"]
    if not winner.get("url") and loser.get("url"):
        winner["url"] = loser["url"]

    local_ms = int(local.get("position_ms") or 0)
    remote_ms = int(remote.get("position_ms") or 0)
    conflicts: list[Conflict] = []
    if abs(local_ms - remote_ms) >= CONFLICT_GAP_MS:
        conflicts.append(
            Conflict(
                entity_id=str(winner.get("url", "")),
                field="position_ms",
                local=spoken_resume(local_ms),
                remote=spoken_resume(remote_ms),
                merged=spoken_resume(int(winner.get("position_ms") or 0)),
                message=(
                    "Two devices remembered different places in "
                    f"{winner.get('label') or 'this recording'}. "
                    "The most recent one was kept."
                ),
            )
        )
    return winner, conflicts


#: How far apart two saved places must be before the difference is worth
#: mentioning. Five minutes, matching ``core/media/positions``: below that it is
#: the same place and saying so is noise.
CONFLICT_GAP_MS = 5 * 60 * 1000
