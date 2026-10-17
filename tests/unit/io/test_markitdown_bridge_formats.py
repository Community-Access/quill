"""The MarkItDown bridge: no wait for a format it cannot read, no raw exceptions.

Measured 2026-10-16 from source: a .doc took 11.6 s on a cold start to reach its
answer, all of it importing MarkItDown -- which has no .doc converter -- before
the open fell through to LibreOffice. And MarkItDown's own exceptions escaped
the callers' fallbacks, so the person heard a library message instead of the
sentence naming what to install.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from quill.io.markitdown_bridge import MARKITDOWN_CANNOT_READ, convert_with_markitdown


@pytest.mark.parametrize("suffix", [".doc", ".DOC", ".ppt"])
def test_formats_markitdown_cannot_read_are_answered_without_importing_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suffix: str
) -> None:
    # Any import of markitdown now fails loudly, so passing proves none happened.
    monkeypatch.setitem(sys.modules, "markitdown", None)
    target = tmp_path / f"old{suffix}"
    target.write_bytes(bytes.fromhex("d0cf11e0a1b11ae1") + b"\0" * 64)
    with pytest.raises(ValueError, match="no converter"):
        convert_with_markitdown(target)
    assert suffix.lower() in MARKITDOWN_CANNOT_READ


def test_markitdowns_own_exceptions_arrive_as_value_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class UnsupportedFormatException(Exception):  # MarkItDown's own family
        pass

    class _MarkItDown:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def convert(self, _path: str) -> object:
            raise UnsupportedFormatException("No converter attempted a conversion")

    fake = types.ModuleType("markitdown")
    fake.MarkItDown = _MarkItDown  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "markitdown", fake)
    target = tmp_path / "odd.docx"
    target.write_bytes(b"PK\x03\x04")
    with pytest.raises(ValueError, match="could not read odd.docx"):
        convert_with_markitdown(target)


def test_a_doc_without_libreoffice_ends_in_the_missing_tool_sentence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End to end through the open reader: the answer, not a raw exception."""
    monkeypatch.setitem(sys.modules, "markitdown", None)
    monkeypatch.setattr("quill.core.external_tools.libreoffice_executable", lambda: None)
    from quill.io.open_read import read_open_document

    target = tmp_path / "old.doc"
    target.write_bytes(bytes.fromhex("d0cf11e0a1b11ae1") + b"\0" * 4088)
    document, _book = read_open_document(target, ".doc")
    assert document.source_metadata.get("source_kind") == "doc"
    assert "LibreOffice" in document.text
