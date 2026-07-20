"""Bundled Radio Reading Services snapshot loader.

Reads ``quill/data/reading_services.json`` -- a curated, hand-vetted list of
radio reading services for people who are blind or have print disabilities --
so the app can surface them without a live directory lookup. Missing or
corrupt snapshots are never fatal: they log and return an empty list.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from quill.core.radio.models import RadioStation

_LOG = logging.getLogger(__name__)


def reading_services_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "reading_services.json"


def load_reading_services() -> list[RadioStation]:
    path = reading_services_path()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        _LOG.warning("Radio Reading Services snapshot unavailable (%s): %s", path, error)
        return []
    if not isinstance(doc, dict):
        return []
    services = doc.get("services", [])
    if not isinstance(services, list):
        return []

    stations: list[RadioStation] = []
    for svc in services:
        if not isinstance(svc, dict):
            continue
        name = str(svc.get("name", "")).strip()
        stream_url = str(svc.get("stream_url", "")).strip()
        if not name or not stream_url:
            continue
        stations.append(
            RadioStation(
                name=name,
                stream_url=stream_url,
                station_uuid=str(svc.get("station_uuid", "")),
                homepage=str(svc.get("homepage", "")),
                country="United States",
                tags=("reading service", "blind"),
                source="Radio Reading Service",
            )
        )
    return stations
