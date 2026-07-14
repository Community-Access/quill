"""Tests for the on-demand Pandoc downloader (footprint unbundle)."""

from __future__ import annotations

import hashlib
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
    monkeypatch.setattr(pandoc_install, "app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(pandoc_install, "pandoc_install_supported", lambda: True)
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)

    payload = _pandoc_zip(b"PANDOC-BINARY")
    digest = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(pandoc_install, "PANDOC_DOWNLOAD_SHA256", digest)

    def _fake_download(url, target, progress_fn, timeout):
        assert url.startswith("https://")
        Path(target).write_bytes(payload)

    monkeypatch.setattr(pandoc_install, "_download", _fake_download)
    exe = pandoc_install.install_pandoc()
    assert exe == tmp_path / "tools" / "pandoc" / "pandoc.exe"
    assert exe.read_bytes() == b"PANDOC-BINARY"


def test_digest_mismatch_is_rejected(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pandoc_install, "app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(pandoc_install, "pandoc_install_supported", lambda: True)
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(pandoc_install, "PANDOC_DOWNLOAD_SHA256", "0" * 64)
    monkeypatch.setattr(
        pandoc_install,
        "_download",
        lambda url, target, progress_fn, timeout: Path(target).write_bytes(_pandoc_zip(b"x")),
    )
    with pytest.raises(pandoc_install.PandocInstallError) as excinfo:
        pandoc_install.install_pandoc()
    assert "integrity check" in str(excinfo.value)
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
