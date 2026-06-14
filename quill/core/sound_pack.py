"""QSP (QUILL Sound Pack) loader.

A sound pack is either a ``.qsp`` ZIP archive or a plain directory sharing the
same layout:

    manifest.json           -- required; see quill/core/schemas/sound_pack.json
    expand.wav              -- any WAV files referenced by the manifest
    ...

Public API
----------
* :class:`SoundPack`       -- loaded pack: metadata + pre-buffered WAV bytes
* :class:`SoundPackError`  -- raised when a pack cannot be loaded
* :func:`validate_manifest` -- return a list of problems (empty == valid)
* :func:`load_sound_pack`  -- load and pre-buffer a pack from a path

The JSON schema at ``quill/core/schemas/sound_pack.json`` is the normative
contract for external tools. This module is the authority the loader enforces.
"""

from __future__ import annotations

import json
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)

_FORMAT = "qsp"
_VERSION = "1"
_MANIFEST_NAME = "manifest.json"
_TOP_LEVEL_KEYS = frozenset({
    "format",
    "version",
    "name",
    "author",
    "description",
    "license",
    "events",
})


# ---------------------------------------------------------------------------
# Public data model
# ---------------------------------------------------------------------------


@dataclass
class SoundPack:
    """A fully loaded sound pack ready for playback.

    ``events`` maps sound-event IDs (e.g. ``"abbreviation_expanded"``) to the
    raw bytes of the corresponding WAV file.  Only events whose WAV files were
    successfully read are present; missing files are logged and dropped.
    """

    name: str
    author: str
    description: str
    license: str
    events: dict[str, bytes] = field(default_factory=dict)


class SoundPackError(Exception):
    """Raised when a QSP pack cannot be loaded or its manifest is invalid."""


# ---------------------------------------------------------------------------
# Internal reader protocol: unifies ZIP and directory access
# ---------------------------------------------------------------------------


class _PackReader(Protocol):
    def read(self, name: str) -> bytes: ...
    def exists(self, name: str) -> bool: ...


class _ZipReader:
    def __init__(self, zf: zipfile.ZipFile) -> None:
        self._zf = zf
        self._names: frozenset[str] = frozenset(zf.namelist())

    def read(self, name: str) -> bytes:
        return self._zf.read(name)

    def exists(self, name: str) -> bool:
        return name in self._names


class _DirReader:
    def __init__(self, base: Path) -> None:
        self._base = base

    def read(self, name: str) -> bytes:
        return (self._base / name).read_bytes()

    def exists(self, name: str) -> bool:
        return (self._base / name).is_file()


# ---------------------------------------------------------------------------
# Manifest validation (hand-rolled; no jsonschema dependency)
# ---------------------------------------------------------------------------


def _require_str(value: object, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str):
        errors.append(f"{label} must be a string")
        return None
    return value


def validate_manifest(raw: object) -> list[str]:
    """Validate a parsed manifest object and return human-readable problems.

    Returns an empty list when ``raw`` is a valid QSP manifest.
    Never raises for a malformed manifest.
    """
    errors: list[str] = []
    if not isinstance(raw, dict):
        return ["manifest must be a JSON object"]

    for key in raw:
        if key not in _TOP_LEVEL_KEYS:
            errors.append(f"manifest has unknown property '{key}'")

    fmt = raw.get("format")
    if fmt != _FORMAT:
        errors.append(f"format must be '{_FORMAT}' (got {fmt!r})")

    ver = raw.get("version")
    if ver != _VERSION:
        errors.append(f"version must be '{_VERSION}' (got {ver!r})")

    name = _require_str(raw.get("name"), "name", errors)
    if name is not None and not (1 <= len(name) <= 80):
        errors.append("name must be 1-80 characters")

    for opt_key, max_len in (("author", 120), ("description", 400), ("license", 64)):
        if opt_key in raw:
            candidate = _require_str(raw.get(opt_key), opt_key, errors)
            if candidate is not None and len(candidate) > max_len:
                errors.append(f"{opt_key} must be at most {max_len} characters")

    events = raw.get("events")
    if not isinstance(events, dict):
        errors.append("events must be an object")
    else:
        for event_id, wav_path in events.items():
            if not isinstance(event_id, str) or not event_id:
                errors.append(f"events key {event_id!r} must be a non-empty string")
                continue
            if not isinstance(wav_path, str) or not wav_path:
                errors.append(f"events[{event_id!r}] must be a non-empty string path")
                continue
            if _path_is_unsafe(wav_path):
                errors.append(f"events[{event_id!r}] path {wav_path!r} must not use '..' segments")

    return errors


def _path_is_unsafe(wav_path: str) -> bool:
    """Return True when wav_path contains traversal sequences or is absolute."""
    parts = Path(wav_path).parts
    # Path.is_absolute() on Windows requires a drive letter, so a POSIX-style
    # leading slash (e.g. "/etc/passwd") would be missed.  Check both.
    if ".." in parts:
        return True
    if Path(wav_path).is_absolute():
        return True
    if wav_path.startswith("/") or wav_path.startswith("\\"):
        return True
    return False


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_sound_pack(path: Path) -> SoundPack:
    """Load and pre-buffer a QSP sound pack.

    ``path`` may be a ``.qsp`` ZIP file or a directory with the same layout.
    Raises :class:`SoundPackError` when the manifest is missing or invalid.
    WAV files referenced in the manifest but absent from the archive are logged
    and silently dropped; the pack still loads with the remaining events.
    """
    if path.is_dir():
        return _load_from_reader(path, _DirReader(path))
    if path.is_file():
        if not zipfile.is_zipfile(path):
            raise SoundPackError(f"{path}: not a ZIP archive and not a directory")
        with zipfile.ZipFile(path, "r") as zf:
            return _load_from_reader(path, _ZipReader(zf))
    raise SoundPackError(f"{path}: does not exist")


def _load_from_reader(path: Path, reader: _PackReader) -> SoundPack:
    if not reader.exists(_MANIFEST_NAME):
        raise SoundPackError(f"{path}: missing {_MANIFEST_NAME}")

    try:
        raw_json = json.loads(reader.read(_MANIFEST_NAME))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SoundPackError(f"{path}: {_MANIFEST_NAME} is not valid JSON: {exc}") from exc

    errors = validate_manifest(raw_json)
    if errors:
        problems = "; ".join(errors)
        raise SoundPackError(f"{path}: invalid manifest: {problems}")

    assert isinstance(raw_json, dict)

    pack = SoundPack(
        name=str(raw_json["name"]),
        author=str(raw_json.get("author", "")),
        description=str(raw_json.get("description", "")),
        license=str(raw_json.get("license", "")),
    )

    events: dict[str, object] = raw_json.get("events", {})
    assert isinstance(events, dict)

    for event_id, wav_path_raw in events.items():
        wav_path = str(wav_path_raw)
        if not reader.exists(wav_path):
            logger.warning("sound pack %s: missing WAV for '%s': %s", path.name, event_id, wav_path)
            continue
        try:
            pack.events[event_id] = reader.read(wav_path)
        except Exception:
            logger.warning(
                "sound pack %s: could not read WAV for '%s': %s",
                path.name,
                event_id,
                wav_path,
                exc_info=True,
            )

    logger.debug("sound pack '%s' loaded: %d event(s)", pack.name, len(pack.events))
    return pack
