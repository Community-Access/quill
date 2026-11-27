"""Reading and writing ``abbreviations.json`` -- the on-disk schema, in one place.

Extracted from :mod:`quill.core.abbreviations` when per-application scoping
arrived and that module reached its GATE-11 ceiling. The cut is a real seam:
everything here is about the **file**, and everything left behind is about what
an abbreviation *does*. They change for different reasons -- a new expansion
variable does not touch the schema, and a new stored field does not touch
matching.

Three rules the format keeps, stated where the format is written:

* **Every field defaults.** A v1 file has none of the v2 keys and loads
  unchanged.
* **A field nobody set is not written.** ``apps`` appears only on an entry
  somebody actually scoped, so a library nobody has scoped stays byte-for-byte
  what it was.
* **A corrupt file degrades to the built-in defaults**, never to an empty
  library -- silently wiping somebody's abbreviations is the worst thing a
  loader here could do. The damaged file is copied aside first and Quill
  Inkwell says once where (:func:`_keep_damaged_library`, FUX-05): the next
  save writes the defaults over ``abbreviations.json``, and until 2026-11-24
  that was the end of the person's library, with nothing said.

Re-exported from ``quill.core.abbreviations`` so every existing import keeps
working.

wx-free, strict-typed.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from quill.core.abbreviations import (
    _ABBREVIATIONS_FILE,
    SCHEMA_VERSION,
    SOUND_MODES,
    SPEAK_MODES,
    TRIGGER_MODES,
    Abbreviation,
    AbbreviationLibrary,
    _make_default_library,
)
from quill.core.storage import write_json_atomic


def _one_of(value: object, allowed: tuple[str, ...], default: str) -> str:
    """*value* when it is one of *allowed*, else *default* (unknown values in a
    hand-edited file degrade to the safe setting rather than breaking the load)."""
    text = str(value) if value is not None else ""
    return text if text in allowed else default


def _app_names(value: object) -> tuple[str, ...]:
    """A stored ``apps`` list as normalised executable stems.

    Normalised on the way in rather than at match time: the file may be
    hand-edited, "Outlook.exe" and "outlook" are the same application, and
    comparing them on every keystroke would be doing this work thousands of
    times to reach the same answer.
    """
    if not isinstance(value, (list, tuple)):
        return ()
    names: list[str] = []
    for raw in value:
        name = str(raw or "").strip().lower()
        if name.endswith(".exe"):
            name = name[: -len(".exe")]
        if name and name not in names:
            names.append(name)
    return tuple(names)


def _as_int(value: object) -> int:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else 0


def entry_from_dict(raw: dict[str, object]) -> Abbreviation:
    """One stored entry, every field defaulting: the library file and an export alike.

    Shared with Manage Abbreviations' Import, so an exported file brings every
    per-entry setting back rather than only the typed and expanded text.
    """
    return Abbreviation(
        id=str(raw.get("id") or uuid.uuid4()),
        abbreviation=str(raw.get("abbreviation", "")),
        expansion=str(raw.get("expansion", "")),
        case_sensitive=bool(raw.get("case_sensitive", False)),
        enabled=bool(raw.get("enabled", True)),
        description=str(raw.get("description", "")),
        # v2 per-entry settings. Every one defaults, so a v1 file
        # (which has none of these keys) loads unchanged.
        category=str(raw.get("category", "")),
        speak_mode=_one_of(raw.get("speak_mode"), SPEAK_MODES, "silent"),
        sound=_one_of(raw.get("sound"), SOUND_MODES, "inherit"),
        trailing_space=bool(raw.get("trailing_space", False)),
        triggers=_one_of(raw.get("triggers"), TRIGGER_MODES, "both"),
        usage_count=_as_int(raw.get("usage_count")),
        last_used=str(raw.get("last_used", "")),
        apps=_app_names(raw.get("apps")),
    )


def entry_to_dict(a: Abbreviation) -> dict[str, object]:
    """One entry as it is stored, and as Export writes it (the same shape)."""
    return {
        "id": a.id,
        "abbreviation": a.abbreviation,
        "expansion": a.expansion,
        "case_sensitive": a.case_sensitive,
        "enabled": a.enabled,
        "description": a.description,
        "category": a.category,
        "speak_mode": a.speak_mode,
        "sound": a.sound,
        "trailing_space": a.trailing_space,
        "triggers": a.triggers,
        "usage_count": a.usage_count,
        "last_used": a.last_used,
        # Written only when set, so a library nobody has scoped
        # stays byte-for-byte what it was.
        **({"apps": list(a.apps)} if a.apps else {}),
    }


def load_abbreviation_library(data_dir: Path | None = None) -> AbbreviationLibrary:
    from quill.core import paths
    from quill.core.storage import read_json

    base = data_dir if data_dir is not None else paths.app_data_dir()
    path = base / _ABBREVIATIONS_FILE
    if not path.exists():
        return _make_default_library()
    # read_json returns its default (not a raise) on a corrupt/unreadable file.
    # Use a sentinel so a present-but-corrupt file degrades to the built-in
    # defaults rather than an empty library (passing default={} would look like
    # a valid-but-empty payload and silently wipe the user's abbreviations).
    corrupt = object()
    try:
        data = read_json(path, default=corrupt)
    except Exception:  # noqa: BLE001
        data = corrupt
    if data is corrupt or not isinstance(data, dict):
        _keep_damaged_library(path)
        return _make_default_library()
    abbreviations: list[Abbreviation] = []
    for raw in data.get("abbreviations", []):
        if not isinstance(raw, dict):
            continue
        try:
            abbreviations.append(entry_from_dict(raw))
        except Exception:  # noqa: BLE001
            continue
    return AbbreviationLibrary(
        version=int(data.get("version", 1)),
        abbreviations=abbreviations,
    )


def _keep_damaged_library(path: Path) -> None:
    """Copy an unreadable library aside and queue Inkwell's one sentence about it."""
    from quill.core.settings_recovery import keep_damaged

    def said(copy: Path | None) -> str:
        if copy is None:
            return (
                "Your abbreviation library could not be read, so Quill Inkwell started "
                "with its built-in abbreviations. It could not copy the file aside: "
                f"{path.name} is still in {path.parent}, and it is replaced the next "
                "time an abbreviation is saved."
            )
        return (
            "Your abbreviation library could not be read, so Quill Inkwell started "
            f"with its built-in abbreviations. Your library was kept as {copy.name}, "
            f"in {copy.parent}."
        )

    keep_damaged(path, app="Quill Inkwell", what="abbreviations", sentence=said)


def save_abbreviation_library(library: AbbreviationLibrary, data_dir: Path | None = None) -> None:
    from quill.core import paths

    base = data_dir if data_dir is not None else paths.app_data_dir()
    path = base / _ABBREVIATIONS_FILE
    write_json_atomic(
        path,
        {
            "version": SCHEMA_VERSION,
            "abbreviations": [entry_to_dict(a) for a in library.abbreviations],
        },
    )
