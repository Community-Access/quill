"""Resume a radio recording across a restart (R3).

The scheduler is in-process, so a clean or crash close loses the live ffmpeg
child and any in-progress recording. This module is the one missing building
block: a persisted *active-recording marker* written when a recording starts and
cleared when it stops cleanly, plus startup reconciliation of the temp dir.

At launch the host (a) moves finished orphan files out of the temp dir to the
destination so a crash no longer strands them, and (b) if a marker is present
and its scheduled end is still within a grace window, offers to resume the
recording for the remaining minutes (or auto-resumes, per the user's remembered
choice). ``last_seen`` is stamped periodically elsewhere so the missed-recording
window stays accurate even after a crash.

wx-free, strict-typed. Persistence is atomic via ``write_json_atomic``.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from quill.core.radio.recording import RECORD_FORMATS, _default_dir, _finalize_move

#: Resume a scheduled/in-progress recording only if its end is within this many
#: minutes of now (settable via the host). Past the grace window the show is
#: effectively over, so we do not bother the user with a "resume 0 minutes?"
#: prompt; the marker is cleared and the orphan (if any) is reconciled.
DEFAULT_RESUME_GRACE_MINUTES = 10

#: A temp-dir file whose mtime is within this many seconds is treated as still
#: being written (an orphan ffmpeg that survived a crash) and is left alone --
#: moving a live file would corrupt it. Older files are finished orphans and
#: are reconciled to the destination.
_STILL_WRITING_SECS = 30

#: Legacy single-marker file (pre-concurrent-recording). Still read at launch
#: so a marker written by an older build is migrated/resumed once, then cleared.
_MARKER_FILE = "radio_active_recording.json"

#: Directory of per-recording markers (concurrent recording): one
#: ``<job_id>.json`` file per in-progress recording, so several simultaneous
#: recordings each persist and clear their own marker with no read-modify-write
#: race on a shared file.
_MARKERS_DIR = "radio_active_recordings"

_RECORDING_SUFFIXES = frozenset(f".{fmt}" for fmt in RECORD_FORMATS)


@dataclass(slots=True)
class ActiveRecordingMarker:
    """The persisted "a recording is in progress" marker (R3).

    Written at :meth:`RadioRecorder.start` and removed on a clean stop. On a
    crash/kill the file remains, so the next launch can offer to resume.
    ``temp_path`` is where ffmpeg is writing (may equal ``output_path`` when no
    temp dir is set); ``output_path`` is where the finished file belongs.
    ``scheduled_end`` is the absolute ISO moment the recording was meant to end
    (``started_at + duration_minutes``), used to compute the remaining minutes.
    ``entry_id`` links back to the schedule entry (empty for a manual recording).
    ``job_id`` is the recorder's own id for the recording (concurrent
    recording): it keys the marker's own file so several simultaneous
    recordings each persist their own marker instead of one clobbering the
    rest.
    """

    station_name: str
    stream_url: str
    temp_path: str
    output_path: str
    started_at: str  # ISO datetime
    scheduled_end: str  # ISO datetime
    duration_minutes: int
    entry_id: str = ""
    job_id: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ActiveRecordingMarker | None:
        try:
            raw_duration = data.get("duration_minutes", 0)
            duration = int(raw_duration) if isinstance(raw_duration, (int, float, str)) else 0
            return cls(
                station_name=str(data.get("station_name", "") or ""),
                stream_url=str(data.get("stream_url", "") or ""),
                temp_path=str(data.get("temp_path", "") or ""),
                output_path=str(data.get("output_path", "") or ""),
                started_at=str(data.get("started_at", "") or ""),
                scheduled_end=str(data.get("scheduled_end", "") or ""),
                duration_minutes=duration,
                entry_id=str(data.get("entry_id", "") or ""),
                job_id=str(data.get("job_id", "") or ""),
            )
        except (TypeError, ValueError):
            return None

    @property
    def started(self) -> datetime | None:
        return _parse_iso(self.started_at)

    @property
    def end(self) -> datetime | None:
        return _parse_iso(self.scheduled_end)


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _marker_path(data_dir: Path) -> Path:
    return data_dir / _MARKER_FILE


def _markers_dir(data_dir: Path) -> Path:
    return data_dir / _MARKERS_DIR


def _safe_key(key: str) -> str:
    """A filesystem-safe file stem for a marker key (job/entry id).

    Job ids are uuid hex, so this is normally a no-op; it only guards against a
    stray separator making the path escape the markers directory.
    """
    cleaned = "".join(ch for ch in key if ch.isalnum() or ch in ("-", "_"))
    return cleaned or "recording"


def _marker_key(marker: ActiveRecordingMarker) -> str:
    """The storage key for *marker*: its recorder job id, else its schedule
    entry id, else a stable fallback derived from the output path."""
    return marker.job_id or marker.entry_id or _safe_key(marker.output_path or marker.stream_url)


def load_marker(data_dir: Path) -> ActiveRecordingMarker | None:
    """Read one active-recording marker (``None`` if none): the first of
    :func:`load_markers`. Kept for single-recording call sites and tests."""
    markers = load_markers(data_dir)
    return markers[0] if markers else None


def load_markers(data_dir: Path) -> list[ActiveRecordingMarker]:
    """Every active-recording marker (concurrent recording), earliest first.

    Reads each ``<job_id>.json`` in the markers directory and, for migration,
    the legacy single-marker file if it is still present -- so a marker written
    by an older single-recording build is still found and resumed once. Corrupt
    or unreadable files are skipped, never fatal.
    """
    markers: list[ActiveRecordingMarker] = []
    directory = _markers_dir(data_dir)
    try:
        files = sorted(directory.glob("*.json"))
    except OSError:
        files = []
    for path in files:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(raw, dict):
            continue
        marker = ActiveRecordingMarker.from_dict(raw)
        if marker is not None and marker.stream_url:
            markers.append(marker)
    # Migration: a legacy single-marker file from an older build.
    try:
        raw = json.loads(_marker_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = None
    if isinstance(raw, dict):
        legacy = ActiveRecordingMarker.from_dict(raw)
        if legacy is not None and legacy.stream_url:
            markers.append(legacy)
    markers.sort(key=lambda m: m.started_at)
    return markers


def save_marker(data_dir: Path, marker: ActiveRecordingMarker) -> None:
    """Persist *marker* atomically to its own ``<key>.json`` (recorder start
    path). The key is the recording's job id, so several simultaneous
    recordings never overwrite each other's marker."""
    from quill.core.storage import write_json_atomic

    directory = _markers_dir(data_dir)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    write_json_atomic(directory / f"{_safe_key(_marker_key(marker))}.json", marker.to_dict())


def clear_marker(data_dir: Path, key: str | ActiveRecordingMarker | None = None) -> None:
    """Remove one marker on a clean stop; absent is not an error.

    *key* may be a job/entry id string, a marker (its key is used), or ``None``.
    A ``None`` key clears the legacy single-marker file only (back-compat for
    the old no-argument clear); a per-recording marker is always cleared by id.
    """
    targets: list[Path] = []
    if key is None:
        targets.append(_marker_path(data_dir))
    else:
        stem = _marker_key(key) if isinstance(key, ActiveRecordingMarker) else str(key)
        targets.append(_markers_dir(data_dir) / f"{_safe_key(stem)}.json")
    for path in targets:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            # Best-effort: a marker we cannot clear just becomes stale; the next
            # launch reconciles the orphan and re-clears it.
            pass


def clear_all_markers(data_dir: Path) -> None:
    """Remove every marker -- per-recording files and the legacy single file
    (the clean-close path: nothing to resume next launch)."""
    directory = _markers_dir(data_dir)
    try:
        files = list(directory.glob("*.json"))
    except OSError:
        files = []
    for path in files:
        try:
            path.unlink()
        except OSError:
            pass
    clear_marker(data_dir, None)


def remaining_minutes(marker: ActiveRecordingMarker, now: datetime | None = None) -> int:
    """Minutes left until the marker's scheduled end, floored at 0 (R3).

    A resume past the end yields 0 (the show is over); the host treats 0 as
    "do not resume". A marker with an unparseable end yields 0.
    """
    end = marker.end
    if end is None:
        return 0
    if now is None:
        now = datetime.now()
    end_abs = end if end.tzinfo is not None else end.astimezone()
    now_abs = now if now.tzinfo is not None else now.astimezone()
    left = math.ceil((end_abs - now_abs).total_seconds() / 60)
    return max(0, left)


def within_resume_grace(
    marker: ActiveRecordingMarker,
    now: datetime | None = None,
    grace_minutes: int = DEFAULT_RESUME_GRACE_MINUTES,
) -> bool:
    """True if the marker's end is still ahead or within *grace_minutes* past now.

    Resume is offered while the show has time left, or just ended (the user may
    have restarted moments after a crash). Past the grace window the recording
    is gone and we silently reconcile instead of prompting.
    """
    end = marker.end
    if end is None:
        return False
    if now is None:
        now = datetime.now()
    end_abs = end if end.tzinfo is not None else end.astimezone()
    now_abs = now if now.tzinfo is not None else now.astimezone()
    return (end_abs - now_abs) >= -timedelta(minutes=max(0, grace_minutes))


def reconcile_temp_strays(settings: object, *, now: datetime | None = None) -> list[Path]:
    """Move finished orphan recording files from the temp dir to the destination
    (R3/12, R3/13.6). Returns the files moved, earliest first.

    Only files whose mtime is older than :data:`_STILL_WRITING_SECS` are moved,
    so a file an orphaned ffmpeg is still writing is left intact. Files already
    in the destination are untouched. A temp dir that equals the destination
    (or none set) is a no-op. Name collisions in the destination are uniquified
    via :func:`_finalize_move` so an orphan never clobbers an existing recording.
    """
    temp_root = getattr(settings, "temp_dir", "") or ""
    if not temp_root:
        return []
    temp_dir = Path(temp_root)
    dest_root_str = str(getattr(settings, "destination_root", "") or "")
    dest_root = Path(dest_root_str) if dest_root_str else _default_dir()
    if temp_dir == dest_root:
        return []
    if not temp_dir.is_dir():
        return []
    if now is None:
        now = datetime.now()
    cutoff = now - timedelta(seconds=_STILL_WRITING_SECS)
    moved: list[Path] = []
    try:
        candidates = sorted(temp_dir.iterdir())
    except OSError:
        return []
    dest_root.mkdir(parents=True, exist_ok=True)
    for path in candidates:
        if not path.is_file() or path.suffix.lower() not in _RECORDING_SUFFIXES:
            continue
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            continue
        if mtime >= cutoff:
            continue  # still being written
        target = dest_root / path.name
        landed = _finalize_move(path, target)
        moved.append(landed)
    moved.sort(key=lambda p: p.name)
    return moved
