"""Back up and restore a listener's QUILL Cast library as one portable zip.

Cast had **Export My Data** -- a one-shot readable JSON -- and the shared setup
transfer. Neither is a restore (list.md 5.6). Quill Radio has had Back Up /
Restore over :mod:`quill.core.radio.backup` since #1193, and Cast's data is the
more painful of the two to lose: subscriptions, folders, playlists, positions,
notes, statistics and speeds are years of accumulated choices, where a station
list can be rebuilt from a directory in an afternoon.

**File-level, deliberately.** The JSON is copied verbatim rather than
re-serialised, so a backup made by one version restores cleanly into another
and a field this build has never heard of survives the round trip. The same
choice Radio made, for the same reason.

**Downloaded episodes are optional and off by default.** A library of downloads
is tens of gigabytes and is the one part that can be fetched again from the
publisher; the 40 KB of JSON beside it cannot. Somebody moving to a new
machine wants the small thing to be quick and reliable, and can choose the
large one deliberately.

**Safe on restore.** Only the known state filenames are accepted, every entry
is checked against zip-slip before extraction, and the manifest is validated
before a single byte is written. A hostile or damaged archive can cost the
restore, never the folder.

Pure filesystem I/O, wx-free, fully testable.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from quill.core.error_codes import CodedError

__all__ = [
    "BACKUP_SUFFIX",
    "CAST_DATA_FILES",
    "BackupManifest",
    "CastBackupError",
    "RestoreResult",
    "create_backup",
    "read_manifest",
    "restore_backup",
    "suggested_filename",
]

#: Every QUILL Cast state file that lives directly in the data dir, in a
#: stable order so a backup lists them predictably. A file that does not exist
#: yet -- no notes taken, no playlists made -- is simply skipped rather than
#: being an error: an empty library is a perfectly good thing to back up
#: before starting.
#:
#: ``media_bookmarks.json`` and ``radio-listens.json`` are shared with Quill
#: Radio and are included anyway. Somebody restoring a Cast backup onto a new
#: machine wants their bookmarks, and the alternative -- leaving them out
#: because another app can also write them -- loses data to a technicality.
CAST_DATA_FILES: tuple[str, ...] = (
    "podcasts_library.json",
    "podcast_history.json",
    "podcast_episode_notes.json",
    "podcast_stats.json",
    "podcast_quick_actions.json",
    "podcast-ask-prefs.json",
    "cast-go-to.json",
    "radio-show-speeds.json",
    "radio-listens.json",
    "media_bookmarks.json",
)

BACKUP_SUFFIX = ".qcbackup"
_MANIFEST_NAME = "quill-cast-backup.json"
_DATA_PREFIX = "data/"
_EPISODES_PREFIX = "episodes/"
_SCHEMA_VERSION = 1
_APP_TAG = "quill-cast"


class CastBackupError(CodedError):
    """A backup could not be created, or a restore file was invalid."""

    code = "QUILL-CAST-BACKUP-FAILED"


@dataclass(frozen=True, slots=True)
class RestoreResult:
    """What a restore actually put back."""

    data_files: tuple[str, ...] = ()
    episodes: tuple[str, ...] = ()

    def summary(self) -> str:
        """One spoken sentence naming what came back.

        Counts rather than lists: ten filenames read aloud is not an answer to
        "did it work", and the filenames are not what anybody is asking about.
        """
        files = len(self.data_files)
        if not files and not self.episodes:
            return "Nothing was restored: the backup was empty."
        parts = [f"{files} data file{'' if files == 1 else 's'}"]
        if self.episodes:
            count = len(self.episodes)
            parts.append(f"{count} downloaded episode{'' if count == 1 else 's'}")
        return "Restored " + " and ".join(parts) + "."


@dataclass(slots=True)
class BackupManifest:
    """The manifest inside a backup zip, and what :func:`read_manifest` returns
    for a preview before anything is overwritten."""

    schema: int = _SCHEMA_VERSION
    app: str = _APP_TAG
    app_version: str = ""
    created: str = ""
    data_files: list[str] = field(default_factory=list)
    episodes: int = 0
    shows: int = 0

    def to_json(self) -> str:
        return json.dumps(
            {
                "schema": self.schema,
                "app": self.app,
                "app_version": self.app_version,
                "created": self.created,
                "data_files": self.data_files,
                "episodes": self.episodes,
                "shows": self.shows,
            },
            indent=2,
        )

    def describe(self) -> str:
        """What this backup holds, for the confirm prompt before a restore.

        Restoring overwrites a library, so the sentence that precedes it has to
        carry the two facts somebody needs to spot the wrong file: when it was
        made, and how big the library in it is.
        """
        when = self.created.split("T")[0] if self.created else "an unknown date"
        shows = (
            f"{self.shows} podcast{'' if self.shows == 1 else 's'}" if self.shows else "a library"
        )
        episodes = (
            f", and {self.episodes} downloaded episode{'' if self.episodes == 1 else 's'}"
            if self.episodes
            else ""
        )
        return f"This backup was made on {when} and holds {shows}{episodes}."


def suggested_filename(*, stamp: str = "") -> str:
    """``quill-cast-backup-2026-08-24.qcbackup``.

    Dated, because the first thing anybody does with a second backup is try to
    tell it from the first.
    """
    day = (stamp or _now_iso()).split("T")[0]
    return f"quill-cast-backup-{day}{BACKUP_SUFFIX}"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def create_backup(
    data_dir: Path,
    dest: Path,
    *,
    downloads_dir: Path | None = None,
    include_episodes: bool = False,
    app_version: str = "",
    shows: int = 0,
) -> Path:
    """Write a ``.qcbackup`` zip of the Cast state files to *dest*.

    Includes every present file in :data:`CAST_DATA_FILES`. When
    *include_episodes* is true and *downloads_dir* exists, the audio under it
    is added too, keeping its per-show folder structure -- the folders are how
    the library finds a downloaded file again. Returns *dest*.
    """
    data_dir = Path(data_dir)
    dest = Path(dest)
    present = [name for name in CAST_DATA_FILES if (data_dir / name).is_file()]

    episode_files: list[tuple[Path, str]] = []
    if include_episodes and downloads_dir is not None and Path(downloads_dir).is_dir():
        root = Path(downloads_dir)
        for path in sorted(root.rglob("*")):
            if path.is_file():
                episode_files.append((path, path.relative_to(root).as_posix()))

    manifest = BackupManifest(
        app_version=app_version,
        created=_now_iso(),
        data_files=present,
        episodes=len(episode_files),
        shows=shows,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(_MANIFEST_NAME, manifest.to_json())
            for name in present:
                zf.write(data_dir / name, _DATA_PREFIX + name)
            for path, relative in episode_files:
                zf.write(path, _EPISODES_PREFIX + relative)
    except OSError as exc:
        # A half-written zip is worse than none: somebody would restore from it.
        dest.unlink(missing_ok=True)
        raise CastBackupError(f"Could not write the backup: {exc}") from exc
    return dest


def _load_manifest(zf: zipfile.ZipFile) -> BackupManifest:
    try:
        raw = json.loads(zf.read(_MANIFEST_NAME).decode("utf-8"))
    except KeyError as exc:
        raise CastBackupError("This file is not a QUILL Cast backup.") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CastBackupError("The backup's manifest is corrupt.") from exc
    if not isinstance(raw, dict) or raw.get("app") != _APP_TAG:
        raise CastBackupError("This file is not a QUILL Cast backup.")
    schema = raw.get("schema")
    if not isinstance(schema, int) or schema > _SCHEMA_VERSION:
        raise CastBackupError(
            "This backup was made by a newer version of QUILL Cast and cannot be restored here."
        )
    return BackupManifest(
        schema=schema,
        app=str(raw.get("app", "")),
        app_version=str(raw.get("app_version", "")),
        created=str(raw.get("created", "")),
        data_files=[x for x in raw.get("data_files", []) if isinstance(x, str)],
        episodes=int(raw.get("episodes", 0) or 0),
        shows=int(raw.get("shows", 0) or 0),
    )


def read_manifest(src: Path) -> BackupManifest:
    """Peek at a backup's manifest without restoring anything."""
    try:
        with zipfile.ZipFile(Path(src)) as zf:
            return _load_manifest(zf)
    except zipfile.BadZipFile as exc:
        raise CastBackupError("This file is not a valid QUILL Cast backup.") from exc
    except OSError as exc:
        raise CastBackupError(f"Could not read the backup: {exc}") from exc


def _safe_relative(name: str) -> str:
    """The archive path as a relative POSIX path, or "" when it is not safe.

    Zip-slip in one place: an entry naming ``..`` or an absolute path, or a
    Windows drive letter, or a backslash that becomes a separator on extract,
    is refused outright rather than sanitised. A backup is not a place to be
    clever about hostile input.
    """
    cleaned = name.replace("\\", "/").strip()
    if not cleaned or cleaned.endswith("/"):
        return ""
    if cleaned.startswith("/") or ":" in cleaned:
        return ""
    parts = [part for part in cleaned.split("/") if part]
    if any(part in {"..", "."} for part in parts):
        return ""
    return "/".join(parts)


def restore_backup(
    src: Path,
    data_dir: Path,
    *,
    downloads_dir: Path | None = None,
) -> RestoreResult:
    """Restore the state files (and any episodes) from *src* into the data dir.

    Only the known :data:`CAST_DATA_FILES` are accepted from ``data/``, and
    every entry is checked before extraction, so a malformed or hostile archive
    can never write outside the target folders. Episodes restore into
    *downloads_dir* when the archive carries them and a folder is given.
    """
    data_dir = Path(data_dir)
    allowed = set(CAST_DATA_FILES)
    restored_data: list[str] = []
    restored_episodes: list[str] = []
    try:
        with zipfile.ZipFile(Path(src)) as zf:
            _load_manifest(zf)  # validate before writing anything
            data_dir.mkdir(parents=True, exist_ok=True)
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                if name.startswith(_DATA_PREFIX):
                    base = _safe_relative(name[len(_DATA_PREFIX) :])
                    if base in allowed:
                        (data_dir / base).write_bytes(zf.read(info))
                        restored_data.append(base)
                elif name.startswith(_EPISODES_PREFIX) and downloads_dir is not None:
                    relative = _safe_relative(name[len(_EPISODES_PREFIX) :])
                    if not relative:
                        continue
                    target = Path(downloads_dir) / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(info))
                    restored_episodes.append(relative)
    except zipfile.BadZipFile as exc:
        raise CastBackupError("This file is not a valid QUILL Cast backup.") from exc
    except OSError as exc:
        raise CastBackupError(f"Could not restore the backup: {exc}") from exc
    return RestoreResult(tuple(restored_data), tuple(restored_episodes))
