"""Scale, crop or turn a site's picture on this computer, to send it back (complete.md 2.3, Media).

WordPress has no route that scales an existing original in place, so this was
"wp-admin only". It need not be: QUILL downloads the original, changes it here
with Pillow (which QUILL already ships), and the Workbench sends it back
through Replace File, in place where the site lists a replace route and
otherwise as a new file with every use pointed at it.

One line says what to do, the way a person would put it:

- ``1200 wide`` or ``1200`` -- that width, the height following;
- ``800 high`` -- that height, the width following;
- ``50%`` -- half of each side;
- ``turn 90``, ``turn 180`` or ``turn 270`` -- clockwise;
- ``crop 10, 0, 80, 100`` -- left, top, width and height in percent.

The picture keeps its format, and its shape unless cropped; a JPEG is written at
quality 88 so a scale does not cost visible quality. Wx-free.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress.site import human_size

__all__ = ["ScaleError", "Scaled", "Wanted", "change_picture", "parse_wanted"]


class ScaleError(CodedError):
    """A scale request QUILL cannot carry out, said as one sentence."""

    code = "QUILL-WORDPRESS-MEDIA-SCALE"


@dataclass(frozen=True, slots=True)
class Wanted:
    """What to do: ``kind`` is width, height, percent, turn or crop."""

    kind: str
    amount: float = 0.0
    box: tuple[float, float, float, float] = (0.0, 0.0, 100.0, 100.0)

    def words(self) -> str:
        if self.kind == "width":
            return f"scaled to {self.amount:g} pixels wide"
        if self.kind == "height":
            return f"scaled to {self.amount:g} pixels high"
        if self.kind == "percent":
            return f"scaled to {self.amount:g} percent"
        if self.kind == "turn":
            return f"turned {self.amount:g} degrees clockwise"
        left, top, width, height = self.box
        return (
            f"cropped to {width:g} by {height:g} percent, from {left:g} percent in and "
            f"{top:g} percent down"
        )


_NUMBERS = re.compile(r"-?\d+(?:\.\d+)?")


def parse_wanted(text: str) -> Wanted:
    """``1200 wide``, ``800 high``, ``50%``, ``turn 90`` or ``crop 10, 0, 80, 100``."""
    said = " ".join(str(text or "").lower().split())
    numbers = [float(n) for n in _NUMBERS.findall(said)]
    if said.startswith(("crop", "cut")):
        if len(numbers) != 4:
            raise ScaleError("A crop needs four numbers in percent: left, top, width, height.")
        left, top, width, height = numbers
        if (
            min(numbers) < 0
            or width <= 0
            or height <= 0
            or left + width > 100
            or top + height > 100
        ):
            raise ScaleError("That crop goes past the picture's edge, or has no size.")
        return Wanted("crop", box=(left, top, width, height))
    if not numbers:
        raise ScaleError("Say a size, such as 1200 wide, 800 high or 50%.")
    amount = numbers[0]
    if said.startswith(("turn", "rotate")):
        if amount % 360 not in (90, 180, 270):
            raise ScaleError("A picture turns 90, 180 or 270 degrees.")
        return Wanted("turn", amount % 360)
    if amount <= 0:
        raise ScaleError("A size has to be more than 0.")
    if "%" in said or "percent" in said:
        if amount > 400:
            raise ScaleError("QUILL scales a picture up to 400 percent at most.")
        return Wanted("percent", amount)
    kind = "height" if ("high" in said or "tall" in said or "height" in said) else "width"
    return Wanted(kind, amount)


@dataclass(frozen=True, slots=True)
class Scaled:
    """The changed picture, and its size and weight before and after."""

    data: bytes
    before: tuple[int, int]
    after: tuple[int, int]
    before_bytes: int

    def report(self) -> str:
        (w0, h0), (w1, h1) = self.before, self.after
        return (
            f"Before: {w0} by {h0}, {human_size(self.before_bytes)}. "
            f"After: {w1} by {h1}, {human_size(len(self.data))}."
        )


def change_picture(data: bytes, wanted: Wanted) -> Scaled:
    """Do *wanted* to the picture in *data*, here, keeping its format."""
    from PIL import Image, ImageOps

    try:
        with Image.open(io.BytesIO(data)) as opened:
            fmt = opened.format or "PNG"
            opened.load()
            image = ImageOps.exif_transpose(opened) or opened.copy()
    except Exception as exc:  # noqa: BLE001 - Pillow raises many kinds for one meaning
        raise ScaleError("This file is not a picture QUILL can read, so nothing changed.") from exc
    before = image.size
    width, height = before
    if wanted.kind == "turn":
        image = image.rotate(-wanted.amount, expand=True)
    elif wanted.kind == "crop":
        left, top, w, h = wanted.box
        box = (
            round(width * left / 100),
            round(height * top / 100),
            round(width * (left + w) / 100),
            round(height * (top + h) / 100),
        )
        image = image.crop(box)
    else:
        if wanted.kind == "width":
            size = (round(wanted.amount), max(1, round(height * wanted.amount / width)))
        elif wanted.kind == "height":
            size = (max(1, round(width * wanted.amount / height)), round(wanted.amount))
        else:
            size = (
                max(1, round(width * wanted.amount / 100)),
                max(1, round(height * wanted.amount / 100)),
            )
        if size[0] > 20000 or size[1] > 20000:
            raise ScaleError("That would be more than 20,000 pixels on a side.")
        image = image.resize(size, Image.Resampling.LANCZOS)
    if fmt == "JPEG" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    out = io.BytesIO()
    options: dict[str, Any] = {"optimize": True} if fmt in ("JPEG", "PNG") else {}
    if fmt in ("JPEG", "WEBP"):
        options["quality"] = 88
    image.save(out, format=fmt, **options)
    return Scaled(out.getvalue(), before, image.size, len(data))
