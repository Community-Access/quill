"""Opening a file never loses a byte of it, in either editor (2026-10-04).

The PlanCake design note found the one real data-loss path in the family: QUILL
Lite decoded a non-UTF-8 file as Windows-1252 with ``errors="replace"``, so the
five bytes cp1252 leaves undefined became replacement characters and were
written back that way on the next save. Both editors now share one decoder,
:func:`quill.core.text_decoding.decode_bytes`, and every fixture here is real
bytes put through each editor's own reader and writer and compared byte for
byte.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.lite.textfile import decode_text, encode_text
from quill.core.text_decoding import (
    REOPEN_ENCODINGS,
    UTF16_BE_BOM_CODEC,
    decode_as,
    decode_bytes,
    open_notice,
    reopen_mismatch_sentence,
)
from quill.io.text import read_text_document, write_text_document

CRLF = bytes([13, 10])

#: ``(name, bytes, encoding the decoder should report)``.
FIXTURES: list[tuple[str, bytes, str]] = [
    # Smart quotes and an em dash, as Notepad wrote them before UTF-8.
    (
        "cp1252",
        b"It"
        + bytes([0x92])
        + b"s "
        + bytes([0x93])
        + b"done"
        + bytes([0x94])
        + b" "
        + bytes([0x97])
        + b" really."
        + CRLF,
        "cp1252",
    ),
    # 0x81, 0x8D, 0x8F, 0x90 and 0x9D: undefined in cp1252, the bytes the old
    # Lite decoder replaced. Latin-1 keeps every one of them.
    ("latin-1", b"caf" + bytes([0xE9, 0x81, 0x8D, 0x8F, 0x90, 0x9D]) + b"\n", "latin-1"),
    ("utf-16 le bom", "Grüße, ☃".encode("utf-16"), "utf-16"),
    (
        "utf-16 be bom",
        bytes([0xFE, 0xFF]) + "Grüße\r\nwelt".encode("utf-16-be"),
        UTF16_BE_BOM_CODEC,
    ),
    ("utf-8 bom", bytes([0xEF, 0xBB, 0xBF]) + "naïve résumé\n".encode(), "utf-8-sig"),
    ("utf-8", "plain café".encode(), "utf-8"),
    # A UTF-8 BOM followed by bytes that are not UTF-8: the BOM lied, so the
    # whole file, mark included, is read by the fallback chain.
    ("lying bom", bytes([0xEF, 0xBB, 0xBF, 0x81, 0xFF]), "latin-1"),
    # UTF-32's mark begins with UTF-16's: excluded, not read as empty UTF-16.
    ("utf-32 mark", "hi".encode("utf-32"), "cp1252"),
    # Every byte value there is, in one file, less the two line-ending bytes
    # (a file mixing CR and LF is normalised to one ending, by design).
    ("all bytes", bytes(b for b in range(256) if b not in (10, 13)), "latin-1"),
]


@pytest.mark.parametrize(("name", "raw", "encoding"), FIXTURES, ids=[f[0] for f in FIXTURES])
def test_the_shared_decoder_names_the_encoding_and_loses_nothing(
    name: str, raw: bytes, encoding: str
) -> None:
    decoded = decode_bytes(raw)
    assert decoded.encoding == encoding, name
    assert "�" not in decoded.text
    assert decoded.text.encode(decoded.encoding) == raw


@pytest.mark.parametrize(("name", "raw", "encoding"), FIXTURES, ids=[f[0] for f in FIXTURES])
def test_quill_lite_saves_every_fixture_back_byte_for_byte(
    name: str, raw: bytes, encoding: str
) -> None:
    decoded = decode_text(raw)
    assert decoded.encoding == encoding, name
    assert encode_text(decoded.text, encoding=decoded.encoding, newline=decoded.newline) == raw


@pytest.mark.parametrize(("name", "raw", "encoding"), FIXTURES, ids=[f[0] for f in FIXTURES])
def test_quill_saves_every_fixture_back_byte_for_byte(
    tmp_path: Path, name: str, raw: bytes, encoding: str
) -> None:
    if CRLF in raw and b"\n" in raw.replace(CRLF, b""):
        pytest.skip("mixed line endings are normalised to one, by design")
    if bytes([13]) in raw.replace(CRLF, b""):
        pytest.skip("a lone CR is normalised by QUILL's editor, by design")
    target = tmp_path / "fixture.txt"
    target.write_bytes(raw)
    document = read_text_document(target)
    assert document.encoding == encoding, name
    write_text_document(document, target)
    assert target.read_bytes() == raw


def test_the_bytes_the_old_lite_decoder_replaced_now_survive_a_save() -> None:
    """The regression itself, stated as the user would meet it."""
    raw = b"Price: 5" + bytes([0x81]) + b" and " + bytes([0x9D]) + b"\r\n"
    decoded = decode_text(raw)
    assert "�" not in decoded.text
    assert encode_text(decoded.text, encoding=decoded.encoding, newline=decoded.newline) == raw


def test_a_big_endian_file_stays_big_endian_in_quill_too(tmp_path: Path) -> None:
    """The registered codec: QUILL's writer used to flip it to little-endian."""
    raw = bytes([0xFE, 0xFF]) + "one\ntwo".encode("utf-16-be")
    target = tmp_path / "be.txt"
    target.write_bytes(raw)
    document = read_text_document(target)
    document.set_text("one\ntwo")
    write_text_document(document, target)
    assert target.read_bytes() == raw


def test_the_open_notice_is_said_only_for_a_file_that_is_not_utf8() -> None:
    assert open_notice("utf-8") == ""
    assert open_notice("utf-8-sig") == ""
    assert open_notice("cp1252") == "Opened as Windows-1252, not UTF-8."
    assert open_notice("latin-1") == "Opened as Latin-1 (ISO 8859-1), not UTF-8."
    assert open_notice("utf-16") == "Opened as UTF-16, not UTF-8."


def test_reopen_reads_the_same_bytes_strictly_as_the_chosen_code_page() -> None:
    raw = bytes([0xC0, 0xE9, 0xF0])  # three letters in Windows-1251
    assert decode_as(raw, "cp1251").text == "Айр"
    assert decode_as(raw, "cp1251").encoding == "cp1251"
    with pytest.raises(UnicodeDecodeError):
        decode_as(raw, "utf-8")


def test_reopen_keeps_the_mark_a_file_carries() -> None:
    assert decode_as(bytes([0xEF, 0xBB, 0xBF]) + b"x", "utf-8").encoding == "utf-8-sig"
    be = bytes([0xFE, 0xFF]) + "x".encode("utf-16-be")
    assert decode_as(be, "utf-16").encoding == UTF16_BE_BOM_CODEC
    assert decode_as("x".encode("utf-16-le"), "utf-16").encoding == "utf-16-le"


@pytest.mark.parametrize(("codec", "_name"), REOPEN_ENCODINGS)
def test_every_offered_reopen_encoding_round_trips_what_it_reads(codec: str, _name: str) -> None:
    raw = "Plain words 123.\n".encode(codec if codec != "utf-16" else "utf-16")
    decoded = decode_as(raw, codec)
    assert decoded.text.encode(decoded.encoding) == raw


def test_a_mismatch_is_one_plain_sentence() -> None:
    sentence = reopen_mismatch_sentence("utf-8")
    assert sentence.startswith("This file is not valid UTF-8")
    assert sentence.endswith(".")
