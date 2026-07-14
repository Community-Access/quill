"""Tests for the transition-sound conformer + bundled default page-turn cue."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

import pytest

from quill.core.speech.earcon import (
    PcmFormat,
    conform_wav_frames,
    default_sound_path,
)


def _write_wav(path: Path, *, rate: int, channels: int, width: int, samples: list[int]) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        if width == 2:
            frames = b"".join(struct.pack("<h", s) for s in samples)
        elif width == 4:
            frames = b"".join(struct.pack("<i", s) for s in samples)
        else:
            frames = bytes((s + 128) & 0xFF for s in samples)
        w.writeframes(frames)


def _frame_count(frames: bytes, fmt: PcmFormat) -> int:
    return len(frames) // (fmt.sampwidth * fmt.channels)


def test_conform_resamples_to_target_rate(tmp_path: Path) -> None:
    src = tmp_path / "tone.wav"
    _write_wav(src, rate=8000, channels=1, width=2, samples=[1000] * 8000)  # 1.0 s
    out = conform_wav_frames(src, PcmFormat(sample_rate=16000, channels=1, sampwidth=2))
    # Upsampled 8k -> 16k roughly doubles the frame count (~1 s of audio).
    assert _frame_count(out, PcmFormat(16000, 1, 2)) == pytest.approx(16000, abs=2)


def test_conform_mixes_mono_to_stereo_and_changes_width(tmp_path: Path) -> None:
    src = tmp_path / "m.wav"
    _write_wav(src, rate=22050, channels=1, width=2, samples=[5000] * 100)
    fmt = PcmFormat(sample_rate=22050, channels=2, sampwidth=2)
    out = conform_wav_frames(src, fmt)
    assert _frame_count(out, fmt) == 100  # same rate -> same frame count
    # Stereo: the two channels of each frame are identical (mono duplicated).
    first = out[0:2]
    second = out[2:4]
    assert first == second


def test_conform_downmixes_stereo_to_mono(tmp_path: Path) -> None:
    src = tmp_path / "s.wav"
    # L=1000, R=3000 per frame -> mono average 2000.
    interleaved = []
    for _ in range(50):
        interleaved += [1000, 3000]
    _write_wav(src, rate=22050, channels=2, width=2, samples=interleaved)
    out = conform_wav_frames(src, PcmFormat(22050, 1, 2))
    samples = struct.unpack(f"<{len(out) // 2}h", out)
    assert len(samples) == 50
    assert samples[0] == pytest.approx(2000, abs=2)


def test_conform_volume_zero_is_silence(tmp_path: Path) -> None:
    src = tmp_path / "loud.wav"
    _write_wav(src, rate=22050, channels=1, width=2, samples=[20000] * 100)
    out = conform_wav_frames(src, PcmFormat(22050, 1, 2), volume=0.0)
    assert out == b"\x00" * len(out)


def test_conform_rejects_unsupported_width(tmp_path: Path) -> None:
    # 3-byte (24-bit) WAV is unsupported -> ValueError (caller falls back to chime).
    path = tmp_path / "odd.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(3)
        w.setframerate(22050)
        w.writeframes(b"\x00\x00\x00" * 10)
    with pytest.raises(ValueError):
        conform_wav_frames(path, PcmFormat())


def test_default_sound_path_points_at_bundled_page_turn() -> None:
    path = default_sound_path()
    assert path is not None, "the bundled page_turn.wav default should be present"
    assert path.name == "page_turn.wav" and path.is_file()
    with wave.open(str(path), "rb") as w:
        assert w.getnframes() > 0
