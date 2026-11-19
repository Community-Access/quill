"""Scale, crop or turn a site's picture on this computer (complete.md 2.3, Media)."""

from __future__ import annotations

import io

import pytest

from quill.core.wordpress import media_scale as ms

pytest.importorskip("PIL")


def _picture(size: tuple[int, int] = (400, 300), fmt: str = "JPEG") -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", size, (200, 100, 50)).save(out, format=fmt)
    return out.getvalue()


@pytest.mark.parametrize(
    ("said", "kind", "amount"),
    [
        ("1200 wide", "width", 1200),
        ("1200", "width", 1200),
        ("800 high", "height", 800),
        ("50%", "percent", 50),
        ("turn 90", "turn", 90),
        ("rotate 270", "turn", 270),
    ],
)
def test_what_a_person_types_is_understood(said: str, kind: str, amount: float) -> None:
    wanted = ms.parse_wanted(said)
    assert (wanted.kind, wanted.amount) == (kind, amount)


@pytest.mark.parametrize("said", ["", "turn 45", "crop 10, 0, 95, 100", "-5 wide", "900%"])
def test_what_cannot_be_done_is_one_sentence(said: str) -> None:
    with pytest.raises(ms.ScaleError):
        ms.parse_wanted(said)


def test_scaling_keeps_the_shape_and_the_format() -> None:
    from PIL import Image

    scaled = ms.change_picture(_picture(), ms.parse_wanted("200 wide"))
    assert scaled.before == (400, 300) and scaled.after == (200, 150)
    assert Image.open(io.BytesIO(scaled.data)).format == "JPEG"
    assert scaled.report().startswith("Before: 400 by 300")


def test_turning_and_cropping() -> None:
    assert ms.change_picture(_picture(fmt="PNG"), ms.parse_wanted("turn 90")).after == (300, 400)
    cropped = ms.change_picture(_picture(), ms.parse_wanted("crop 25, 0, 50, 100"))
    assert cropped.after == (200, 300)


def test_a_file_that_is_not_a_picture_says_so() -> None:
    with pytest.raises(ms.ScaleError, match="not a picture"):
        ms.change_picture(b"not a picture", ms.parse_wanted("50%"))
