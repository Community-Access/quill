"""QUILL's own Kindle (MOBI) reader, on books built in the test (mobi_fixture)."""

from __future__ import annotations

import os
import struct
from pathlib import Path

import pytest

from quill.core.error_codes import CodedError
from quill.io.mobi_read import (
    MAX_RECORD_OUTPUT,
    MobiCompressionError,
    MobiCorruptError,
    MobiDrmError,
    MobiKf8Error,
    MobiReadError,
    palmdoc_decompress,
    parse_mobi,
    read_mobi,
    trailing_size,
)
from tests.unit.io.mobi_fixture import (
    JPEG_STUB,
    PNG_PIXEL,
    build_mobi,
    palmdoc_compress,
    pdb,
    trailing_entry,
)

BOOK = "<html><body><p>Hello, garden. Hello, garden. Café — done.</p></body></html>"


# ---------------------------------------------------------------- PalmDOC


def test_each_palmdoc_branch_decodes() -> None:
    # 0x00 and 0x09-0x7F literal; 0x01-0x08 a run; 0xC0-0xFF space + char; a pair.
    assert palmdoc_decompress(b"\x00a\x09") == b"\x00a\x09"
    assert palmdoc_decompress(b"\x03\x80\x81\x82") == b"\x80\x81\x82"
    assert palmdoc_decompress(b"\xe1") == b" a"
    pair = struct.pack(">H", 0x8000 | (3 << 3) | (4 - 3))
    assert palmdoc_decompress(b"abc" + pair) == b"abcabca"  # overlapping copy


def test_the_compressor_round_trips_through_the_reader() -> None:
    for size in (0, 1, 7, 300, 4096):
        data = os.urandom(size) + b" the cat and the hat and the bat " * 5
        assert palmdoc_decompress(palmdoc_compress(data)) == data


def test_a_back_reference_before_the_start_is_damage() -> None:
    with pytest.raises(MobiCorruptError):
        palmdoc_decompress(b"a" + struct.pack(">H", 0x8000 | (9 << 3)))


def test_a_pair_cut_short_at_the_end_stops_without_a_hang() -> None:
    assert palmdoc_decompress(b"ab\x80") == b"ab"


def test_a_record_that_would_grow_without_bound_is_refused() -> None:
    pair = struct.pack(">H", 0x8000 | (1 << 3) | 7)
    with pytest.raises(MobiCorruptError):
        palmdoc_decompress(b"a" + pair * (MAX_RECORD_OUTPUT // 10 + 2))


# ------------------------------------------------------------- trailing entries


def test_trailing_entries_are_stripped_by_their_flags() -> None:
    record = b"text" + bytes(2) + b"\x02" + trailing_entry(b"xy") + trailing_entry(b"z" * 200)
    assert trailing_size(record, 0b111) == len(record) - 4
    assert trailing_size(b"text", 0) == 0


def test_trailing_sizes_never_pass_the_record() -> None:
    assert trailing_size(b"\x81", 0b10) <= 1
    assert trailing_size(b"\xff\xff\xff\xff", 0xFFFF) <= 4
    assert trailing_size(b"", 0xFFFF) == 0


# --------------------------------------------------------------- whole books


def test_a_palmdoc_book_reads_with_its_title_language_and_pictures() -> None:
    data = build_mobi(
        BOOK * 200,
        extra_flags=0b11,
        trailing=trailing_entry(b"\x01\x02"),
        multibyte=1,
        pictures=(PNG_PIXEL, b"FLIS\0\0\0\x08", JPEG_STUB),
        exth={503: "The Garden Book", 524: "en-GB"},
    )
    book = parse_mobi(data)
    assert book.html == BOOK * 200
    assert book.title == "The Garden Book" and book.language == "en-GB"
    assert {i: p.extension for i, p in book.pictures.items()} == {1: ".png", 3: ".jpg"}
    assert book.pictures[1].data == PNG_PIXEL


def test_an_uncompressed_book_reads() -> None:
    book = parse_mobi(build_mobi(BOOK, compression=1, title="Plain"))
    assert book.html == BOOK and book.title == "Plain" and book.pictures == {}


def test_a_windows_1252_book_decodes_as_such() -> None:
    raw = "<p>Café</p>".encode("cp1252")
    assert parse_mobi(build_mobi(raw, encoding=1252)).html == "<p>Café</p>"


def test_read_mobi_reads_a_file(tmp_path: Path) -> None:
    path = tmp_path / "book.mobi"
    path.write_bytes(build_mobi(BOOK))
    assert read_mobi(path).html == BOOK


# ---------------------------------------------------------------- refusals


@pytest.mark.parametrize(
    ("kwargs", "error", "code", "words"),
    [
        ({"encryption": 2}, MobiDrmError, "QUILL-IO-MOBI-DRM", "locked with DRM"),
        ({"compression": 17480}, MobiCompressionError, "QUILL-IO-MOBI-COMPRESSION", "to Word"),
        ({"compression": 9}, MobiCompressionError, "QUILL-IO-MOBI-COMPRESSION", "compression"),
        ({"version": 8}, MobiKf8Error, "QUILL-IO-MOBI-KF8", "(AZW3)"),
    ],
)
def test_each_refusal_is_coded_and_one_sentence(
    kwargs: dict[str, int], error: type[MobiReadError], code: str, words: str
) -> None:
    with pytest.raises(error) as raised:
        parse_mobi(build_mobi(BOOK, **kwargs), name="locked.mobi")
    assert isinstance(raised.value, CodedError) and raised.value.code == code
    sentence = raised.value.sentence
    assert sentence.startswith("locked.mobi ") and words in sentence
    assert sentence.count(". ") == 0 and sentence.endswith(".")
    assert str(raised.value) == f"[{code}] {sentence}"


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"not a book at all" * 10,
        pdb([b"x" * 300, b"y"], kind=b"TEXtREAd"),
        pdb([b"\0" * 300, b"y"]),  # no MOBI header in record 0
        build_mobi(BOOK)[:90],  # the record table runs past the end
    ],
    ids=["empty", "text", "palmdoc-text", "no-mobi-header", "cut-short"],
)
def test_damaged_files_are_refused_with_a_sentence(data: bytes) -> None:
    with pytest.raises(MobiCorruptError) as raised:
        parse_mobi(data, name="odd.mobi")
    assert raised.value.code == "QUILL-IO-MOBI-CORRUPT"
    assert raised.value.sentence == ("odd.mobi is damaged or is not a Kindle book.")


def test_record_offsets_that_go_backwards_are_damage() -> None:
    data = bytearray(build_mobi(BOOK))
    struct.pack_into(">I", data, 78 + 8, 10)  # record 1 starts inside the header
    with pytest.raises(MobiCorruptError):
        parse_mobi(bytes(data))


def test_a_text_record_count_past_the_records_is_damage() -> None:
    data = bytearray(build_mobi(BOOK))
    record0 = struct.unpack(">I", data[78:82])[0]
    struct.pack_into(">H", data, record0 + 8, 60)
    with pytest.raises(MobiCorruptError):
        parse_mobi(bytes(data))


def test_a_damaged_text_record_names_the_book() -> None:
    data = bytearray(build_mobi("<p>abcdefgh</p>"))
    record1 = struct.unpack(">I", data[86:90])[0]
    data[record1 : record1 + 3] = b"\x80\xff\x80"  # a back-reference into nothing
    with pytest.raises(MobiCorruptError) as raised:
        parse_mobi(bytes(data), name="bad.mobi")
    assert raised.value.sentence.startswith("bad.mobi is damaged")


def test_a_file_past_the_size_limit_is_not_read(tmp_path: Path, monkeypatch) -> None:
    from quill.io import mobi_read

    path = tmp_path / "huge.mobi"
    path.write_bytes(build_mobi(BOOK))
    monkeypatch.setattr(mobi_read, "MAX_FILE_BYTES", 10)
    with pytest.raises(MobiCorruptError) as raised:
        read_mobi(path)
    assert raised.value.sentence == "huge.mobi is over 256 MB, too large to open as a Kindle book."


def test_random_bytes_never_hang_and_only_ever_refuse() -> None:
    good = build_mobi(BOOK * 20, pictures=(PNG_PIXEL,))
    for seed in range(300):
        rng = __import__("random").Random(seed)
        data = bytearray(good)
        for _ in range(rng.randint(1, 12)):
            data[rng.randrange(len(data))] = rng.randrange(256)
        try:
            parse_mobi(bytes(data))
        except MobiReadError:
            pass
