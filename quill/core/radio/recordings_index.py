"""The recordings shelf: everything Internet Radio has recorded, is
recording, or plans to record -- one wx-free status model for the
Recordings Manager (embedded QUILL and standalone Quill Radio alike).

Completed recordings are simply the audio files in the recordings folder
(the ``destination_root`` from :class:`~quill.core.radio.recording.
RecordingSettings`, default ``~/Music/Quill Radio Recordings``); the active
recording is whichever file the :class:`RadioRecorder` is writing right now
-- found by identity, not by folder, so a recording writing to a temp dir
still shows as "Recording" (R1/quill-radio #8, the temp-dir invisibility
bug); scheduled entries come from the :class:`RecordingScheduler`.

Strict-typed, no wx.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from quill.core.radio.recording import RECORD_FORMATS

#: Every extension a recording can have (RECORD_FORMATS) -- the scan is
#: deliberately limited to formats QUILL itself writes, so unrelated files
#: a user keeps in the same folder never show up as "recordings".
_RECORDING_SUFFIXES = frozenset(f".{fmt}" for fmt in RECORD_FORMATS)

STATUS_RECORDING = "Recording"
STATUS_RECORDED = "Recorded"
STATUS_SCHEDULED = "Scheduled"
#: A one-time schedule that already ran (R1/10.1): shown so the dialog stops
#: claiming "N scheduled" forever, but excluded from the scheduled count and
#: not double-counted. A successful once-fire also auto-disables the entry
#: (R2), so this status is mostly seen for legacy schedules saved before that.
STATUS_COMPLETED = "Completed"


@dataclass(slots=True)
class ActiveRecording:
    """A recording being written right now, by identity (R1/10.3).

    Passed to :func:`list_recordings` instead of a bare path so the active
    row can be found even when it lives in a temp dir the folder scan never
    reaches, and so a firing schedule whose stream is the one recording is
    not also double-listed as "Scheduled" (10.2). ``path`` may be ``None``
    only when ``station_name``/``stream_url`` still identify the recording.
    ``job_id`` (concurrent recording) is the recorder's id for this recording,
    carried onto the row so the Recordings dialog's Stop button can target this
    exact capture when several are running.
    """

    path: Path | None
    station_name: str = ""
    stream_url: str = ""
    started_at: datetime | None = None
    job_id: str = ""


@dataclass(slots=True)
class RecordingEntry:
    """One row of the Recordings Manager."""

    #: Stable identity for in-place refresh (R1/9): the resolved file path
    #: for recorded/recording rows, ``"schedule:<id>"`` for scheduled ones.
    #: The dialog keys its diff by this so a row never loses its place when
    #: the status flips (Recording -> Recorded) or the size grows.
    id: str
    name: str
    status: str  # STATUS_RECORDING / STATUS_RECORDED / STATUS_SCHEDULED / STATUS_COMPLETED
    path: Path | None  # None for scheduled entries (no file yet)
    size_bytes: int = 0
    modified: datetime | None = None
    detail: str = ""  # scheduled time, station name, ...
    #: When the active recording started (R1/10.4): the dialog ticks an
    #: elapsed readout from this. ``None`` for non-active rows.
    started_at: datetime | None = None
    #: The recorder job id for a Recording row (concurrent recording), so the
    #: dialog's Stop button can stop this exact recording. Empty for other rows.
    job_id: str = ""

    @property
    def size_display(self) -> str:
        if self.path is None:
            return ""
        size = float(self.size_bytes)
        for unit in ("bytes", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:,.0f} {unit}" if unit == "bytes" else f"{size:,.1f} {unit}"
            size /= 1024
        return ""

    @property
    def spoken_summary(self) -> str:
        """One line for the details pane / announcements."""
        parts = [self.name, self.status.lower()]
        if self.size_bytes:
            parts.append(self.size_display)
        if self.started_at is not None:
            parts.append(f"elapsed {format_elapsed(self.started_at, datetime.now())}")
        elif self.modified is not None:
            parts.append(self.modified.strftime("%Y-%m-%d %H:%M"))
        if self.detail:
            parts.append(self.detail)
        return ", ".join(parts)


def format_elapsed(started_at: datetime, now: datetime | None = None) -> str:
    """``MM:SS`` (or ``H:MM:SS`` past an hour) since *started_at* (R1/10.4).

    Tolerant of naive/aware mismatches: a naive ``started_at`` is treated as
    local, the same frame :meth:`RadioRecorder.start` stamps it in. Pure and
    unit-tested so the dialog's per-second tick has no surprises.
    """
    if now is None:
        now = datetime.now()
    start = started_at if started_at.tzinfo is not None else started_at.astimezone()
    end = now if now.tzinfo is not None else now.astimezone()
    delta = max(timedelta(0), end - start)
    total = int(delta.total_seconds())
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def recordings_dir(settings: object) -> Path:
    """The folder recordings land in for *settings* (RecordingSettings)."""
    from quill.core.radio.recording import _default_dir

    root = str(getattr(settings, "destination_root", "") or "")
    return Path(root) if root else _default_dir()


def _zone_offset_label(timezone: str, when: datetime) -> str:
    """A short, unambiguous label for *timezone* at *when*, e.g. ``UTC-4``.

    Empty for local time (no label needed); a bad zone name degrades to empty
    so a corrupt record never crashes the index. Used so a scheduled entry's
    wall-clock time reads correctly in the Recordings dialog even when the
    machine is in a different zone than the entry (R1/10.6).
    """
    if not timezone:
        return ""
    try:
        zone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return ""
    when_abs = when if when.tzinfo is not None else when.astimezone()
    offset = when_abs.astimezone(zone).utcoffset()
    if offset is None:
        return ""
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    label = f"UTC{sign}{hours}"
    return f"{label}:{minutes:02d}" if minutes else label


def _schedule_detail(item: object, *, now: datetime) -> str:
    """The "When"-column detail for a scheduled entry, zone-labeled (10.6).

    Just the recurrence + time + zone label -- the station name lives in the
    Name column, so the When column stays narrow and the spoken summary does
    not repeat it.
    """
    recurrence = str(getattr(item, "recurrence", "once"))
    run_at = str(getattr(item, "run_at", "")).replace("T", " ")
    timezone = str(getattr(item, "timezone", "") or "")
    zone_label = _zone_offset_label(timezone, now)
    zone_suffix = f" ({zone_label})" if zone_label else ""
    if recurrence == "once":
        return f"once at {run_at}{zone_suffix}" if run_at else f"once{zone_suffix}"
    time_part = run_at.split(" ")[-1] if run_at else ""
    return f"{recurrence} at {time_part}{zone_suffix}".strip()


def list_recordings(
    settings: object,
    *,
    active: ActiveRecording | list[ActiveRecording] | None = None,
    scheduled: list[object] | None = None,
    now: datetime | None = None,
) -> list[RecordingEntry]:
    """Every recording row: active first, then files newest-first, then
    scheduled entries. A missing folder reads as no completed recordings.

    *active* may be a single :class:`ActiveRecording`, a list of them
    (concurrent recording -- one row per running recording, oldest first), or
    ``None``. Each active recording is found by identity (R1/10.3): it is always
    shown, even when it is writing to a temp dir the folder scan never reaches.
    A firing schedule whose stream is any of the recordings is suppressed from
    the scheduled list so it is not double-counted (10.2). A one-time schedule
    that already ran shows as ``Completed`` and is excluded from the scheduled
    count (10.1).
    """
    if now is None:
        now = datetime.now()
    entries: list[RecordingEntry] = []
    folder = recordings_dir(settings)
    if active is None:
        actives: list[ActiveRecording] = []
    elif isinstance(active, ActiveRecording):
        actives = [active]
    else:
        actives = list(active)

    # The resolved paths and stream URLs of every active recording, so the
    # folder scan never re-lists an active file and a firing schedule is not
    # double-listed as Scheduled while its stream is recording (10.2).
    active_resolved_paths: set[Path] = set()
    active_urls: set[str] = set()

    # Active recordings lead the list, each found by path even when it lives in
    # a temp dir the folder scan below never reaches (R1/10.3).
    for item in actives:
        if item.stream_url:
            active_urls.add(item.stream_url)
        item_path = item.path
        if item_path is None:
            continue
        resolved = item_path.resolve()
        active_resolved_paths.add(resolved)
        size, modified = _stat(item_path)
        entries.append(
            RecordingEntry(
                id=str(resolved),
                name=(item.station_name or item_path.stem),
                status=STATUS_RECORDING,
                path=item_path,
                size_bytes=size,
                modified=modified,
                detail="writing now",
                started_at=item.started_at,
                job_id=item.job_id,
            )
        )

    files: list[tuple[float, RecordingEntry]] = []
    try:
        candidates = sorted(folder.iterdir())
    except OSError:
        candidates = []
    for path in candidates:
        if not path.is_file() or path.suffix.lower() not in _RECORDING_SUFFIXES:
            continue
        resolved = path.resolve()
        # An active file is already a leading row; never also emit it as
        # Recorded (which would double-list it, and on a same-volume temp dir
        # could even match the scan).
        if resolved in active_resolved_paths:
            continue
        try:
            stat = path.stat()
            size = int(stat.st_size)
            modified = datetime.fromtimestamp(stat.st_mtime)
        except OSError:
            size, modified = 0, None
            stat = None
        files.append((
            stat.st_mtime if stat and modified else 0.0,
            RecordingEntry(
                id=str(resolved),
                name=path.stem,
                status=STATUS_RECORDED,
                path=path,
                size_bytes=size,
                modified=modified,
            ),
        ))
    files.sort(key=lambda pair: pair[0], reverse=True)
    entries.extend(entry for _mtime, entry in files)

    for sched_item in scheduled or []:
        if not bool(getattr(sched_item, "enabled", True)):
            continue
        entry_id = str(getattr(sched_item, "id", "") or "")
        identity = f"schedule:{entry_id}" if entry_id else ""
        recurrence = str(getattr(sched_item, "recurrence", "once"))
        last_fired = str(getattr(sched_item, "last_fired_date", "") or "")
        # A one-time schedule that already ran is Completed, not Scheduled --
        # it must stop counting toward "N scheduled" (R1/10.1). R2 also
        # auto-disables a once entry on success, so this is the legacy path.
        if recurrence == "once" and last_fired:
            entries.append(
                RecordingEntry(
                    id=identity,
                    name=str(getattr(sched_item, "station_name", "") or "Scheduled recording"),
                    status=STATUS_COMPLETED,
                    path=None,
                    detail=f"completed -- ran {last_fired}",
                )
            )
            continue
        # While this stream is one of the recordings, the firing schedule is a
        # Recording row above -- do not also list it as Scheduled (10.2).
        item_url = str(getattr(sched_item, "stream_url", "") or "")
        if item_url and item_url in active_urls:
            continue
        entries.append(
            RecordingEntry(
                id=identity,
                name=str(getattr(sched_item, "station_name", "") or "Scheduled recording"),
                status=STATUS_SCHEDULED,
                path=None,
                detail=_schedule_detail(sched_item, now=now),
            )
        )
    return entries


def _stat(path: Path | None) -> tuple[int, datetime | None]:
    """Best-effort size/modified for *path*; (0, None) if unreadable."""
    if path is None:
        return 0, None
    try:
        stat = path.stat()
        return int(stat.st_size), datetime.fromtimestamp(stat.st_mtime)
    except OSError:
        return 0, None
