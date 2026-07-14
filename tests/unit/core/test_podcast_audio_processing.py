"""Tests for podcast download-time audio processing (silence trim, ACX
loudness normalization) -- mocked at the ffmpeg-invocation boundary, no
real ffmpeg needed, matching the existing silence.py/loudness.py test
convention of only unit-testing the pure/wrapper layers directly."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.podcasts.audio_processing import (
    _build_apply_command,
    normalize_downloaded_episode_loudness,
    trim_downloaded_episode_silence,
)


def test_build_apply_command_uses_measured_values_when_present() -> None:
    measured = {
        "input_i": "-20.0",
        "input_tp": "-1.5",
        "input_lra": "7.0",
        "input_thresh": "-30.0",
        "target_offset": "0.5",
    }
    args = _build_apply_command("ffmpeg", Path("in.mp3"), Path("out.mp3"), measured)
    joined = " ".join(args)
    assert "measured_I=-20.0" in joined
    assert "linear=true" in joined
    assert "-c:a" not in args  # never forces pcm_s16le -- would corrupt an mp3/m4a


def test_build_apply_command_falls_back_without_measurement() -> None:
    args = _build_apply_command("ffmpeg", Path("in.mp3"), Path("out.mp3"), None)
    assert "-c:a" not in args


def test_trim_missing_file_returns_false(tmp_path: Path) -> None:
    assert trim_downloaded_episode_silence(tmp_path / "does-not-exist.mp3") is False


def test_trim_success_replaces_file_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "episode.mp3"
    source.write_bytes(b"original bytes")

    def _fake_trim_silence(src: Path, out: Path, **_kwargs: object) -> Path:
        out.write_bytes(b"trimmed bytes")
        return out

    monkeypatch.setattr("quill.core.speech.silence.trim_silence", _fake_trim_silence)
    assert trim_downloaded_episode_silence(source) is True
    assert source.read_bytes() == b"trimmed bytes"


def test_trim_failure_leaves_file_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "episode.mp3"
    source.write_bytes(b"original bytes")

    def _fake_trim_silence(src: Path, out: Path, **_kwargs: object) -> Path:
        raise OSError("ffmpeg exploded")

    monkeypatch.setattr("quill.core.speech.silence.trim_silence", _fake_trim_silence)
    assert trim_downloaded_episode_silence(source) is False
    assert source.read_bytes() == b"original bytes"


def test_normalize_missing_ffmpeg_returns_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "episode.mp3"
    source.write_bytes(b"data")
    monkeypatch.setattr("quill.core.speech.ffmpeg.find_ffmpeg", lambda: None)
    assert normalize_downloaded_episode_loudness(source) is False


def test_normalize_missing_file_returns_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("quill.core.speech.ffmpeg.find_ffmpeg", lambda: "/usr/bin/ffmpeg")
    assert normalize_downloaded_episode_loudness(tmp_path / "missing.mp3") is False
