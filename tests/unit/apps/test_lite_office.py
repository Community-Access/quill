"""QUILL Lite opens Word, Excel and PowerPoint files as text (2026-10-16).

It used to decode a .docx's zip bytes as Latin-1 and show them. The reading
is QUILL's (``quill.io.office_text``, tested in tests/unit/io/
test_office_corpus.py); what is tested here is QUILL Lite's half: it reads the
same formats QUILL's File > Open reads and no others, it reads them with
nothing QUILL Lite's build leaves out, an unreadable file is a sentence, and
the file is never written back.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from quill.apps.lite_window_pdf import is_read_only_source
from quill.core.lite.filetypes import OPEN_WILDCARD
from quill.core.lite.open_prepare import (
    OFFICE_OPEN_SUFFIXES,
    PLAIN,
    prepare,
    prepare_in_background,
)

CORPUS = Path(__file__).resolve().parents[2] / "corpus" / "office"


def _as_built(monkeypatch: pytest.MonkeyPatch) -> None:
    """QUILL Lite's spec excludes all of these; the readers must not need them."""
    for name in ("markitdown", "magika", "onnxruntime", "docx", "pptx", "openpyxl", "lxml"):
        monkeypatch.setitem(sys.modules, name, None)


def test_lite_reads_only_what_quill_file_open_reads() -> None:
    from quill.io.open_read import OFFICE_STREAM_SUFFIXES

    # Rule: QUILL Lite may never be ahead of QUILL.
    assert OFFICE_OPEN_SUFFIXES <= OFFICE_STREAM_SUFFIXES


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("report.docx", "## Highlights\n\n- North grew fastest"),
        ("budget.xlsx", "## Sheet: Budget"),
        ("deck.pptx", "# Slide 2: Figures"),
        ("minutes.odt", "# Minutes"),
    ],
)
def test_office_files_open_as_text_with_nothing_lite_leaves_out(
    monkeypatch: pytest.MonkeyPatch, name: str, expected: str
) -> None:
    _as_built(monkeypatch)
    prepared = prepare(CORPUS / name, PLAIN)
    assert prepared.mode == PLAIN
    assert expected in prepared.text
    assert "PK" not in prepared.text[:4]  # not the zip's bytes, as it used to be


def test_office_files_open_on_the_worker() -> None:
    assert prepare_in_background(CORPUS / "report.docx")


def test_unreadable_files_are_a_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    _as_built(monkeypatch)
    monkeypatch.setattr("quill.core.external_tools.libreoffice_executable", lambda: None)
    with pytest.raises(OSError) as legacy:
        prepare(CORPUS / "legacy.doc", PLAIN)
    assert '"Word Document (.docx)"' in str(legacy.value)
    with pytest.raises(OSError) as locked:
        prepare(CORPUS / "locked.docx", PLAIN)
    assert "password-protected" in str(locked.value)


def test_office_files_are_never_written_back() -> None:
    for suffix in OFFICE_OPEN_SUFFIXES:
        assert is_read_only_source(f"report{suffix}"), suffix
    assert not is_read_only_source("report.txt")
    assert not is_read_only_source("report.rtf")


def test_the_open_dialog_offers_them() -> None:
    assert "*.docx" in OPEN_WILDCARD.split("|")[1]
    assert "Word, Excel and PowerPoint, opened as text" in OPEN_WILDCARD
