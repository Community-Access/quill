"""The recordings shelf: everything Internet Radio has recorded, is
recording, or plans to record -- one wx-free status model for the
Recordings Manager dialog.

Completed recordings are simply the audio files in the recordings folder
(the ``destination_root`` from
:class:`~quill_radio_mac.core.recording.RecordingSettings`, default
``<data_dir>/radio_recordings``); the active recording is whichever file
the :class:`~quill_radio_mac.core.recording.RadioRecorder` is writing
right now; scheduled entries come from
:class:`~quill_radio_mac.core.recording_schedule.RecordingScheduler`.

Ported near-verbatim from upstream ``quill.core.radio.recordings_index``.

Strict-typed, no wx.

Threading contract: pure functions and a plain dataclass; the filesystem
scan in :func:`list_recordings` does synchronous IO and should be called
off the UI thread (via the task manager) exactly like any other disk
scan in this app.

macOS notes: none -- fully platform-neutral.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from quill_radio_mac.core.recording import RECORD_FORMATS

#: Every extension a recording can have (RECORD_FORMATS) -- the scan is
#: deliberately limited to formats this app itself writes, so unrelated
#: files a user keeps in the same folder never show up as "recordings".
_RECORDING_SUFFIXES = frozenset(f".{fmt}" for fmt in RECORD_FORMATS)

STATUS_RECORDING = "Recording"
STATUS_RECORDED = "Recorded"
STATUS_SCHEDULED = "Scheduled"


@dataclass(slots=True)
class RecordingEntry:
    """One row of the Recordings Manager."""

    name: str
    status: str  # STATUS_RECORDING / STATUS_RECORDED / STATUS_SCHEDULED
    path: Path | None  # None for scheduled entries (no file yet)
    size_bytes: int = 0
    modified: datetime | None = None
    detail: str = ""  # scheduled time, station name, ...

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
        if self.modified is not None:
            parts.append(self.modified.strftime("%Y-%m-%d %H:%M"))
        if self.detail:
            parts.append(self.detail)
        return ", ".join(parts)


def recordings_dir(settings: object) -> Path:
    """The folder recordings land in for *settings* (RecordingSettings)."""
    from quill_radio_mac.core.recording import _default_dir

    root = str(getattr(settings, "destination_root", "") or "")
    return Path(root) if root else _default_dir()


def list_recordings(
    settings: object,
    *,
    active_path: Path | None = None,
    scheduled: list[object] | None = None,
) -> list[RecordingEntry]:
    """Every recording row: active first, then files newest-first, then
    scheduled entries. A missing folder reads as no completed recordings."""
    entries: list[RecordingEntry] = []
    folder = recordings_dir(settings)
    active_resolved = active_path.resolve() if active_path is not None else None

    files: list[tuple[float, RecordingEntry]] = []
    try:
        candidates = sorted(folder.iterdir())
    except OSError:
        candidates = []
    for path in candidates:
        if not path.is_file() or path.suffix.lower() not in _RECORDING_SUFFIXES:
            continue
        try:
            stat = path.stat()
            size = int(stat.st_size)
            modified = datetime.fromtimestamp(stat.st_mtime)
        except OSError:
            size, modified = 0, None
        is_active = active_resolved is not None and path.resolve() == active_resolved
        entry = RecordingEntry(
            name=path.stem,
            status=STATUS_RECORDING if is_active else STATUS_RECORDED,
            path=path,
            size_bytes=size,
            modified=modified,
            detail="writing now" if is_active else "",
        )
        if is_active:
            entries.append(entry)  # active recording always leads the list
        else:
            files.append((stat.st_mtime if modified else 0.0, entry))
    files.sort(key=lambda pair: pair[0], reverse=True)
    entries.extend(entry for _mtime, entry in files)

    for item in scheduled or []:
        if not bool(getattr(item, "enabled", True)):
            continue
        station = str(getattr(item, "station_name", "") or "Scheduled recording")
        recurrence = str(getattr(item, "recurrence", "once"))
        run_at = str(getattr(item, "run_at", "")).replace("T", " ")
        if recurrence == "once":
            detail = f"once at {run_at}" if run_at else "once"
        else:
            time_part = run_at.split(" ")[-1] if run_at else ""
            detail = f"{recurrence} at {time_part}".strip()
        entries.append(
            RecordingEntry(name=station, status=STATUS_SCHEDULED, path=None, detail=detail)
        )
    return entries
