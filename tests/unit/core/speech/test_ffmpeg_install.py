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


def test_download_zip_refuses_non_https(tmp_path) -> None:
    with pytest.raises(fi.FFmpegInstallError, match="secure"):
        fi._download_zip("http://example.com/x.zip", tmp_path / "x.zip", None, 5.0)
