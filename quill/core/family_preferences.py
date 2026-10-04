"""Choices shared between the Quill apps, only when you ask (qc.md X-05).

A few preferences mean exactly the same thing in every Quill app that has
them -- whether a window's name is said as it opens and closes, and whether a
one-key action answers with a sound, words or both. Somebody who sets one in
QUILL Cast may well want it in Quill Radio too. This lets them say so:

* **Off until you turn it on, per app.** An app joins by its own checkbox
  ("Share these choices with my other Quill apps"); nothing is shared from or
  into an app that has not joined.
* **Only what means the same everywhere.** :data:`SHARED` is the whole list.
  Nothing about keys, focus, or how the screen reader is driven is ever on it.
* **Never silent.** When an app picks up a shared choice at launch, it says
  which, once.

The record is a small file in the shared data folder. wx-free, strict-typed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = ["SHARED", "adopt", "is_sharing", "publish", "set_sharing", "words_for"]

_FILE = "family_preferences.json"

#: Field name -> how it is named when a listener is told it changed.
SHARED: dict[str, str] = {
    "announce_dialog_transitions": "announce dialog transitions",
    "action_feedback": "what a one-key action answers with",
}


def _read(data_dir: Path) -> dict[str, Any]:
    try:
        raw = json.loads((data_dir / _FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"apps": {}, "values": {}}
    if not isinstance(raw, dict):
        return {"apps": {}, "values": {}}
    apps_raw = raw.get("apps")
    values_raw = raw.get("values")
    apps: dict[str, Any] = apps_raw if isinstance(apps_raw, dict) else {}
    values: dict[str, Any] = values_raw if isinstance(values_raw, dict) else {}
    return {
        "apps": {str(k): bool(v) for k, v in apps.items()},
        "values": {str(k): v for k, v in values.items() if k in SHARED},
    }


def _write(data_dir: Path, record: dict[str, Any]) -> None:
    from quill.core.storage import write_json_atomic

    write_json_atomic(data_dir / _FILE, {"version": 1, **record})


def is_sharing(data_dir: Path, app: str) -> bool:
    return bool(_read(data_dir)["apps"].get(app, False))


def publish(data_dir: Path, app: str, source: Any) -> None:
    """When *app* shares, record its current values of every shared choice it has."""
    record = _read(data_dir)
    if not record["apps"].get(app):
        return
    for name in SHARED:
        if hasattr(source, name):
            record["values"][name] = getattr(source, name)
    _write(data_dir, record)


def adopt(data_dir: Path, app: str, target: Any) -> list[str]:
    """When *app* shares, take the shared values it differs on. Returns the
    names changed, so the caller can say so."""
    record = _read(data_dir)
    if not record["apps"].get(app):
        return []
    changed: list[str] = []
    for name, value in record["values"].items():
        if not hasattr(target, name):
            continue
        current = getattr(target, name)
        if type(current) is not type(value) or current == value:
            continue
        setattr(target, name, value)
        changed.append(name)
    return changed


def set_sharing(data_dir: Path, app: str, on: bool, current: Any) -> list[str]:
    """Join or leave. Joining takes any shared values already recorded (and
    returns their names); with none recorded yet, this app's become the shared ones."""
    record = _read(data_dir)
    record["apps"][app] = bool(on)
    _write(data_dir, record)
    if not on:
        return []
    if record["values"]:
        return adopt(data_dir, app, current)
    publish(data_dir, app, current)
    return []


def words_for(names: list[str]) -> str:
    """ "announce dialog transitions and what a one-key action answers with" """
    said = [SHARED.get(name, name) for name in names]
    if len(said) <= 1:
        return "".join(said)
    return ", ".join(said[:-1]) + " and " + said[-1]
