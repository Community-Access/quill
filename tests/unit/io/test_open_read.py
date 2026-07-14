from __future__ import annotations

from pathlib import Path

from quill.io.open_read import (
    BRF_SUFFIXES,
    LIGHT_STRUCTURED_SUFFIXES,
    OFFICE_STREAM_SUFFIXES,
    read_open_document,
)


def test_read_open_document_reads_plain_text(tmp_path: Path) -> None:
    target = tmp_path / "note.txt"
    target.write_text("hello world\n", encoding="utf-8")

    loaded, epub_book = read_open_document(target, ".txt")

    assert "hello world" in loaded.text
    assert epub_book is None


def test_read_open_document_tags_csv_grid_metadata(tmp_path: Path) -> None:
    target = tmp_path / "data.csv"
    target.write_text("a,b\n1,2\n", encoding="utf-8")

    loaded, epub_book = read_open_document(target, ".csv", csv_mode="grid")

    assert loaded.source_metadata["csv_open_mode"] == "grid"
    assert loaded.source_metadata["engine"] == "csv grid"
    assert epub_book is None


def test_read_open_document_tags_csv_text_metadata(tmp_path: Path) -> None:
    target = tmp_path / "data.csv"
    target.write_text("a,b\n1,2\n", encoding="utf-8")

    loaded, _ = read_open_document(target, ".csv", csv_mode="text")

    assert loaded.source_metadata["csv_open_mode"] == "text"
    assert loaded.source_metadata["engine"] == "csv text"


def test_read_open_document_applies_word_open_mode(tmp_path: Path, monkeypatch) -> None:
    from quill.core.document import Document

    target = tmp_path / "sample.docx"
    target.write_bytes(b"PK\x03\x04")

    def _fake_read(path: Path, *, docx_engine: str = "auto") -> Document:
        return Document(text="word body\n", path=path, source_metadata={})

    monkeypatch.setattr("quill.io.structured.read_structured_document", _fake_read)

    loaded, epub_book = read_open_document(target, ".docx", word_mode="structured")

    assert loaded.source_metadata["word_open_mode"] == "structured"
    assert epub_book is None


def test_read_open_document_returns_epub_book(tmp_path: Path) -> None:
    import zipfile

    target = tmp_path / "sample.epub"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("OEBPS/chapter1.xhtml", "<html><body><p>Hi EPUB</p></body></html>")

    loaded, epub_book = read_open_document(target, ".epub")

    assert "Hi EPUB" in loaded.text
    # An EPUB book object is parsed and handed back for the UI thread to install.
    assert epub_book is not None


def test_office_and_light_suffix_sets_are_disjoint() -> None:
    assert OFFICE_STREAM_SUFFIXES.isdisjoint(LIGHT_STRUCTURED_SUFFIXES)
    assert ".docx" in OFFICE_STREAM_SUFFIXES
    assert ".pptx" in OFFICE_STREAM_SUFFIXES
    assert ".pdf" in OFFICE_STREAM_SUFFIXES


def test_brf_suffix_set_lists_braille_family() -> None:
    """BR-004: the four-suffix BRF family is registered."""
    assert BRF_SUFFIXES == frozenset({".brf", ".brl", ".pef", ".ueb"})
    # None of the BRF suffixes may collide with the other route sets.
    assert BRF_SUFFIXES.isdisjoint(OFFICE_STREAM_SUFFIXES)
    assert BRF_SUFFIXES.isdisjoint(LIGHT_STRUCTURED_SUFFIXES)


def test_read_open_document_reads_brf_byte_identical(tmp_path: Path) -> None:
    """BR-004: a BRF with form feeds, CRLF, and trailing spaces reads unchanged."""
    target = tmp_path / "note.brf"
    payload = b",,,\r\nPAGE 1\r\n\x0c,,,PAGE 2   \r\n\x0c"
    target.write_bytes(payload)

    loaded, epub_book = read_open_document(target, ".brf")

    assert epub_book is None
    # Byte-identical: the path uses read_bytes under the hood, so every
    # form feed, CR, LF, and trailing space must round-trip.
    assert loaded.text.encode("utf-8") == payload
    assert loaded.text.count("\x0c") == 2
    assert loaded.text.endswith("   \r\n\x0c")
    assert loaded.encoding == "ascii"
    assert loaded.line_ending == "\r\n"
    # Source metadata is the BRF kind, not the generic text kind.
    assert loaded.source_metadata["source_kind"] == "brf"
    assert loaded.source_metadata["brf_suffix"] == "brf"
    assert loaded.source_metadata["brf_had_bom"] is False
    assert loaded.source_metadata["brf_non_ascii_count"] == 0


def test_read_open_document_strips_brf_utf8_bom(tmp_path: Path) -> None:
    """BR-004 + BR-005: a UTF-8 BOM at the start of a .brl is stripped on read."""
    target = tmp_path / "note.brl"
    payload = b"\xef\xbb\xbf,,, HELLO\r\n"
    target.write_bytes(payload)

    loaded, _ = read_open_document(target, ".brl")

    assert loaded.text == ",,, HELLO\r\n"
    assert loaded.source_metadata["brf_had_bom"] is True
    assert loaded.source_metadata["source_kind"] == "brf"
    assert loaded.source_metadata["brf_suffix"] == "brl"


def test_read_open_document_warns_on_non_brf_ascii(tmp_path: Path) -> None:
    """BR-004 + BR-005: a Unicode braille codepoint (U+2800) is flagged but preserved."""
    target = tmp_path / "note.brf"
    target.write_bytes(",,,\u2800\r\n".encode("utf-8"))

    loaded, _ = read_open_document(target, ".brf")

    assert "\u2800" in loaded.text  # bytes are preserved; no transform
    offsets = loaded.source_metadata["brf_non_ascii_offsets"]
    assert offsets == [3]  # the Unicode braille sits at char offset 3
    assert loaded.source_metadata["brf_non_ascii_count"] == 1


def test_read_open_document_uses_corpus_fixture_byte_identical() -> None:
    """BR-004 + BR-012: the corpus fixture round-trips byte-for-byte on read."""
    from pathlib import Path as _P

    fixture = _P("tests/corpus/braille/one_crazy_night.brf")
    raw = fixture.read_bytes()

    loaded, _ = read_open_document(fixture, ".brf")

    assert loaded.text.encode("utf-8") == raw
    assert loaded.source_metadata["brf_had_bom"] is False
    assert loaded.source_metadata["brf_non_ascii_count"] == 0
    # 69 form-feed page breaks in the corpus fixture.
    assert loaded.text.count("\x0c") == 69
    assert loaded.line_ending == "\r\n"
