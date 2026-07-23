"""Per-app feature areas the user can turn off (like QUILL's feature profiles,
but for the standalone companion apps -- Quill Radio, Quill Weather, Quill Cast).

Each app declares its major **areas** (e.g. Radio's "Weather" menu). A user can
switch any of them off, and the app honors that when it builds its menus -- a
disabled area simply is not created, so its menu (and every command under it)
disappears. Areas default to **on**; only an explicit "off" is stored, so a new
area added in a later version is enabled for everyone until they say otherwise.

The store is shared by the sibling apps (one data dir) but keyed by app id, so
turning "Weather" off in Quill Radio never touches Quill Cast. wx-free,
strict-typed, atomic JSON like the rest of the app stores.

Note: this is deliberately separate from ``core/features.FeatureManager`` (the
editor-feature catalog with profiles, unlock codes, and dependency chains).
That system treats an unknown id as *off*; app areas must default *on*, and are
a much simpler concern -- a flat set of "areas this user turned off."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_STORE_NAME = "app_area_features.json"


@dataclass(frozen=True, slots=True)
class AppArea:
    """One switchable area of an app (id, a short label, and a one-line why)."""

    id: str
    label: str
    description: str = ""


@dataclass(slots=True)
class AppFeatureSettings:
    """Which of an app's areas the user has turned off. Everything not listed is
    on, so unknown/new areas default enabled."""

    app_id: str
    disabled: set[str] = field(default_factory=set)

    def is_enabled(self, area_id: str) -> bool:
        return area_id not in self.disabled

    def set_enabled(self, area_id: str, enabled: bool) -> None:
        if enabled:
            self.disabled.discard(area_id)
        else:
            self.disabled.add(area_id)


def _store_path(data_dir: Path) -> Path:
    return data_dir / _STORE_NAME


def _read_all(data_dir: Path) -> dict:
    import json

    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def load_app_features(data_dir: Path, app_id: str) -> AppFeatureSettings:
    """Read one app's disabled-area set (absent or broken reads as all-on)."""
    raw = _read_all(data_dir)
    entry = raw.get(app_id)
    disabled: set[str] = set()
    if isinstance(entry, dict) and isinstance(entry.get("disabled"), list):
        disabled = {str(x) for x in entry["disabled"]}
    elif isinstance(entry, list):  # tolerate a bare list form
        disabled = {str(x) for x in entry}
    return AppFeatureSettings(app_id=app_id, disabled=disabled)


def save_app_features(data_dir: Path, settings: AppFeatureSettings) -> None:
    """Persist one app's disabled-area set without disturbing the others'."""
    from quill.core.storage import write_json_atomic

    raw = _read_all(data_dir)
    raw[settings.app_id] = {"disabled": sorted(settings.disabled)}
    write_json_atomic(_store_path(data_dir), raw)
