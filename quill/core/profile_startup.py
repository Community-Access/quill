"""Startup and per-file profile selection (issue #138).

Three ways to land in the right feature profile fast:

* prompt for a profile every time Quill starts (an opt-in setting), and/or
* prompt only when a modifier key is held while launching, and
* switch automatically based on the opened file's extension.

The preferences live in their own small JSON file (not the big Settings blob) so
the feature is self-contained. The decision logic here is pure so it can be
unit-tested without wx or a real launch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.features import PROFILE_DEFINITIONS
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_CONFIG_FILENAME = "profile_startup.json"


@dataclass(slots=True)
class ProfileStartupConfig:
    """Persisted preferences for startup / per-file profile selection."""

    prompt_on_startup: bool = False
    prompt_on_modifier: bool = True
    extension_map: dict[str, str] = field(default_factory=dict)

    def with_extension(self, extension: str, profile_id: str) -> ProfileStartupConfig:
        """Return a copy that maps ``extension`` to ``profile_id``."""
        updated = dict(self.extension_map)
        updated[normalize_extension(extension)] = profile_id
        return ProfileStartupConfig(
            prompt_on_startup=self.prompt_on_startup,
            prompt_on_modifier=self.prompt_on_modifier,
            extension_map=updated,
        )


def normalize_extension(extension: str) -> str:
    """Return a lowercase extension with a single leading dot (``Py`` -> ``.py``)."""
    cleaned = extension.strip().lower()
    if not cleaned:
        return ""
    return cleaned if cleaned.startswith(".") else f".{cleaned}"


def should_prompt_on_startup(config: ProfileStartupConfig, *, modifier_held: bool) -> bool:
    """Decide whether to show the profile picker at launch.

    True when the always-prompt setting is on, or when the modifier-prompt
    setting is on and a modifier key was held during launch.
    """
    if config.prompt_on_startup:
        return True
    return bool(config.prompt_on_modifier and modifier_held)


def profile_for_path(path: str | Path | None, config: ProfileStartupConfig) -> str | None:
    """Return the built-in profile id mapped to ``path``'s extension, if any.

    Returns ``None`` when there is no path, no mapping, or the mapped profile no
    longer exists (so a stale mapping can never select a missing profile).
    """
    if not path:
        return None
    extension = normalize_extension(Path(path).suffix)
    if not extension:
        return None
    profile_id = config.extension_map.get(extension)
    if profile_id in PROFILE_DEFINITIONS:
        return profile_id
    return None


def _config_path() -> Path:
    return app_data_dir() / _CONFIG_FILENAME


def load_profile_startup_config() -> ProfileStartupConfig:
    raw = read_json(_config_path(), {})
    if not isinstance(raw, dict):
        return ProfileStartupConfig()
    raw_map = raw.get("extension_map", {})
    extension_map: dict[str, str] = {}
    if isinstance(raw_map, dict):
        for key, value in raw_map.items():
            normalized = normalize_extension(str(key))
            if normalized and str(value) in PROFILE_DEFINITIONS:
                extension_map[normalized] = str(value)
    return ProfileStartupConfig(
        prompt_on_startup=bool(raw.get("prompt_on_startup", False)),
        prompt_on_modifier=bool(raw.get("prompt_on_modifier", True)),
        extension_map=extension_map,
    )


def save_profile_startup_config(config: ProfileStartupConfig) -> None:
    base = app_data_dir()
    payload = {
        "schema_version": 1,  # persistence contract: enables future migration
        "prompt_on_startup": bool(config.prompt_on_startup),
        "prompt_on_modifier": bool(config.prompt_on_modifier),
        "extension_map": dict(config.extension_map),
    }
    write_json_atomic(_config_path(), payload, base=base)
