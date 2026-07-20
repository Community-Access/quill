"""wx-free WeatherIndex (NOAA Weather Radio) domain model + JSON parsers."""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.radio.models import RadioStation

_SOURCE = "NOAA Weather Radio"


@dataclass(slots=True, frozen=True)
class WxState:
    slug: str
    name: str
    station_count: int = 0
    #: How many of this state's transmitters have a playable internet re-stream
    #: (the WeatherIndex ``stations_with_feeds`` count). Most NWR transmitters
    #: are VHF-only with no feed, so this is usually far below ``station_count``;
    #: the Browse tree uses it to hide states with nothing to play.
    stations_with_feeds: int = 0


@dataclass(slots=True, frozen=True)
class WxStation:
    callsign: str
    frequency_mhz: float
    name: str = ""
    state: str = ""
    counties: tuple[str, ...] = ()
    same_codes: tuple[str, ...] = ()
    wfo: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    feeds: tuple[str, ...] = ()


def _f(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def parse_states(data: object) -> list[WxState]:
    out: list[WxState] = []
    for row in data if isinstance(data, list) else []:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("state_slug", "")).strip()
        if slug:
            out.append(
                WxState(
                    slug,
                    str(row.get("state_name", slug)),
                    int(_f(row.get("station_count"), 0)),
                    int(_f(row.get("stations_with_feeds"), 0)),
                )
            )
    return out


def _feeds(row: dict) -> tuple[str, ...]:
    urls: list[str] = []
    for feed in row.get("feeds", []) or []:
        if not isinstance(feed, dict):
            continue
        url = str(feed.get("stream_url") or feed.get("url") or "").strip()
        if url:
            urls.append(url)
    return tuple(urls)


def parse_station(data: object) -> WxStation | None:
    if not isinstance(data, dict):
        return None
    callsign = str(data.get("callsign", "")).strip()
    if not callsign:
        return None
    return WxStation(
        callsign=callsign,
        frequency_mhz=_f(data.get("frequency")),
        name=str(data.get("city", "")).strip(),
        state=str(data.get("state_slug", "")).strip(),
        counties=tuple(str(c).strip() for c in data.get("counties", []) or [] if str(c).strip()),
        same_codes=tuple(str(c).strip() for c in data.get("same", []) or [] if str(c).strip()),
        wfo=str(data.get("wfo_code") or data.get("wfo") or "").strip(),
        latitude=_f(data.get("latitude")),
        longitude=_f(data.get("longitude")),
        feeds=_feeds(data),
    )


def parse_stations(data: object) -> list[WxStation]:
    rows = data if isinstance(data, list) else []
    return [s for s in (parse_station(r) for r in rows) if s is not None]


def to_radio_station(s: WxStation) -> RadioStation:
    place = f" - {s.name}" if s.name else ""
    label = f"NOAA Weather Radio - {s.callsign} - {s.frequency_mhz:.2f} MHz{place}"
    return RadioStation(
        name=label,
        stream_url=s.feeds[0] if s.feeds else "",
        station_uuid=f"wxindex:{s.callsign}",
        country="United States",
        tags=("weather", "noaa"),
        source=_SOURCE,
    )
