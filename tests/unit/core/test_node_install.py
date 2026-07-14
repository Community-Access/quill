"""Tests for the optional in-app Node.js runtime download (quill.core.node_install)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

import quill.core.node_install as node_mod
from quill.core.node_install import (
    NodeInstallError,
    _extract_node_from_zip,
    _resolve_zip_url_from_shasums,
    install_node_runtime,
    is_node_available,
    node_executable_path,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_node_zip(include_node_exe: bool = True) -> bytes:
    """Create an in-memory zip that mirrors the official Node.js Windows layout."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("node-v20.0.0-win-x64/node_modules/.placeholder", "")
        if include_node_exe:
            zf.writestr("node-v20.0.0-win-x64/node.exe", b"fake-node-binary")
    return buf.getvalue()


def _fake_shasums(filename: str = "node-v20.0.0-win-x64.zip") -> str:
    return (
        f"aabbcc  {filename}\nddeeff  node-v20.0.0-win-x64.tar.gz\n001122  node-v20.0.0-x64.msi\n"
    )


class _FakeResponse:
    """Minimal file-like object returned by a patched urlopen."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.headers: dict[str, str] = {"Content-Length": str(len(payload))}

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_: object) -> bool:
        return False

    def read(self, n: int = -1) -> bytes:
        if n == -1:
            chunk, self._payload = self._payload, b""
        else:
            chunk, self._payload = self._payload[:n], self._payload[n:]
        return chunk


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_resolve_zip_url_picks_win_x64() -> None:
    url = _resolve_zip_url_from_shasums(_fake_shasums("node-v20.5.1-win-x64.zip"))
    assert url.endswith("node-v20.5.1-win-x64.zip")
    assert url.startswith("https://nodejs.org/dist/latest-v20.x/")


def test_resolve_zip_url_raises_when_not_found() -> None:
    with pytest.raises(NodeInstallError, match="Could not find"):
        _resolve_zip_url_from_shasums("aabbcc  node-v20.0.0-x64.msi\n")


def test_extract_node_from_zip_succeeds(tmp_path: Path) -> None:
    fake_zip = tmp_path / "fake.zip"
    fake_zip.write_bytes(_make_node_zip())
    node_path = _extract_node_from_zip(fake_zip, tmp_path)
    assert node_path == tmp_path / "node.exe"
    assert node_path.read_bytes() == b"fake-node-binary"


def test_extract_node_from_zip_raises_when_exe_missing(tmp_path: Path) -> None:
    fake_zip = tmp_path / "no_node.zip"
    fake_zip.write_bytes(_make_node_zip(include_node_exe=False))
    with pytest.raises(NodeInstallError, match="node.exe was not found"):
        _extract_node_from_zip(fake_zip, tmp_path)


def test_extract_node_from_zip_raises_on_corrupt_archive(tmp_path: Path) -> None:
    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_bytes(b"this is not a zip")
    with pytest.raises(NodeInstallError, match="not a valid zip"):
        _extract_node_from_zip(bad_zip, tmp_path)


# ---------------------------------------------------------------------------
# node_executable_path probe order
# ---------------------------------------------------------------------------


def test_node_executable_path_prefers_managed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    managed = tmp_path / "tools" / "node"
    managed.mkdir(parents=True)
    (managed / "node.exe").write_bytes(b"")
    monkeypatch.setattr(node_mod, "managed_node_dir", lambda: managed)
    monkeypatch.setattr(node_mod.shutil, "which", lambda _: r"C:\Windows\System32\node.exe")

    result = node_executable_path()

    assert result == managed / "node.exe"


def test_node_executable_path_falls_back_to_system(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(node_mod, "managed_node_dir", lambda: tmp_path / "tools" / "node")
    monkeypatch.setattr(node_mod.shutil, "which", lambda _: r"C:\nvm\node.exe")

    result = node_executable_path()

    assert result == Path(r"C:\nvm\node.exe")


def test_node_executable_path_returns_none_when_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(node_mod, "managed_node_dir", lambda: tmp_path / "tools" / "node")
    monkeypatch.setattr(node_mod.shutil, "which", lambda _: None)

    assert node_executable_path() is None


def test_is_node_available_true_when_managed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    managed = tmp_path / "tools" / "node"
    managed.mkdir(parents=True)
    (managed / "node.exe").write_bytes(b"")
    monkeypatch.setattr(node_mod, "managed_node_dir", lambda: managed)
    monkeypatch.setattr(node_mod.shutil, "which", lambda _: None)

    assert is_node_available() is True


def test_is_node_available_false_when_neither(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(node_mod, "managed_node_dir", lambda: tmp_path / "tools" / "node")
    monkeypatch.setattr(node_mod.shutil, "which", lambda _: None)

    assert is_node_available() is False


# ---------------------------------------------------------------------------
# install_node_runtime safety gates
# ---------------------------------------------------------------------------


def test_install_blocked_in_safe_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(NodeInstallError, match="Safe Mode"):
        install_node_runtime(dest_dir=tmp_path)


def test_install_blocked_on_non_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(node_mod.sys, "platform", "linux")
    with pytest.raises(NodeInstallError, match="Windows-only"):
        install_node_runtime(dest_dir=tmp_path)


# ---------------------------------------------------------------------------
# install_node_runtime full flow (two-step: SHASUMS then download)
# ---------------------------------------------------------------------------


def test_install_node_runtime_downloads_and_extracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(node_mod.sys, "platform", "win32")
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)

    shasums_payload = _fake_shasums("node-v20.9.0-win-x64.zip").encode()
    node_zip_payload = _make_node_zip()

    call_count = 0

    def fake_urlopen(request, *, timeout, context):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _FakeResponse(shasums_payload)
        return _FakeResponse(node_zip_payload)

    monkeypatch.setattr(node_mod.urllib.request, "urlopen", fake_urlopen)

    progress_log: list[tuple[float, str]] = []
    node_path = install_node_runtime(
        progress=lambda f, msg: progress_log.append((f, msg)),
        dest_dir=tmp_path,
    )

    assert node_path == tmp_path / "node.exe"
    assert node_path.read_bytes() == b"fake-node-binary"
    assert call_count == 2
    assert progress_log[-1][0] == 1.0
    assert any("Extracting" in msg for _, msg in progress_log)


def test_install_node_runtime_propagates_network_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(node_mod.sys, "platform", "win32")
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(
        node_mod.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("network down")),
    )

    with pytest.raises(NodeInstallError, match="Could not fetch the Node.js release index"):
        install_node_runtime(dest_dir=tmp_path)


def test_install_node_runtime_rejects_http_zip_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_download_node_zip refuses HTTP (non-HTTPS) URLs even if somehow resolved."""
    monkeypatch.setattr(node_mod.sys, "platform", "win32")
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)

    http_shasums = "aabb  node-v20.0.0-win-x64.zip\n"
    http_base_url = "http://insecure.example.com/dist/latest-v20.x"

    monkeypatch.setattr(node_mod, "_SHASUMS_URL", f"{http_base_url}/SHASUMS256.txt")
    monkeypatch.setattr(
        node_mod.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _FakeResponse(http_shasums.encode()),
    )

    with pytest.raises(NodeInstallError, match="secure \\(HTTPS\\)"):
        install_node_runtime(dest_dir=tmp_path)
