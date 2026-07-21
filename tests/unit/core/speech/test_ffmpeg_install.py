from __future__ import annotations

import io
import zipfile

import pytest

from quill.core.speech import ffmpeg_install as fi


def _build_zip(names: list[str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name in names:
            zf.writestr(name, b"BINARY")
    return buf.getvalue()


def test_extract_flattens_ffmpeg_and_ffprobe(tmp_path) -> None:
    zip_path = tmp_path / "ffmpeg.zip"
    zip_path.write_bytes(
        _build_zip([
            "ffmpeg-8.1-essentials_build/bin/ffmpeg.exe",
            "ffmpeg-8.1-essentials_build/bin/ffprobe.exe",
            "ffmpeg-8.1-essentials_build/doc/readme.txt",
        ])
    )
    dest = tmp_path / "out"
    dest.mkdir()
    result = fi._extract_ffmpeg_from_zip(zip_path, dest)
    assert result == dest / "ffmpeg.exe"
    assert (dest / "ffmpeg.exe").is_file()
    assert (dest / "ffprobe.exe").is_file()


def test_extract_raises_when_ffmpeg_missing(tmp_path) -> None:
    zip_path = tmp_path / "x.zip"
    zip_path.write_bytes(_build_zip(["build/bin/ffprobe.exe", "build/doc/readme.txt"]))
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(fi.FFmpegInstallError, match="ffmpeg.exe was not found"):
        fi._extract_ffmpeg_from_zip(zip_path, dest)


def test_extract_rejects_bad_zip(tmp_path) -> None:
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not a zip")
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(fi.FFmpegInstallError, match="not a valid zip"):
        fi._extract_ffmpeg_from_zip(bad, dest)


def test_install_blocked_in_safe_mode(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(fi.FFmpegInstallError, match="Safe Mode"):
        fi.install_ffmpeg(dest_dir=tmp_path)


def test_install_rejects_unsupported_platform(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(fi, "ffmpeg_install_supported", lambda: False)
    with pytest.raises(fi.FFmpegInstallError, match="Windows-only"):
        fi.install_ffmpeg(dest_dir=tmp_path)


def test_download_source_is_the_pinned_assets_v1_mirror() -> None:
    """ffmpeg is now mirrored on assets-v1 and pinned: the source is that URL + SHA."""
    url, sha = fi.ffmpeg_download_source()
    assert url == fi._ASSETS_V1_BASE + fi.FFMPEG_PINNED_FILENAME
    assert url.startswith("https://github.com/Community-Access/quill/releases/download/assets-v1/")
    assert sha == fi.FFMPEG_PINNED_SHA256
    assert fi._is_real_sha256(sha)


def test_download_source_activates_pinned_mirror_when_sha_is_real(monkeypatch) -> None:
    """Filling FFMPEG_PINNED_FILENAME + a real SHA flips to the assets-v1 mirror."""
    real_sha = "a" * 64
    monkeypatch.setattr(fi, "FFMPEG_PINNED_FILENAME", "ffmpeg-7.1-essentials_build.zip")
    monkeypatch.setattr(fi, "FFMPEG_PINNED_SHA256", real_sha)
    url, sha = fi.ffmpeg_download_source()
    assert url == fi._ASSETS_V1_BASE + "ffmpeg-7.1-essentials_build.zip"
    assert url.startswith("https://github.com/Community-Access/quill/releases/download/assets-v1/")
    assert sha == real_sha


def test_download_source_ignores_placeholder_sha(monkeypatch) -> None:
    """A blank or short (placeholder) SHA does not activate the mirror."""
    monkeypatch.setattr(fi, "FFMPEG_PINNED_FILENAME", "ffmpeg-7.1-essentials_build.zip")
    monkeypatch.setattr(fi, "FFMPEG_PINNED_SHA256", "PENDING")
    url, sha = fi.ffmpeg_download_source()
    assert url == fi.FFMPEG_DOWNLOAD_URL
    assert sha == ""


def test_install_surfaces_shared_core_download_error(monkeypatch, tmp_path) -> None:
    """A shared-core download failure (HTTPS refusal, network, mismatch) surfaces
    as an FFmpegInstallError. HTTPS enforcement itself lives in release_assets."""
    from quill.core import release_assets

    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(fi, "ffmpeg_install_supported", lambda: True)

    def _boom(_urls, _dest, **_kwargs):
        raise release_assets.ReleaseAssetError("Refusing a non-HTTPS download URL.")

    monkeypatch.setattr(release_assets, "download_verified", _boom)
    with pytest.raises(fi.FFmpegInstallError, match="non-HTTPS"):
        fi.install_ffmpeg(dest_dir=tmp_path)
