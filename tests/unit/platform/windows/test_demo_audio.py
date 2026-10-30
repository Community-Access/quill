"""Demonstration sound sources: timelines without holes and the same device only."""

from __future__ import annotations

import wave

import pytest

from quill.platform.windows import demo_audio
from quill.platform.windows.demo_audio import (
    Microphone,
    WavStream,
    level_from_wav,
    resolve_microphone,
)

RATE = 48_000


def _frames(path):
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes()


def test_gap_between_packets_is_filled_with_silence(tmp_path):
    stream = WavStream(tmp_path / "a.wav", start_hint=100.0)
    tone = (1000).to_bytes(2, "little", signed=True) * 2 * 480  # 10 ms stereo
    stream.write(tone, 100.0)
    stream.write(tone, 100.51)  # half a second later: Windows sent nothing meanwhile
    stream.finish(101.0)
    frames = _frames(tmp_path / "a.wav")
    assert frames == pytest.approx(RATE * 1.0, abs=RATE * 0.02)
    level = stream.level("Tone")
    assert not level.digital_silence and level.present


def test_nothing_arriving_is_a_full_segment_of_silence(tmp_path):
    stream = WavStream(tmp_path / "b.wav", start_hint=10.0)
    stream.finish(12.0)
    assert _frames(tmp_path / "b.wav") == RATE * 2
    assert stream.first_time == 10.0
    assert level_from_wav(tmp_path / "b.wav", "Quiet").digital_silence


def test_muted_source_writes_zeros_but_keeps_time(tmp_path):
    stream = WavStream(tmp_path / "c.wav")
    stream.muted = True
    stream.write(b"\x10\x00" * 2 * 480, 5.0)
    stream.finish(5.01)
    assert level_from_wav(tmp_path / "c.wav", "Mic").digital_silence
    assert _frames(tmp_path / "c.wav") == 480


def test_header_is_true_before_close_so_a_crash_leaves_a_readable_file(tmp_path):
    stream = WavStream(tmp_path / "d.wav")
    stream.write(b"\x01\x00" * 2 * 4800, 1.0)
    with wave.open(str(tmp_path / "d.wav"), "rb") as handle:  # read while still open
        assert handle.getnframes() == 4800
    stream.finish()


def test_microphone_resolves_only_the_same_device(monkeypatch):
    mics = [
        Microphone(1, "Headset Microphone (Logitech USB Headset H390)", "Windows WASAPI", 1),
        Microphone(2, "Headset Microphone (Logitech USB Headset H340)", "Windows WASAPI", 1),
        Microphone(3, "Microphone Array (Realtek High Definition Audio)", "Windows WASAPI", 2),
    ]
    monkeypatch.setattr(demo_audio, "list_microphones", lambda: mics)
    assert resolve_microphone("Microphone Array (Realtek High Definition Audio)").index == 3
    # A 31-character MME name shared by two headsets matches neither.
    assert resolve_microphone("Headset Microphone (Logitech US") is None
    assert resolve_microphone("Microphone Array (Realtek High").index == 3
    assert resolve_microphone("USB Camera Microphone") is None
