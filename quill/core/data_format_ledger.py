"""The per-machine ledger of the newest data format ever written (plan 5.1).

``data-format-ledger.json`` sits in each data folder -- the shared
``%APPDATA%\\Quill`` (QUILL, Quill Radio, QUILL Cast), QUILL Lite's own folder,
or a portable copy's ``data`` folder -- and remembers, for each
:mod:`quill.core.data_formats` id, the highest version any build has written
there, and which build it was::

    {"version": 1,
     "formats": {"radio.favorites": {"high": 1, "by": "radio 3.2.0",
                                     "at": "2026-10-03T09:00:00+00:00"}}}

Each app calls :func:`record_running_build` once at start-up, before its first
save. The numbers only ever go up -- except through :func:`lower`, which only
a restore of a saved copy calls, because the files are then genuinely older.
"Is it safe to go back to Stable?" is answered from here
(:func:`quill.core.updater.going_back.downgrade_verdict`).

Recording never raises and never blocks a launch. wx-free and strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from quill.core.data_formats import DataFormat, formats_for

__all__ = [
    "LEDGER_NAME",
    "Ledger",
    "LedgerEntry",
    "ledger_folder",
    "lower",
    "read_ledger",
    "record",
    "record_running_build",
]

LEDGER_NAME = "data-format-ledger.json"
_SCHEMA = 1


@dataclass(frozen=True)
class LedgerEntry:
    high: int
    by: str = ""
    at: str = ""


@dataclass(frozen=True)
class Ledger:
    formats: dict[str, LedgerEntry] = field(default_factory=dict)

    def high(self, format_id: str) -> int:
        entry = self.formats.get(format_id)
        return entry.high if entry else 0

    def to_json(self) -> dict[str, object]:
        return {
            "version": _SCHEMA,
            "formats": {
                key: {"high": entry.high, "by": entry.by, "at": entry.at}
                for key, entry in sorted(self.formats.items())
            },
        }


def read_ledger(folder: Path) -> Ledger:
    """The ledger in *folder*; an absent or unreadable one is empty."""
    try:
        raw = json.loads((folder / LEDGER_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Ledger()
    formats_raw = raw.get("formats") if isinstance(raw, dict) else None
    if not isinstance(formats_raw, dict):
        return Ledger()
    formats: dict[str, LedgerEntry] = {}
    for key, value in formats_raw.items():
        if not isinstance(value, dict):
            continue
        try:
            high = int(value.get("high", 0))
        except (TypeError, ValueError):
            continue
        formats[str(key)] = LedgerEntry(
            high, str(value.get("by") or ""), str(value.get("at") or "")
        )
    return Ledger(formats)


def record(
    folder: Path,
    formats: tuple[DataFormat, ...],
    build: str,
    *,
    now: datetime | None = None,
) -> Ledger:
    """Raise each of *formats* in *folder*'s ledger to at least its ``current``.

    Writes only when something went up, so an ordinary launch touches nothing.
    """
    ledger = read_ledger(folder)
    updated = dict(ledger.formats)
    stamp = (now or datetime.now(UTC)).isoformat(timespec="seconds")
    changed = False
    for fmt in formats:
        if fmt.current > ledger.high(fmt.id):
            updated[fmt.id] = LedgerEntry(fmt.current, build, stamp)
            changed = True
    result = Ledger(updated)
    if changed:
        from quill.core.storage import write_json_atomic

        folder.mkdir(parents=True, exist_ok=True)
        write_json_atomic(folder / LEDGER_NAME, result.to_json())
    return result


def lower(
    folder: Path,
    formats: dict[str, int],
    build: str,
    *,
    now: datetime | None = None,
) -> Ledger:
    """Set each of *formats* to exactly its given version -- the restore case.

    Called only after a saved copy was written back: those files are what the
    copy says they are, so the ledger must say so too, or the next "is it safe
    to go back?" would refuse for formats no longer on disk.
    """
    ledger = read_ledger(folder)
    updated = dict(ledger.formats)
    stamp = (now or datetime.now(UTC)).isoformat(timespec="seconds")
    for format_id, version in formats.items():
        updated[format_id] = LedgerEntry(int(version), build, stamp)
    result = Ledger(updated)
    from quill.core.storage import write_json_atomic

    folder.mkdir(parents=True, exist_ok=True)
    write_json_atomic(folder / LEDGER_NAME, result.to_json())
    return result


def ledger_folder(app_key: str) -> Path:
    """The data folder whose ledger *app_key*'s formats are recorded in."""
    if app_key == "quilllite":
        from quill.core.lite.paths import data_dir

        return data_dir()
    from quill.core.paths import app_data_dir

    return app_data_dir()


def record_running_build(app_key: str, version: str) -> None:
    """The one call an app makes at start-up. Never raises.

    QUILL, Quill Radio and QUILL Cast record into the shared data folder;
    QUILL Lite into its own.
    """
    try:
        if app_key == "quilllite":
            from quill.core.lite.paths import data_dir

            folder = data_dir()
            wanted = "lite_data"
        else:
            from quill.core.paths import app_data_dir

            folder = app_data_dir()
            wanted = "quill_data"
        formats = tuple(f for f in formats_for(app_key) if f.location == wanted)
        if formats:
            record(folder, formats, f"{app_key} {version}".strip())
    except Exception:  # noqa: BLE001 - recording is never worth a failed launch
        return
