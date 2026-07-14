from __future__ import annotations

import wave
from pathlib import Path

from quill.core.speech import capture


def test_write_wav_pcm16_is_valid(tmp_path: Path) -> None:
    frames = b"\x01\x00\x02\x00\x03\x00\x04\x00"  # 4 int16 samples
    target = tmp_path / "rec.wav"
    capture.write_wav_pcm16(target, frames)
    with wave.open(str(target), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 16_000
        assert wav.getnframes() == 4
        assert wav.readframes(4) == frames


def test_capture_available_returns_bool() -> None:
    # Whatever the environment, this must not raise and must be a bool.
    assert isinstance(capture.capture_available(), bool)


def test_mic_recorder_starts_unrecording() -> None:
    assert capture.MicRecorder().is_recording is False


def test_mic_recorder_pause_resume_toggles_flag() -> None:
    # pause()/resume() drive Locked Dictation pause without needing a live stream.
    recorder = capture.MicRecorder()
    assert recorder.is_paused is False
    recorder.pause()
    assert recorder.is_paused is True
    recorder.resume()
    assert recorder.is_paused is False


def test_list_input_devices_returns_list() -> None:
    # Must not raise whether or not sounddevice is installed.
    assert isinstance(capture.list_input_devices(), list)
