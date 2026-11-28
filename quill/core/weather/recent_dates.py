"""The last ten dates looked at in Weather on a Past Date, newest first, with
the place each was looked at for. Saved atomically to
``weather_recent_dates.json``; a missing or damaged file reads as empty.

wx-free and strict-typed.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

_STORE_NAME = "weather_recent_dates.json"
MAX_RECENT = 10


@dataclass(frozen=True, slots=True)
class RecentDate:
    date: str  # ISO
    place_id: str
    place_label: str


def store_path(data_dir: Path) -> Path:
    return data_dir / _STORE_NAME


def load(data_dir: Path) -> list[RecentDate]:
    try:
        raw = json.loads(store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out: list[RecentDate] = []
    for item in raw.get("recent", []) if isinstance(raw, dict) else []:
        if not isinstance(item, dict):
            continue
        iso, place = item.get("date"), item.get("place_id")
        if not (isinstance(iso, str) and isinstance(place, str)):
            continue
        try:
            date.fromisoformat(iso)
        except ValueError:
            continue
        out.append(RecentDate(iso, place, str(item.get("place_label", ""))[:200]))
    return out[:MAX_RECENT]


def remember(entries: list[RecentDate], entry: RecentDate) -> list[RecentDate]:
    """*entry* first, without a repeat of the same date and place, at most ten."""
    kept = [e for e in entries if (e.date, e.place_id) != (entry.date, entry.place_id)]
    return [entry, *kept][:MAX_RECENT]


def save(data_dir: Path, entries: list[RecentDate]) -> None:
    """Best effort: a failed save never breaks looking at a day."""
    from quill.core.storage import write_json_atomic

    payload = {
        "version": 1,
        "recent": [
            {"date": e.date, "place_id": e.place_id, "place_label": e.place_label}
            for e in entries[:MAX_RECENT]
        ],
    }
    try:
        write_json_atomic(store_path(data_dir), payload)
    except OSError as exc:
        logger.warning("could not save recent weather dates: %s", exc)
