"""Write a picture's description into a copy of it, never into the picture itself.

QUILL Studio's Save Described Copies uses this, so a description travels with
the photo into Windows Explorer's details, photo libraries and anything that
reads XMP. A sighted relative gets the picture; its blind owner can still find
it by its words. The tag choices follow Kelly Ford's Image Description
Toolkit (MIT; see the third-party notices):

* **JPEG**: EXIF ``ImageDescription`` (plain ASCII, as the standard says, so
  accents are folded), EXIF ``XPComment`` (UTF-16, the Comments field Windows
  shows) and XMP ``dc:description`` (UTF-8). The segments are spliced into
  the file as it is, so the picture is never re-encoded and loses nothing.
* **PNG**: an ``iTXt`` ``Description`` chunk and an XMP ``iTXt`` chunk, added
  before the image data. The pixels are copied byte for byte.

An XMP packet the original already carried is **merged**, not replaced
(:func:`merged_xmp_packet`): every other property it had -- a rating, keywords,
a photo library's face tags -- stays in the copy, and only a ``dc:description``
already there gives way to the new one.

Any other kind of picture has no field written here and is left out, said by
name. The source is only ever read: :func:`write_described_copy` refuses a
target that is the source, and a target that already exists gets a new name.

wx-free, strict-typed and network-free.
"""

from __future__ import annotations

import io
import re
import struct
import unicodedata
import zlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from quill.core.error_codes import CodedError

__all__ = [
    "SUPPORTED_SUFFIXES",
    "CopyOutcome",
    "DescribedCopyError",
    "jpeg_with_description",
    "merged_xmp_packet",
    "png_with_description",
    "write_described_copies",
    "write_described_copy",
    "xmp_packet",
]

SUPPORTED_SUFFIXES: frozenset[str] = frozenset({".jpg", ".jpeg", ".png"})

_EXIF_HEADER = b"Exif\x00\x00"
_XMP_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_IMAGE_DESCRIPTION = 0x010E
_XP_COMMENT = 0x9C9C
_MAX_SEGMENT = 65533
_FOLD = str.maketrans({"—": "-", "–": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "…": "..."})


class DescribedCopyError(CodedError):
    """A described copy could not be written; the message is a sentence."""

    code = "QUILL-IO-PICTURE-METADATA-FAILED"


def xmp_packet(description: str) -> bytes:
    """A minimal XMP packet holding *description* as ``dc:description``."""
    text = escape(description, {'"': "&quot;"})
    return (
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f'<dc:description><rdf:Alt><rdf:li xml:lang="x-default">{text}</rdf:li></rdf:Alt>'
        "</dc:description></rdf:Description></rdf:RDF></x:xmpmeta>"
        '<?xpacket end="w"?>'
    ).encode()


_DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"
_RDF_CLOSE = re.compile(r"</(?P<prefix>[A-Za-z_][\w.-]*):RDF\s*>")


def _description_block(description: str, rdf: str) -> str:
    text = escape(description, {'"': "&quot;"})
    return (
        f'<{rdf}:Description {rdf}:about="" xmlns:dc="{_DC_NAMESPACE}">'
        f'<dc:description><{rdf}:Alt><{rdf}:li xml:lang="x-default">{text}</{rdf}:li>'
        f"</{rdf}:Alt></dc:description></{rdf}:Description>"
    )


def merged_xmp_packet(existing: bytes, description: str) -> bytes:
    """*existing*, an XMP packet, with *description* as its ``dc:description``.

    Everything else in the packet is kept as it was written, byte for byte:
    only a ``dc:description`` already there (as an element or an attribute,
    under whatever prefix the packet gives Dublin Core) is taken out, and one
    ``rdf:Description`` holding the new one is added before ``</rdf:RDF>``.
    A packet that cannot be read as text, or has no ``rdf:RDF``, gives way to
    :func:`xmp_packet`, as before.
    """
    try:
        text = existing.decode("utf-8")
    except UnicodeDecodeError:
        return xmp_packet(description)
    if _RDF_CLOSE.search(text) is None:
        return xmp_packet(description)
    declared = r"xmlns:([A-Za-z_][\w.-]*)\s*=\s*[\"']" + re.escape(_DC_NAMESPACE)
    for prefix in set(re.findall(declared, text)):
        name = re.escape(prefix) + ":description"
        text = re.sub(rf"<{name}(\s[^>]*)?/>", "", text)
        text = re.sub(rf"<{name}(\s[^>]*)?>.*?</{name}\s*>", "", text, flags=re.DOTALL)
        text = re.sub(rf"\s{name}\s*=\s*(\"[^\"]*\"|'[^']*')", "", text)
    close = list(_RDF_CLOSE.finditer(text))[-1]
    block = _description_block(description, close.group("prefix"))
    return (text[: close.start()] + block + text[close.start() :]).encode("utf-8")


def _ascii(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.translate(_FOLD))
    return folded.encode("ascii", "ignore").decode("ascii")


def _segment(marker: int, payload: bytes) -> bytes:
    if len(payload) > _MAX_SEGMENT:
        raise DescribedCopyError("The description is too long to fit in the picture's metadata.")
    return struct.pack(">BBH", 0xFF, marker, len(payload) + 2) + payload


def _exif_payload(data: bytes, description: str) -> bytes:
    from PIL import Image

    with Image.open(io.BytesIO(data)) as opened:
        exif: Any = opened.getexif()
    exif[_IMAGE_DESCRIPTION] = _ascii(description)
    exif[_XP_COMMENT] = description.encode("utf-16-le") + b"\x00\x00"
    payload = bytes(exif.tobytes())
    return payload if payload.startswith(_EXIF_HEADER) else _EXIF_HEADER + payload


def jpeg_with_description(data: bytes, description: str) -> bytes:
    """*data*, a JPEG, with *description* in its EXIF and XMP; the image untouched."""
    if not data.startswith(b"\xff\xd8"):
        raise DescribedCopyError("That file is not a JPEG picture.")
    exif = _segment(0xE1, _exif_payload(data, description))
    existing: bytes | None = None
    head: list[bytes] = []
    position = 2
    while position + 4 <= len(data) and data[position] == 0xFF:
        marker = data[position + 1]
        if marker == 0xDA or not 0xE0 <= marker <= 0xFE:
            break  # the image data starts here; everything after is copied as it is
        (length,) = struct.unpack(">H", data[position + 2 : position + 4])
        segment = data[position : position + 2 + length]
        payload = segment[4:]
        if marker == 0xE1 and payload.startswith(_XMP_HEADER):
            if existing is None:
                existing = payload[len(_XMP_HEADER) :]
        elif not (marker == 0xE1 and payload.startswith(_EXIF_HEADER)):
            head.append(segment)
        position += 2 + length
    packet = (
        xmp_packet(description) if existing is None else merged_xmp_packet(existing, description)
    )
    xmp = _segment(0xE1, _XMP_HEADER + packet)
    app0 = [s for s in head if s[1] == 0xE0]
    others = [s for s in head if s[1] != 0xE0]
    return b"\xff\xd8" + b"".join(app0) + exif + xmp + b"".join(others) + data[position:]


def _chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def _itxt(keyword: str, text: str) -> bytes:
    return _chunk(
        b"iTXt", keyword.encode("latin-1") + b"\x00\x00\x00\x00\x00" + text.encode("utf-8")
    )


def _png_xmp(data: bytes) -> bytes | None:
    """The XMP packet in *data*'s uncompressed ``iTXt`` chunk, if it has one."""
    position = len(_PNG_SIGNATURE)
    while position + 8 <= len(data):
        (length,) = struct.unpack(">I", data[position : position + 4])
        kind = data[position + 4 : position + 8]
        body = data[position + 8 : position + 8 + length]
        if kind == b"iTXt" and body.startswith(b"XML:com.adobe.xmp\x00"):
            rest = body[len(b"XML:com.adobe.xmp\x00") :]
            if rest[:1] == b"\x00":  # not compressed
                # compression method, then language tag and translated keyword
                parts = rest[2:].split(b"\x00", 2)
                if len(parts) == 3:
                    return parts[2]
            return None
        position += 12 + length
    return None


def png_with_description(data: bytes, description: str) -> bytes:
    """*data*, a PNG, with *description* in ``iTXt`` chunks before the image data."""
    if not data.startswith(_PNG_SIGNATURE):
        raise DescribedCopyError("That file is not a PNG picture.")
    ours = (b"Description", b"XML:com.adobe.xmp")
    existing = _png_xmp(data)
    packet = (
        xmp_packet(description) if existing is None else merged_xmp_packet(existing, description)
    )
    out = [_PNG_SIGNATURE]
    position = len(_PNG_SIGNATURE)
    added = False
    while position + 8 <= len(data):
        (length,) = struct.unpack(">I", data[position : position + 4])
        kind = data[position + 4 : position + 8]
        chunk = data[position : position + 12 + length]
        if kind in (b"IDAT", b"IEND") and not added:
            out += [
                _itxt("Description", description),
                _itxt("XML:com.adobe.xmp", packet.decode("utf-8")),
            ]
            added = True
        keyword = data[position + 8 : position + 8 + length].split(b"\x00", 1)[0]
        if not (kind in (b"iTXt", b"tEXt", b"zTXt") and keyword in ours):
            out.append(chunk)
        position += 12 + length
    if not added:
        raise DescribedCopyError("That PNG picture has no image data.")
    return b"".join(out)


def _free_name(path: Path) -> Path:
    if not path.exists():
        return path
    for number in range(2, 10_000):
        candidate = path.with_name(f"{path.stem} ({number}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise DescribedCopyError(f"Could not find a free file name for {path.name}.")


def write_described_copy(source: Path, target: Path, description: str) -> Path:
    """Write a copy of *source* holding *description* at *target* (or a free name
    beside it); returns where it went. *source* is only read."""
    suffix = source.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise DescribedCopyError(
            f"{source.name} is a kind of picture QUILL writes no description into."
        )
    target = _free_name(target)
    if target.resolve() == source.resolve():
        raise DescribedCopyError("A described copy never replaces the picture itself.")
    try:
        data = source.read_bytes()
    except OSError as error:
        raise DescribedCopyError(
            f"{source.name} could not be read: {error.strerror or error}"
        ) from error
    text = description.strip()
    copied = (
        png_with_description(data, text) if suffix == ".png" else jpeg_with_description(data, text)
    )
    from quill.core.storage import write_bytes_atomic

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        write_bytes_atomic(target, copied)
    except OSError as error:
        raise DescribedCopyError(
            f"The copy of {source.name} could not be saved: {error}"
        ) from error
    return target


@dataclass(slots=True)
class CopyOutcome:
    """What Save Described Copies did, for its one sentence."""

    written: list[Path] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def sentence(self, where: str) -> str:
        count = len(self.written)
        parts = [f"Saved {count} described {'copy' if count == 1 else 'copies'} in {where}."]
        if self.unsupported:
            parts.append(
                f"{_names(self.unsupported)} left out: QUILL writes descriptions into JPEG and "
                "PNG pictures only."
            )
        if self.missing:
            one = len(self.missing) == 1
            parts.append(
                f"{_names(self.missing)} {'is' if one else 'are'} no longer where "
                f"{'it was' if one else 'they were'} described."
            )
        if self.failed:
            parts.append(f"{_names(self.failed)} could not be copied.")
        return " ".join(parts)


def _names(names: list[str]) -> str:
    shown = ", ".join(names[:3]) + (" and others" if len(names) > 3 else "")
    return f"{len(names)} {'picture' if len(names) == 1 else 'pictures'} ({shown})"


def write_described_copies(results: Iterable[Any], destination: Path) -> CopyOutcome:
    """One described copy per picture result that has a description, its latest.

    *results* are :class:`quill.core.ai.picture_batch.PictureResult` objects;
    each copy keeps the picture's place below the folder that was described.
    """
    outcome = CopyOutcome()
    for result in results:
        if not result.descriptions:
            continue
        source = Path(result.path)
        if source.suffix.lower() not in SUPPORTED_SUFFIXES:
            outcome.unsupported.append(source.name)
            continue
        if not source.is_file():
            outcome.missing.append(source.name)
            continue
        try:
            written = write_described_copy(
                source, destination / Path(result.relative), result.descriptions[-1].text
            )
        except DescribedCopyError:
            outcome.failed.append(source.name)
            continue
        outcome.written.append(written)
    return outcome
