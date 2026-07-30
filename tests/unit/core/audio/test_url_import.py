"""Tests for the audio-converter URL import core (#1255 §4.6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.audio import url_import as ui


@pytest.mark.parametrize(
    "text,expected",
    [
        ("https://youtu.be/abc123", True),
        ("http://example.com/song.mp3", True),
        ("  https://site.org/x  ", True),
        ("example.com/song", False),  # no scheme
        ("C:/music/song.wav", False),  # local path
        ("", False),
        ("https://", False),
    ],
)
def test_looks_like_url(text: str, expected: bool) -> None:
    assert ui.looks_like_url(text) is expected


def test_download_refused_in_safe_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(ui.UrlImportError) as exc:
        ui.download_audio("https://x.com/a", tmp_path, downloader=lambda *a: tmp_path / "n.m4a")
    assert "Safe Mode" in str(exc.value)


def test_download_rejects_non_url(tmp_path: Path) -> None:
    with pytest.raises(ui.UrlImportError) as exc:
        ui.download_audio("not a url", tmp_path, downloader=lambda *a: tmp_path / "n.m4a")
    assert "web address" in str(exc.value)


def test_download_uses_injected_downloader(tmp_path: Path) -> None:
    produced = tmp_path / "song.m4a"
    produced.write_bytes(b"audio")

    def fake(url: str, dest: Path, progress: object) -> Path:
        assert url.startswith("https://")
        assert dest == tmp_path
        return produced

    result = ui.download_audio("https://youtu.be/abc", tmp_path, downloader=fake)
    assert result == produced


def test_download_raises_when_file_missing(tmp_path: Path) -> None:
    with pytest.raises(ui.UrlImportError) as exc:
        ui.download_audio(
            "https://youtu.be/abc", tmp_path, downloader=lambda *a: tmp_path / "gone.m4a"
        )
    assert "no file" in str(exc.value)


def test_download_wraps_downloader_errors(tmp_path: Path) -> None:
    def boom(url: str, dest: Path, progress: object) -> Path:
        raise RuntimeError("network exploded")

    with pytest.raises(ui.UrlImportError) as exc:
        ui.download_audio("https://youtu.be/abc", tmp_path, downloader=boom)
    assert "network exploded" in str(exc.value)


def test_error_is_coded() -> None:
    assert ui.UrlImportError.code == "QUILL-AUDIO-URLIMPORT-DOWNLOAD"


# --------------------------------------------------------------------------- #
# ensure_and_download (install-if-needed + download)
# --------------------------------------------------------------------------- #


def test_ensure_installs_then_downloads_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(ui, "url_import_available", lambda: False)
    produced = tmp_path / "song.m4a"
    produced.write_bytes(b"x")
    calls: list[str] = []

    def installer(progress: object) -> None:
        calls.append("install")

    def downloader(url: str, dest: Path, progress: object) -> Path:
        calls.append("download")
        return produced

    out = ui.ensure_and_download(
        "https://youtu.be/abc", tmp_path, installer=installer, downloader=downloader
    )
    assert out == produced
    assert calls == ["install", "download"]  # install first, then download


def test_ensure_skips_install_when_present(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ui, "url_import_available", lambda: True)
    produced = tmp_path / "song.m4a"
    produced.write_bytes(b"x")

    def installer(progress: object) -> None:
        raise AssertionError("must not install when yt-dlp is already available")

    out = ui.ensure_and_download(
        "https://youtu.be/abc",
        tmp_path,
        installer=installer,
        downloader=lambda *a: produced,
    )
    assert out == produced


def test_ensure_refused_in_safe_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(ui.UrlImportError, match="Safe Mode"):
        ui.ensure_and_download(
            "https://youtu.be/abc",
            tmp_path,
            installer=lambda p: None,
            downloader=lambda *a: tmp_path,
        )


def test_ensure_wraps_install_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ui, "url_import_available", lambda: False)

    def installer(progress: object) -> None:
        raise RuntimeError("pip exploded")

    with pytest.raises(ui.UrlImportError, match="yt-dlp component"):
        ui.ensure_and_download(
            "https://youtu.be/abc", tmp_path, installer=installer, downloader=lambda *a: tmp_path
        )
