"""A photo's own facts, read on this computer, as context for describing it.

A camera writes when a photo was taken, on what, and often where, into the
file's EXIF block. "A beach at sunset, taken last June" is worth more than "a
beach at sunset", so Describe a Folder and Describe Again can put one line in
front of the prompt: "Photo details, read from the file: taken 14 June 2024 at
6:05 PM, on an Apple iPhone 15, lens iPhone 15 back camera 6.86mm f/1.6."

Three rules, from codex.md 10B.4 and the Image Description Toolkit proposal:

* **Read here.** Pillow reads the block; nothing is looked up anywhere. There is
  no geocoding: a place name would need a second receiver of where someone
  lives, and the proposal rules that out.
* **Location only when asked.** The coordinates go into the line only when the
  person checks a box that starts unchecked every time. The picture itself is
  re-encoded before it is sent (:func:`quill.core.ai.picture_prep.fit_image`),
  which drops the EXIF block, so the coordinates cannot leave inside the file
  either.
* **Said, not hidden.** The confirmation names what goes with the pictures
  (:func:`details_phrase`).

The idea of sending the photo's facts as context is Kelly Ford's, from his
Image Description Toolkit (MIT; see the third-party notices).

wx-free, strict-typed and network-free.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime
from typing import Any

__all__ = [
    "PhotoDetails",
    "details_line",
    "details_phrase",
    "read_photo_details",
    "spoken_date",
]

# EXIF tag numbers (CIPA DC-008).
_MAKE = 0x010F
_MODEL = 0x0110
_DATETIME = 0x0132
_EXIF_IFD = 0x8769
_GPS_IFD = 0x8825
_DATETIME_ORIGINAL = 0x9003
_LENS_MAKE = 0xA433
_LENS_MODEL = 0xA434
_GPS_LAT_REF, _GPS_LAT, _GPS_LON_REF, _GPS_LON = 1, 2, 3, 4

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


@dataclass(frozen=True, slots=True)
class PhotoDetails:
    """What the file says about itself. Empty fields were not in the file."""

    taken: datetime | None = None
    camera: str = ""
    lens: str = ""
    latitude: float | None = None
    longitude: float | None = None

    @property
    def has_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def empty(self) -> bool:
        return self.taken is None and not self.camera and not self.lens


def _text(value: Any) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    return " ".join(str(value or "").replace("\x00", " ").split())


def _taken(value: Any) -> datetime | None:
    text = _text(value)
    for pattern, length in (("%Y:%m:%d %H:%M:%S", 19), ("%Y-%m-%d %H:%M:%S", 19), ("%Y:%m:%d", 10)):
        try:
            return datetime.strptime(text[:length], pattern)
        except ValueError:
            continue
    return None


def _degrees(value: Any, ref: Any) -> float | None:
    try:
        d, m, s = (float(part) for part in value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    result = d + m / 60 + s / 3600
    if _text(ref).upper() in ("S", "W"):
        result = -result
    return round(result, 6)


def _camera(make: str, model: str) -> str:
    if make and model.lower().startswith(make.lower()):
        return model
    return " ".join(part for part in (make, model) if part)


def read_photo_details(data: bytes) -> PhotoDetails:
    """The date taken, camera, lens and coordinates in *data*'s EXIF block.

    A picture with no EXIF, or one Pillow cannot read, has no details: this
    never raises, because a missing date is never a reason not to describe.
    """
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as opened:
            exif = opened.getexif()
            base = dict(exif)
            extra = dict(exif.get_ifd(_EXIF_IFD))
            gps = dict(exif.get_ifd(_GPS_IFD))
    except Exception:  # noqa: BLE001 - an unreadable block is no details
        return PhotoDetails()
    taken = _taken(extra.get(_DATETIME_ORIGINAL) or base.get(_DATETIME))
    camera = _camera(_text(base.get(_MAKE)), _text(base.get(_MODEL)))
    lens = _text(extra.get(_LENS_MODEL)) or _text(extra.get(_LENS_MAKE))
    latitude = _degrees(gps.get(_GPS_LAT), gps.get(_GPS_LAT_REF)) if gps else None
    longitude = _degrees(gps.get(_GPS_LON), gps.get(_GPS_LON_REF)) if gps else None
    return PhotoDetails(taken, camera, lens, latitude, longitude)


def spoken_date(moment: datetime) -> str:
    """ "14 June 2024 at 6:05 PM": the date as a person says it."""
    hour = moment.hour % 12 or 12
    half = "AM" if moment.hour < 12 else "PM"
    day = f"{moment.day} {_MONTHS[moment.month - 1]} {moment.year}"
    if moment.hour == 0 and moment.minute == 0 and moment.second == 0:
        return day
    return f"{day} at {hour}:{moment.minute:02d} {half}"


def details_line(details: PhotoDetails, *, location: bool = False) -> str:
    """The one line put in front of the prompt, or "" when the file says nothing.

    The coordinates are in it only when *location* is True -- the person's
    own check box -- and the file has them.
    """
    parts: list[str] = []
    if details.taken is not None:
        parts.append(f"taken {spoken_date(details.taken)}")
    if details.camera:
        parts.append(f"on {_article(details.camera)}")
    if details.lens:
        parts.append(f"lens {details.lens}")
    if location and details.has_location:
        parts.append(f"at latitude {details.latitude}, longitude {details.longitude}")
    if not parts:
        return ""
    return "Photo details, read from the file: " + ", ".join(parts) + "."


def _article(camera: str) -> str:
    return f"an {camera}" if camera[:1].lower() in "aeiou" else f"a {camera}"


def details_phrase(*, details: bool, location: bool) -> str:
    """What goes with each picture, for the confirmation: ", with each picture's
    date, camera and lens" -- empty when only the picture goes."""
    if not details:
        return ""
    if location:
        return ", with each picture's date, camera, lens and the place it was taken"
    return ", with each picture's date, camera and lens"
