"""The permanent, per-place cache behind Weather History.

The past does not change, so a day once fetched is kept for good: the second
look at a date costs no request at all, which is what keeps a history window
inside Open-Meteo's free daily allowance. Two exceptions, because the newest
data is still settling: a day in the last :data:`SETTLING_DAYS` is refetched
after :data:`SETTLING_TTL_SECONDS`, and station records (which a new record can
change) are refetched after :data:`RECORDS_TTL_SECONDS`.

One JSON file per place (coordinates rounded to two decimals, about a
kilometre), under ``weather_history/`` in the data folder. Values are kept in
metric -- degrees Celsius, millimetres, km/h -- so changing the temperature unit
never empties the cache. Writes are atomic; a damaged file reads as empty.

wx-free and strict-typed.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SCHEMA = 1
SETTLING_DAYS = 7
SETTLING_TTL_SECONDS = 6 * 60 * 60
RECORDS_TTL_SECONDS = 30 * 24 * 60 * 60
STATION_TTL_SECONDS = 365 * 24 * 60 * 60
#: Bounds on one place's file.
MAX_DAYS = 12_000
MAX_DAY_KEYS = 400  # normals and records, by "MM-DD"
MAX_DETAILS = 400  # whole days with their hours (Weather on a Past Date)


@dataclass(slots=True)
class DayRecord:
    """One day's weather, in metric. ``source`` is ``recent`` (Open-Meteo's
    forecast service, the last 92 days) or ``archive`` (ERA5 reanalysis)."""

    date: str
    code: int | None = None
    high_c: float | None = None
    low_c: float | None = None
    precip_mm: float | None = None
    snow_cm: float | None = None
    wind_max_kmh: float | None = None
    source: str = "archive"

    @classmethod
    def from_json(cls, raw: Any) -> DayRecord | None:
        if not isinstance(raw, dict) or not isinstance(raw.get("date"), str):
            return None
        return cls(
            date=raw["date"],
            code=_opt_int(raw.get("code")),
            high_c=_opt_num(raw.get("high_c")),
            low_c=_opt_num(raw.get("low_c")),
            precip_mm=_opt_num(raw.get("precip_mm")),
            snow_cm=_opt_num(raw.get("snow_cm")),
            wind_max_kmh=_opt_num(raw.get("wind_max_kmh")),
            source=str(raw.get("source", "archive"))[:12],
        )

    @property
    def has_data(self) -> bool:
        return self.high_c is not None or self.low_c is not None or self.precip_mm is not None


def _opt_num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _opt_int(value: Any) -> int | None:
    number = _opt_num(value)
    return round(number) if number is not None else None


def place_key(latitude: float, longitude: float) -> str:
    return f"{latitude:.2f},{longitude:.2f}"


def _file_name(key: str) -> str:
    return re.sub(r"[^0-9A-Za-z.-]", "_", key) + ".json"


class HistoryCache:
    """One place's cached days, ACIS station, normals and records."""

    def __init__(self, data_dir: Path | None, latitude: float, longitude: float) -> None:
        self.key = place_key(latitude, longitude)
        self.path = (
            data_dir / "weather_history" / _file_name(self.key) if data_dir is not None else None
        )
        self.days: dict[str, tuple[DayRecord, float]] = {}
        self.station: dict[str, Any] | None = None
        self.station_fetched = 0.0
        self.normals: dict[str, dict[str, Any]] = {}
        self.records: dict[str, dict[str, Any]] = {}
        #: ISO date -> (a PastDay as JSON, when it was fetched)
        self.details: dict[str, tuple[dict[str, Any], float]] = {}
        self.dirty = False
        self._load()

    # -- days -------------------------------------------------------------

    def get_day(self, iso: str, *, today: date, now: float) -> DayRecord | None:
        entry = self.days.get(iso)
        if entry is None:
            return None
        record, fetched = entry
        if date.fromisoformat(iso) >= today - timedelta(days=SETTLING_DAYS):
            if now - fetched >= SETTLING_TTL_SECONDS or iso == today.isoformat():
                return None
        return record

    def put_day(self, record: DayRecord, now: float) -> None:
        self.days[record.date] = (record, now)
        self.dirty = True

    # -- whole days -------------------------------------------------------

    def get_detail(self, iso: str, *, today: date, now: float) -> dict[str, Any] | None:
        entry = self.details.get(iso)
        if entry is None:
            return None
        detail, fetched = entry
        if date.fromisoformat(iso) >= today - timedelta(days=SETTLING_DAYS):
            if now - fetched >= SETTLING_TTL_SECONDS or iso == today.isoformat():
                return None
        return detail

    def put_detail(self, iso: str, detail: dict[str, Any], now: float) -> None:
        self.details[iso] = (detail, now)
        self.dirty = True

    # -- ACIS -------------------------------------------------------------

    def get_station(self, now: float) -> dict[str, Any] | None:
        if self.station is None or now - self.station_fetched >= STATION_TTL_SECONDS:
            return None
        return self.station

    def put_station(self, station: dict[str, Any], now: float) -> None:
        self.station, self.station_fetched = station, now
        self.dirty = True

    def get_normals(self, month_day: str, station_id: str) -> dict[str, Any] | None:
        entry = self.normals.get(month_day)
        return entry if entry and entry.get("station") == station_id else None

    def put_normals(self, month_day: str, values: dict[str, Any]) -> None:
        self.normals[month_day] = values
        self.dirty = True

    def get_records(self, month_day: str, station_id: str, now: float) -> dict[str, Any] | None:
        entry = self.records.get(month_day)
        if not entry or entry.get("station") != station_id:
            return None
        if now - float(entry.get("fetched", 0)) >= RECORDS_TTL_SECONDS:
            return None
        return entry

    def put_records(self, month_day: str, values: dict[str, Any], now: float) -> None:
        self.records[month_day] = {**values, "fetched": now}
        self.dirty = True

    # -- persistence -------------------------------------------------------

    def _load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning("weather history cache %s unreadable (%s); ignoring", self.path, exc)
            return
        if not isinstance(raw, dict) or raw.get("version") != _SCHEMA:
            return
        for item in raw.get("days") or []:
            record = DayRecord.from_json(item)
            fetched = item.get("fetched") if isinstance(item, dict) else None
            if record is not None and isinstance(fetched, int | float):
                self.days[record.date] = (record, float(fetched))
        for item in raw.get("details") or []:
            if isinstance(item, dict) and isinstance(item.get("date"), str):
                fetched = item.get("fetched")
                body = item.get("day")
                if isinstance(fetched, int | float) and isinstance(body, dict):
                    self.details[item["date"]] = (body, float(fetched))
        station = raw.get("station")
        if isinstance(station, dict) and isinstance(station.get("sid"), str):
            self.station = station
            self.station_fetched = float(raw.get("station_fetched") or 0)
        for name in ("normals", "records"):
            block = raw.get(name)
            if isinstance(block, dict):
                getattr(self, name).update({
                    k: v for k, v in block.items() if isinstance(k, str) and isinstance(v, dict)
                })

    def save(self) -> None:
        """Atomic, bounded and best effort. Only writes when something changed."""
        if self.path is None or not self.dirty:
            return
        from quill.core.storage import write_json_atomic

        days = sorted(self.days.values(), key=lambda pair: pair[1])[-MAX_DAYS:]
        payload = {
            "version": _SCHEMA,
            "place": self.key,
            "days": [{**asdict(record), "fetched": fetched} for record, fetched in days],
            "details": [
                {"date": iso, "day": body, "fetched": fetched}
                for iso, (body, fetched) in sorted(
                    self.details.items(), key=lambda pair: pair[1][1]
                )[-MAX_DETAILS:]
            ],
            "station": self.station,
            "station_fetched": self.station_fetched,
            "normals": dict(list(self.normals.items())[-MAX_DAY_KEYS:]),
            "records": dict(list(self.records.items())[-MAX_DAY_KEYS:]),
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            write_json_atomic(self.path, payload)
            self.dirty = False
        except OSError as exc:
            logger.warning("could not save weather history cache: %s", exc)
