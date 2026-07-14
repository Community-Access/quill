"""Tests for the local Tesseract OCR backend (free-first Tier 2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.io.ocr import OcrUnavailableError
from quill.io.tesseract_ocr import (
    _parse_tsv,
    discover_tesseract_executable,
    ocr_image_with_tesseract,
    tesseract_available,
)

_TSV_HEADER = (
    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"
)


def _word(page: int, block: int, par: int, line: int, word: int, conf: float, text: str) -> str:
    return f"5\t{page}\t{block}\t{par}\t{line}\t{word}\t0\t0\t10\t10\t{conf}\t{text}"


def test_parse_tsv_groups_words_into_lines_with_confidence() -> None:
    payload = "\n".join([
        _TSV_HEADER,
        _word(1, 1, 1, 1, 1, 96.0, "Dear"),
        _word(1, 1, 1, 1, 2, 90.0, "reader,"),
        _word(1, 1, 1, 2, 1, 80.0, "hello."),
    ])
    page = _parse_tsv(payload)
    assert [line.text for line in page.lines] == ["Dear reader,", "hello."]
    assert page.lines[0].confidence == pytest.approx(93.0)
    assert page.mean_confidence == pytest.approx((96 + 90 + 80) / 3)
    assert page.text == "Dear reader,\nhello.\n"


def test_parse_tsv_separates_paragraphs_with_blank_line() -> None:
    payload = "\n".join([
        _TSV_HEADER,
        _word(1, 1, 1, 1, 1, 95.0, "Heading"),
        _word(1, 1, 2, 1, 1, 95.0, "Body"),
    ])
    page = _parse_tsv(payload)
    assert page.text == "Heading\n\nBody\n"


def test_parse_tsv_ignores_non_word_rows_and_negative_confidence() -> None:
    payload = "\n".join([
        _TSV_HEADER,
        "1\t1\t0\t0\t0\t0\t0\t0\t100\t100\t-1\t",
        _word(1, 1, 1, 1, 1, -1.0, "ghost"),
        _word(1, 1, 1, 1, 2, 88.0, "word"),
    ])
    page = _parse_tsv(payload)
    assert page.lines[0].text == "ghost word"
    # Only the real confidence participates in the mean.
    assert page.mean_confidence == pytest.approx(88.0)


def test_parse_tsv_empty_payload_yields_empty_result() -> None:
    page = _parse_tsv(_TSV_HEADER)
    assert page.text == ""
    assert page.lines == []
    assert page.mean_confidence == -1.0


def test_discover_prefers_explicit_override(tmp_path: Path) -> None:
    exe = tmp_path / "tesseract.exe"
    exe.write_bytes(b"x")
    assert discover_tesseract_executable(str(exe)) == exe


def test_discover_ignores_missing_override(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.io.tesseract_ocr.managed_tesseract_dir", lambda: tmp_path / "no")
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr("sys.platform", "linux")
    assert discover_tesseract_executable(str(tmp_path / "missing.exe")) is None


def test_discover_finds_managed_install(tmp_path: Path, monkeypatch) -> None:
    managed = tmp_path / "ocr" / "tesseract" / "Tesseract-OCR"
    managed.mkdir(parents=True)
    exe = managed / "tesseract.exe"
    exe.write_bytes(b"x")
    monkeypatch.setattr(
        "quill.io.tesseract_ocr.managed_tesseract_dir", lambda: tmp_path / "ocr" / "tesseract"
    )
    assert discover_tesseract_executable() == exe
    assert tesseract_available()


def test_ocr_image_raises_friendly_error_when_engine_absent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "quill.io.tesseract_ocr.discover_tesseract_executable", lambda override=None: None
    )
    with pytest.raises(OcrUnavailableError) as excinfo:
        ocr_image_with_tesseract(tmp_path / "scan.png")
    assert "not installed" in str(excinfo.value)
