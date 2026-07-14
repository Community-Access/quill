from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

from quill.core import dectalk_runtime as dectalk_module
from quill.core.read_aloud import ReadAloudUnavailableError


def _make_fake_zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        # The runtime returns DECtalk.dll (the synthesis engine), not the
        # graphical speak.exe sample.
        zf.writestr("AMD64/DECtalk.dll", "binary")
        zf.writestr("AMD64/speak.exe", "binary")
    return buffer.getvalue()


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._payload


def _patch_urlopen(monkeypatch, payload: bytes) -> None:
    monkeypatch.setattr(
        dectalk_module.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _FakeResponse(payload),
    )


def test_download_dectalk_runtime_rejects_checksum_mismatch(monkeypatch, tmp_path: Path) -> None:
    _patch_urlopen(monkeypatch, b"not the real archive")
    try:
        dectalk_module.download_dectalk_runtime(tmp_path)
    except ReadAloudUnavailableError as exc:
        message = str(exc)
        assert "integrity check" in message
        assert dectalk_module.DECTALK_RELEASE_ZIP_SHA256 in message
    else:
        raise AssertionError("Expected ReadAloudUnavailableError for checksum mismatch")
    # The bad archive must not have been written to disk.
    assert not (tmp_path / "vs2022.zip").exists()


def test_download_dectalk_runtime_accepts_matching_checksum(monkeypatch, tmp_path: Path) -> None:
    payload = _make_fake_zip_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(dectalk_module, "DECTALK_RELEASE_ZIP_SHA256", digest)
    _patch_urlopen(monkeypatch, payload)
    runtime = dectalk_module.download_dectalk_runtime(tmp_path)
    assert runtime.name == "DECtalk.dll"
    assert runtime.exists()
