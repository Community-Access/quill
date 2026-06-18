"""Per-Quillin namespaced settings storage.

Each Quillin receives an isolated JSON store at::

    %APPDATA%\\Quill\\quillin_settings\\<quillin-id>.json

Writes are atomic (temp-file + os.replace). Reads return a shallow copy so
callers cannot mutate the in-memory cache. The store survives app restarts and
is kept even when a Quillin is disabled; only an explicit delete call or an
uninstall that chooses "Delete settings" removes it.

This module imports no ``wx`` and no platform code so it can be used from
``quill/core`` and from Quillin host code without import cycles.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import write_json_atomic

_ID_PATTERN = re.compile(r"^[a-z0-9]+([._-][a-z0-9]+)*$")
_SETTINGS_SUBDIR = "quillin_settings"


def _settings_dir() -> Path:
    return app_data_dir() / _SETTINGS_SUBDIR


def _settings_path(quillin_id: str) -> Path:
    if not _ID_PATTERN.match(quillin_id):
        raise ValueError(f"Invalid Quillin id: {quillin_id!r}")
    return _settings_dir() / f"{quillin_id}.json"


def load_settings(quillin_id: str) -> dict[str, object]:
    """Return all stored settings for *quillin_id*, or an empty dict if none exist."""
    path = _settings_path(quillin_id)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return dict(data)
    except (json.JSONDecodeError, OSError):
        return {}


def get_setting(quillin_id: str, key: str, default: object = None) -> object:
    """Return the stored value for *key* in *quillin_id*'s settings, or *default*."""
    return load_settings(quillin_id).get(key, default)


def save_settings(quillin_id: str, settings: dict[str, object]) -> None:
    """Atomically persist *settings* for *quillin_id*, replacing all prior data."""
    path = _settings_path(quillin_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, copy.deepcopy(settings))


def set_setting(quillin_id: str, key: str, value: object) -> None:
    """Update a single *key* in *quillin_id*'s settings store."""
    current = load_settings(quillin_id)
    current[key] = value
    save_settings(quillin_id, current)


def reset_setting(quillin_id: str, key: str, default: object = None) -> None:
    """Reset *key* to *default* (removes the key if *default* is None)."""
    current = load_settings(quillin_id)
    if default is None:
        current.pop(key, None)
    else:
        current[key] = default
    save_settings(quillin_id, current)


def reset_all_settings(quillin_id: str) -> None:
    """Delete all stored settings for *quillin_id* (equivalent to the manifest defaults)."""
    path = _settings_path(quillin_id)
    if path.is_file():
        path.unlink()


def delete_settings_file(quillin_id: str) -> bool:
    """Remove the settings file entirely. Returns True if a file was deleted."""
    path = _settings_path(quillin_id)
    if path.is_file():
        path.unlink()
        return True
    return False


def apply_defaults(quillin_id: str, manifest_defaults: dict[str, object]) -> None:
    """Write *manifest_defaults* for any key not yet present in the stored settings.

    Called once when a Quillin is first loaded so fresh installs start with
    manifest-declared defaults without overwriting values the user has already changed.
    """
    current = load_settings(quillin_id)
    updated = False
    for key, value in manifest_defaults.items():
        if key not in current:
            current[key] = copy.deepcopy(value)
            updated = True
    if updated:
        save_settings(quillin_id, current)


def settings_path_for(quillin_id: str) -> Path:
    """Return the Path where *quillin_id*'s settings are stored (may not exist yet)."""
    return _settings_path(quillin_id)
