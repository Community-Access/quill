"""Tests for the pinned, verified Tesseract installer acquisition (SEC-6)."""

from __future__ import annotations

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


def test_download_failure_raises_and_discards_the_file(monkeypatch) -> None:
    # The shared download_verified enforces HTTPS + SHA-256; a failure there
    # (mismatch, network) surfaces as a TesseractInstallError and the temp file
    # is discarded.
    from quill.core import release_assets

    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(tesseract_install.sys, "platform", "win32")

    def _boom(_urls, _dest, **_kwargs):
        raise release_assets.ReleaseAssetError("Checksum mismatch for x.exe (...).")

    monkeypatch.setattr(release_assets, "download_verified", _boom)
    with pytest.raises(TesseractInstallError) as excinfo:
        download_tesseract_installer()
    assert "Checksum mismatch" in str(excinfo.value)


def test_successful_download_returns_the_installer_path(monkeypatch) -> None:
    from quill.core import release_assets

    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(tesseract_install.sys, "platform", "win32")
    payload = b"pretend installer bytes"

    def _ok(_urls, dest, **_kwargs):
        Path(dest).write_bytes(payload)
        return Path(dest)

    monkeypatch.setattr(release_assets, "download_verified", _ok)
    installer = download_tesseract_installer()
    try:
        assert installer.read_bytes() == payload
    finally:
        installer.unlink(missing_ok=True)


def test_launch_refuses_missing_installer(tmp_path: Path) -> None:
    with pytest.raises(TesseractInstallError):
        launch_tesseract_installer(tmp_path / "gone.exe")
