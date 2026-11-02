"""Photo details read on this computer; GPS only when the person asks, never in the file."""

from __future__ import annotations

import io
from datetime import datetime

from quill.core.ai import photo_details as pd


def _photo(*, gps: bool = True, png: bool = False) -> bytes:
    from PIL import Image

    image = Image.new("RGB", (400, 300), (30, 90, 160))
    exif = image.getexif()
    exif[0x010F] = "Apple"
    exif[0x0110] = "iPhone 15"
    extra = exif.get_ifd(0x8769)
    extra[0x9003] = "2024:06:14 18:05:00"
    extra[0xA434] = "iPhone 15 back camera 6.86mm f/1.6"
    if gps:
        place = exif.get_ifd(0x8825)
        place[1] = "N"
        place[2] = (51.0, 30.0, 0.0)
        place[3] = "W"
        place[4] = (0.0, 7.0, 30.0)
    out = io.BytesIO()
    image.save(out, format="PNG" if png else "JPEG", exif=exif.tobytes())
    return out.getvalue()


def test_date_camera_lens_and_location_are_read_from_the_file() -> None:
    details = pd.read_photo_details(_photo())
    assert details.taken == datetime(2024, 6, 14, 18, 5)
    assert details.camera == "Apple iPhone 15"
    assert details.lens == "iPhone 15 back camera 6.86mm f/1.6"
    assert details.latitude == 51.5 and details.longitude == -0.125


def test_the_line_leaves_location_out_unless_asked() -> None:
    details = pd.read_photo_details(_photo())
    line = pd.details_line(details)
    assert line == (
        "Photo details, read from the file: taken 14 June 2024 at 6:05 PM, on an Apple "
        "iPhone 15, lens iPhone 15 back camera 6.86mm f/1.6."
    )
    assert "latitude" not in line
    assert "at latitude 51.5, longitude -0.125" in pd.details_line(details, location=True)


def test_a_picture_with_no_exif_has_no_details_and_never_raises() -> None:
    assert pd.read_photo_details(b"not a picture") == pd.PhotoDetails()
    assert pd.details_line(pd.PhotoDetails()) == ""


def test_the_confirmation_phrase_names_what_goes() -> None:
    assert pd.details_phrase(details=False, location=True) == ""
    assert pd.details_phrase(details=True, location=False).endswith("date, camera and lens")
    assert "place it was taken" in pd.details_phrase(details=True, location=True)


def test_the_fitted_picture_carries_no_exif_so_no_location_leaves_in_it() -> None:
    from quill.core.ai.picture_prep import fit_image

    for png in (False, True):
        fitted = fit_image(_photo(png=png), 200)
        assert pd.read_photo_details(fitted.data) == pd.PhotoDetails(), png
