"""JSON schemas for the verbosity data files (verbosity §20, §30, §35).

These are the data contracts the later sub-PRs validate against: the persisted
verbosity settings, the custom-profile store, a QUILL Verbosity Pack (``.qvp.json``),
and an exported/imported profile. They are plain draft-07 schema dicts so the
QVP loader (sub-PR 1.3) and storage layer (sub-PR 1.2) can validate without any
code execution — QVP files are strictly data.

Pure and wx-free.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = [
    "VERBOSITY_SETTINGS_SCHEMA",
    "CUSTOM_PROFILE_SCHEMA",
    "QVP_SCHEMA",
    "PROFILE_IO_SCHEMA",
    "SCHEMAS",
    "schema_for",
]

_CHANNEL_NAMES = ["SPEECH", "BRAILLE", "SOUND", "VISUAL"]
_PROFILE_NAMES = ["Beginner", "Normal", "Expert", "Quiet"]

VERBOSITY_SETTINGS_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "QUILL verbosity settings",
    "type": "object",
    "properties": {
        "profile": {"type": "string", "enum": _PROFILE_NAMES},
        "channels": {
            "type": "array",
            "items": {"type": "string", "enum": _CHANNEL_NAMES},
            "uniqueItems": True,
        },
        "validation_timing": {"type": "string", "enum": ["live", "on_focus", "on_button"]},
        "quiet_mode": {"type": "boolean"},
        "meeting_mode": {"type": "boolean"},
    },
    "additionalProperties": True,
}

CUSTOM_PROFILE_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "QUILL custom verbosity profile",
    "type": "object",
    "required": ["name"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "base": {"type": "string", "enum": _PROFILE_NAMES},
        "channels": {
            "type": "array",
            "items": {"type": "string", "enum": _CHANNEL_NAMES},
            "uniqueItems": True,
        },
        "per_verb_overrides": {"type": "object", "additionalProperties": {"type": "string"}},
        "per_chord_overrides": {"type": "object", "additionalProperties": {"type": "string"}},
        "templates": {"type": "object", "additionalProperties": {"type": "string"}},
        "data_order": {
            "type": "object",
            "additionalProperties": {"type": "array", "items": {"type": "string"}},
        },
    },
    "additionalProperties": False,
}


def _load_qvp_schema() -> dict[str, Any]:
    """Load the canonical QVP schema from ``quill/core/schemas/qvp.json``.

    The ``.qvp.json`` format is defined once, in that file, and validated by hand
    in :mod:`quill.core.verbosity.qvp` (QUILL ships no jsonschema runtime
    dependency). Exposing it here keeps a single source of truth.
    """
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "qvp.json"
    try:
        loaded = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):  # pragma: no cover - shipped asset
        return {}
    return loaded if isinstance(loaded, dict) else {}


#: The canonical ``.qvp.json`` pack schema (loaded from the shipped JSON file).
QVP_SCHEMA: dict[str, Any] = _load_qvp_schema()

PROFILE_IO_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "QUILL verbosity profile import/export",
    "type": "object",
    "required": ["format", "profile"],
    "properties": {
        "format": {"const": "quill-verbosity-profile"},
        "version": {"type": "string"},
        "profile": CUSTOM_PROFILE_SCHEMA,
    },
    "additionalProperties": False,
}

#: Schemas keyed by short name.
SCHEMAS: dict[str, dict[str, Any]] = {
    "settings": VERBOSITY_SETTINGS_SCHEMA,
    "custom_profile": CUSTOM_PROFILE_SCHEMA,
    "qvp": QVP_SCHEMA,
    "profile_io": PROFILE_IO_SCHEMA,
}


def schema_for(name: str) -> dict[str, Any]:
    """Return the schema registered under ``name`` (raises ``KeyError`` if unknown)."""
    return SCHEMAS[name]
