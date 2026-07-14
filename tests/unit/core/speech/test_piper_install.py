"""Tests for the on-demand Piper engine download integrity check."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from quill.core.speech import piper_install as pi


def test_verify_sha256_passes_on_match(tmp_path: Path) -> None:
    blob = tmp_path / "piper.zip"
    blob.write_bytes(b"pretend piper archive")
    expected = hashlib.sha256(b"pretend piper archive").hexdigest()
    # Must not raise.
    pi._verify_sha256(blob, expected)


def test_verify_sha256_is_case_insensitive(tmp_path: Path) -> None:
    blob = tmp_path / "piper.zip"
    blob.write_bytes(b"data")
    expected = hashlib.sha256(b"data").hexdigest().upper()
    pi._verify_sha256(blob, expected)


def test_verify_sha256_rejects_a_mismatch(tmp_path: Path) -> None:
    blob = tmp_path / "piper.zip"
    blob.write_bytes(b"corrupted or substituted download")
    with pytest.raises(pi.PiperInstallError, match="integrity check"):
        pi._verify_sha256(blob, "0" * 64)


def test_pinned_sha256_is_a_full_length_hex_digest() -> None:
    # A truncated or malformed pin would reject every real download.
    assert len(pi.PIPER_DOWNLOAD_SHA256) == 64
    int(pi.PIPER_DOWNLOAD_SHA256, 16)  # raises ValueError if not hex


def test_maybe_fetch_hosted_piper_is_dormant_without_a_pinned_asset(tmp_path, monkeypatch) -> None:
    """With no pinned 'piper' asset published, the hosted fetch is skipped
    entirely (returns None) so install_piper falls back to the upstream URL --
    no wasted request until the zip is uploaded."""
    from quill.core import release_assets

    monkeypatch.setattr(release_assets, "ASSETS", {}, raising=True)
    assert pi._maybe_fetch_hosted_piper(tmp_path, None) is None


# --------------------------------------------------------------------------- #
# Offline Edition bundle (speech-models-bundled/piper)
# --------------------------------------------------------------------------- #


def _make_bundle(tmp_path: Path, monkeypatch, *, with_zip: bool = True) -> Path:
    app_root = tmp_path / "app"
    bundle = app_root / "speech-models-bundled" / "piper"
    (bundle / "voices").mkdir(parents=True)
    if with_zip:
        import io
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("piper/piper.exe", b"fake exe")
            zf.writestr("piper/espeak-ng-data/en.dict", b"dict")
        (bundle / "piper_windows_amd64.zip").write_bytes(buffer.getvalue())
    monkeypatch.setenv("QUILL_APP_ROOT", str(app_root))
    return bundle


def test_bundled_dir_is_none_without_app_root(monkeypatch) -> None:
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    assert pi.bundled_piper_offline_dir() is None
    assert pi.bundled_piper_voice_paths("en_US-lessac-medium") is None
    assert pi.list_bundled_piper_voices() == []
    assert pi.install_bundled_piper_voice("en_US-lessac-medium") is None


def test_install_piper_prefers_the_offline_bundle(tmp_path: Path, monkeypatch) -> None:
    """A staged, SHA-verified engine zip installs with zero network access."""
    bundle = _make_bundle(tmp_path, monkeypatch)
    real_sha = hashlib.sha256((bundle / "piper_windows_amd64.zip").read_bytes()).hexdigest()
    monkeypatch.setattr(pi, "PIPER_DOWNLOAD_SHA256", real_sha)
    monkeypatch.setattr(pi, "piper_install_supported", lambda: True)
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)

    def _no_network(*_args, **_kwargs):  # pragma: no cover - must never run
        raise AssertionError("offline install must not touch the network")

    monkeypatch.setattr(pi, "_download_zip", _no_network)
    monkeypatch.setattr(pi, "_maybe_fetch_hosted_piper", _no_network)
    dest = tmp_path / "managed"
    exe = pi.install_piper(dest_dir=dest)
    assert exe == dest / "piper.exe"
    assert exe.read_bytes() == b"fake exe"
    assert (dest / "espeak-ng-data" / "en.dict").is_file()


def test_offline_bundle_still_fails_closed_on_a_bad_hash(tmp_path: Path, monkeypatch) -> None:
    # A tampered staged zip is rejected by the same pinned-hash gate as online.
    _make_bundle(tmp_path, monkeypatch)
    monkeypatch.setattr(pi, "piper_install_supported", lambda: True)
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    with pytest.raises(pi.PiperInstallError, match="integrity check"):
        pi.install_piper(dest_dir=tmp_path / "managed")


def test_bundled_voices_list_and_install(tmp_path: Path, monkeypatch) -> None:
    bundle = _make_bundle(tmp_path, monkeypatch, with_zip=False)
    (bundle / "voices" / "en_US-lessac-medium.onnx").write_bytes(b"onnx")
    (bundle / "voices" / "en_US-lessac-medium.onnx.json").write_text("{}")
    # A voice missing its .onnx.json metadata is not offered.
    (bundle / "voices" / "en_GB-alan-medium.onnx").write_bytes(b"onnx")

    assert pi.list_bundled_piper_voices() == ["en_US-lessac-medium"]
    assert pi.bundled_piper_voice_paths("en_GB-alan-medium") is None

    dest = tmp_path / "piper-models"
    installed = pi.install_bundled_piper_voice("en_US-lessac-medium", dest_dir=dest)
    assert installed == dest / "en_US-lessac-medium.onnx"
    assert (dest / "en_US-lessac-medium.onnx").read_bytes() == b"onnx"
    assert (dest / "en_US-lessac-medium.onnx.json").is_file()
    # An un-bundled voice reports None so the caller falls back to download.
    assert pi.install_bundled_piper_voice("en_GB-alan-medium", dest_dir=dest) is None


def test_maybe_fetch_hosted_piper_uses_a_pinned_asset(tmp_path, monkeypatch) -> None:
    from quill.core import release_assets

    monkeypatch.setitem(
        release_assets.ASSETS,
        "piper",
        release_assets.ReleaseAsset(
            component="piper",
            tag="assets-v1",
            filename="piper_windows_amd64.zip",
            sha256=pi.PIPER_DOWNLOAD_SHA256,
        ),
    )
    calls: dict = {}

    def fake_fetch_file(component, dest_dir, **kwargs):
        calls["component"] = component
        return dest_dir / "piper_windows_amd64.zip"

    monkeypatch.setattr(release_assets, "fetch_file", fake_fetch_file)
    result = pi._maybe_fetch_hosted_piper(tmp_path, None)
    assert result == tmp_path / "piper_windows_amd64.zip"
    assert calls["component"] == "piper"


def test_maybe_fetch_hosted_piper_falls_back_when_hosted_fetch_fails(tmp_path, monkeypatch) -> None:
    from quill.core import release_assets

    monkeypatch.setitem(
        release_assets.ASSETS,
        "piper",
        release_assets.ReleaseAsset(
            component="piper",
            tag="assets-v1",
            filename="piper_windows_amd64.zip",
            sha256=pi.PIPER_DOWNLOAD_SHA256,
        ),
    )

    def boom(*_a, **_k):
        raise RuntimeError("hosted asset unavailable")

    monkeypatch.setattr(release_assets, "fetch_file", boom)
    assert pi._maybe_fetch_hosted_piper(tmp_path, None) is None
