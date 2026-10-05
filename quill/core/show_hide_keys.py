"""The show/hide key a listener chose for Quill Weather, Converter or Media Player.

Those three registered a fixed key until 2026-10-05 and had nowhere to keep a
choice, so one small file in the shared data folder keeps it for all three:
``show_hide_keys.json``, ``{"schema": 1, "keys": {"weather": "", ...}}``.
Quill Inkwell keeps its own in ``InkwellSettings.tray_hotkey``, where it always
lived.

An app that is **missing** from the file has never decided, and its first
launch on this build decides (:func:`quill.core.family_chords.migrate_show_hide_key`)
and writes the answer -- which is what makes the "your key is now off" sentence
a once-only thing. Pure and wx-free.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "STORE_NAME",
    "has_run_before",
    "load_show_hide_key",
    "save_show_hide_key",
    "saved_keys",
]

STORE_NAME = "show_hide_keys.json"
SCHEMA = 1


def _read(data_dir: Path) -> dict[str, str]:
    from quill.core.storage import read_json

    raw = read_json(data_dir / STORE_NAME, default={})
    keys = raw.get("keys", {}) if isinstance(raw, dict) else {}
    if not isinstance(keys, dict):
        return {}
    return {str(app): str(key) for app, key in keys.items() if isinstance(key, str)}


def saved_keys(data_dir: Path) -> dict[str, str]:
    """``{app id: key}`` for every app that has decided (``""`` is "none")."""
    return _read(data_dir)


def save_show_hide_key(data_dir: Path, app_id: str, chord: str) -> None:
    """Keep *chord* (``""`` for none) as *app_id*'s show/hide key."""
    from quill.core.storage import write_json_atomic

    keys = _read(data_dir)
    keys[app_id] = chord.strip()
    write_json_atomic(data_dir / STORE_NAME, {"schema": SCHEMA, "keys": keys})


def has_run_before(data_dir: Path, app_id: str, *evidence: Path) -> bool:
    """Whether *app_id* has run on this machine: it has kept a window size
    (every family app does, on close, since 2026-09-10) or any *evidence* file
    of its own exists."""
    from quill.core.window_geometry import has_geometry

    try:
        return has_geometry(data_dir, app_id) or any(path.exists() for path in evidence)
    except OSError:
        return False


def load_show_hide_key(data_dir: Path, app_id: str, *, existing_user: bool) -> tuple[str, str]:
    """``(key to register, sentence to say once)`` for *app_id* at launch.

    The sentence is ``""`` except on the one launch that moved somebody off the
    old default. *existing_user* is whether this app has run on this machine
    before; somebody new is told nothing, because nothing changed for them.
    """
    from quill.core.family_chords import migrate_show_hide_key, retired_key_notice

    keys = _read(data_dir)
    if app_id in keys:
        return keys[app_id], ""
    chord, tell = migrate_show_hide_key(app_id, None, existing_user=existing_user)
    try:
        save_show_hide_key(data_dir, app_id, chord)
    except OSError:
        # Not written means asked again next time, which only costs the
        # sentence being said twice: not a reason to stop the app opening.
        pass
    return chord, retired_key_notice(app_id) if tell else ""
