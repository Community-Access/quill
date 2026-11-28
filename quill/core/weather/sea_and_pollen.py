"""Pollen (Europe only) and the marine forecast (coastal places), from
Open-Meteo, keyless.

* **Pollen** is Copernicus CAMS through Open-Meteo's air-quality service. It
  covers Europe only, so outside Europe no request is made and nothing is
  shown -- an empty pollen line elsewhere would read as "no pollen", which is
  not what it means.
* **Marine** is Open-Meteo's marine service: wave height, direction and period,
  swell and sea temperature. Inland it answers with nothing, and the line is
  left out.

The levels for pollen use common European bands (grains per cubic metre); they
differ by plant, so trees, grasses and weeds each have their own.

wx-free and strict-typed; the transport is passed in for tests.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

GetJson = Callable[..., Any]

#: (field, spoken name, low-below, high-from) in grains per cubic metre.
POLLEN = (
    ("alder_pollen", "alder", 15, 90),
    ("birch_pollen", "birch", 15, 90),
    ("olive_pollen", "olive", 15, 90),
    ("grass_pollen", "grass", 20, 50),
    ("mugwort_pollen", "mugwort", 10, 50),
    ("ragweed_pollen", "ragweed", 10, 50),
)


def in_europe(latitude: float, longitude: float) -> bool:
    """The CAMS European domain, roughly."""
    return 30.0 <= latitude <= 72.0 and -25.0 <= longitude <= 45.0


@dataclass(slots=True)
class Pollen:
    levels: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class Marine:
    wave_height_m: float | None = None
    wave_direction: float | None = None
    wave_period_s: float | None = None
    swell_height_m: float | None = None
    sea_temperature_c: float | None = None

    @property
    def has_data(self) -> bool:
        return any(
            v is not None for v in (self.wave_height_m, self.swell_height_m, self.sea_temperature_c)
        )


def _num(block: Any, key: str) -> float | None:
    value = block.get(key) if isinstance(block, dict) else None
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None


def pollen_url(latitude: float, longitude: float) -> str:
    return "https://air-quality-api.open-meteo.com/v1/air-quality?" + urllib.parse.urlencode({
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "current": ",".join(p[0] for p in POLLEN),
        "timezone": "auto",
    })


def parse_pollen(data: Any) -> Pollen | None:
    current = data.get("current") if isinstance(data, dict) else None
    levels = {p[0]: v for p in POLLEN if (v := _num(current, p[0])) is not None}
    return Pollen(levels) if levels else None


def fetch_pollen(latitude: float, longitude: float, *, get: GetJson | None = None) -> Pollen | None:
    """None outside Europe (no request is made) or when CAMS has no values."""
    if not in_europe(latitude, longitude):
        return None
    if get is None:
        from quill.core.weather.open_meteo_limits import get_json

        get = get_json
    return parse_pollen(get(pollen_url(latitude, longitude)))


def pollen_text(pollen: Pollen | None) -> str:
    """'Pollen: birch high, grass low.' or 'Pollen: none in the air right now.'"""
    if pollen is None:
        return ""
    found: list[tuple[float, str]] = []
    for key, name, low, high in POLLEN:
        value = pollen.levels.get(key)
        if value is None or value < 1:
            continue
        level = "low" if value < low else "high" if value >= high else "moderate"
        found.append((value, f"{name} {level}"))
    if not found:
        return "Pollen: none in the air right now."
    found.sort(key=lambda pair: -pair[0])
    return "Pollen: " + ", ".join(text for _value, text in found) + "."


def marine_url(latitude: float, longitude: float) -> str:
    return "https://marine-api.open-meteo.com/v1/marine?" + urllib.parse.urlencode({
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "current": (
            "wave_height,wave_direction,wave_period,swell_wave_height,sea_surface_temperature"
        ),
        "timezone": "auto",
    })


def parse_marine(data: Any) -> Marine | None:
    current = data.get("current") if isinstance(data, dict) else None
    marine = Marine(
        wave_height_m=_num(current, "wave_height"),
        wave_direction=_num(current, "wave_direction"),
        wave_period_s=_num(current, "wave_period"),
        swell_height_m=_num(current, "swell_wave_height"),
        sea_temperature_c=_num(current, "sea_surface_temperature"),
    )
    return marine if marine.has_data else None


def fetch_marine(latitude: float, longitude: float, *, get: GetJson | None = None) -> Marine | None:
    if get is None:
        from quill.core.weather.open_meteo_limits import get_json

        get = get_json
    return parse_marine(get(marine_url(latitude, longitude)))


def _height(metres: float, metric: bool) -> str:
    if metric:
        return f"{metres:.1f} metres".replace(".0 ", " ")
    feet = round(metres * 3.281)
    return "1 foot" if feet == 1 else f"{feet} feet"


def marine_text(marine: Marine | None, *, metric: bool = False) -> str:
    """'Sea: waves 10 feet from the west every 14 seconds, swell 10 feet, sea
    temperature 67 degrees.'"""
    if marine is None:
        return ""
    from quill.core.weather.open_meteo import compass_name

    bits: list[str] = []
    if marine.wave_height_m is not None:
        wave = f"waves {_height(marine.wave_height_m, metric)}"
        if marine.wave_direction is not None:
            wave += f" from the {compass_name(marine.wave_direction)}"
        if marine.wave_period_s:
            wave += f" every {round(marine.wave_period_s)} seconds"
        bits.append(wave)
    if marine.swell_height_m is not None:
        bits.append(f"swell {_height(marine.swell_height_m, metric)}")
    if marine.sea_temperature_c is not None:
        sea = marine.sea_temperature_c if metric else marine.sea_temperature_c * 9 / 5 + 32
        bits.append(f"sea temperature {round(sea)} degrees")
    return "Sea: " + ", ".join(bits) + "." if bits else ""
