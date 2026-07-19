"""National Weather Service client (api.weather.gov) for QUILL Weather.

A free, no-account, open-government API. The flow (PRD 11.1): resolve a point to
its forecast office/grid/zones and provider URLs, then fetch the period
forecast, the latest observation from the nearest station, and any active
alerts. Point metadata changes rarely and is cached by the caller; alerts are
never polled more than every 30 seconds (PRD 10.2), enforced by the UI's
refresh cadence, not here.

Parsing is split into pure ``*_from_json`` helpers so the whole normalization
path is unit-tested against saved fixtures with no network. Fetching degrades
gracefully: a failed observation or forecast is recorded as a note and the rest
of the report still returns -- but a failure to resolve the point (no forecast
possible at all) raises. wx-free, strict-typed, HTTPS-only, egress-audited,
Safe-Mode-gated.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.error_codes import CodedError
from quill.core.weather._http import HTTP_ERRORS, http_json
from quill.core.weather.models import (
    CurrentConditions,
    ForecastPeriod,
    WeatherAlert,
    WeatherLocation,
    WeatherReport,
)

_API = "https://api.weather.gov"


class WeatherError(CodedError):
    """An NWS request failed (network, Safe Mode, or an unusable response)."""

    code = "QUILL-WEATHER-NWS-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    if safe_mode:
        raise WeatherError("Weather is a network service and is disabled in Safe Mode.")


@dataclass(slots=True)
class PointMetadata:
    office: str
    grid_x: int
    grid_y: int
    forecast_url: str
    hourly_forecast_url: str
    observation_stations_url: str
    forecast_zone: str
    county_zone: str
    city: str
    state: str


# -- unit helpers -------------------------------------------------------------


def c_to_f(celsius: float | None) -> float | None:
    return None if celsius is None else round(celsius * 9 / 5 + 32, 1)


def mps_to_mph(mps: float | None) -> float | None:
    return None if mps is None else round(mps * 2.236936, 1)


def kmh_to_mph(kmh: float | None) -> float | None:
    return None if kmh is None else round(kmh * 0.621371, 1)


def _value_and_unit(field: object) -> tuple[float | None, str]:
    """Pull (value, unitCode) from an NWS quantitative-value object; the API
    reports SI with an explicit unitCode, so conversions must read it rather
    than assume (wind is km/h, temperature usually degC -- but not always)."""
    if not isinstance(field, dict):
        return None, ""
    value = field.get("value")
    unit = str(field.get("unitCode", ""))
    return (value if isinstance(value, (int, float)) else None), unit


def degrees_to_compass(degrees: float | None) -> str:
    if degrees is None:
        return ""
    points = (
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    )
    return points[int((degrees % 360) / 22.5 + 0.5) % 16]


# -- pure parsers -------------------------------------------------------------


def point_from_json(data: object) -> PointMetadata:
    if not isinstance(data, dict):
        raise WeatherError("The weather service returned no location metadata.")
    props = data.get("properties")
    if not isinstance(props, dict):
        raise WeatherError("The weather service returned no location metadata.")
    rel = (props.get("relativeLocation") or {}).get("properties") or {}
    try:
        return PointMetadata(
            office=str(props.get("gridId", "")),
            grid_x=int(props.get("gridX", 0)),
            grid_y=int(props.get("gridY", 0)),
            forecast_url=str(props.get("forecast", "")),
            hourly_forecast_url=str(props.get("forecastHourly", "")),
            observation_stations_url=str(props.get("observationStations", "")),
            forecast_zone=str(props.get("forecastZone", "")).rsplit("/", 1)[-1],
            county_zone=str(props.get("county", "")).rsplit("/", 1)[-1],
            city=str(rel.get("city", "")),
            state=str(rel.get("state", "")),
        )
    except (TypeError, ValueError) as error:
        raise WeatherError("The weather service location metadata was unreadable.") from error


def periods_from_json(data: object, *, limit: int = 14) -> list[ForecastPeriod]:
    props = data.get("properties") if isinstance(data, dict) else None
    raw = props.get("periods") if isinstance(props, dict) else None
    periods: list[ForecastPeriod] = []
    for item in raw or []:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        precip = (item.get("probabilityOfPrecipitation") or {}).get("value")
        periods.append(
            ForecastPeriod(
                name=str(item["name"]),
                temperature=int(item.get("temperature", 0)),
                temperature_unit=str(item.get("temperatureUnit", "F")),
                short_forecast=str(item.get("shortForecast", "")),
                detailed_forecast=str(item.get("detailedForecast", "")),
                wind_speed=str(item.get("windSpeed", "")),
                wind_direction=str(item.get("windDirection", "")),
                precipitation_percent=int(precip) if isinstance(precip, (int, float)) else None,
                is_daytime=bool(item.get("isDaytime", True)),
            )
        )
        if len(periods) >= limit:
            break
    return periods


def observation_from_json(data: object) -> CurrentConditions:
    props = data.get("properties") if isinstance(data, dict) else None
    if not isinstance(props, dict):
        return CurrentConditions()

    temp_value, temp_unit = _value_and_unit(props.get("temperature"))
    if temp_value is None:
        temp_c = temp_f = None
    elif "degF" in temp_unit:
        temp_f = round(temp_value, 1)
        temp_c = round((temp_value - 32) * 5 / 9, 1)
    else:  # degC (the NWS default)
        temp_c = round(temp_value, 1)
        temp_f = c_to_f(temp_value)

    wind_value, wind_unit = _value_and_unit(props.get("windSpeed"))
    if wind_value is None:
        wind_mph = None
    elif "m_s" in wind_unit:
        wind_mph = mps_to_mph(wind_value)
    else:  # km_h-1 (the NWS default for observations)
        wind_mph = kmh_to_mph(wind_value)

    humidity, _ = _value_and_unit(props.get("relativeHumidity"))
    wind_deg, _ = _value_and_unit(props.get("windDirection"))
    return CurrentConditions(
        text_description=str(props.get("textDescription", "")),
        temperature_c=temp_c,
        temperature_f=temp_f,
        humidity_percent=round(humidity) if humidity is not None else None,
        wind_speed_mph=wind_mph,
        wind_direction=degrees_to_compass(wind_deg) if wind_deg is not None else "",
        station_id=str(props.get("station", "")).rsplit("/", 1)[-1],
        observed_at=str(props.get("timestamp", "")),
    )


def alerts_from_json(data: object) -> list[WeatherAlert]:
    features = data.get("features") if isinstance(data, dict) else None
    alerts: list[WeatherAlert] = []
    for feature in features or []:
        props = feature.get("properties") if isinstance(feature, dict) else None
        if not isinstance(props, dict) or not props.get("event"):
            continue
        alerts.append(
            WeatherAlert(
                id=str(props.get("id", feature.get("id", ""))),
                event=str(props["event"]),
                severity=str(props.get("severity", "") or ""),
                urgency=str(props.get("urgency", "") or ""),
                certainty=str(props.get("certainty", "") or ""),
                headline=str(props.get("headline", "") or ""),
                description=str(props.get("description", "") or ""),
                instruction=str(props.get("instruction", "") or ""),
                area_description=str(props.get("areaDesc", "") or ""),
                effective=str(props.get("effective", "") or ""),
                onset=str(props.get("onset", "") or ""),
                expires=str(props.get("expires", "") or ""),
                ends=str(props.get("ends", "") or ""),
                sender_name=str(props.get("senderName", "") or ""),
            )
        )
    alerts.sort(key=lambda a: a.tier_rank)
    return alerts


def _first_station_id(data: object) -> str:
    features = data.get("features") if isinstance(data, dict) else None
    for feature in features or []:
        props = feature.get("properties") if isinstance(feature, dict) else None
        if isinstance(props, dict) and props.get("stationIdentifier"):
            return str(props["stationIdentifier"])
    return ""


# -- fetchers -----------------------------------------------------------------


def resolve_point(latitude: float, longitude: float, *, safe_mode: bool = False) -> PointMetadata:
    """Resolve coordinates to NWS office/grid/zones + provider URLs."""
    refuse_in_safe_mode(safe_mode)
    try:
        data = http_json(f"{_API}/points/{latitude:.4f},{longitude:.4f}")
    except HTTP_ERRORS as error:
        raise WeatherError(f"Could not reach the weather service: {error}") from error
    return point_from_json(data)


def active_alerts(
    latitude: float, longitude: float, *, safe_mode: bool = False
) -> list[WeatherAlert]:
    """Active watches/warnings/advisories for a point (its own endpoint, so an
    alert check never depends on a successful forecast fetch)."""
    refuse_in_safe_mode(safe_mode)
    try:
        data = http_json(f"{_API}/alerts/active?point={latitude:.4f},{longitude:.4f}")
    except HTTP_ERRORS as error:
        raise WeatherError(f"Could not reach the weather service: {error}") from error
    return alerts_from_json(data)


def fetch_report(
    location: WeatherLocation,
    *,
    safe_mode: bool = False,
    daily_days: int = 10,
    temperature_unit: str = "F",
) -> WeatherReport:
    """Gather a full Weather Now report for a location. Point resolution is
    required (raises on failure); the NWS forecast, observation, and alerts, and
    the Open-Meteo extended daily outlook, each degrade to a note so one dead
    sub-request never blanks the whole screen."""
    refuse_in_safe_mode(safe_mode)
    point = resolve_point(location.latitude, location.longitude)
    report = WeatherReport(
        location=location,
        office=point.office,
        forecast_zone=point.forecast_zone,
        county_zone=point.county_zone,
    )
    if point.city and not location.resolved_name:
        location.resolved_name = f"{point.city}, {point.state}".strip(", ")

    try:
        report.periods = periods_from_json(http_json(point.forecast_url))
    except HTTP_ERRORS:
        report.notes.append("The forecast is temporarily unavailable.")

    try:
        report.current = _fetch_latest_observation(point.observation_stations_url)
    except HTTP_ERRORS:
        report.notes.append("Current conditions are temporarily unavailable.")

    try:
        report.alerts = active_alerts(location.latitude, location.longitude)
    except WeatherError:
        report.notes.append("Active alerts could not be checked -- try Refresh.")

    if daily_days > 0:
        from quill.core.weather import open_meteo

        try:
            report.daily = open_meteo.daily_forecast(
                location.latitude, location.longitude, days=daily_days, unit=temperature_unit
            )
        except open_meteo.OpenMeteoError:
            report.notes.append("The extended daily outlook is temporarily unavailable.")

    return report


def _fetch_latest_observation(stations_url: str) -> CurrentConditions | None:
    if not stations_url:
        return None
    station = _first_station_id(http_json(stations_url))
    if not station:
        return None
    data = http_json(f"{_API}/stations/{station}/observations/latest")
    return observation_from_json(data)
