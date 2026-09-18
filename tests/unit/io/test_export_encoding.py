"""Save As Plain Text and Save As HTML stop rewriting the file (bad.md F4, P0.7).

Two defects in one helper. ``_write_utf8`` opened the target and wrote straight
into it, so an interrupted Save As left a truncated file where the document had
been -- alone among QUILL's writers, every other one of which goes through
``write_text_atomic``. And it hard-coded UTF-8 and then assigned
``document.encoding = "utf-8"``, so a file read as cp1252, Shift-JIS or UTF-16
was silently re-encoded and the document forgot it had ever been anything else.

The HTML writer made the second half worse by stamping ``<meta charset="utf-8">``
into every page: the file and its own declaration agreed with each other and
disagreed with the document they came from.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.document import Document
from quill.io import text as io_text
from quill.io.export import markdown_to_html, write_html_document, write_plain_text_document


def test_plain_text_keeps_the_encoding_the_file_was_read_in(tmp_path: Path) -> None:
    document = Document(text="café", encoding="cp1252", line_ending="\r\n")
    target = write_plain_text_document(document, tmp_path / "note.txt")

    assert target.read_bytes() == "café".encode("cp1252")
    assert document.encoding == "cp1252"


def test_plain_text_keeps_the_documents_line_endings(tmp_path: Path) -> None:
    document = Document(text="one\ntwo", encoding="utf-8", line_ending="\r\n")
    target = write_plain_text_document(document, tmp_path / "note.txt")

    assert target.read_bytes() == b"one\r\ntwo"


def test_html_declares_the_charset_it_was_actually_written_in(tmp_path: Path) -> None:
    document = Document(text="hello", encoding="utf-16", line_ending="\n")
    target = write_html_document(document, tmp_path / "page.html")

    rendered = target.read_text(encoding="utf-16")
    assert '<meta charset="utf-16">' in rendered
    assert document.encoding == "utf-16"


def test_the_charset_is_escaped_into_the_meta_tag() -> None:
    assert '<meta charset="utf-8">' in markdown_to_html("hi", "t")
    assert '<meta charset="shift_jis">' in markdown_to_html("hi", "t", charset="shift_jis")


def test_text_the_encoding_cannot_hold_widens_to_utf8_and_says_so(tmp_path: Path) -> None:
    """Better than refusing at the last step, and it must not be silent."""
    warnings: list[str] = []
    io_text.set_save_warning_hook(warnings.append)
    try:
        document = Document(text="em — dash", encoding="ascii")
        target = write_plain_text_document(document, tmp_path / "note.txt")
    finally:
        io_text.set_save_warning_hook(None)

    assert document.encoding == "utf-8"
    assert "em — dash" in target.read_text(encoding="utf-8")
    assert warnings and "ascii" in warnings[0]


def test_an_unknown_encoding_widens_rather_than_raising(tmp_path: Path) -> None:
    document = Document(text="hello", encoding="not-a-codec")
    target = write_plain_text_document(document, tmp_path / "note.txt")

    assert target.read_text(encoding="utf-8") == "hello"
    assert document.encoding == "utf-8"


def test_the_export_leaves_no_temp_file_behind(tmp_path: Path) -> None:
    """The atomic writer's temp file is in the target's own directory."""
    document = Document(text="hello", encoding="utf-8")
    write_plain_text_document(document, tmp_path / "note.txt")

    assert sorted(p.name for p in tmp_path.iterdir()) == ["note.txt"]
