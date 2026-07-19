"""Free, no-account geocoding for QUILL Weather: turn what a user types (a US
ZIP, or a city and state) into the latitude/longitude the NWS API needs.

Uses Zippopotam.us (https://www.zippopotam.us) -- a free, keyless service that
maps US ZIP codes and city/state pairs to coordinates. NWS itself does not
geocode addresses (see PRD 7.3), so a separate provider is required; Zippopotam
is chosen for needing no account, no key, and no commercial terms, matching the
Radio directory sources already in QUILL. A bare ``lat,lon`` string is parsed
locally with no network call at all.

wx-free, strict-typed, HTTPS-only, egress-audited, Safe-Mode-gated.
"""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

from quill.core.error_codes import CodedError
from quill.core.weather._http import HTTP_ERRORS, http_json

_ZIP_RE = re.compile(r"^\s*(\d{5})\s*$")
_LATLON_RE = re.compile(r"^\s*(-?\d{1,3}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$")
_CITY_STATE_RE = re.compile(r"^\s*(.+?)\s*,\s*([A-Za-z]{2})\s*$")


class WeatherGeocodeError(CodedError):
    """A location could not be resolved to coordinates."""

    code = "QUILL-WEATHER-GEOCODE-REQUEST"


@dataclass(slots=True)
class GeocodeResult:
    latitude: float
    longitude: float
    name: str  # "Tucson"
    state: str  # "AZ" or "Arizona"
    query: str  # what was typed
    #: The provider's full descriptive name, when available -- used to tell
    #: apart same-named places in a search list ("Springfield, Sangamon County,
    #: Illinois" vs "Springfield, Greene County, Missouri").
    full_name: str = ""

    @property
    def display_name(self) -> str:
        if self.full_name:
            return self.full_name
        return f"{self.name}, {self.state}".strip(", ") if self.name else self.query


def refuse_in_safe_mode(safe_mode: bool) -> None:
    if safe_mode:
        raise WeatherGeocodeError("Weather is a network service and is disabled in Safe Mode.")


def parse_latlon(text: str) -> GeocodeResult | None:
    """Parse a bare ``lat,lon`` string with no network call, else None."""
    m = _LATLON_RE.match(text or "")
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return GeocodeResult(latitude=lat, longitude=lon, name="", state="", query=text.strip())


def geocode(query: str, *, safe_mode: bool = False) -> GeocodeResult:
    """Resolve a ZIP, a "City, ST" pair, or a bare "lat,lon" to coordinates.

    Order: bare coordinates are parsed locally (no request); a 5-digit ZIP and a
    "City, ST" pair each hit Zippopotam. Raises :class:`WeatherGeocodeError`
    with a plain message the UI can show when nothing resolves."""
    text = (query or "").strip()
    if not text:
        raise WeatherGeocodeError("Enter a ZIP code, a city and state, or coordinates.")

    local = parse_latlon(text)
    if local is not None:
        return local

    refuse_in_safe_mode(safe_mode)

    zip_match = _ZIP_RE.match(text)
    if zip_match:
        return _zippopotam(f"https://api.zippopotam.us/us/{zip_match.group(1)}", text)

    city_state = _CITY_STATE_RE.match(text)
    if city_state:
        city = urllib.parse.quote(city_state.group(1).strip())
        state = city_state.group(2).upper()
        return _zippopotam(f"https://api.zippopotam.us/us/{state}/{city}", text)

    raise WeatherGeocodeError(
        f"Could not read '{text}'. Try a 5-digit ZIP, 'City, ST', or 'lat,lon'."
    )


def search(query: str, *, limit: int = 10, safe_mode: bool = False) -> list[GeocodeResult]:
    """Search for places matching free text -- a ZIP, city, county, or address
    -- and return the candidates to choose from (PRD 6.1). Uses the free,
    keyless Nominatim (OpenStreetMap) US search, which -- unlike a bare ZIP
    lookup -- disambiguates same-named places. A bare ``lat,lon`` is returned
    as the single exact point with no request."""
    text = (query or "").strip()
    if not text:
        return []
    local = parse_latlon(text)
    if local is not None:
        return [local]

    refuse_in_safe_mode(safe_mode)
    limit = max(1, min(20, limit))
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        "q": text,
        "format": "jsonv2",
        "countrycodes": "us",
        "limit": limit,
        "addressdetails": 1,
    })
    try:
        data = http_json(url)
    except HTTP_ERRORS as error:
        raise WeatherGeocodeError(f"Could not search for '{text}'.") from error
    return results_from_nominatim(data, text)


def results_from_nominatim(data: object, query: str) -> list[GeocodeResult]:
    """Parse a Nominatim search response into candidates (pure, testable)."""
    results: list[GeocodeResult] = []
    if not isinstance(data, list):
        return results
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        raw_addr = item.get("address")
        addr = raw_addr if isinstance(raw_addr, dict) else {}
        name = str(
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("hamlet")
            or addr.get("county")
            or item.get("name")
            or ""
        ).strip()
        results.append(
            GeocodeResult(
                latitude=lat,
                longitude=lon,
                name=name,
                state=str(addr.get("state", "")).strip(),
                query=query,
                full_name=str(item.get("display_name", "")).strip(),
            )
        )
    return results


def _zippopotam(url: str, query: str) -> GeocodeResult:
    try:
        data = http_json(url)
    except HTTP_ERRORS as error:  # 404 => unknown ZIP/city, others => network
        raise WeatherGeocodeError(f"Could not find '{query}'.") from error
    return result_from_zippopotam(data, query)


def result_from_zippopotam(data: object, query: str) -> GeocodeResult:
    """Pull the first place out of a Zippopotam response (pure, testable)."""
    if not isinstance(data, dict):
        raise WeatherGeocodeError(f"Could not find '{query}'.")
    places = data.get("places")
    if not isinstance(places, list) or not places:
        raise WeatherGeocodeError(f"Could not find '{query}'.")
    place = places[0]
    try:
        lat = float(place["latitude"])
        lon = float(place["longitude"])
    except (KeyError, TypeError, ValueError) as error:
        raise WeatherGeocodeError(f"Could not read coordinates for '{query}'.") from error
    return GeocodeResult(
        latitude=lat,
        longitude=lon,
        name=str(place.get("place name", "")).strip(),
        state=str(place.get("state abbreviation", "")).strip(),
        query=query,
    )
