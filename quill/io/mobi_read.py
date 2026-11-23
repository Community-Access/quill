"""Read a DRM-free Kindle (MOBI) book: its text, its pictures, its title.

Scribe for Documents returns a Kindle book (``.mobi``) beside its other
formats, and "every returned format can be read" (Scribe phase one,
2026-11-23), so QUILL and QUILL Lite open one as a document. This module is
QUILL's own reader, written from the published format description (the
MobileRead wiki's MOBI and PalmDOC pages); no GPL code (KindleUnpack, calibre,
the ``mobi`` package) is used or copied.

What a MOBI is, as far as this reader needs:

* A **Palm database**: a 78-byte header whose type/creator at offset 60 says
  ``BOOKMOBI``, a record count at 76, and then one 8-byte entry per record
  whose first four bytes are the record's offset in the file.
* **Record 0**: the PalmDOC header (compression, text length, text record
  count, encryption) and then the MOBI header (``MOBI`` at 16: its length,
  text encoding, file version, first image record, the EXTH flag and the
  extra-data flags that say what trails each text record).
* **Text records** 1..n: each compressed on its own (PalmDOC LZ77, or not at
  all), with trailing entries to strip first. Joined, they are Kindle HTML.
* **Image records**, counted from the first image record; ``<img
  recindex="00003">`` names the third.

What it will not read, each refused with a coded error and one sentence
(GATE-EC): a book locked with DRM, one compressed with HUFF/CDIC, a KF8-only
book (AZW3), and a damaged file. Every size is bounded and every loop
advances, so a hostile file can cost a refusal and never a hang.

wx-free; strict-typed.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.error_codes import CodedError

__all__ = [
    "MAX_FILE_BYTES",
    "MobiBook",
    "MobiCompressionError",
    "MobiCorruptError",
    "MobiDrmError",
    "MobiKf8Error",
    "MobiPicture",
    "MobiReadError",
    "palmdoc_decompress",
    "parse_mobi",
    "read_mobi",
    "trailing_size",
]

#: A larger file is refused unread: Kindle books are rarely past a few tens of
#: megabytes, and the whole file is held in memory while it is read.
MAX_FILE_BYTES = 256 * 1024 * 1024
#: The book's text, decompressed, may not pass this.
MAX_TEXT_BYTES = 64 * 1024 * 1024
#: One PalmDOC record decompresses to 4096 bytes; anything past this is damage.
MAX_RECORD_OUTPUT = 64 * 1024
#: The most pictures a book may bring with it.
MAX_PICTURES = 2000

_PDB_HEADER = 78
_COMPRESSION_NONE = 1
_COMPRESSION_PALMDOC = 2
_ENCODINGS = {65001: "utf-8", 1252: "cp1252"}
_PICTURE_KINDS: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"BM", ".bmp"),
)
_NO_PICTURE_INDEX = 0xFFFFFFFF


class MobiReadError(CodedError):
    """A Kindle book QUILL cannot read. ``sentence`` is what to say."""

    code = "QUILL-IO-MOBI-UNREADABLE"

    def __init__(self, sentence: str) -> None:
        super().__init__(sentence)
        self.sentence = sentence


class MobiDrmError(MobiReadError):
    """The book is locked with DRM; only the store's own reader can open it."""

    code = "QUILL-IO-MOBI-DRM"


class MobiCompressionError(MobiReadError):
    """HUFF/CDIC (or another) compression this reader does not decode."""

    code = "QUILL-IO-MOBI-COMPRESSION"


class MobiKf8Error(MobiReadError):
    """A KF8-only book (AZW3): no older MOBI text inside to read."""

    code = "QUILL-IO-MOBI-KF8"


class MobiCorruptError(MobiReadError):
    """Not a Kindle book, or one that is damaged."""

    code = "QUILL-IO-MOBI-CORRUPT"


@dataclass(frozen=True, slots=True)
class MobiPicture:
    """One image record: its 1-based ``recindex``, its bytes and its extension."""

    index: int
    data: bytes
    extension: str


@dataclass(frozen=True, slots=True)
class MobiBook:
    """What :func:`parse_mobi` found. ``html`` is the Kindle HTML, decoded."""

    title: str
    html: str
    language: str = ""
    pictures: dict[int, MobiPicture] = field(default_factory=dict)


def _damaged(name: str) -> MobiCorruptError:
    return MobiCorruptError(f"{name} is damaged or is not a Kindle book.")


#: How to read a book this reader refuses but a converter can rewrite. Word,
#: because both editors open Word and QUILL Lite does not open EPUB.
_CONVERT = "convert it to Word with an e-book converter, then open that."


def read_mobi(path: Path) -> MobiBook:
    """Read *path*. Raises :class:`MobiReadError` (a sentence) or ``OSError``."""
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise MobiCorruptError(f"{path.name} is over 256 MB, too large to open as a Kindle book.")
    return parse_mobi(path.read_bytes(), name=path.name)


def parse_mobi(data: bytes, *, name: str = "This book") -> MobiBook:
    """Parse a whole MOBI file held in memory."""
    offsets = _record_offsets(data, name)
    record0 = data[offsets[0] : offsets[1]]
    if len(record0) < 16:
        raise _damaged(name)
    compression, _unused, text_length, text_count, _size, encryption = struct.unpack(
        ">HHIHHH", record0[:14]
    )
    header = _mobi_header(record0, name)  # not a Kindle book at all, first
    if encryption != 0:
        raise MobiDrmError(
            f"{name} is locked with DRM, so it can only be read in the Kindle app or on "
            "the Kindle it was bought for."
        )
    if compression not in (_COMPRESSION_NONE, _COMPRESSION_PALMDOC):  # HUFF/CDIC, or other
        raise MobiCompressionError(
            f"{name} uses a kind of compression this editor does not read; {_CONVERT}"
        )
    if header.version >= 8:
        raise MobiKf8Error(
            f"{name} is a newer Kindle book (AZW3) that this editor cannot read; {_CONVERT}"
        )
    if text_length > MAX_TEXT_BYTES or text_count == 0 or text_count >= len(offsets) - 1:
        raise _damaged(name)
    chunks: list[bytes] = []
    total = 0
    for index in range(1, text_count + 1):
        record = data[offsets[index] : offsets[index + 1]]
        body = record[: len(record) - trailing_size(record, header.extra_flags)]
        try:
            text = palmdoc_decompress(body) if compression == _COMPRESSION_PALMDOC else bytes(body)
        except MobiCorruptError:
            raise _damaged(name) from None
        total += len(text)
        if total > MAX_TEXT_BYTES:
            raise _damaged(name)
        chunks.append(text)
    raw = b"".join(chunks)[:text_length] if text_length else b"".join(chunks)
    codec = _ENCODINGS.get(header.encoding, "cp1252")
    html = raw.decode(codec, errors="replace")
    return MobiBook(
        title=header.title,
        html=html,
        language=header.language,
        pictures=_pictures(data, offsets, header.first_image, text_count),
    )


def _record_offsets(data: bytes, name: str) -> list[int]:
    """Every record's start, then the file's end: one more entry than records."""
    if len(data) < _PDB_HEADER + 8 or data[60:68] != b"BOOKMOBI":
        raise _damaged(name)
    (count,) = struct.unpack(">H", data[76:78])
    table_end = _PDB_HEADER + 8 * count
    if count < 2 or table_end > len(data):
        raise _damaged(name)
    offsets = [
        struct.unpack(">I", data[_PDB_HEADER + 8 * k : _PDB_HEADER + 8 * k + 4])[0]
        for k in range(count)
    ]
    offsets.append(len(data))
    previous = table_end
    for offset in offsets:
        if offset < previous or offset > len(data):
            raise _damaged(name)
        previous = offset
    return offsets


@dataclass(frozen=True, slots=True)
class _Header:
    encoding: int
    version: int
    first_image: int
    extra_flags: int
    title: str
    language: str


def _mobi_header(record0: bytes, name: str) -> _Header:
    if record0[16:20] != b"MOBI" or len(record0) < 0x84:
        raise _damaged(name)
    (length,) = struct.unpack(">I", record0[20:24])
    encoding, _uid, version = struct.unpack(">III", record0[28:40])
    title_offset, title_length = struct.unpack(">II", record0[0x54:0x5C])
    (first_image,) = struct.unpack(">I", record0[0x6C:0x70])
    (exth_flags,) = struct.unpack(">I", record0[0x80:0x84])
    extra_flags = 0
    if length >= 0xE4 and len(record0) >= 0xF4:
        (extra_flags,) = struct.unpack(">H", record0[0xF2:0xF4])
    codec = _ENCODINGS.get(encoding, "cp1252")
    title = record0[title_offset : title_offset + min(title_length, 1024)].decode(
        codec, errors="replace"
    )
    exth = _exth(record0, 16 + length, codec) if exth_flags & 0x40 else {}
    return _Header(
        encoding=encoding,
        version=version,
        first_image=first_image,
        extra_flags=extra_flags,
        title=(exth.get(503) or title).strip(),
        language=exth.get(524, "").strip(),
    )


def _exth(record0: bytes, start: int, codec: str) -> dict[int, str]:
    """The EXTH entries this reader uses (503 title, 524 language), or ``{}``."""
    if record0[start : start + 4] != b"EXTH" or start + 12 > len(record0):
        return {}
    (count,) = struct.unpack(">I", record0[start + 8 : start + 12])
    found: dict[int, str] = {}
    cursor = start + 12
    for _ in range(min(count, 1024)):
        if cursor + 8 > len(record0):
            break
        kind, size = struct.unpack(">II", record0[cursor : cursor + 8])
        if size < 8 or cursor + size > len(record0):
            break
        if kind in (503, 524):
            found[kind] = record0[cursor + 8 : cursor + size].decode(codec, errors="replace")
        cursor += size
    return found


def _pictures(
    data: bytes, offsets: list[int], first_image: int, text_count: int
) -> dict[int, MobiPicture]:
    """Image records by ``recindex`` (1-based from the first image record)."""
    pictures: dict[int, MobiPicture] = {}
    if first_image in (0, _NO_PICTURE_INDEX) or first_image <= text_count:
        return pictures
    for record_index in range(first_image, len(offsets) - 1):
        if len(pictures) >= MAX_PICTURES:
            break
        record = data[offsets[record_index] : offsets[record_index + 1]]
        extension = next((ext for magic, ext in _PICTURE_KINDS if record.startswith(magic)), "")
        if extension:
            index = record_index - first_image + 1
            pictures[index] = MobiPicture(index=index, data=bytes(record), extension=extension)
    return pictures


def trailing_size(record: bytes, flags: int) -> int:
    """How many bytes at the end of a text record are trailing entries, not text.

    Each set bit from 1 to 15 of the extra-data flags is one entry, laid at the
    end of the record in turn from bit 1, and each entry ends in its own size
    written backwards: from the last byte towards the front, seven bits a byte,
    until a byte with its top bit set. Bit 0 is the multibyte overlap, the last
    one stripped: its low two bits, plus one. Never more than the record.
    """
    size = len(record)
    consumed = 0
    for bit in range(1, 16):
        if not flags & (1 << bit):
            continue
        value = 0
        shift = 0
        position = size - consumed
        for _ in range(4):
            if position <= 0:
                break
            byte = record[position - 1]
            position -= 1
            value |= (byte & 0x7F) << shift
            shift += 7
            if byte & 0x80:
                break
        consumed = min(size, consumed + value)
    if flags & 1 and consumed < size:
        consumed = min(size, consumed + (record[size - consumed - 1] & 3) + 1)
    return consumed


def palmdoc_decompress(data: bytes) -> bytes:
    """PalmDOC LZ77, bounded: a damaged record raises :class:`MobiCorruptError`."""
    out = bytearray()
    index = 0
    length = len(data)
    while index < length:
        byte = data[index]
        index += 1
        if byte == 0 or 0x09 <= byte <= 0x7F:
            out.append(byte)
        elif byte <= 0x08:
            out += data[index : index + byte]
            index += byte
        elif byte >= 0xC0:
            out.append(0x20)
            out.append(byte ^ 0x80)
        else:
            if index >= length:
                break  # a pair cut short at the end: nothing left to copy
            pair = (byte << 8) | data[index]
            index += 1
            distance = (pair >> 3) & 0x7FF
            count = (pair & 7) + 3
            if distance == 0 or distance > len(out):
                raise _damaged("This Kindle book")
            start = len(out) - distance
            for step in range(count):  # may overlap what it is writing
                out.append(out[start + step])
        if len(out) > MAX_RECORD_OUTPUT:
            raise _damaged("This Kindle book")
    return bytes(out)
