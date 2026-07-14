from pathlib import Path

import pytest

from quill.core.document import Document
from quill.io.text import read_text_document, write_text_document


def test_read_text_document(tmp_path: Path) -> None:
    target = tmp_path / "example.txt"
    target.write_text("hello\nworld\n", encoding="utf-8")

    document = read_text_document(target)
    assert document.text == "hello\nworld\n"
    assert document.path == target
    assert document.modified is False


def test_write_text_document(tmp_path: Path) -> None:
    target = tmp_path / "save.txt"
    document = Document(text="line1\nline2", line_ending="\r\n")

    write_text_document(document, target)
    assert target.read_text(encoding="utf-8") == "line1\nline2"
    assert document.path == target
    assert document.modified is False


def test_write_text_document_requires_path() -> None:
    document = Document(text="x")
    with pytest.raises(ValueError):
        write_text_document(document)


def test_read_markdown_document_preserves_source_verbatim(tmp_path: Path) -> None:
    target = tmp_path / "notes.md"
    markdown = "# Title\n\n- one\n- two\n\n**bold** and `code`\n"
    target.write_text(markdown, encoding="utf-8")

    document = read_text_document(target)

    # Markdown is edited as plain text, so the reader keeps it byte-for-byte.
    assert document.text == markdown
    assert document.source_metadata["source_kind"] == "text"
    assert document.modified is False


def test_read_html_document_preserves_markup(tmp_path: Path) -> None:
    target = tmp_path / "page.html"
    html = "<html>\n  <body>\n    <p>Hello &amp; welcome</p>\n  </body>\n</html>\n"
    target.write_text(html, encoding="utf-8")

    document = read_text_document(target)

    # HTML opens as plain text; entities and tags are left untouched.
    assert document.text == html
    assert "<p>Hello &amp; welcome</p>" in document.text


def test_markdown_roundtrip_through_writer(tmp_path: Path) -> None:
    source = tmp_path / "in.md"
    source.write_text("# Heading\n\nBody line\n", encoding="utf-8")
    document = read_text_document(source)

    destination = tmp_path / "out.md"
    write_text_document(document, destination)

    assert destination.read_text(encoding="utf-8") == "# Heading\n\nBody line\n"


# --- #648: UTF-8 BOM handling -------------------------------------------------


def test_read_strips_utf8_bom_from_editable_text(tmp_path: Path) -> None:
    target = tmp_path / "bom.txt"
    target.write_bytes(b"\xef\xbb\xbfhello world\n")

    document = read_text_document(target)

    # The BOM must not appear as an editable character at the start (#648).
    assert document.text == "hello world\n"
    assert not document.text.startswith("﻿")
    # It is remembered via the encoding so the save path re-adds it.
    assert document.encoding == "utf-8-sig"


def test_bom_file_round_trips_byte_for_byte(tmp_path: Path) -> None:
    source = tmp_path / "bom.txt"
    original = b"\xef\xbb\xbffirst line\nsecond line\n"
    source.write_bytes(original)

    document = read_text_document(source)
    destination = tmp_path / "out.txt"
    write_text_document(document, destination)

    # Opening a BOM file and saving it preserves the BOM exactly (#648/#649).
    assert destination.read_bytes() == original


def test_read_without_bom_keeps_plain_utf8(tmp_path: Path) -> None:
    target = tmp_path / "plain.txt"
    target.write_bytes(b"no bom here\n")

    document = read_text_document(target)

    assert document.text == "no bom here\n"
    assert document.encoding == "utf-8"


# --- #649: line-ending and blank-line preservation ----------------------------


def test_read_detects_crlf_line_ending(tmp_path: Path) -> None:
    target = tmp_path / "crlf.txt"
    target.write_bytes(b"alpha\r\nbeta\r\n")

    document = read_text_document(target)

    # CRLF must be detected even though the editable text is LF-normalised (#649).
    assert document.line_ending == "\r\n"
    assert document.text == "alpha\nbeta\n"


def test_crlf_file_round_trips_byte_for_byte(tmp_path: Path) -> None:
    source = tmp_path / "crlf.txt"
    original = b"alpha\r\nbeta\r\n\r\n\r\ngamma\r\n"
    source.write_bytes(original)

    document = read_text_document(source)
    destination = tmp_path / "out.txt"
    write_text_document(document, destination)

    # Open-then-save must reproduce the original bytes, including CRLF endings
    # and runs of more than two consecutive blank lines (#649).
    assert destination.read_bytes() == original


# --- #867: non-UTF-8 text must fall back instead of crashing ------------------


def test_read_falls_back_to_cp1252_on_invalid_utf8(tmp_path: Path) -> None:
    target = tmp_path / "windows1252.txt"
    # 0x92 is a right single quote in cp1252 and an invalid UTF-8 start byte,
    # matching issue #867's UnicodeDecodeError.
    target.write_bytes(b"it\x92s a test\n")

    document = read_text_document(target)

    assert document.text == "it’s a test\n"
    assert document.encoding == "cp1252"
    assert document.source_metadata["encoding_detected"] == "cp1252"


def test_read_falls_back_to_latin1_when_not_valid_cp1252(tmp_path: Path) -> None:
    target = tmp_path / "latin1.txt"
    # 0x81 is unassigned in cp1252 but valid in latin-1.
    target.write_bytes(b"bad\x81byte\n")

    document = read_text_document(target)

    assert document.encoding == "latin-1"
    assert document.source_metadata["encoding_detected"] == "latin-1"


def test_read_does_not_fall_back_for_explicit_non_utf8_encoding(tmp_path: Path) -> None:
    target = tmp_path / "explicit.txt"
    target.write_bytes(b"\xff\xfe")

    with pytest.raises(UnicodeDecodeError):
        read_text_document(target, encoding="ascii")
