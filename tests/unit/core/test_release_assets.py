from __future__ import annotations

import hashlib
import io
import zipfile

import pytest

from quill.core import release_assets as ra


def test_is_pinned_accepts_real_rejects_placeholder_and_moving_ref() -> None:
    assert ra.is_pinned(ra.ASSETS["whispercpp"]) is True
    # Placeholder SHA -> not pinned.
    assert ra.is_pinned(ra.ReleaseAsset("x", "assets-v1", "f.zip", "<REPLACE>")) is False
    # Non-hex / wrong length -> not pinned.
    assert ra.is_pinned(ra.ReleaseAsset("x", "assets-v1", "f.zip", "zz")) is False
    # Moving ref in the URL -> not pinned even with a real-looking SHA.
    assert ra.is_pinned(ra.ReleaseAsset("x", "latest", "f.zip", "a" * 64)) is False


def test_safe_mode_blocks_fetch(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(ra.ReleaseAssetError, match="Safe Mode"):
        ra.fetch_component("whispercpp", tmp_path / "d")


def test_unknown_component_raises(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    with pytest.raises(ra.ReleaseAssetError, match="Unknown component"):
        ra.fetch_component("does-not-exist", tmp_path / "d")


def test_unpinned_asset_refused(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setitem(
        ra.ASSETS, "ph", ra.ReleaseAsset("ph", "assets-v1", "p.zip", "<PLACEHOLDER>")
    )
    with pytest.raises(ra.ReleaseAssetError, match="unpinned"):
        ra.fetch_component("ph", tmp_path / "d")


def test_checksum_mismatch_raises(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setitem(ra.ASSETS, "t", ra.ReleaseAsset("t", "assets-v1", "t.zip", "0" * 64))
    monkeypatch.setattr(
        ra,
        "_download_resumable",
        lambda url, dest, progress, **k: dest.write_bytes(b"not-the-bytes"),
    )
    with pytest.raises(ra.ReleaseAssetError, match="[Cc]hecksum mismatch"):
        ra.fetch_component("t", tmp_path / "d")


def test_should_cancel_raises_download_cancelled_without_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    # should_cancel is checked at the top of the download (before any network),
    # and a cancel is never retried -- it surfaces immediately as DownloadCancelled.
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    with pytest.raises(ra.DownloadCancelled):
        ra.fetch_component("whispercpp", tmp_path / "d", should_cancel=lambda: True)


def test_kokoro_asset_is_pinned() -> None:
    assert ra.is_pinned(ra.ASSETS["kokoro"]) is True
    assert ra.ASSETS["kokoro"].expect_member == "kokoro-v1.0.int8.onnx"


def test_vosk_asset_is_pinned_wheel_on_assets_v1() -> None:
    """Vosk is self-hosted: a pinned .whl on assets-v1, byte-identical to the PyPI wheel."""
    asset = ra.ASSETS["vosk"]
    assert asset.tag == "assets-v1"
    assert asset.filename.endswith("win_amd64.whl")
    assert ra.is_pinned(asset) is True
    assert asset.url.endswith("/assets-v1/vosk-0.3.45-py3-none-win_amd64.whl")


def test_fetch_file_verifies_and_returns_raw_file_without_unpacking(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    payload = b"PK-fake-wheel-bytes"
    import hashlib

    sha = hashlib.sha256(payload).hexdigest()
    monkeypatch.setitem(
        ra.ASSETS, "wheelish", ra.ReleaseAsset("wheelish", "assets-v1", "x.whl", sha)
    )
    monkeypatch.setattr(
        ra, "_download_resumable", lambda url, dest, progress, **k: dest.write_bytes(payload)
    )
    out = ra.fetch_file("wheelish", tmp_path / "dl")
    assert out == tmp_path / "dl" / "x.whl"
    assert out.read_bytes() == payload  # returned as-is, not extracted


def test_fetch_file_rejects_checksum_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setitem(ra.ASSETS, "w", ra.ReleaseAsset("w", "assets-v1", "w.whl", "0" * 64))
    monkeypatch.setattr(
        ra, "_download_resumable", lambda url, dest, progress, **k: dest.write_bytes(b"nope")
    )
    with pytest.raises(ra.ReleaseAssetError, match="[Cc]hecksum mismatch"):
        ra.fetch_file("w", tmp_path / "dl")


def test_fetch_file_refuses_unpinned(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setitem(
        ra.ASSETS, "ph", ra.ReleaseAsset("ph", "assets-v1", "p.whl", "<PLACEHOLDER>")
    )
    with pytest.raises(ra.ReleaseAssetError, match="unpinned|placeholder"):
        ra.fetch_file("ph", tmp_path / "dl")


def test_fetch_verifies_then_unpacks_expected_member(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Release/whisper-cli.exe", b"exe")
        zf.writestr("Release/whisper.dll", b"dll")
    data = buf.getvalue()
    sha = hashlib.sha256(data).hexdigest()
    monkeypatch.setitem(
        ra.ASSETS,
        "t",
        ra.ReleaseAsset("t", "assets-v1", "t.zip", sha, expect_member="whisper-cli.exe"),
    )
    monkeypatch.setattr(
        ra, "_download_resumable", lambda url, dest, progress, **k: dest.write_bytes(data)
    )

    dest = tmp_path / "speech-engine"
    out = ra.fetch_component("t", dest)
    assert (out / "whisper-cli.exe").is_file()  # the engine binary lands flat in the target
    assert (out / "whisper.dll").is_file()  # alongside its deps


def test_libmpv_asset_is_pinned_pack_on_assets_v1() -> None:
    """libmpv is self-hosted: a pinned zip carrying the DLL + GPL texts + source offer."""
    asset = ra.ASSETS["libmpv"]
    assert asset.tag == "assets-v1"
    assert asset.expect_member == "libmpv-2.dll"
    assert ra.is_pinned(asset) is True
    assert asset.url.endswith("/assets-v1/libmpv-pack.zip")
    assert "GPL" in asset.license and "source offer" in asset.license


def test_mathcat_asset_is_pinned_pack_on_assets_v1() -> None:
    """MathCAT is self-hosted: a pinned zip carrying the DLL plus its Rules data."""
    asset = ra.ASSETS["mathcat"]
    assert asset.tag == "assets-v1"
    assert asset.expect_member == "libmathcat_c.dll"
    assert ra.is_pinned(asset) is True
    assert asset.url.endswith("/assets-v1/mathcat-pack.zip")
    assert "MIT" in asset.license
