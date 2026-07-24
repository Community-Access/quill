"""Shared Python runtime reference counting -- who still needs each runtime.

The QuillVille suite shares ONE versioned Python runtime (embeddable CPython +
wxPython + the shared packages) instead of every app carrying its own copy (see
``docs/design/2026-07-21-quillville-installer-and-shared-runtime-program.md``,
Part A). This tracks which installed apps require each runtime *version*, so a
runtime is installed once, reused by every app pinned to it, and only becomes
removable when the last app that needs it is uninstalled.

It is the runtime twin of :mod:`quill.core.components` (which does the same for
ffmpeg/mpv/models/voices): same file-backed, wx-free, idempotent, never-crash
design, keyed by a runtime version string (e.g. ``"3.13.1"``) rather than a
component id. State lives in ``runtime.state.json`` in the shared data dir.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic

_FILE_NAME = "runtime.state.json"


def _state_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def _load(data_dir: Path) -> dict[str, list[str]]:
    """The refs map: ``runtime_version -> sorted app_ids that require it``."""
    raw = read_json(_state_path(data_dir), {})
    refs: dict[str, list[str]] = {}
    if isinstance(raw, dict):
        entries = raw.get("refs")
        if isinstance(entries, dict):
            for version, apps in entries.items():
                if isinstance(apps, list):
                    refs[str(version)] = sorted({str(app) for app in apps if isinstance(app, str)})
    return refs


def _save(data_dir: Path, refs: dict[str, list[str]]) -> None:
    # Drop versions with no remaining app so the file never accretes junk.
    clean = {version: apps for version, apps in refs.items() if apps}
    write_json_atomic(_state_path(data_dir), {"refs": clean})


def register(data_dir: Path, app_id: str, runtime_version: str) -> None:
    """Record that *app_id* currently runs on exactly *runtime_version*.

    Idempotent -- safe to call on every launch. This app's ref is added to
    *runtime_version* and removed from any other version it previously used, so
    the refs always reflect the app's live runtime (e.g. after an upgrade that
    moved it onto a newer CPython).
    """
    wanted = str(runtime_version)
    refs = _load(data_dir)
    apps = set(refs.get(wanted, []))
    apps.add(app_id)
    refs[wanted] = sorted(apps)
    for version in list(refs):
        if version != wanted and app_id in refs[version]:
            refs[version] = [app for app in refs[version] if app != app_id]
    _save(data_dir, refs)


def register_running_app(app_id: str, runtime_version: str) -> None:
    """Register the running app's runtime version in the shared store.

    The one line an app calls at launch -- the ``app_data_dir()`` lookup and the
    never-crash guard live here. Best-effort: a bad data dir or read-only disk
    must never stop the app from starting.
    """
    try:
        from quill.core.paths import app_data_dir

        register(app_data_dir(), app_id, runtime_version)
    except Exception:  # noqa: BLE001 - registering refs must never block launch
        pass


def unregister(data_dir: Path, app_id: str) -> None:
    """Drop all of *app_id*'s runtime refs -- call from the app's uninstaller."""
    refs = _load(data_dir)
    changed = False
    for version in list(refs):
        if app_id in refs[version]:
            refs[version] = [app for app in refs[version] if app != app_id]
            changed = True
    if changed:
        _save(data_dir, refs)


def apps_requiring(data_dir: Path, runtime_version: str) -> list[str]:
    """The installed apps that still run on *runtime_version* (sorted)."""
    return _load(data_dir).get(str(runtime_version), [])


def is_referenced(data_dir: Path, runtime_version: str) -> bool:
    """True while at least one installed app still needs *runtime_version*."""
    return bool(apps_requiring(data_dir, runtime_version))


def unreferenced(data_dir: Path, candidates: Iterable[str]) -> list[str]:
    """Of *candidates*, the runtime versions no installed app needs -- removable."""
    refs = _load(data_dir)
    return sorted(
        version for version in {str(candidate) for candidate in candidates} if not refs.get(version)
    )
