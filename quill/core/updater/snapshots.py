"""The copy of an app's settings saved when it joins Beta or Dev (plan 5.4).

"Before switching, Quill Radio saves a copy of your favorites, history and
settings" is a promise the risk dialog makes, so it is kept *before* the
channel changes: if the copy cannot be made, the switch does not happen.

Each app reuses the backup it already has rather than inventing a format:

=========== ===================================================================
QUILL       a zip of the small settings files in QUILL's data folder
QUILL Lite  a zip of every settings file in QUILL Lite's own folder
Quill Radio ``radio.backup.create_backup`` (a ``.qrbackup``), no recordings
QUILL Cast  ``podcasts.backup.create_backup`` (a ``.qcbackup``), no episodes
=========== ===================================================================

Stored at ``<data folder>/channel-snapshots/<app>-<version>-<reason>-<stamp>``,
with ``<copy>.ledger.json`` beside it: the data-format versions the copy holds,
so restoring it can set the ledger back to match. The newest ``joined-*`` copy
is always kept (it is the way back from Beta); of the rest, the three newest.

:func:`restore_snapshot` puts a copy back (plan 5.4): it first saves a
``before-restore`` copy of how things are now -- so nothing is thrown away --
then writes the copy's files back, leaves alone any shared file a sibling on
Beta or Dev wrote a newer version of, and lowers the ledger to what the copy
holds. Radio and Cast restore through their own backup code; QUILL and QUILL
Lite copies are zips of their settings files.

wx-free and strict-typed.
"""

from __future__ import annotations

import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from quill.core.error_codes import CodedError

__all__ = [
    "KEEP_PER_APP",
    "RestoreOutcome",
    "SnapshotError",
    "data_folder",
    "restore_snapshot",
    "snapshot_dir",
    "take_snapshot",
]

KEEP_PER_APP = 3
#: A settings copy is tens of kilobytes; anything this large is not settings.
_MAX_FILE_BYTES = 5 * 1024 * 1024
_EXTENSIONS = {"quill": ".zip", "quilllite": ".zip", "radio": ".qrbackup", "cast": ".qcbackup"}


class SnapshotError(CodedError):
    """The copy could not be made; :attr:`reason` says why, in plain words."""

    code = "QUILL-UPDATE-CHANNEL-SNAPSHOT-FAILED"

    @property
    def reason(self) -> str:
        return str(self.args[0]) if self.args else ""


def data_folder(app_key: str) -> Path:
    """The folder *app_key* keeps its settings in."""
    if app_key == "quilllite":
        from quill.core.lite.paths import data_dir

        return data_dir()
    from quill.core.paths import app_data_dir

    return app_data_dir()


def snapshot_dir(app_key: str, *, data: Path | None = None) -> Path:
    return (data or data_folder(app_key)) / "channel-snapshots"


def _zip_json_files(source: Path, dest: Path) -> Path:
    files = [
        path
        for path in sorted(source.glob("*.json"))
        if path.is_file() and path.stat().st_size <= _MAX_FILE_BYTES
    ]
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, arcname=path.name)
    return dest


def _radio(source: Path, dest: Path, version: str) -> Path:
    from quill.core.radio.backup import SNAPSHOT_DATA_FILES, create_backup

    return create_backup(
        source, dest, include_recordings=False, app_version=version, files=SNAPSHOT_DATA_FILES
    )


def _cast(source: Path, dest: Path, version: str) -> Path:
    from quill.core.podcasts.backup import create_backup

    return create_backup(source, dest, include_episodes=False, app_version=version)


_Adapter = Callable[[Path, Path, str], Path]

_ADAPTERS: dict[str, _Adapter] = {
    "quill": lambda source, dest, _version: _zip_json_files(source, dest),
    "quilllite": lambda source, dest, _version: _zip_json_files(source, dest),
    "radio": _radio,
    "cast": _cast,
}


def _safe(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z.\-]+", "-", text).strip("-") or "unknown"


def take_snapshot(
    app_key: str,
    version: str,
    reason: str,
    *,
    data: Path | None = None,
    now: datetime | None = None,
) -> Path:
    """Save the copy and return its path; raise :class:`SnapshotError` if not.

    *reason* is ``joined-beta``, ``joined-dev`` or ``before-update``.
    """
    adapter = _ADAPTERS.get(app_key)
    if adapter is None:
        raise SnapshotError(f"there is no way to copy settings for {app_key} yet")
    source = data or data_folder(app_key)
    folder = snapshot_dir(app_key, data=source)
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")
    dest = folder / f"{app_key}-{_safe(version)}-{_safe(reason)}-{stamp}{_EXTENSIONS[app_key]}"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        written = adapter(source, dest, version)
    except Exception as error:  # noqa: BLE001 - any failure means "no copy", said plainly
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass
        raise SnapshotError(str(error) or error.__class__.__name__) from error
    _write_ledger_sidecar(app_key, source, written)
    _prune(folder, app_key)
    return written


_SIDECAR = ".ledger.json"


def _write_ledger_sidecar(app_key: str, source: Path, copy: Path) -> None:
    """Remember which data-format versions this copy holds (for the restore)."""
    import json

    from quill.core.data_format_ledger import read_ledger
    from quill.core.data_formats import formats_for

    ledger = read_ledger(source)
    held = {f.id: ledger.high(f.id) for f in formats_for(app_key) if ledger.high(f.id)}
    try:
        copy.with_name(copy.name + _SIDECAR).write_text(
            json.dumps({"version": 1, "formats": held}), encoding="utf-8"
        )
    except OSError:
        return


def _read_ledger_sidecar(copy: Path) -> dict[str, int] | None:
    import json

    try:
        raw = json.loads(copy.with_name(copy.name + _SIDECAR).read_text(encoding="utf-8"))
        return {str(k): int(v) for k, v in raw.get("formats", {}).items()}
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def _prune(folder: Path, app_key: str) -> None:
    mine = sorted(
        (
            path
            for path in folder.glob(f"{app_key}-*")
            if path.is_file() and not path.name.endswith(_SIDECAR)
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    joined = next((path for path in mine if "-joined-" in path.name), None)
    others = [path for path in mine if path != joined]
    for old in others[KEEP_PER_APP:]:
        for doomed in (old, old.with_name(old.name + _SIDECAR)):
            try:
                doomed.unlink(missing_ok=True)
            except OSError:
                pass


# -- putting a copy back (plan 5.4) --------------------------------------------


@dataclass(frozen=True)
class RestoreOutcome:
    #: The copy of how things were just before the restore.
    before: Path
    restored: tuple[str, ...]
    #: Shared files left as they were (a sibling on Beta or Dev wrote them).
    kept: tuple[str, ...]


def _restore_zip(copy: Path, target: Path, only: set[str] | None = None) -> list[str]:
    """Write a settings zip back. *only* limits it to those names -- QUILL's data
    folder is shared with Quill Radio and QUILL Cast, so QUILL puts back its own
    settings and keys and never another app's files."""
    restored = []
    with zipfile.ZipFile(copy) as archive:
        for info in archive.infolist():
            name = info.filename
            if info.is_dir() or "/" in name or "\\" in name or not name.endswith(".json"):
                continue
            if only is not None and name not in only:
                continue
            (target / name).write_bytes(archive.read(info))
            restored.append(name)
    return restored


def restore_snapshot(
    app_key: str,
    copy: Path,
    *,
    version_now: str,
    keep_shared: tuple[str, ...] = (),
    fallback_formats: dict[str, int] | None = None,
    data: Path | None = None,
    now: datetime | None = None,
) -> RestoreOutcome:
    """Put *copy* back into *app_key*'s data folder. Raises :class:`SnapshotError`.

    *keep_shared* are shared format ids a sibling on Beta or Dev wrote; their
    files stay as they are. *fallback_formats* is what to lower the ledger to
    when the copy predates its ledger sidecar (the Stable build's formats).
    """
    from quill.core.data_format_ledger import lower
    from quill.core.data_formats import FORMATS, formats_for

    target = data or data_folder(app_key)
    if not copy.is_file():
        raise SnapshotError("the saved copy is no longer there")
    before = take_snapshot(app_key, version_now, "before-restore", data=target, now=now)
    kept_files = {
        name: (target / name).read_bytes()
        for fmt in FORMATS
        if fmt.id in keep_shared
        for name in fmt.files
        if (target / name).is_file()
    }
    try:
        if app_key == "radio":
            from quill.core.radio.backup import restore_backup as radio_restore

            restored = list(radio_restore(copy, target).data_files)
        elif app_key == "cast":
            from quill.core.podcasts.backup import restore_backup as cast_restore

            restored = list(cast_restore(copy, target).data_files)
        elif app_key == "quill":
            own = {name for fmt in formats_for("quill") for name in fmt.files}
            restored = _restore_zip(copy, target, own)
        else:
            restored = _restore_zip(copy, target)
    except Exception as error:  # noqa: BLE001 - said plainly; the before copy is safe
        raise SnapshotError(str(error) or error.__class__.__name__) from error
    for name, payload in kept_files.items():
        (target / name).write_bytes(payload)
    held = _read_ledger_sidecar(copy)
    if held is None:
        held = dict(fallback_formats or {})
    mine = {f.id for f in formats_for(app_key)} - set(keep_shared)
    lower(target, {k: v for k, v in held.items() if k in mine}, f"{app_key} restored copy")
    return RestoreOutcome(before, tuple(restored), tuple(sorted(kept_files)))
