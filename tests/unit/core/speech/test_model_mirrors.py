"""Tests for the optional assets-v1 speech-model mirrors (HF-removal prep)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from quill.core import release_assets
from quill.core.release_assets import ReleaseAssetError
from quill.core.speech import catalog, model_mirrors
from quill.core.speech.model_mirrors import MirrorAsset
from quill.core.speech.providers import fasterwhisper as fw
from quill.core.speech.providers import whispercpp

# --------------------------------------------------------------------------- #
# Manifest resolution
# --------------------------------------------------------------------------- #


def test_whispercpp_everyday_models_are_mirrored() -> None:
    # The everyday whisper.cpp models are hosted on assets-v1 now.
    for model_id in ("tiny", "base", "small", "small.en-tdrz", "medium"):
        assert model_mirrors.mirror_for("whispercpp", model_id) is not None
    # large-v3 (~3.1 GB) exceeds GitHub's 2 GiB/file limit, so it is not mirrored.
    assert model_mirrors.mirror_for("whispercpp", "large-v3") is None


def test_faster_whisper_models_that_fit_are_mirrored() -> None:
    for model_id in ("tiny", "base", "small", "medium", "distil-large-v3"):
        asset = model_mirrors.mirror_for("fasterwhisper", model_id)
        assert asset is not None
        assert asset.archive_member == "model.bin"  # zip integrity guard
    # large-v3 (~3 GB fp16) exceeds the 2 GiB release-asset limit -> not mirrored.
    assert model_mirrors.mirror_for("fasterwhisper", "large-v3") is None


def test_mirrored_whisper_sha_matches_the_catalog_pin() -> None:
    # The mirror is a re-publish of the same GGML file, so its pin must equal the
    # catalog's -- a guard against the two drifting apart.
    for model_id in ("tiny", "base", "small", "small.en-tdrz", "medium"):
        info = catalog.model_by_id(model_id)
        mirror = model_mirrors.mirror_for("whispercpp", model_id)
        assert info is not None and mirror is not None
        assert mirror.sha256.lower() == (info.sha256 or "").lower()


def test_mirror_for_ignores_placeholder_sha(monkeypatch) -> None:
    monkeypatch.setitem(
        model_mirrors._MIRRORS, "whispercpp:x", MirrorAsset("ggml-x.bin", "PENDING")
    )
    assert model_mirrors.mirror_for("whispercpp", "x") is None


def test_mirror_for_returns_a_validly_pinned_entry(monkeypatch) -> None:
    asset = MirrorAsset("ggml-x.bin", "a" * 64)
    monkeypatch.setitem(model_mirrors._MIRRORS, "whispercpp:x", asset)
    assert model_mirrors.mirror_for("whispercpp", "x") is asset


def test_mirror_url_points_at_assets_v1() -> None:
    url = model_mirrors.mirror_url(MirrorAsset("ggml-tiny.bin", "a" * 64))
    assert url == (
        "https://github.com/Community-Access/quill/releases/download/assets-v1/ggml-tiny.bin"
    )


# --------------------------------------------------------------------------- #
# Fetch helpers
# --------------------------------------------------------------------------- #


def test_fetch_mirror_file_hands_url_and_sha_to_the_shared_core(monkeypatch, tmp_path) -> None:
    asset = MirrorAsset("ggml-x.bin", "b" * 64)
    seen: dict[str, object] = {}

    def _dv(url, dest, **kwargs):
        seen["url"] = url
        seen["sha256"] = kwargs.get("sha256")
        Path(dest).write_bytes(b"model-bytes")
        return Path(dest)

    monkeypatch.setattr(release_assets, "download_verified", _dv)
    out = model_mirrors.fetch_mirror_file(asset, tmp_path / "m.bin")
    assert out.read_bytes() == b"model-bytes"
    assert seen["url"].endswith("/assets-v1/ggml-x.bin")
    assert seen["sha256"] == "b" * 64


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_fetch_mirror_archive_verifies_then_unpacks(monkeypatch, tmp_path) -> None:
    payload = _zip_bytes(
        {
            "faster-whisper-small/model.bin": b"weights",
            "faster-whisper-small/config.json": b"{}",
        }
    )
    asset = MirrorAsset("fw-small.zip", "c" * 64, archive_member="model.bin")

    def _dv(_url, dest, **_kwargs):
        Path(dest).write_bytes(payload)
        return Path(dest)

    monkeypatch.setattr(release_assets, "download_verified", _dv)
    target = tmp_path / "out"
    model_mirrors.fetch_mirror_archive(asset, target)
    assert (target / "model.bin").read_bytes() == b"weights"
    assert (target / "config.json").exists()


def test_fetch_mirror_archive_rejects_a_zip_missing_the_member(monkeypatch, tmp_path) -> None:
    payload = _zip_bytes({"x/other.txt": b"nope"})
    asset = MirrorAsset("fw.zip", "d" * 64, archive_member="model.bin")

    def _dv(_url, dest, **_kwargs):
        Path(dest).write_bytes(payload)
        return Path(dest)

    monkeypatch.setattr(release_assets, "download_verified", _dv)
    with pytest.raises(ReleaseAssetError):
        model_mirrors.fetch_mirror_archive(asset, tmp_path / "out")


# --------------------------------------------------------------------------- #
# Provider preference: mirror first, Hugging Face as the fallback
# --------------------------------------------------------------------------- #


def test_whispercpp_downloads_from_the_mirror(monkeypatch, tmp_path) -> None:
    info = catalog.model_by_id("small")
    assert info is not None
    monkeypatch.setattr(
        model_mirrors, "mirror_for", lambda _p, _m: MirrorAsset("ggml-small.bin", info.sha256)
    )
    used = {"mirror": False}

    def _fetch(_asset, dest, **_kwargs):
        used["mirror"] = True
        Path(dest).write_bytes(b"ggml")
        return Path(dest)

    monkeypatch.setattr(model_mirrors, "fetch_mirror_file", _fetch)
    target = tmp_path / "ggml-small.bin"
    whispercpp._download_to_file(info, target, None)
    assert used["mirror"] is True
    assert target.read_bytes() == b"ggml"


def test_whispercpp_no_hugging_face_fallback_on_mirror_failure(monkeypatch, tmp_path) -> None:
    # HF is gone: a mirror failure surfaces a coded error, it does not reach HF.
    info = catalog.model_by_id("small")
    assert info is not None
    monkeypatch.setattr(
        model_mirrors, "mirror_for", lambda _p, _m: MirrorAsset("ggml-small.bin", info.sha256)
    )

    def _boom(_asset, _dest, **_kwargs):
        raise ReleaseAssetError("mirror not reachable")

    monkeypatch.setattr(model_mirrors, "fetch_mirror_file", _boom)
    with pytest.raises(whispercpp.WhisperModelDownloadNetworkError):
        whispercpp._download_to_file(info, tmp_path / "ggml-small.bin", None)


def test_fasterwhisper_downloads_from_the_mirror(monkeypatch, tmp_path) -> None:
    info = catalog.fw_model_by_id("small")
    assert info is not None
    monkeypatch.setattr(
        model_mirrors,
        "mirror_for",
        lambda _p, _m: MirrorAsset("fw-small.zip", "e" * 64, archive_member="model.bin"),
    )
    used = {"mirror": False}

    def _fetch(_asset, target, **_kwargs):
        used["mirror"] = True
        return target

    monkeypatch.setattr(model_mirrors, "fetch_mirror_archive", _fetch)
    fw._download_repo("Systran/faster-whisper-small", tmp_path / "out", info, None)
    assert used["mirror"] is True


def test_fasterwhisper_unmirrored_model_gives_manual_message(monkeypatch, tmp_path) -> None:
    from quill.core.speech.provider import SpeechError

    info = catalog.fw_model_by_id("large-v3")
    assert info is not None
    monkeypatch.setattr(model_mirrors, "mirror_for", lambda _p, _m: None)
    with pytest.raises(SpeechError, match="too large"):
        fw._download_repo("Systran/faster-whisper-large-v3", tmp_path / "out", info, None)
