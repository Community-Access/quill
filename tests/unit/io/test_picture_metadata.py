"""Save Described Copies: the description goes into copies; the originals are only read."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from quill.io import picture_metadata as pm

_TEXT = "A café terrace at dusk — two people talking."


def _picture(path: Path, fmt: str) -> Path:
    from PIL import Image

    image = Image.new("RGB", (32, 24), (10, 200, 30))
    exif = image.getexif()
    exif[0x0110] = "Pixel 8"
    out = io.BytesIO()
    image.save(out, format=fmt, exif=exif.tobytes())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out.getvalue())
    return path


def _scan_data(data: bytes) -> bytes:
    return data[data.index(b"\xff\xda") :]


def test_a_jpeg_copy_carries_the_description_and_the_same_image_data(tmp_path: Path) -> None:
    from PIL import Image

    source = _picture(tmp_path / "in" / "terrace.jpg", "JPEG")
    before = source.read_bytes()
    copy = pm.write_described_copy(source, tmp_path / "out" / "terrace.jpg", _TEXT)
    assert source.read_bytes() == before  # the original is untouched
    data = copy.read_bytes()
    assert _scan_data(data) == _scan_data(before)  # never re-encoded
    with Image.open(copy) as opened:
        exif = opened.getexif()
        assert exif[0x0110] == "Pixel 8"  # what the camera wrote is kept
        assert exif[0x010E] == "A cafe terrace at dusk - two people talking."
        assert bytes(exif[0x9C9C]).decode("utf-16-le").rstrip("\x00") == _TEXT
    assert pm.xmp_packet(_TEXT) in data and "café".encode() in data


def test_a_png_copy_carries_the_description_in_itxt(tmp_path: Path) -> None:
    from PIL import Image

    source = _picture(tmp_path / "shot.png", "PNG")
    copy = pm.write_described_copy(source, tmp_path / "out" / "shot.png", _TEXT)
    with Image.open(copy) as opened:
        assert opened.text["Description"] == _TEXT
        assert "dc:description" in opened.text["XML:com.adobe.xmp"]
        opened.load()
    with Image.open(source) as original, Image.open(copy) as described:
        assert original.tobytes() == described.tobytes()


def test_a_copy_never_replaces_the_picture_or_an_existing_file(tmp_path: Path) -> None:
    source = _picture(tmp_path / "a.jpg", "JPEG")
    beside = pm.write_described_copy(source, source, _TEXT)
    assert beside.name == "a (2).jpg" and source.read_bytes() != beside.read_bytes()


def test_other_kinds_of_picture_are_left_out_by_name(tmp_path: Path) -> None:
    source = tmp_path / "a.webp"
    source.write_bytes(b"RIFF")
    with pytest.raises(pm.DescribedCopyError) as raised:
        pm.write_described_copy(source, tmp_path / "out" / "a.webp", _TEXT)
    assert raised.value.code == "QUILL-IO-PICTURE-METADATA-FAILED"


def test_write_described_copies_uses_the_latest_description_and_says_what_it_did(
    tmp_path: Path,
) -> None:
    from PIL import Image

    from quill.core.ai.picture_batch import Description, new_result, with_description

    folder = tmp_path / "pics"
    jpeg = _picture(folder / "sub" / "one.jpg", "JPEG")
    webp = folder / "two.webp"
    webp.write_bytes(b"RIFF")
    gone = _picture(folder / "three.jpg", "JPEG")
    results = []
    for picture in (jpeg, webp, gone):
        result = new_result(folder, picture)
        for text in ("First.", "Second."):
            result = with_description(result, Description(text=text, connection="chatgpt"))
        results.append(result)
    gone.unlink()
    outcome = pm.write_described_copies(results, tmp_path / "copies")
    assert [p.relative_to(tmp_path / "copies").as_posix() for p in outcome.written] == [
        "sub/one.jpg"
    ]
    with Image.open(outcome.written[0]) as opened:
        assert opened.getexif()[0x010E] == "Second."
    assert outcome.sentence("copies") == (
        "Saved 1 described copy in copies. 1 picture (two.webp) left out: QUILL writes "
        "descriptions into JPEG and PNG pictures only. 1 picture (three.jpg) is no longer where "
        "it was described."
    )
