"""Save Described Copies: the description goes into copies; the originals are only read."""

from __future__ import annotations

import io
import struct
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


_THEIR_XMP = (
    '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
    '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    '<rdf:Description rdf:about="" xmlns:xmp="http://ns.adobe.com/xap/1.0/"'
    ' xmlns:dc="http://purl.org/dc/elements/1.1/" xmp:Rating="4">'
    "<dc:subject><rdf:Bag><rdf:li>Grandma</rdf:li></rdf:Bag></dc:subject>"
    '<dc:description><rdf:Alt><rdf:li xml:lang="x-default">IMG_0042</rdf:li></rdf:Alt>'
    "</dc:description></rdf:Description></rdf:RDF></x:xmpmeta>"
    '<?xpacket end="w"?>'
)


def _jpeg_with_their_xmp(path: Path) -> Path:
    """A real JPEG, made by Pillow, carrying a photo library's XMP packet."""
    data = _picture(path, "JPEG").read_bytes()
    xmp = pm._segment(0xE1, pm._XMP_HEADER + _THEIR_XMP.encode())
    path.write_bytes(data[:2] + xmp + data[2:])
    return path


def _xmp_in(data: bytes) -> str:
    """The XMP packet in a JPEG's APP1 segment, read by its own length field."""
    header = data.index(pm._XMP_HEADER)
    (length,) = struct.unpack(">H", data[header - 2 : header])
    return data[header + len(pm._XMP_HEADER) : header + length - 2].decode("utf-8")


def test_a_jpeg_copy_merges_into_the_xmp_the_photo_already_had(tmp_path: Path) -> None:
    from xml.etree import ElementTree

    from PIL import Image

    source = _jpeg_with_their_xmp(tmp_path / "in" / "grandma.jpg")
    copy = pm.write_described_copy(source, tmp_path / "out" / "grandma.jpg", _TEXT)
    data = copy.read_bytes()
    assert data.count(pm._XMP_HEADER) == 1  # one packet, not two
    packet = _xmp_in(data)
    root = ElementTree.fromstring(
        packet[packet.index("<x:xmpmeta") : packet.index("<?xpacket end")]
    )
    rdf = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
    dc = "{http://purl.org/dc/elements/1.1/}"
    xmp = "{http://ns.adobe.com/xap/1.0/}"
    descriptions = list(root.iter(f"{rdf}Description"))
    assert [d.get(f"{xmp}Rating") for d in descriptions if d.get(f"{xmp}Rating")] == ["4"]
    assert [li.text for li in root.iter(f"{rdf}li") if li.text == "Grandma"] == ["Grandma"]
    said = list(root.iter(f"{dc}description"))
    assert len(said) == 1  # the old one gave way
    assert said[0].findtext(f"{rdf}Alt/{rdf}li") == _TEXT
    assert "IMG_0042" not in packet
    with Image.open(copy) as opened:
        opened.load()  # still a picture any viewer opens


def test_a_png_copy_merges_into_the_xmp_the_picture_already_had(tmp_path: Path) -> None:
    from PIL import Image, PngImagePlugin

    info = PngImagePlugin.PngInfo()
    info.add_itxt("XML:com.adobe.xmp", _THEIR_XMP)
    source = tmp_path / "shot.png"
    Image.new("RGB", (8, 8)).save(source, pnginfo=info)
    copy = pm.write_described_copy(source, tmp_path / "out" / "shot.png", _TEXT)
    with Image.open(copy) as opened:
        packet = opened.text["XML:com.adobe.xmp"]
    assert 'xmp:Rating="4"' in packet and "Grandma" in packet
    assert _TEXT in packet and "IMG_0042" not in packet
    assert packet.count("dc:description>") == 2  # one element: open and close


def test_merge_keeps_every_byte_it_does_not_replace() -> None:
    merged = pm.merged_xmp_packet(_THEIR_XMP.encode(), "New words").decode()
    assert merged.replace(
        '<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<dc:description><rdf:Alt><rdf:li xml:lang="x-default">New words</rdf:li></rdf:Alt>'
        "</dc:description></rdf:Description>",
        "",
    ) == _THEIR_XMP.replace(
        '<dc:description><rdf:Alt><rdf:li xml:lang="x-default">IMG_0042</rdf:li></rdf:Alt>'
        "</dc:description>",
        "",
    )


def test_merge_removes_a_description_written_as_an_attribute() -> None:
    packet = (
        '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF '
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description '
        'rdf:about="" xmlns:d="http://purl.org/dc/elements/1.1/" d:description="old" '
        'd:title="Kept"/></rdf:RDF></x:xmpmeta>'
    )
    merged = pm.merged_xmp_packet(packet.encode(), "new").decode()
    assert 'd:title="Kept"' in merged and "old" not in merged and ">new<" in merged


def test_an_unreadable_packet_gives_way_to_a_fresh_one() -> None:
    assert pm.merged_xmp_packet(b"\xff\xfe junk", "x") == pm.xmp_packet("x")
