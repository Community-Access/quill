"""Configurable data-location support (issue #615).

Moving the data directory while QUILL is running is not safe: the
in-memory ``Settings`` object is loaded once at startup and never reloaded
on demand, ``CopyTray`` caches its data directory at construction, and
there is no atomic move primitive for an entire directory tree under
Windows' transient file locks. So a location change is recorded as a
*pending* migration (``request_data_location_change``) and applied once,
very early in ``quill.__main__.main()`` -- before ``ensure_app_directories()``
or anything else resolves :func:`quill.core.paths.app_data_dir` -- by
:func:`apply_pending_data_location_migration`.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from quill.core import storage_mode
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, retry_on_transient_lock, write_json_atomic

_PENDING_MARKER_NAME = "pending-data-location.json"
_MIGRATION_NOTICE_NAME = "data-location-migration-notice.json"

# Legacy-install import (prior-version data stranded in a different location,
# e.g. a portable bundle's data/ folder after the user switched to an
# installed build, or vice versa). Queued on first run, applied next launch.
_LEGACY_IMPORT_MARKER_NAME = "pending-legacy-import.json"
_LEGACY_IMPORT_DECLINED_NAME = "legacy-import-declined.json"

# Files that, by their presence, identify a directory as a real QUILL data
# dir worth importing. Kept to actual user-content files: the dirs created by
# ``ensure_app_directories`` (logs/, sessions/, ...) exist empty on a fresh
# install and must not count as "has data".
_QUILL_DATA_FILE_MARKERS = ("settings.json", "keymap.json")

# Names never carried across by an import: location-control files (moving
# them would re-point the active dir back at the source) and our own markers.
_LEGACY_IMPORT_SKIP = frozenset({
    "storage-mode.json",
    _PENDING_MARKER_NAME,
    _MIGRATION_NOTICE_NAME,
    _LEGACY_IMPORT_MARKER_NAME,
    _LEGACY_IMPORT_DECLINED_NAME,
})

_VALID_MODES = {"appdata", "portable", "custom"}


def _appdata_target() -> Path:
    """Mirror paths.py::app_data_dir()'s appdata branch, for resolving a move target."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Quill"
    return Path.home() / ".quill"


def resolve_target(mode: str, custom_path: Path | None = None) -> Path:
    """Return the directory ``mode`` (and ``custom_path``, if any) resolves to."""
    if mode not in _VALID_MODES:
        raise ValueError(f"Unknown storage mode: {mode}")
    if mode == "custom":
        if custom_path is None:
            raise ValueError("Custom storage mode requires a path")
        return Path(custom_path).expanduser().resolve()
    if mode == "portable":
        root = storage_mode.portable_root_dir()
        if root is None:
            raise ValueError("Portable mode is not available -- not running from a portable bundle")
        return root
    return _appdata_target()


def request_data_location_change(mode: str, custom_path: Path | None = None) -> Path:
    """Record an intent to move the data directory; applied on next launch.

    Returns the resolved target directory, for the caller's confirmation
    message. If the target is already the current data directory, the
    storage-mode choice is saved immediately and no migration is queued.
    """
    target = resolve_target(mode, custom_path)
    current = app_data_dir().resolve()

    if target == current:
        storage_mode.save_storage_mode(mode, path=target if mode == "custom" else None)
        (current / _PENDING_MARKER_NAME).unlink(missing_ok=True)
        return target

    document: dict[str, object] = {"mode": mode, "target": str(target)}
    if mode == "custom":
        document["custom_path"] = str(target)
    write_json_atomic(current / _PENDING_MARKER_NAME, document)
    return target


def pending_data_location_target() -> Path | None:
    """The target directory queued by :func:`request_data_location_change`,
    or None when no move is pending.

    A caller offering an immediate restart (e.g. the setup wizard, mirroring
    Preferences' existing restart offer) uses this to know whether a real
    move was queued, since ``request_data_location_change`` applies in place
    with no marker when the chosen target already matches the current one.
    """
    marker = app_data_dir().resolve() / _PENDING_MARKER_NAME
    document = read_json(marker, None)
    if not isinstance(document, dict):
        return None
    target = document.get("target")
    if not isinstance(target, str) or not target:
        return None
    return Path(target)


def apply_pending_data_location_migration() -> None:
    """Apply a pending data-location move recorded by Preferences, if any.

    Must run before ``ensure_app_directories()``/``load_settings()`` so it
    reads the marker from the *current* (pre-move) location. Writes a
    one-line notice (success or failure) at whichever location the app
    will actually use afterwards, for :func:`pop_pending_migration_notice`
    to surface once the UI exists.
    """
    current = app_data_dir()
    marker = current / _PENDING_MARKER_NAME
    if not marker.exists():
        return

    document = read_json(marker, default={})
    marker.unlink(missing_ok=True)
    if not isinstance(document, dict):
        return

    mode = document.get("mode")
    target_raw = document.get("target")
    if not isinstance(mode, str) or mode not in _VALID_MODES or not isinstance(target_raw, str):
        return
    target = Path(target_raw)

    try:
        _move_directory_contents(current, target)
    except OSError as error:
        _write_migration_notice(
            current, f"Could not move Quill's data to {target}: {error}. Staying at {current}."
        )
        return

    custom_value = document.get("custom_path")
    custom_path = Path(str(custom_value)) if mode == "custom" and custom_value else None
    storage_mode.save_storage_mode(mode, path=custom_path)
    _write_migration_notice(target, f"Quill's data is now stored at {target}.")


def pop_pending_migration_notice() -> str | None:
    """Read and clear the one-time migration status message, or return None.

    Mirrors ``paths.py::new_install_marker_path()``'s consume-once pattern:
    call from the UI layer once a frame exists (see
    ``main_frame.py::_maybe_run_first_run_onboarding``) so the message can
    be announced/shown, rather than threading it through ``run_app()``.
    """
    marker = app_data_dir() / _MIGRATION_NOTICE_NAME
    if not marker.exists():
        return None
    document = read_json(marker, default={})
    marker.unlink(missing_ok=True)
    if not isinstance(document, dict):
        return None
    message = document.get("message")
    return message if isinstance(message, str) else None


def _write_migration_notice(location: Path, message: str) -> None:
    write_json_atomic(location / _MIGRATION_NOTICE_NAME, {"message": message})


def _move_directory_contents(
    source: Path, destination: Path, *, skip: frozenset[str] = frozenset()
) -> None:
    """Move every entry in ``source`` into ``destination``, retrying transient locks.

    Moves per top-level entry (not a single directory rename) so it works
    whether or not the destination already exists, and so a partial
    failure leaves both ends in a recoverable state rather than a
    half-renamed directory. Never overwrites an existing destination entry
    -- skips it instead, so a retry after a partial failure does not lose
    data that already made it across.

    ``skip`` names (case-insensitive) are left in ``source`` untouched. The
    legacy-install import uses it to avoid carrying location-control files
    (``storage-mode.json`` and the pending markers) across, which would
    otherwise re-point the active data dir back at the emptied source.
    """
    destination.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        return
    skip_lower = {name.lower() for name in skip}
    for entry in source.iterdir():
        if entry.name.lower() in skip_lower:
            continue
        target_entry = destination / entry.name
        if target_entry.exists():
            continue

        def _do_move(_entry: Path = entry, _target: Path = target_entry) -> None:
            shutil.move(str(_entry), str(_target))

        retry_on_transient_lock(_do_move)


def _is_quill_data_dir(directory: Path) -> bool:
    """True when *directory* holds user content from a real QUILL install.

    Only counts content files (``settings.json``/``keymap.json``) or a
    non-empty ``sessions``/``autosave`` folder. The empty subdirectories
    ``ensure_app_directories`` creates on a fresh install do not qualify, so
    a freshly-resolved data dir is correctly treated as "no data yet".
    """
    if not directory.is_dir():
        return False
    if any((directory / name).is_file() for name in _QUILL_DATA_FILE_MARKERS):
        return True
    for sub in ("sessions", "autosave"):
        child = directory / sub
        if child.is_dir() and any(child.iterdir()):
            return True
    return False


def _legacy_candidate_dirs() -> list[Path]:
    """Other locations a prior QUILL install may have written its data to."""
    candidates = [_appdata_target()]
    root = storage_mode.portable_root_dir()
    if root is not None:
        candidates.append(root)
    candidates.append(Path.home() / ".quill")
    return candidates


def detect_importable_legacy_dir() -> Path | None:
    """Return a populated prior-install data dir to import, or None.

    Returns a candidate only when the *current* data dir has no keymap of its
    own yet (a fresh location), so we never offer to import on top of a data
    dir the user is already established in. The returned directory is a
    different, populated location -- typically the user upgraded between
    portable and installed builds, or the saved storage mode was lost on
    reinstall, stranding the old data.
    """
    current = app_data_dir().resolve()
    # A keymap.json in the current dir means the user already has settings
    # here (or a prior import already ran); do not offer again.
    if (current / "keymap.json").is_file():
        return None
    seen = {current}
    for candidate in _legacy_candidate_dirs():
        resolved = candidate.expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if _is_quill_data_dir(resolved):
            return resolved
    return None


def request_legacy_data_import(source: Path) -> None:
    """Queue an import of *source*'s contents into the current data dir.

    Applied on the next launch by :func:`apply_pending_legacy_import`, for
    the same reason data-location moves are deferred (see module docstring):
    a live move is not safe while Settings/CopyTray hold the current path.
    """
    current = app_data_dir()
    write_json_atomic(current / _LEGACY_IMPORT_MARKER_NAME, {"source": str(source)})


def decline_legacy_data_import(source: Path) -> None:
    """Record that the user declined importing *source*, so we stop asking."""
    current = app_data_dir()
    write_json_atomic(current / _LEGACY_IMPORT_DECLINED_NAME, {"source": str(source)})


def legacy_data_import_declined(source: Path) -> bool:
    """True when the user already declined importing this *source*."""
    marker = app_data_dir() / _LEGACY_IMPORT_DECLINED_NAME
    if not marker.exists():
        return False
    document = read_json(marker, default={})
    return isinstance(document, dict) and document.get("source") == str(source)


def apply_pending_legacy_import() -> None:
    """Apply a queued prior-install import, if any (mirrors the #615 apply).

    Must run before ``ensure_app_directories()``/``load_settings()`` so the
    imported files are present when settings/keymap are first read this
    launch. Writes a one-line notice for :func:`pop_pending_migration_notice`
    to surface once the UI exists. Location-control files are not carried
    across (see ``_LEGACY_IMPORT_SKIP``).
    """
    current = app_data_dir()
    marker = current / _LEGACY_IMPORT_MARKER_NAME
    if not marker.exists():
        return
    document = read_json(marker, default={})
    marker.unlink(missing_ok=True)
    if not isinstance(document, dict):
        return
    source_raw = document.get("source")
    if not isinstance(source_raw, str) or not source_raw:
        return
    source = Path(source_raw)
    if not source.exists() or source.resolve() == current.resolve():
        return
    try:
        _move_directory_contents(source, current, skip=_LEGACY_IMPORT_SKIP)
    except OSError as error:
        _write_migration_notice(current, f"Could not import Quill data from {source}: {error}.")
        return
    _write_migration_notice(current, f"Imported your Quill data from {source}.")


__all__ = [
    "apply_pending_data_location_migration",
    "apply_pending_legacy_import",
    "decline_legacy_data_import",
    "detect_importable_legacy_dir",
    "legacy_data_import_declined",
    "pop_pending_migration_notice",
    "request_data_location_change",
    "request_legacy_data_import",
    "resolve_target",
]
