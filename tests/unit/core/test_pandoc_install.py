"""Tests for the on-demand Pandoc downloader (footprint unbundle)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from quill.core import pandoc_install


def test_managed_dir_is_under_app_data(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pandoc_install, "app_data_dir", lambda: tmp_path)
    assert pandoc_install.managed_pandoc_dir() == tmp_path / "tools" / "pandoc"
    assert pandoc_install.managed_pandoc_executable() is None
    exe = tmp_path / "tools" / "pandoc" / "pandoc.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"x")
    assert pandoc_install.managed_pandoc_executable() == exe


def test_safe_mode_blocks_download(monkeypatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(pandoc_install.PandocInstallError) as excinfo:
        pandoc_install.install_pandoc()
    assert "Safe Mode" in str(excinfo.value)


def _pandoc_zip(exe_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # Mirror the official nested layout: pandoc-<ver>/pandoc.exe.
        zf.writestr("pandoc-3.10/pandoc.exe", exe_bytes)
        zf.writestr("pandoc-3.10/COPYRIGHT.txt", b"license")
    return buf.getvalue()


def test_verify_and_extract_pins_the_digest(monkeypatch, tmp_path: Path) -> None:
    from quill.core import release_assets

    monkeypatch.setattr(pandoc_install, "app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(pandoc_install, "pandoc_install_supported", lambda: True)
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)

    payload = _pandoc_zip(b"PANDOC-BINARY")

    def _ok(_urls, dest, **kwargs):
        # The pin is handed to the shared, verified download core.
        assert kwargs.get("sha256") == pandoc_install.PANDOC_DOWNLOAD_SHA256
        Path(dest).write_bytes(payload)
        return Path(dest)

    monkeypatch.setattr(release_assets, "download_verified", _ok)
    exe = pandoc_install.install_pandoc()
    assert exe == tmp_path / "tools" / "pandoc" / "pandoc.exe"
    assert exe.read_bytes() == b"PANDOC-BINARY"


def test_digest_mismatch_is_rejected(monkeypatch, tmp_path: Path) -> None:
    from quill.core import release_assets

    monkeypatch.setattr(pandoc_install, "app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(pandoc_install, "pandoc_install_supported", lambda: True)
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)

    def _boom(_urls, _dest, **_kwargs):
        raise release_assets.ReleaseAssetError("Checksum mismatch for pandoc (...).")

    monkeypatch.setattr(release_assets, "download_verified", _boom)
    with pytest.raises(pandoc_install.PandocInstallError) as excinfo:
        pandoc_install.install_pandoc()
    assert "Checksum mismatch" in str(excinfo.value)
    # Nothing is left installed after a rejected download.
    assert pandoc_install.managed_pandoc_executable() is None


def test_external_tools_finds_the_downloaded_pandoc(monkeypatch, tmp_path: Path) -> None:
    from quill.core import external_tools

    exe = tmp_path / "tools" / "pandoc" / "pandoc.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"x")
    monkeypatch.setattr(pandoc_install, "app_data_dir", lambda: tmp_path)
    # No bundled copy, and force PATH miss so the managed tier is what resolves.
    monkeypatch.setattr(external_tools, "_bundled_tool_path", lambda definition: None)
    monkeypatch.setattr(external_tools, "_tool_version", lambda path: "pandoc 3.10")
    status = external_tools.get_external_tool_status("pandoc")
    assert status.installed is True
    assert status.source == "downloaded"
    assert Path(status.path) == exe.resolve()
