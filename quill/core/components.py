"""Component reference counting -- who still needs each shared downloadable.

QuillVille apps share ONE component store (``%APPDATA%\\Quill``: ffmpeg, mpv,
speech engines, voices, models). This tracks which installed apps require each
component, so a component is fetched once, reused by every app that needs it,
and only becomes garbage-collectable when the last app that needs it is gone
(the runtime/component plan, S5). It is the dedup/GC heart, kept in ONE place.

App-owned, not installer-owned: each app declares its ``REQUIRED_COMPONENTS``
and calls :func:`register` on launch (idempotent); the uninstaller calls
:func:`unregister`. State lives in one file -- ``components.state.json`` in the
shared data dir -- and this module is wx-free and fully unit-testable.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic

_FILE_NAME = "components.state.json"


def _state_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def _load(data_dir: Path) -> dict[str, list[str]]:
    """The refs map: ``component_id -> sorted app_ids that require it``."""
    raw = read_json(_state_path(data_dir), {})
    refs: dict[str, list[str]] = {}
    if isinstance(raw, dict):
        entries = raw.get("refs")
        if isinstance(entries, dict):
            for component_id, apps in entries.items():
                if isinstance(apps, list):
                    refs[str(component_id)] = sorted(
                        {str(app) for app in apps if isinstance(app, str)}
                    )
    return refs


def _save(data_dir: Path, refs: dict[str, list[str]]) -> None:
    # Drop components with no remaining app so the file never accretes junk.
    clean = {cid: apps for cid, apps in refs.items() if apps}
    write_json_atomic(_state_path(data_dir), {"refs": clean})


def register(data_dir: Path, app_id: str, component_ids: Iterable[str]) -> None:
    """Record that *app_id* currently requires exactly *component_ids*.

    Idempotent -- safe to call on every launch. This app's ref is added to each
    id in *component_ids* and removed from any component it no longer needs, so
    the refs always reflect the app's live ``REQUIRED_COMPONENTS``.
    """
    wanted = {str(component_id) for component_id in component_ids}
    refs = _load(data_dir)
    for component_id in wanted:
        apps = set(refs.get(component_id, []))
        apps.add(app_id)
        refs[component_id] = sorted(apps)
    for component_id in list(refs):
        if component_id not in wanted and app_id in refs[component_id]:
            refs[component_id] = [app for app in refs[component_id] if app != app_id]
    _save(data_dir, refs)


def unregister(data_dir: Path, app_id: str) -> None:
    """Drop all of *app_id*'s refs -- call from the app's uninstaller step."""
    refs = _load(data_dir)
    changed = False
    for component_id in list(refs):
        if app_id in refs[component_id]:
            refs[component_id] = [app for app in refs[component_id] if app != app_id]
            changed = True
    if changed:
        _save(data_dir, refs)


def apps_requiring(data_dir: Path, component_id: str) -> list[str]:
    """The installed apps that still require *component_id* (sorted)."""
    return _load(data_dir).get(str(component_id), [])


def is_referenced(data_dir: Path, component_id: str) -> bool:
    """True while at least one installed app still needs *component_id*."""
    return bool(apps_requiring(data_dir, component_id))


def unreferenced(data_dir: Path, candidates: Iterable[str]) -> list[str]:
    """Of *candidates*, the ones no installed app requires -- GC-eligible."""
    refs = _load(data_dir)
    return sorted(
        component_id
        for component_id in {str(candidate) for candidate in candidates}
        if not refs.get(component_id)
    )
