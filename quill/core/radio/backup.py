"""Back up and restore a listener's Quill Radio data as one portable zip.

For moving to a new device (a BrailleNote Evolve, a new PC) or after an OS
reinstall (#1193): :func:`create_backup` bundles the small JSON state files --
favorites, history/settings, the wake timer, and the recording schedule -- and,
optionally, the recorded audio, into a single ``.qrbackup`` zip with a manifest.
:func:`restore_backup` validates and restores them into the data dir.

File-level (it copies the JSON verbatim rather than re-serialising), so a backup
made by one version restores cleanly into another. Pure filesystem I/O, wx-free,
fully testable. Safe on restore: only the known state filenames are accepted and
every entry is checked against zip-slip before extraction.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

#: The Quill Radio state files that live directly in the data dir. Order is
#: stable so a backup lists them predictably. A file that is not present yet
#: (e.g. no schedule set) is simply skipped.
RADIO_DATA_FILES: tuple[str, ...] = (
    "radio_favorites.json",
    "radio_history.json",
    "radio_wake_timer.json",
    "radio_recording_schedule.json",
)

BACKUP_SUFFIX = ".qrbackup"
_MANIFEST_NAME = "quill-radio-backup.json"
_DATA_PREFIX = "data/"
_RECORDINGS_PREFIX = "recordings/"
_SCHEMA_VERSION = 1
_APP_TAG = "quill-radio"


class RadioBackupError(Exception):
    """A backup could not be created, or a restore file was invalid."""


@dataclass(frozen=True, slots=True)
class RestoreResult:
    """What a restore actually put back."""

    data_files: tuple[str, ...] = ()
    recordings: tuple[str, ...] = ()


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

    def to_json(self) -> str:
        return json.dumps(
            {
                "schema": self.schema,
                "app": self.app,
                "app_version": self.app_version,
                "created": self.created,
                "data_files": self.data_files,
                "recordings": self.recordings,
            },
            indent=2,
        )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def create_backup(
    data_dir: Path,
    dest: Path,
    *,
    recordings_dir: Path | None = None,
    include_recordings: bool = False,
    app_version: str = "",
) -> Path:
    """Write a ``.qrbackup`` zip of the Radio state files to *dest*.

    Includes every present file in :data:`RADIO_DATA_FILES`. When
    *include_recordings* is true and *recordings_dir* exists, its files are added
    too (flat, top level only). Returns *dest*.
    """
    data_dir = Path(data_dir)
    dest = Path(dest)
    present = [name for name in RADIO_DATA_FILES if (data_dir / name).is_file()]

    recording_files: list[Path] = []
    if include_recordings and recordings_dir is not None and Path(recordings_dir).is_dir():
        recording_files = [p for p in sorted(Path(recordings_dir).iterdir()) if p.is_file()]

    manifest = BackupManifest(
        app_version=app_version,
        created=_now_iso(),
        data_files=present,
        recordings=len(recording_files),
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(_MANIFEST_NAME, manifest.to_json())
            for name in present:
                zf.write(data_dir / name, _DATA_PREFIX + name)
            for path in recording_files:
                zf.write(path, _RECORDINGS_PREFIX + path.name)
    except OSError as exc:
        dest.unlink(missing_ok=True)
        raise RadioBackupError(f"Could not write the backup: {exc}") from exc
    return dest


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
    return BackupManifest(
        schema=schema,
        app=str(raw.get("app", "")),
        app_version=str(raw.get("app_version", "")),
        created=str(raw.get("created", "")),
        data_files=[str(x) for x in raw.get("data_files", []) if isinstance(x, str)],
        recordings=int(raw.get("recordings", 0) or 0),
    )


def read_manifest(src: Path) -> BackupManifest:
    """Peek at a backup's manifest without restoring (for a confirm prompt)."""
    try:
        with zipfile.ZipFile(Path(src)) as zf:
            return _load_manifest(zf)
    except zipfile.BadZipFile as exc:
        raise RadioBackupError("This file is not a valid Quill Radio backup.") from exc


def restore_backup(
    src: Path,
    data_dir: Path,
    *,
    recordings_dir: Path | None = None,
) -> RestoreResult:
    """Restore the state files (and any recordings) from *src* into the data dir.

    Only the known :data:`RADIO_DATA_FILES` are accepted from ``data/`` and every
    entry is checked against zip-slip, so a malformed or hostile archive can
    never write outside the target folders. Recordings restore into
    *recordings_dir* when the archive carries them and a folder is given.
    """
    data_dir = Path(data_dir)
    allowed = set(RADIO_DATA_FILES)
    restored_data: list[str] = []
    restored_recordings: list[str] = []
    try:
        with zipfile.ZipFile(Path(src)) as zf:
            _load_manifest(zf)  # validate before writing anything
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
                elif name.startswith(_RECORDINGS_PREFIX) and recordings_dir is not None:
                    base = name[len(_RECORDINGS_PREFIX) :]
                    if base and "/" not in base and "\\" not in base and not base.startswith("."):
                        target_dir = Path(recordings_dir)
                        target_dir.mkdir(parents=True, exist_ok=True)
                        (target_dir / base).write_bytes(zf.read(info))
                        restored_recordings.append(base)
    except zipfile.BadZipFile as exc:
        raise RadioBackupError("This file is not a valid Quill Radio backup.") from exc
    except OSError as exc:
        raise RadioBackupError(f"Could not restore the backup: {exc}") from exc
    return RestoreResult(tuple(restored_data), tuple(restored_recordings))
