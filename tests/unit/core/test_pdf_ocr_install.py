"""Tests for the on-demand PDF/Office text-extraction pack installer."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core import pdf_ocr_install as install_module
from quill.core.pdf_ocr_install import (
    PdfOcrInstallError,
    activate_pdf_ocr_pack,
    install_pdf_ocr_support,
    is_pdf_ocr_available,
    missing_pdf_ocr_modules,
    pdf_ocr_install_supported,
    pdf_ocr_pack_dir,
)


@pytest.fixture(autouse=True)
def _isolated_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))


def test_pdf_ocr_pack_dir_is_under_engine_packs(tmp_path: Path) -> None:
    path = pdf_ocr_pack_dir()
    assert path.name == "pdf-ocr"
    assert path.parent.name == "engine-packs"


def test_activate_pdf_ocr_pack_no_pack_is_a_no_op(tmp_path: Path) -> None:
    before = list(sys.path)
    activate_pdf_ocr_pack()
    assert sys.path == before


def test_activate_pdf_ocr_pack_adds_existing_nonempty_pack_to_syspath(tmp_path: Path) -> None:
    pack = pdf_ocr_pack_dir()
    pack.mkdir(parents=True)
    (pack / "marker.txt").write_text("x", encoding="utf-8")
    try:
        activate_pdf_ocr_pack()
        assert str(pack) in sys.path
    finally:
        if str(pack) in sys.path:
            sys.path.remove(str(pack))


def test_activate_pdf_ocr_pack_ignores_empty_pack_dir(tmp_path: Path) -> None:
    pack = pdf_ocr_pack_dir()
    pack.mkdir(parents=True)
    before = list(sys.path)
    activate_pdf_ocr_pack()
    assert sys.path == before


def test_pdf_ocr_install_supported_true_when_pip_present() -> None:
    assert pdf_ocr_install_supported() is True


def test_is_pdf_ocr_available_reflects_missing_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(install_module.importlib.util, "find_spec", lambda name: None)
    assert is_pdf_ocr_available() is False
    assert missing_pdf_ocr_modules() == ("markitdown", "pdfplumber", "pypdf")


def test_is_pdf_ocr_available_true_when_all_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(install_module.importlib.util, "find_spec", lambda name: object())
    assert is_pdf_ocr_available() is True
    assert missing_pdf_ocr_modules() == ()


def test_install_blocked_in_safe_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(PdfOcrInstallError, match="Safe Mode"):
        install_pdf_ocr_support(dest_dir=tmp_path / "dest")


def test_install_raises_when_pip_unsupported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(install_module, "pdf_ocr_install_supported", lambda: False)
    with pytest.raises(PdfOcrInstallError, match="pip is unavailable"):
        install_pdf_ocr_support(dest_dir=tmp_path / "dest")


def test_install_success_runs_pip_and_activates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dest = tmp_path / "dest"
    calls: list[list[str]] = []
    progress_calls: list[tuple[float, str]] = []

    def fake_runner(command, *, timeout_seconds):
        calls.append(list(command))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(install_module, "is_pdf_ocr_available", lambda: True)
    result = install_pdf_ocr_support(
        progress=lambda frac, msg: progress_calls.append((frac, msg)),
        dest_dir=dest,
        python_executable="python",
        runner=fake_runner,
    )
    assert result == dest
    assert len(calls) == 1
    assert "--target" in calls[0]
    assert str(dest) in calls[0]
    assert progress_calls[-1] == (1.0, "Done.")
    assert str(dest) in sys.path
    sys.path.remove(str(dest))


def test_install_failure_raises_with_pip_exit_detail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_runner(command, *, timeout_seconds):
        return SimpleNamespace(returncode=1, stdout="", stderr="disk full")

    with pytest.raises(PdfOcrInstallError, match="pip exit 1"):
        install_pdf_ocr_support(
            dest_dir=tmp_path / "dest", python_executable="python", runner=fake_runner
        )


def test_install_still_missing_after_success_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_runner(command, *, timeout_seconds):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(install_module, "is_pdf_ocr_available", lambda: False)
    monkeypatch.setattr(install_module, "missing_pdf_ocr_modules", lambda: ("pypdf",))
    with pytest.raises(PdfOcrInstallError, match="could not be fully imported"):
        install_pdf_ocr_support(
            dest_dir=tmp_path / "dest", python_executable="python", runner=fake_runner
        )
