"""A picture of a page is read by whichever on-device engine this computer has.

Import / Convert Document sent pictures to Tesseract only, so on a computer
without it -- every QUILL Lite, and QUILL until the download -- a photo of a
letter failed with "Install it from Tools > OCR...", while a scanned PDF already
fell back to Windows OCR. Since 2026-10-17 both take the same route.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.io.docconvert import (
    TIER_LOCAL_OCR,
    TIER_WINDOWS_OCR,
    DocConvertError,
    _Deps,
    convert_document,
)
from quill.io.ocr import OcrResult


def _image(tmp_path: Path) -> Path:
    path = tmp_path / "letter.png"
    path.write_bytes(b"\x89PNG not decoded: the engines are fakes")
    return path


def test_without_tesseract_a_picture_is_read_by_windows_ocr(tmp_path: Path) -> None:
    deps = _Deps(
        tesseract_ready=lambda: False,
        windows_ocr_ready=lambda: True,
        windows_ocr_image=lambda _path, _lang: OcrResult(text="Dear Sam,\n", engine="windows"),
    )
    outcome = convert_document(_image(tmp_path), deps=deps)
    assert outcome.tier == TIER_WINDOWS_OCR
    assert outcome.text == "Dear Sam,\n"
    assert outcome.page_count == 1


def test_tesseract_stays_first_when_it_is_installed(tmp_path: Path) -> None:
    deps = _Deps(
        tesseract_ready=lambda: True,
        ocr_image=lambda _path, _lang: OcrResult(text="Dear Sam,\n", engine="tesseract"),
        windows_ocr_ready=lambda: True,
    )
    assert convert_document(_image(tmp_path), deps=deps).tier == TIER_LOCAL_OCR


def test_with_neither_engine_it_says_so_without_naming_a_menu(tmp_path: Path) -> None:
    deps = _Deps(tesseract_ready=lambda: False, windows_ocr_ready=lambda: False)
    with pytest.raises(DocConvertError, match="No OCR engine is available on this computer"):
        convert_document(_image(tmp_path), deps=deps)
