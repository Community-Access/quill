"""Bundled NOAA Weather Radio directory snapshot loader.

Reads ``quill/data/noaa_directory.json`` -- a resilience snapshot of the
WeatherIndex directory generated offline by ``scripts/snapshot_wxindex.py`` --
so the app has station data even when the network or api.wxindex.org is
unavailable. Missing or corrupt snapshots are never fatal: they log and
return an empty ``Snapshot``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.radio.wxindex_models import WxState, WxStation, parse_states, parse_stations

_LOG = logging.getLogger(__name__)


@dataclass(slots=True)
class Snapshot:
    generated_at: str = ""
    states: list[WxState] = field(default_factory=list)
    stations: list[WxStation] = field(default_factory=list)


def snapshot_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "noaa_directory.json"


def load_snapshot() -> Snapshot:
    path = snapshot_path()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        _LOG.warning("NOAA directory snapshot unavailable (%s): %s", path, error)
        return Snapshot()
    if not isinstance(doc, dict):
        return Snapshot()
    return Snapshot(
        generated_at=str(doc.get("generated_at", "")),
        states=parse_states(doc.get("states", [])),
        stations=parse_stations(doc.get("stations", [])),
    )
