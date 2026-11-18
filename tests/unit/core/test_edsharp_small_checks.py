"""Two checks from EdSharp's history (complete.md Part 4): batch files are
saved without a byte-order mark, and Replace takes "$" as typed."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.document import Document
from quill.core.encoding_tools import save_encoding
from quill.core.search import SearchOptions, replace_all
from quill.io.text import write_text_document

BOM = b"\xef\xbb\xbf"


@pytest.mark.parametrize("name", ["run.cmd", "RUN.BAT", "setup.bat"])
def test_a_batch_file_is_saved_without_a_byte_order_mark(tmp_path: Path, name: str) -> None:
    document = Document(text="@echo off\necho hi\n", encoding="utf-8-sig", line_ending="\r\n")
    target = write_text_document(document, tmp_path / name)
    data = target.read_bytes()
    assert not data.startswith(BOM)
    assert data.startswith(b"@echo off\r\n")
    assert document.encoding == "utf-8"


def test_other_files_keep_the_byte_order_mark_they_asked_for(tmp_path: Path) -> None:
    document = Document(text="hello\n", encoding="utf-8-sig")
    target = write_text_document(document, tmp_path / "notes.txt")
    assert target.read_bytes().startswith(BOM)
    assert document.encoding == "utf-8-sig"


def test_save_encoding_only_touches_a_utf8_bom_on_a_batch_file() -> None:
    assert save_encoding(Path("a.cmd"), "utf-8-sig") == "utf-8"
    assert save_encoding("a.bat", "UTF_8_SIG") == "utf-8"
    assert save_encoding(Path("a.cmd"), "cp1252") == "cp1252"
    assert save_encoding(Path("a.ps1"), "utf-8-sig") == "utf-8-sig"


@pytest.mark.parametrize("options", [SearchOptions(), SearchOptions(wildcard=True)])
def test_replace_takes_a_dollar_sign_as_typed_unless_regex_is_on(options: SearchOptions) -> None:
    text, count = replace_all("cost: PRICE", "PRICE", r"$5, $1 and \1", options)
    assert (text, count) == (r"cost: $5, $1 and \1", 1)
