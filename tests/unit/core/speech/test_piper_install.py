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
