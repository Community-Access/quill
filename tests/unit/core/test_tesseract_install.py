"""Tests for the pinned, verified Tesseract installer acquisition (SEC-6)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from quill.core import tesseract_install
from quill.core.tesseract_install import (
    TESSERACT_DOWNLOAD_SHA256,
    TESSERACT_DOWNLOAD_URL,
    TesseractInstallError,
    download_tesseract_installer,
    launch_tesseract_installer,
)


def test_download_url_is_pinned_https_assets_release() -> None:
    assert TESSERACT_DOWNLOAD_URL.startswith(
        "https://github.com/Community-Access/quill/releases/download/assets-v1/"
    )
    # A real pin, never a placeholder.
    assert len(TESSERACT_DOWNLOAD_SHA256) == 64
    int(TESSERACT_DOWNLOAD_SHA256, 16)


def test_download_blocked_in_safe_mode(monkeypatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(TesseractInstallError) as excinfo:
        download_tesseract_installer()
    assert "Safe Mode" in str(excinfo.value)


def test_download_is_windows_only(monkeypatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(tesseract_install.sys, "platform", "darwin")
    with pytest.raises(TesseractInstallError) as excinfo:
        download_tesseract_installer()
    assert "Homebrew" in str(excinfo.value)


def test_sha_mismatch_discards_the_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(tesseract_install.sys, "platform", "win32")

    def _fake_download(url, target, progress_fn, timeout_seconds):
        Path(target).write_bytes(b"not the real installer")

    monkeypatch.setattr(tesseract_install, "_download", _fake_download)
    with pytest.raises(TesseractInstallError) as excinfo:
        download_tesseract_installer()
    assert "integrity check" in str(excinfo.value)


def test_matching_sha_returns_the_installer_path(monkeypatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(tesseract_install.sys, "platform", "win32")
    payload = b"pretend installer bytes"
    digest = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(tesseract_install, "TESSERACT_DOWNLOAD_SHA256", digest)

    def _fake_download(url, target, progress_fn, timeout_seconds):
        Path(target).write_bytes(payload)

    monkeypatch.setattr(tesseract_install, "_download", _fake_download)
    installer = download_tesseract_installer()
    try:
        assert installer.read_bytes() == payload
    finally:
        installer.unlink(missing_ok=True)


def test_non_https_url_is_refused(tmp_path: Path) -> None:
    with pytest.raises(TesseractInstallError) as excinfo:
        tesseract_install._download("http://example.com/x.exe", tmp_path / "x.exe", None, 5.0)
    assert "HTTPS" in str(excinfo.value)


def test_launch_refuses_missing_installer(tmp_path: Path) -> None:
    with pytest.raises(TesseractInstallError):
        launch_tesseract_installer(tmp_path / "gone.exe")
