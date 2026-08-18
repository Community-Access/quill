"""Which podcast confirmations are still wanted. Tiny, shared, its own file.

One store for both apps on purpose: Mark All as Played is the same verb over
the same library in Quill Cast and Quill Radio, so "Don't ask me again"
checked in either app should quiet both -- two flags would mean the question
comes back in the other app and looks ignored. This is NOT the library file
(``podcasts.json``), so the Radio-must-never-write-the-library clobber rule
does not apply; worst case for a simultaneous write is one boolean.

wx-free, strict-typed, never raises: asking one extra time is always safer
than crashing, so every failure answers the default.
"""

from __future__ import annotations

import json
from pathlib import Path

_FILE_NAME = "podcast-ask-prefs.json"

_MARK_ALL_KEY = "ask_before_mark_all_played"


def _path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def _read(data_dir: Path) -> dict:
    try:
        raw = json.loads(_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def ask_before_mark_all_played(data_dir: Path) -> bool:
    """Whether Mark All as Played still confirms first. Default: it does."""
    try:
        return bool(_read(data_dir).get(_MARK_ALL_KEY, True))
    except Exception:  # noqa: BLE001 - asking again is the safe answer
        return True


def set_ask_before_mark_all_played(data_dir: Path, ask: bool) -> None:
    """Persist the choice (atomic). Best effort; never raises."""
    try:
        from quill.core.storage import write_json_atomic

        prefs = _read(data_dir)
        prefs[_MARK_ALL_KEY] = bool(ask)
        write_json_atomic(_path(data_dir), prefs)
    except Exception:  # noqa: BLE001 - a lost preference must never cost the action
        return
