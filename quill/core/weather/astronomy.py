"""Moon almanac -- phase, illumination, and moonrise/moonset, computed locally.

Leasey's weather reports the moon alongside the sun; QUILL surfaced only
sunrise/sunset. This module fills that gap with pure, dependency-free
astronomy so a moon almanac needs no extra network call or third-party
package (matching the package's hand-rolled, unit-tested style -- see
``open_meteo.weekday_name``'s Zeller's congruence).

Two independent pieces:

* **Phase and illumination** are exact and cheap: the age of the Moon within
  the 29.53-day synodic month gives the named phase and the lit fraction.
  These are the headline numbers and are unit-tested against known dates.

* **Moonrise and moonset** use Montenbruck & Pfleger's compact lunar theory
  ("Astronomy on the Personal Computer") -- the Moon's position from a handful
  of periodic terms, sampled across the local day to find horizon crossings.
  It neglects topocentric parallax, so a rise/set time can be off by a few
  minutes; it is meant for "the Moon is up this evening" orientation, not
  observatory timing. Times are returned in the location's own local clock,
  so the caller passes the UTC offset (Open-Meteo already reports it).

wx-free, strict-typed, no clock, no randomness: every value is a pure function
of the inputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

#: Mean length of the synodic month (new moon to new moon), in days.
_SYNODIC_MONTH = 29.530588853
#: A reference new moon: 2000-01-06 18:14 UTC, as a Julian Day. The Moon's age
#: is measured forward from here.
_REF_NEW_MOON_JD = 2451550.09766

#: The eight traditional phase names, in order over one synodic cycle.
_PHASE_NAMES = (
    "New Moon",
    "Waxing Crescent",
    "First Quarter",
    "Waxing Gibbous",
    "Full Moon",
    "Waning Gibbous",
    "Last Quarter",
    "Waning Crescent",
)

#: The Moon's standard altitude at rise/set (its centre, allowing for
#: refraction and mean semidiameter): +8 arcminutes. Montenbruck's value.
_SIN_H0_MOON = math.sin(math.radians(8.0 / 60.0))
_ARC = 206264.8062  # arcseconds per radian
_COS_EPS = 0.91748  # cos / sin of the mean obliquity of the ecliptic
_SIN_EPS = 0.39778


@dataclass(slots=True)
class MoonAlmanac:
    """The Moon for one day at one place. Times are the location's local clock
    ("6:12 AM"); either may be empty when the Moon does not rise or set that
    calendar day (a normal occurrence roughly once a month)."""

    phase_name: str = ""
    #: Illuminated fraction as a whole percent, 0 (new) to 100 (full).
    illumination_percent: int = 0
    moonrise: str = ""
    moonset: str = ""

    @property
    def line(self) -> str:
        """A self-contained, fully spoken one-line summary."""
        bits = [
            f"The moon is a {self.phase_name.lower()}, {self.illumination_percent} percent lit."
        ]
        if self.moonrise:
            bits.append(f"Moonrise {self.moonrise}.")
        if self.moonset:
            bits.append(f"Moonset {self.moonset}.")
        return " ".join(bits)


def julian_day(year: int, month: int, day: int, hour: float = 0.0) -> float:
    """The Julian Day for a Gregorian calendar date and fractional UT hour."""
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    jd = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5
    return jd + hour / 24.0


def moon_age_days(jd: float) -> float:
    """Days since the most recent new moon (0 .. ~29.53), for a given JD."""
    age = (jd - _REF_NEW_MOON_JD) % _SYNODIC_MONTH
    return age + _SYNODIC_MONTH if age < 0 else age


def phase_name(age_days: float) -> str:
    """The named phase for a moon age. The quarter names snap to a narrow
    window around the exact instant; the rest are the crescents/gibbous."""
    fraction = (age_days % _SYNODIC_MONTH) / _SYNODIC_MONTH
    # Eight equal 45-degree bins around the cycle, centred on the four
    # principal phases so "Full Moon" brackets the true full moon.
    index = int((fraction * 8) + 0.5) % 8
    return _PHASE_NAMES[index]


def illumination_percent(age_days: float) -> int:
    """The illuminated fraction (0-100) from the Moon's age. Uses the phase
    angle: fraction lit = (1 - cos(phase angle)) / 2, exact at the principal
    phases and a close approximation between them."""
    fraction = (age_days % _SYNODIC_MONTH) / _SYNODIC_MONTH
    lit = (1 - math.cos(2 * math.pi * fraction)) / 2
    return int(round(lit * 100))


def _frac(x: float) -> float:
    return x - math.floor(x)


def _moon_ra_dec(t: float) -> tuple[float, float]:
    """Geocentric right ascension (hours) and declination (degrees) of the
    Moon at ``t`` Julian centuries since J2000 (Montenbruck's MiniMoon)."""
    p2 = 2 * math.pi
    l0 = _frac(0.606433 + 1336.855225 * t)
    lm = p2 * _frac(0.374897 + 1325.552410 * t)  # Moon's mean anomaly
    ls = p2 * _frac(0.993133 + 99.997361 * t)  # Sun's mean anomaly
    d = p2 * _frac(0.827361 + 1236.853086 * t)  # mean elongation
    f = p2 * _frac(0.259086 + 1342.227825 * t)  # argument of latitude

    d_lambda = (
        22640 * math.sin(lm)
        - 4586 * math.sin(lm - 2 * d)
        + 2370 * math.sin(2 * d)
        + 769 * math.sin(2 * lm)
        - 668 * math.sin(ls)
        - 412 * math.sin(2 * f)
        - 212 * math.sin(2 * lm - 2 * d)
        - 206 * math.sin(lm + ls - 2 * d)
        + 192 * math.sin(lm + 2 * d)
        - 165 * math.sin(ls - 2 * d)
        - 125 * math.sin(d)
        - 110 * math.sin(lm + ls)
        + 148 * math.sin(lm - ls)
        - 55 * math.sin(2 * f - 2 * d)
    )
    s = f + (d_lambda + 412 * math.sin(2 * f) + 541 * math.sin(ls)) / _ARC
    h = f - 2 * d
    n = (
        -526 * math.sin(h)
        + 44 * math.sin(lm + h)
        - 31 * math.sin(-lm + h)
        - 23 * math.sin(ls + h)
        + 11 * math.sin(-ls + h)
        - 25 * math.sin(-2 * lm + f)
        + 21 * math.sin(-lm + f)
    )
    lambda_moon = p2 * _frac(l0 + d_lambda / 1296000)
    beta_moon = (18520.0 * math.sin(s) + n) / _ARC

    cos_b = math.cos(beta_moon)
    x = math.cos(lambda_moon) * cos_b
    v = math.sin(lambda_moon) * cos_b
    w = math.sin(beta_moon)
    y = _COS_EPS * v - _SIN_EPS * w
    z = _SIN_EPS * v + _COS_EPS * w
    rho = math.sqrt(1.0 - z * z)
    dec = (360.0 / p2) * math.atan(z / rho)
    ra = (48.0 / p2) * math.atan(y / (x + rho))
    if ra < 0:
        ra += 24.0
    return ra, dec


def _lmst(mjd: float, longitude_east_deg: float) -> float:
    """Local mean sidereal time in hours (longitude east-positive; QUILL's
    west-negative longitudes pass straight through)."""
    mjd0 = math.floor(mjd)
    ut = (mjd - mjd0) * 24.0
    t = (mjd0 - 51544.5) / 36525.0
    gmst = (
        6.697374558
        + 1.0027379093 * ut
        + (8640184.812866 + (0.093104 - 6.2e-6 * t) * t) * t / 3600.0
    )
    return (gmst + longitude_east_deg / 15.0) % 24.0


def _sin_altitude(mjd: float, longitude_deg: float, sphi: float, cphi: float) -> float:
    """Sine of the Moon's altitude at modified Julian date ``mjd``."""
    t = (mjd - 51544.5) / 36525.0
    ra, dec = _moon_ra_dec(t)
    tau = 15.0 * (_lmst(mjd, longitude_deg) - ra)  # hour angle, degrees
    dec_r = math.radians(dec)
    return sphi * math.sin(dec_r) + cphi * math.cos(dec_r) * math.cos(math.radians(tau))


def _quad(y_minus: float, y0: float, y_plus: float) -> tuple[float, list[float]]:
    """Interpolate a parabola through (-1, y_minus), (0, y0), (+1, y_plus).
    Returns (y at the extremum, roots within [-1, 1])."""
    a = 0.5 * (y_minus + y_plus) - y0
    b = 0.5 * (y_plus - y_minus)
    c = y0
    roots: list[float] = []
    xe = 0.0
    ye = c
    if a != 0:
        xe = -b / (2 * a)
        ye = (a * xe + b) * xe + c
        dis = b * b - 4 * a * c
        if dis >= 0:
            dx = 0.5 * math.sqrt(dis) / abs(a)
            for z in (xe - dx, xe + dx):
                if abs(z) <= 1:
                    roots.append(z)
    return ye, roots


def _format_local(hour: float) -> str:
    """A local decimal hour (0..24) as '6:12 AM'."""
    hour = hour % 24
    h = int(hour)
    m = int(round((hour - h) * 60))
    if m == 60:
        m = 0
        h = (h + 1) % 24
    suffix = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {suffix}"


def moon_rise_set(
    year: int,
    month: int,
    day: int,
    latitude: float,
    longitude: float,
    utc_offset_hours: float,
) -> tuple[str, str]:
    """Moonrise and moonset (local clock strings) for a calendar day at a
    place. Either may be '' when the Moon does not cross the horizon that day.
    Approximate to a few minutes (topocentric parallax is neglected)."""
    sphi = math.sin(math.radians(latitude))
    cphi = math.cos(math.radians(latitude))
    # Modified Julian date of local midnight, expressed as UT.
    mjd0 = julian_day(year, month, day, 0.0) - 2400000.5 - utc_offset_hours / 24.0

    rise_hour: float | None = None
    set_hour: float | None = None
    y_minus = _sin_altitude(mjd0, longitude, sphi, cphi) - _SIN_H0_MOON
    hour = 1.0
    while hour < 24.5:
        y0 = _sin_altitude(mjd0 + hour / 24.0, longitude, sphi, cphi) - _SIN_H0_MOON
        y_plus = _sin_altitude(mjd0 + (hour + 1) / 24.0, longitude, sphi, cphi) - _SIN_H0_MOON
        ye, roots = _quad(y_minus, y0, y_plus)
        if len(roots) == 1:
            if y_minus < 0:
                rise_hour = rise_hour if rise_hour is not None else hour + roots[0]
            else:
                set_hour = set_hour if set_hour is not None else hour + roots[0]
        elif len(roots) == 2:
            first, second = hour + roots[0], hour + roots[1]
            if ye < 0:  # a set then a rise across the window
                if set_hour is None:
                    set_hour = first
                if rise_hour is None:
                    rise_hour = second
            else:  # a rise then a set
                if rise_hour is None:
                    rise_hour = first
                if set_hour is None:
                    set_hour = second
        y_minus = y_plus
        hour += 2.0

    rise = _format_local(rise_hour) if rise_hour is not None else ""
    setting = _format_local(set_hour) if set_hour is not None else ""
    return rise, setting


def almanac(
    iso_date: str,
    latitude: float,
    longitude: float,
    utc_offset_hours: float = 0.0,
) -> MoonAlmanac:
    """The full moon almanac for an ISO ``YYYY-MM-DD`` date at a location.

    Phase and illumination are computed for local noon (representative of the
    day); rise and set for the local calendar day. On a bad date, an empty
    almanac comes back so a display never breaks.
    """
    try:
        year, month, day = (int(part) for part in iso_date.split("-"))
    except (ValueError, AttributeError):
        return MoonAlmanac()
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return MoonAlmanac()
    # Local noon as UT for the phase (mid-day is representative of the date).
    jd_noon = julian_day(year, month, day, 12.0) - utc_offset_hours / 24.0
    age = moon_age_days(jd_noon)
    rise, setting = moon_rise_set(year, month, day, latitude, longitude, utc_offset_hours)
    return MoonAlmanac(
        phase_name=phase_name(age),
        illumination_percent=illumination_percent(age),
        moonrise=rise,
        moonset=setting,
    )
