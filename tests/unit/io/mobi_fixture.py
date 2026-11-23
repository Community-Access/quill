"""Build tiny Kindle (MOBI) books in a test, from our own HTML.

Everything here is ours: a Palm database header, a record 0 with the PalmDOC
and MOBI headers (and an EXTH block when asked), the text split into records
and PalmDOC-compressed by :func:`palmdoc_compress` (a simple greedy LZ77 that
uses every branch the decoder has), optional trailing entries, and picture
records. The layout follows the published format description; the files it
writes may be committed.
"""

from __future__ import annotations

import struct

RECORD_SIZE = 4096

#: A real (tiny) PNG: one transparent pixel.
PNG_PIXEL = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082"
)
#: Enough of a JPEG for the reader to know it by its first bytes.
JPEG_STUB = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + bytes(32) + b"\xff\xd9"


def palmdoc_compress(data: bytes) -> bytes:
    """PalmDOC LZ77: back-references, space pairs, literals and escaped runs."""
    out = bytearray()
    index = 0
    while index < len(data):
        best_length, best_distance = 0, 0
        for distance in range(1, min(index, 2047) + 1):
            length = 0
            while (
                length < 10
                and index + length < len(data)
                and data[index + length - distance] == data[index + length]
            ):
                length += 1
            if length > best_length:
                best_length, best_distance = length, distance
        if best_length >= 3:
            pair = 0x8000 | (best_distance << 3) | (best_length - 3)
            out += struct.pack(">H", pair)
            index += best_length
            continue
        byte = data[index]
        if byte == 0x20 and index + 1 < len(data) and 0x40 <= data[index + 1] <= 0x7F:
            out.append(data[index + 1] ^ 0x80)
            index += 2
        elif byte == 0 or 0x09 <= byte <= 0x7F:
            out.append(byte)
            index += 1
        else:
            run = bytearray()
            while index < len(data) and len(run) < 8:
                value = data[index]
                if value == 0 or 0x09 <= value <= 0x7F:
                    break
                run.append(value)
                index += 1
            out.append(len(run))
            out += run
    return bytes(out)


def trailing_entry(payload: bytes) -> bytes:
    """One trailing entry: *payload*, then its whole size written backwards."""
    size = len(payload) + 1
    while True:
        encoded = _backward_size(size)
        if len(payload) + len(encoded) == size:
            return payload + encoded
        size = len(payload) + len(encoded)


def _backward_size(value: int) -> bytes:
    groups = []
    while True:
        groups.append(value & 0x7F)
        value >>= 7
        if not value:
            break
    groups.reverse()  # most significant first
    groups[0] |= 0x80  # read backwards from the end, the stop bit is on the last byte read
    return bytes(groups)


def build_mobi(
    html: str | bytes,
    *,
    compression: int = 2,
    encryption: int = 0,
    version: int = 6,
    encoding: int = 65001,
    extra_flags: int = 0,
    trailing: bytes = b"",
    multibyte: int = 0,
    pictures: tuple[bytes, ...] = (),
    title: str = "A Test Book",
    exth: dict[int, str] | None = None,
    record_size: int = RECORD_SIZE,
) -> bytes:
    """A whole MOBI file. *trailing* is appended to each text record, then the
    multibyte overlap: *multibyte* extra bytes and a byte saying how many."""
    raw = html.encode("utf-8") if isinstance(html, str) else html
    chunks = [raw[i : i + record_size] for i in range(0, len(raw), record_size)] or [b""]
    text_records = []
    for chunk in chunks:
        body = palmdoc_compress(chunk) if compression == 2 else chunk
        if extra_flags & 1:
            body += bytes(multibyte) + bytes([multibyte & 3])
        text_records.append(body + trailing)
    first_image = 1 + len(text_records) if pictures else 0xFFFFFFFF
    record0 = _record0(
        len(raw),
        len(text_records),
        compression=compression,
        encryption=encryption,
        version=version,
        encoding=encoding,
        extra_flags=extra_flags,
        first_image=first_image,
        title=title,
        exth=exth or {},
    )
    records = [record0, *text_records, *pictures, b"\xe9\x8e\r\n"]
    return pdb(records)


def pdb(records: list[bytes], kind: bytes = b"BOOKMOBI") -> bytes:
    """A Palm database holding *records*."""
    header = bytearray(78)
    header[0:9] = b"test-book"
    header[60:68] = kind
    struct.pack_into(">H", header, 76, len(records))
    offset = 78 + 8 * len(records) + 2
    table = bytearray()
    for number, record in enumerate(records):
        table += struct.pack(">II", offset, number * 2)
        offset += len(record)
    return bytes(header) + bytes(table) + b"\0\0" + b"".join(records)


def _record0(
    text_length: int,
    text_count: int,
    *,
    compression: int,
    encryption: int,
    version: int,
    encoding: int,
    extra_flags: int,
    first_image: int,
    title: str,
    exth: dict[int, str],
) -> bytes:
    header_length = 0xE8
    mobi = bytearray(header_length)
    mobi[0:4] = b"MOBI"
    struct.pack_into(">III", mobi, 4, header_length, 2, encoding)
    struct.pack_into(">I", mobi, 0x14, version)
    exth_block = _exth(exth) if exth else b""
    title_bytes = title.encode("utf-8")
    title_offset = 16 + header_length + len(exth_block)
    struct.pack_into(">II", mobi, 0x54 - 16, title_offset, len(title_bytes))
    struct.pack_into(">I", mobi, 0x6C - 16, first_image)
    struct.pack_into(">I", mobi, 0x80 - 16, 0x40 if exth else 0)
    struct.pack_into(">H", mobi, 0xF2 - 16, extra_flags)
    palmdoc = struct.pack(
        ">HHIHHHH", compression, 0, text_length, text_count, RECORD_SIZE, encryption, 0
    )
    return palmdoc + bytes(mobi) + exth_block + title_bytes + b"\0\0"


def _exth(entries: dict[int, str]) -> bytes:
    body = b"".join(
        struct.pack(">II", kind, 8 + len(value.encode("utf-8"))) + value.encode("utf-8")
        for kind, value in entries.items()
    )
    block = b"EXTH" + struct.pack(">II", 12 + len(body), len(entries)) + body
    return block + bytes(-len(block) % 4)
