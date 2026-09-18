"""UTF-16 files open as text rather than as gibberish (bad.md F6, P1.8).

A UTF-16 file opened as UTF-8 does not raise: most of its bytes decode through
the cp1252 fallback, so QUILL opened it as a document with a NUL between every
letter. That reads as nonsense to a screen reader and, worse, *saves* as
nonsense -- the round trip destroyed the file. Notepad has written a BOM on
these since Windows 95 and reads one the same way.
"""

from __future__ import annotations

from pathlib import Path

from quill.io.text import detect_utf16, read_text_document, write_text_document

LE_BOM = bytes([0xFF, 0xFE])
BE_BOM = bytes([0xFE, 0xFF])


def test_a_little_endian_bom_is_utf16() -> None:
    assert detect_utf16(LE_BOM + "hi".encode("utf-16-le")) == "utf-16"


def test_a_big_endian_bom_is_utf16_too() -> None:
    assert detect_utf16(BE_BOM + "hi".encode("utf-16-be")) == "utf-16"


def test_utf8_is_not_mistaken_for_it() -> None:
    assert detect_utf16(b"hello") is None
    assert detect_utf16(b"") is None


def test_utf32_is_excluded_rather_than_read_as_an_empty_utf16_file() -> None:
    """Its first two bytes are the UTF-16 LE mark, which is the whole trap."""
    assert detect_utf16("hi".encode("utf-32")) is None


def test_a_utf16_file_opens_as_its_text(tmp_path: Path) -> None:
    target = tmp_path / "notes.txt"
    target.write_bytes("café laté".encode("utf-16"))
    document = read_text_document(target)
    assert document.text == "café laté"
    assert document.encoding == "utf-16"
    assert document.source_metadata["encoding_detected"] == "utf-16"


def test_saving_puts_the_bom_back_and_keeps_the_encoding(tmp_path: Path) -> None:
    target = tmp_path / "notes.txt"
    target.write_bytes("first".encode("utf-16"))
    document = read_text_document(target)
    document.set_text("second")
    write_text_document(document, target)
    raw = target.read_bytes()
    assert raw[:2] in {LE_BOM, BE_BOM}
    assert read_text_document(target).text == "second"


def test_crlf_in_a_utf16_file_is_still_noticed(tmp_path: Path) -> None:
    target = tmp_path / "crlf.txt"
    target.write_bytes(("one" + chr(13) + chr(10) + "two").encode("utf-16"))
    document = read_text_document(target)
    assert document.line_ending == chr(13) + chr(10)
    assert document.text == "one" + chr(10) + "two"
