"""Persistence for verbosity customizations (verbosity §35).

The user's verbosity customizations — templates, per-verb and per-chord
overrides, custom profiles, data-order overrides, mastery state, and feedback
signals — live in ``verbosity_custom.json`` beside the other app data. Writes go
through :func:`quill.core.storage.write_json_atomic` (temp file + atomic
replace), so a crash mid-write can never tear the file. A corrupt file loads as
empty defaults with a load error the caller can surface as a nonblocking
warning, rather than throwing the user out.

Pure of ``wx``; touches the filesystem only through the shared storage helpers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import write_json_atomic

__all__ = [
    "VerbosityCustomData",
    "LoadResult",
    "verbosity_custom_path",
    "load_custom",
    "save_custom",
]

_FILENAME = "verbosity_custom.json"


def verbosity_custom_path() -> Path:
    """The on-disk location of ``verbosity_custom.json``."""
    return app_data_dir() / _FILENAME


@dataclass(slots=True)
class VerbosityCustomData:
    """The mutable bundle of user verbosity customizations."""

    templates: dict[str, str] = field(default_factory=dict)
    per_verb_overrides: dict[str, str] = field(default_factory=dict)
    per_chord_overrides: dict[str, str] = field(default_factory=dict)
    custom_profiles: dict[str, Any] = field(default_factory=dict)
    data_order: dict[str, list[str]] = field(default_factory=dict)
    mastery: dict[str, Any] = field(default_factory=dict)
    feedback: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "templates": dict(self.templates),
            "per_verb_overrides": dict(self.per_verb_overrides),
            "per_chord_overrides": dict(self.per_chord_overrides),
            "custom_profiles": dict(self.custom_profiles),
            "data_order": {k: list(v) for k, v in self.data_order.items()},
            "mastery": dict(self.mastery),
            "feedback": dict(self.feedback),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerbosityCustomData:
        return cls(
            templates={str(k): str(v) for k, v in data.get("templates", {}).items()},
            per_verb_overrides={
                str(k): str(v) for k, v in data.get("per_verb_overrides", {}).items()
            },
            per_chord_overrides={
                str(k): str(v) for k, v in data.get("per_chord_overrides", {}).items()
            },
            custom_profiles=dict(data.get("custom_profiles", {})),
            data_order={
                str(k): [str(item) for item in v] for k, v in data.get("data_order", {}).items()
            },
            mastery=dict(data.get("mastery", {})),
            feedback=dict(data.get("feedback", {})),
        )


@dataclass(frozen=True, slots=True)
class LoadResult:
    """The outcome of loading the custom file: data plus an optional error."""

    data: VerbosityCustomData
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def load_custom(path: Path | None = None) -> LoadResult:
    """Load ``verbosity_custom.json``; on corruption return empty defaults + error.

    A missing file is normal (fresh install) and loads as empty defaults with no
    error. A present-but-corrupt file loads as empty defaults with an ``error``
    string the UI should show as a nonblocking warning.
    """
    target = path or verbosity_custom_path()
    if not target.exists():
        return LoadResult(VerbosityCustomData())
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        return LoadResult(VerbosityCustomData(), f"Could not read {target.name}: {error}")
    if not isinstance(raw, dict):
        return LoadResult(VerbosityCustomData(), f"{target.name} is not a JSON object")
    return LoadResult(VerbosityCustomData.from_dict(raw))


def save_custom(data: VerbosityCustomData, path: Path | None = None) -> Path:
    """Atomically write ``data`` to ``verbosity_custom.json``; return the path."""
    target = path or verbosity_custom_path()
    write_json_atomic(target, data.to_dict())
    return target
