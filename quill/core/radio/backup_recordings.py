"""The recordings half of a Quill Radio backup: sizing, copying, restoring.

Split from :mod:`quill.core.radio.backup` (GATE-11) when the backup learned to
name what it leaves out (2026-10-04). Everything here is about the recorded
audio, which is the one part of a backup that can be large, can live in a
OneDrive folder, and can be in use by another program -- so every function
returns a :class:`~quill.core.skipped_files.SkippedFile` rather than skipping
quietly.

**OneDrive Files On-Demand.** ``os.stat`` reads a placeholder's size and cloud
attributes without downloading it, so :func:`plan_recordings` can say "40
recordings, 3.2 GB, 12 of them only in OneDrive" before anything is read.
:func:`copy_recording` then *reads* a placeholder through once before writing
it into the zip: that read is what asks Windows to download it, and a download
that fails part-way leaves nothing half-written in the backup.

Pure filesystem I/O, wx-free.
"""

from __future__ import annotations

import os
import shutil
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from quill.core.skipped_files import (
    REASON_ALREADY_THERE,
    REASON_CLOUD_ONLY,
    REASON_UNREADABLE,
    SkippedFile,
    classify_error,
    is_cloud_only,
)

__all__ = [
    "RECORDINGS_PREFIX",
    "RecordingsPlan",
    "StatFn",
    "copy_recording",
    "free_bytes",
    "plan_recordings",
    "restore_recording",
]

StatFn = Callable[[Path], os.stat_result]

RECORDINGS_PREFIX = "recordings/"
#: Never carried as "recordings": a backup inside a backup is how a folder
#: shared between recordings and backups (one OneDrive "quill" folder) doubles
#: in size every night.
_NOT_RECORDINGS = frozenset({".qrbackup", ".qcbackup", ".quillsetup", ".tmp", ".partial"})
_NOT_RECORDING_NAMES = frozenset({"desktop.ini", "thumbs.db"})
_CHUNK = 1024 * 1024


@dataclass(frozen=True, slots=True)
class RecordingsPlan:
    """The recordings a backup would carry, sized before asking."""

    folder: Path
    files: tuple[Path, ...] = ()
    total_bytes: int = 0
    cloud_only: int = 0
    cloud_bytes: int = 0

    def question(self) -> str:
        """The include-recordings prompt, with the numbers that decide it."""
        count = len(self.files)
        noun = "recording" if count == 1 else "recordings"
        lines = [
            f"Include your {count} {noun} ({_size(self.total_bytes)}) in the backup? "
            f"They are in {self.folder}."
        ]
        if self.cloud_only:
            lines.append(
                f"{self.cloud_only} of them are stored only in OneDrive "
                f"({_size(self.cloud_bytes)}); Quill Radio will ask Windows to download "
                "them while it backs up, which needs an internet connection."
            )
        lines.append("Choose No to back up just your stations, podcasts and settings.")
        return "\n\n".join(lines)


def _size(count: int) -> str:
    if count >= 1024**3:
        return f"{count / 1024**3:.1f} GB"
    if count >= 1024**2:
        return f"{count / 1024**2:.0f} MB"
    return f"{max(count, 0) // 1024} KB"


def _is_recording_candidate(path: Path) -> bool:
    name = path.name
    if name.startswith((".", "~")) or name.lower() in _NOT_RECORDING_NAMES:
        return False
    return path.suffix.lower() not in _NOT_RECORDINGS


def plan_recordings(
    folder: Path | None,
    *,
    exclude: Path | None = None,
    stat: StatFn | None = None,
) -> RecordingsPlan:
    """Size up the recordings in *folder* (top level only) without reading them.

    ``os.stat`` on a OneDrive placeholder reports its full size and its cloud
    attributes without downloading it, so this is cheap even for a folder
    that is entirely in the cloud.
    """
    if folder is None:
        return RecordingsPlan(folder=Path())
    root = Path(folder)
    try:
        entries = sorted(root.iterdir())
    except OSError:
        return RecordingsPlan(folder=root)
    files: list[Path] = []
    total = cloud = cloud_bytes = 0
    skip_path = exclude.resolve() if exclude is not None else None
    for path in entries:
        try:
            if not path.is_file() or not _is_recording_candidate(path):
                continue
            if skip_path is not None and path.resolve() == skip_path:
                continue
            size = int((stat(path) if stat is not None else path.stat()).st_size)
        except OSError:
            size = 0
        files.append(path)
        total += size
        if is_cloud_only(path, stat=stat):
            cloud += 1
            cloud_bytes += size
    return RecordingsPlan(
        folder=root,
        files=tuple(files),
        total_bytes=total,
        cloud_only=cloud,
        cloud_bytes=cloud_bytes,
    )


def free_bytes(folder: Path) -> int:
    try:
        return int(shutil.disk_usage(folder).free)
    except OSError:
        return 0


def copy_recording(
    zf: zipfile.ZipFile, path: Path, *, cloud: bool, stat: StatFn | None
) -> tuple[SkippedFile | None, bool]:
    """Copy one recording in. Returns ``(skipped, incomplete)``.

    A OneDrive-only file is read through once before anything is written --
    that read *is* the download -- so a download that fails leaves nothing
    half-written in the zip. A local file streams straight in.
    """
    try:
        src = open(path, "rb")  # noqa: SIM115 - closed below on every path
    except OSError as exc:
        return SkippedFile(path.name, classify_error(exc, path, stat=stat), str(exc)), False
    with src:
        try:
            if cloud:
                while src.read(_CHUNK):
                    pass
                src.seek(0)
            first = src.read(_CHUNK)
        except OSError as exc:
            reason = REASON_CLOUD_ONLY if cloud else classify_error(exc, path, stat=stat)
            return SkippedFile(path.name, reason, str(exc)), False
        info = zipfile.ZipInfo.from_file(path, RECORDINGS_PREFIX + path.name)
        info.compress_type = zipfile.ZIP_STORED  # audio does not compress
        # A write failure is the backup's own file and propagates (the whole
        # backup fails); a read failure half-way is this recording's, and is
        # recorded so a restore never writes the half that made it in.
        read_error: OSError | None = None
        with zf.open(info, "w", force_zip64=True) as out:
            out.write(first)
            while True:
                try:
                    chunk = src.read(_CHUNK)
                except OSError as exc:
                    read_error = exc
                    break
                if not chunk:
                    break
                out.write(chunk)
        if read_error is not None:
            return SkippedFile(path.name, REASON_UNREADABLE, str(read_error)), True
    return None, False


def restore_recording(
    zf: zipfile.ZipFile, info: zipfile.ZipInfo, target: Path, stat: StatFn | None
) -> SkippedFile | None:
    try:
        if target.is_file() and target.stat().st_size == info.file_size:
            return SkippedFile(target.name, REASON_ALREADY_THERE)
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, open(target, "wb") as out:
            shutil.copyfileobj(src, out, _CHUNK)
    except OSError as exc:
        return SkippedFile(target.name, classify_error(exc, target, stat=stat), str(exc))
    return None
