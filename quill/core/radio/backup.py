"""Back up and restore a listener's Quill Radio data as one portable zip.

For moving to a new device (a BrailleNote Evolve, a new PC) or after an OS
reinstall (#1193): :func:`create_backup_report` bundles the JSON state files a
Radio listener builds up -- favorites, settings, podcast subscriptions, notes,
tags, schedules -- and, optionally, the recorded audio, into a single
``.qrbackup`` zip with a manifest. :func:`restore_backup` validates and restores
them into the data dir.

File-level (it copies the JSON verbatim rather than re-serialising), so a backup
made by one version restores cleanly into another. Pure filesystem I/O, wx-free,
fully testable. Safe on restore: only the known state filenames are accepted and
every entry is checked against zip-slip before extraction.

**Nothing is left out without a name and a reason** (2026-10-04). A listener
about to reset two computers heard "some items were skipped" and had no way to
learn whether that meant their favorites. So:

* The three things nobody can rebuild -- favorite stations, settings, podcast
  subscriptions -- are :attr:`RadioDataFile.essential`. If one exists and cannot
  be read, the backup **fails** and says which and why; it never saves a file
  that looks like a backup and is missing them. The finished zip is re-read
  before success is reported.
* Every other file left out (a recording OneDrive has not downloaded, one in
  use, one past the path limit) is a :class:`~quill.core.skipped_files.SkippedFile`
  in :attr:`BackupReport.skipped`, which the window can list.
* Recordings stored only in OneDrive are **read**, which is what asks Windows
  to download them, rather than skipped -- unless there is not enough free space
  to hold them, which is said in those words.
"""

from __future__ import annotations

import json
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.radio.backup_recordings import (
    RECORDINGS_PREFIX,
    RecordingsPlan,
    StatFn,
    copy_recording,
    plan_recordings,
    restore_recording,
)
from quill.core.radio.backup_recordings import free_bytes as default_free_bytes
from quill.core.skipped_files import (
    REASON_NO_SPACE_TO_DOWNLOAD,
    SkippedFile,
    classify_error,
    is_cloud_only,
    what_to_do,
)


@dataclass(frozen=True, slots=True)
class RadioDataFile:
    """One state file a backup carries, in the words a listener would use."""

    filename: str
    label: str
    #: Losing it would lose something the listener built by hand. A backup
    #: that cannot read an essential file that exists fails rather than saving.
    essential: bool = False


#: Everything a Radio backup carries. Order is stable so a backup lists them
#: predictably. A file that is not present yet (no schedule set, no podcast
#: followed) is simply not on this computer and is named as such, not an error.
RADIO_DATA: tuple[RadioDataFile, ...] = (
    RadioDataFile("radio_favorites.json", "favorite stations, folders and saved places", True),
    RadioDataFile("radio_history.json", "Quill Radio settings and recently played", True),
    RadioDataFile(
        "podcasts_library.json",
        "podcast subscriptions and where you are in each episode",
        True,
    ),
    RadioDataFile("radio-station-tags.json", "station tags"),
    RadioDataFile("item-notes.json", "notes on stations and podcasts"),
    RadioDataFile("media_bookmarks.json", "bookmarks"),
    RadioDataFile("radio-listens.json", "places in podcasts played from Radio"),
    RadioDataFile("radio-go-to.json", "Go To list"),
    RadioDataFile("radio_recording_settings.json", "recording settings and recordings folder"),
    RadioDataFile("radio_recording_schedule.json", "scheduled recordings"),
    RadioDataFile("radio_wake_timer.json", "wake timer"),
    RadioDataFile("radio-reminders.json", "reminders"),
    RadioDataFile("radio-youtube-saved.json", "saved YouTube rows"),
    RadioDataFile("radio-youtube-channels.json", "followed YouTube channels"),
    RadioDataFile("radio-my-servers.json", "own streaming servers"),
    RadioDataFile("radio-local-media.json", "Local Media list"),
    RadioDataFile("radio_quick_actions.json", "Quick Actions"),
    RadioDataFile("radio-actions.json", "row-action order"),
    RadioDataFile("radio_downloads.json", "download preferences"),
    RadioDataFile("quiet-hours.json", "quiet hours"),
)

#: The filenames alone (what a restore accepts).
RADIO_DATA_FILES: tuple[str, ...] = tuple(item.filename for item in RADIO_DATA)

#: What an update snapshot copies: Radio's own files only. The snapshot's
#: restore must never put back QUILL Cast's podcast library from the moment
#: somebody joined a beta, so the shared files are left to Cast's own copy.
SNAPSHOT_DATA_FILES: tuple[str, ...] = (
    "radio_favorites.json",
    "radio_history.json",
    "radio_wake_timer.json",
    "radio_recording_schedule.json",
    "radio-station-tags.json",
)

_BY_NAME = {item.filename: item for item in RADIO_DATA}

BACKUP_SUFFIX = ".qrbackup"
_MANIFEST_NAME = "quill-radio-backup.json"
_DATA_PREFIX = "data/"
_SCHEMA_VERSION = 1
_APP_TAG = "quill-radio"
#: Head-room kept free when downloading OneDrive-only recordings.
_SPACE_MARGIN = 512 * 1024 * 1024

ProgressCallback = Callable[[int, int, str], None]


class RadioBackupError(CodedError):
    """A backup could not be created, or a restore file was invalid."""

    code = "QUILL-RADIO-BACKUP-FAILED"


@dataclass(frozen=True, slots=True)
class RestoreResult:
    """What a restore actually put back, and what it left alone and why."""

    data_files: tuple[str, ...] = ()
    recordings: tuple[str, ...] = ()
    skipped: tuple[SkippedFile, ...] = ()


@dataclass(slots=True)
class BackupManifest:
    """The manifest embedded in a backup zip (also what :func:`read_manifest`
    returns for a preview before restoring)."""

    schema: int = _SCHEMA_VERSION
    app: str = _APP_TAG
    app_version: str = ""
    created: str = ""
    data_files: list[str] = field(default_factory=list)
    recordings: int = 0
    #: Recordings named in the backup but not complete in it (a read failed
    #: half-way); a restore leaves them out rather than writing half a file.
    incomplete: list[str] = field(default_factory=list)
    #: What the backup left out, as ``{"name", "reason"}`` rows.
    skipped: list[dict[str, str]] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(
            {
                "schema": self.schema,
                "app": self.app,
                "app_version": self.app_version,
                "created": self.created,
                "data_files": self.data_files,
                "recordings": self.recordings,
                "incomplete": self.incomplete,
                "skipped": self.skipped,
            },
            indent=2,
        )


@dataclass(frozen=True, slots=True)
class BackupReport:
    """What a finished backup holds, and what it left out."""

    path: Path
    data_files: tuple[str, ...] = ()
    #: Labels of state files this computer has never made (nothing to lose).
    absent: tuple[str, ...] = ()
    recordings: tuple[str, ...] = ()
    recordings_eligible: int = 0
    skipped: tuple[SkippedFile, ...] = ()
    #: OneDrive-only recordings that were downloaded so they could be copied.
    downloaded: int = 0

    def holds(self) -> str:
        """What is in the backup, as one sentence."""
        labels = [_BY_NAME[name].label for name in self.data_files if name in _BY_NAME]
        parts = ", ".join(labels) if labels else "no settings files"
        recs = ""
        if self.recordings_eligible:
            recs = (
                f" It also holds {len(self.recordings)} of your "
                f"{self.recordings_eligible} recordings."
            )
        return f"The backup holds your {parts}.{recs}"

    def outcome(self) -> str:
        """The spoken result: where it went, counted, and what was left out."""
        lead = f"Backup saved to {self.path.name}."
        if not self.skipped:
            noun = "recording was" if self.downloaded == 1 else "recordings were"
            fetched = (
                f" {self.downloaded} {noun} downloaded from OneDrive first."
                if self.downloaded
                else ""
            )
            return f"{lead} {self.holds()}{fetched}"
        count = len(self.skipped)
        noun = "file was" if count == 1 else "files were"
        return f"{lead} {self.holds()} {count} {noun} left out. " + " ".join(
            what_to_do(self.skipped)
        )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _read_data_files(
    data_dir: Path, names: tuple[str, ...], stat: StatFn | None
) -> tuple[dict[str, bytes], list[str], list[SkippedFile]]:
    """Read every present state file first, so a failure leaves no half-backup."""
    payloads: dict[str, bytes] = {}
    absent: list[str] = []
    skipped: list[SkippedFile] = []
    for name in names:
        path = data_dir / name
        item = _BY_NAME.get(name, RadioDataFile(name, name))
        if not path.is_file():
            absent.append(item.label)
            continue
        try:
            payloads[name] = path.read_bytes()
        except OSError as exc:
            reason = classify_error(exc, path, stat=stat)
            if item.essential:
                advice = " ".join(what_to_do([SkippedFile(name, reason)]))
                raise RadioBackupError(
                    f"Nothing was saved: your {item.label} could not be read ({reason}). "
                    f"A backup without them would not be one. {advice}".strip()
                ) from exc
            skipped.append(SkippedFile(f"Your {item.label}", reason, str(exc)))
    return payloads, absent, skipped


def create_backup_report(
    data_dir: Path,
    dest: Path,
    *,
    recordings_dir: Path | None = None,
    include_recordings: bool = False,
    app_version: str = "",
    files: tuple[str, ...] = RADIO_DATA_FILES,
    progress: ProgressCallback | None = None,
    stat: StatFn | None = None,
    free_bytes: Callable[[Path], int] | None = None,
) -> BackupReport:
    """Write a ``.qrbackup`` to *dest* and say exactly what is in it.

    Raises :class:`RadioBackupError` when the zip cannot be written, when an
    essential state file exists but cannot be read, or when the finished zip
    does not read back -- never a success that is quietly missing them.
    """
    data_dir = Path(data_dir)
    dest = Path(dest)
    payloads, absent, skipped = _read_data_files(data_dir, files, stat)
    present = [name for name in files if name in payloads]

    plan = (
        plan_recordings(recordings_dir, exclude=dest, stat=stat)
        if include_recordings
        else RecordingsPlan(folder=Path())
    )
    room = (free_bytes or default_free_bytes)(plan.folder) if plan.cloud_only else 0
    may_download = plan.cloud_bytes + _SPACE_MARGIN <= room

    copied: list[str] = []
    incomplete: list[str] = []
    downloaded = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for name in present:
                zf.writestr(_DATA_PREFIX + name, payloads[name])
            total = len(plan.files)
            for index, path in enumerate(plan.files, start=1):
                if progress is not None:
                    progress(index, total, path.name)
                cloud = is_cloud_only(path, stat=stat)
                if cloud and not may_download:
                    skipped.append(SkippedFile(path.name, REASON_NO_SPACE_TO_DOWNLOAD))
                    continue
                left_out, partial = copy_recording(zf, path, cloud=cloud, stat=stat)
                if left_out is not None:
                    skipped.append(left_out)
                    if partial:
                        incomplete.append(path.name)
                    continue
                copied.append(path.name)
                downloaded += int(cloud)
            manifest = BackupManifest(
                app_version=app_version,
                created=_now_iso(),
                data_files=present,
                recordings=len(copied),
                incomplete=incomplete,
                skipped=[item.to_dict() for item in skipped],
            )
            zf.writestr(_MANIFEST_NAME, manifest.to_json())
    except OSError as exc:
        dest.unlink(missing_ok=True)
        raise RadioBackupError(f"Could not write the backup: {exc}") from exc
    _verify(dest, payloads)
    return BackupReport(
        path=dest,
        data_files=tuple(present),
        absent=tuple(absent),
        recordings=tuple(copied),
        recordings_eligible=len(plan.files),
        skipped=tuple(skipped),
        downloaded=downloaded,
    )


def _verify(dest: Path, payloads: dict[str, bytes]) -> None:
    """Re-read the state files from the finished zip; fail loudly on any gap."""
    try:
        with zipfile.ZipFile(dest) as zf:
            _load_manifest(zf)
            for name, payload in payloads.items():
                if zf.read(_DATA_PREFIX + name) != payload:
                    raise RadioBackupError(f"The backup did not save {name} correctly.")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        dest.unlink(missing_ok=True)
        raise RadioBackupError(f"The backup did not read back correctly: {exc}") from exc
    except RadioBackupError:
        dest.unlink(missing_ok=True)
        raise


def create_backup(
    data_dir: Path,
    dest: Path,
    *,
    recordings_dir: Path | None = None,
    include_recordings: bool = False,
    app_version: str = "",
    files: tuple[str, ...] = RADIO_DATA_FILES,
) -> Path:
    """Write a ``.qrbackup`` and return *dest* (see :func:`create_backup_report`)."""
    return create_backup_report(
        data_dir,
        dest,
        recordings_dir=recordings_dir,
        include_recordings=include_recordings,
        app_version=app_version,
        files=files,
    ).path


def _load_manifest(zf: zipfile.ZipFile) -> BackupManifest:
    try:
        raw = json.loads(zf.read(_MANIFEST_NAME).decode("utf-8"))
    except KeyError as exc:
        raise RadioBackupError("This file is not a Quill Radio backup.") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RadioBackupError("The backup's manifest is corrupt.") from exc
    if not isinstance(raw, dict) or raw.get("app") != _APP_TAG:
        raise RadioBackupError("This file is not a Quill Radio backup.")
    schema = raw.get("schema")
    if not isinstance(schema, int) or schema > _SCHEMA_VERSION:
        raise RadioBackupError(
            "This backup was made by a newer version of Quill Radio and cannot be restored here."
        )
    skipped_rows = raw.get("skipped", [])
    return BackupManifest(
        schema=schema,
        app=str(raw.get("app", "")),
        app_version=str(raw.get("app_version", "")),
        created=str(raw.get("created", "")),
        data_files=[str(x) for x in raw.get("data_files", []) if isinstance(x, str)],
        recordings=int(raw.get("recordings", 0) or 0),
        incomplete=[str(x) for x in raw.get("incomplete", []) if isinstance(x, str)],
        skipped=[
            {"name": str(row.get("name", "")), "reason": str(row.get("reason", ""))}
            for row in (skipped_rows if isinstance(skipped_rows, list) else [])
            if isinstance(row, dict)
        ],
    )


def read_manifest(src: Path) -> BackupManifest:
    """Peek at a backup's manifest without restoring (for a confirm prompt)."""
    try:
        with zipfile.ZipFile(Path(src)) as zf:
            return _load_manifest(zf)
    except zipfile.BadZipFile as exc:
        raise RadioBackupError("This file is not a valid Quill Radio backup.") from exc


def describe_data_files(names: list[str]) -> str:
    """The labels of *names*, for the restore prompt."""
    labels = [_BY_NAME[name].label for name in names if name in _BY_NAME]
    return ", ".join(labels) if labels else "no settings files"


def restore_backup(
    src: Path,
    data_dir: Path,
    *,
    recordings_dir: Path | None = None,
    stat: StatFn | None = None,
) -> RestoreResult:
    """Restore the state files (and any recordings) from *src* into the data dir.

    Only the known :data:`RADIO_DATA_FILES` are accepted from ``data/`` and every
    entry is checked against zip-slip, so a malformed or hostile archive can
    never write outside the target folders. Recordings restore into
    *recordings_dir*; one already there at the same size is left alone, and
    one that cannot be written is named with its reason rather than costing
    the rest of the restore.
    """
    data_dir = Path(data_dir)
    allowed = set(RADIO_DATA_FILES)
    restored_data: list[str] = []
    restored_recordings: list[str] = []
    skipped: list[SkippedFile] = []
    try:
        with zipfile.ZipFile(Path(src)) as zf:
            manifest = _load_manifest(zf)  # validate before writing anything
            incomplete = set(manifest.incomplete)
            data_dir.mkdir(parents=True, exist_ok=True)
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                if name.startswith(_DATA_PREFIX):
                    base = name[len(_DATA_PREFIX) :]
                    if base in allowed and "/" not in base and "\\" not in base:
                        (data_dir / base).write_bytes(zf.read(info))
                        restored_data.append(base)
                elif name.startswith(RECORDINGS_PREFIX):
                    base = name[len(RECORDINGS_PREFIX) :]
                    if not base or "/" in base or "\\" in base or base.startswith("."):
                        continue
                    if base in incomplete:
                        skipped.append(
                            SkippedFile(base, "was not copied completely when the backup was made")
                        )
                        continue
                    if recordings_dir is None:
                        skipped.append(SkippedFile(base, "no recordings folder is set"))
                        continue
                    left_out = restore_recording(zf, info, Path(recordings_dir) / base, stat)
                    if left_out is None:
                        restored_recordings.append(base)
                    else:
                        skipped.append(left_out)
    except zipfile.BadZipFile as exc:
        raise RadioBackupError("This file is not a valid Quill Radio backup.") from exc
    except OSError as exc:
        raise RadioBackupError(f"Could not restore the backup: {exc}") from exc
    return RestoreResult(tuple(restored_data), tuple(restored_recordings), tuple(skipped))
