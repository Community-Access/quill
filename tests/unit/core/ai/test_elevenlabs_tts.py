"""Tests for the ElevenLabs SDK gateway (roadmap §4.1) — no real SDK/network."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from quill.core.ai import elevenlabs_tts
from quill.core.ai.tts import TTSAuthError, TTSCancelledError, TTSError


class _FakeTTS:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def convert(self, *, voice_id: str, text: str, model_id: str, output_format: str) -> bytes:
        self._calls.append(f"{voice_id}:{model_id}:{output_format}")
        return b"ID3" + text.encode("utf-8")


class _FakeVoice:
    def __init__(self, voice_id: str, name: str) -> None:
        self.voice_id = voice_id
        self.name = name


class _FakeVoices:
    def get_all(self) -> object:
        return type("R", (), {"voices": [_FakeVoice("v1", "Aria"), _FakeVoice("v2", "Brian")]})()


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.text_to_speech = _FakeTTS(self.calls)
        self.voices = _FakeVoices()


@pytest.fixture
def fake_client(monkeypatch) -> _FakeClient:
    client = _FakeClient()
    monkeypatch.setattr(elevenlabs_tts, "_client", lambda api_key: client)
    return client


def test_synthesize_wav_requests_pcm_and_wraps_a_valid_wav(fake_client) -> None:
    import io
    import wave

    # Fake "PCM": b"ID3" + text -> b"ID3Hi." (6 bytes, a clean 3 frames of 16-bit mono).
    data = elevenlabs_tts.synthesize_wav("Hi.", "key", voice="v9", model=elevenlabs_tts.TURBO_MODEL)
    assert fake_client.calls == ["v9:eleven_turbo_v2_5:pcm_22050"]  # PCM, not MP3
    assert data[:4] == b"RIFF"  # wrapped in a WAV container, no ffmpeg
    with wave.open(io.BytesIO(data), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 22050
        assert wav.readframes(wav.getnframes()) == b"ID3Hi."


def test_synthesize_wav_blank_key_raises_auth() -> None:
    with pytest.raises(TTSAuthError):
        elevenlabs_tts.synthesize_wav("Hi.", "   ")


def test_estimate_cost_is_per_1000_chars() -> None:
    assert elevenlabs_tts.estimate_cost_usd(2000) == pytest.approx(
        2.0 * elevenlabs_tts.PRICE_PER_1000_CHARS_USD
    )
    assert elevenlabs_tts.estimate_cost_usd(-5) == 0.0


def test_export_writes_mp3_and_passes_voice_model(fake_client, tmp_path: Path) -> None:
    out = elevenlabs_tts.export_audio(
        "Hello there.", tmp_path / "doc.mp3", "key", model="eleven_turbo_v2_5", voice="v9"
    )
    assert out == tmp_path / "doc.mp3"
    assert out.read_bytes().startswith(b"ID3")
    assert fake_client.calls == ["v9:eleven_turbo_v2_5:mp3_44100_128"]


def test_export_forces_mp3_suffix(fake_client, tmp_path: Path) -> None:
    out = elevenlabs_tts.export_audio("Hi.", tmp_path / "doc.wav", "key")
    assert out.suffix == ".mp3"


def test_export_cancel_before_first_chunk_removes_file(fake_client, tmp_path: Path) -> None:
    cancel = threading.Event()
    cancel.set()
    target = tmp_path / "doc.mp3"
    with pytest.raises(TTSCancelledError):
        elevenlabs_tts.export_audio("Hello.", target, "key", cancel_event=cancel)
    assert not target.exists()


def test_export_empty_text_raises(fake_client, tmp_path: Path) -> None:
    with pytest.raises(TTSError, match="No text"):
        elevenlabs_tts.export_audio("   ", tmp_path / "doc.mp3", "key")


def test_blank_key_raises_auth_error() -> None:
    # _client is the real one here (not faked): a blank key fails before any import.
    with pytest.raises(TTSAuthError):
        elevenlabs_tts.export_audio("Hello.", "/tmp/x.mp3", "   ")


def test_list_voices_maps_account_voices(fake_client) -> None:
    assert elevenlabs_tts.list_voices("key") == [("v1", "Aria"), ("v2", "Brian")]


def test_available_reflects_import(monkeypatch) -> None:
    # When the SDK is absent, available() is False (import guarded).
    import builtins

    real_import = builtins.__import__

    def _no_elevenlabs(name, *args, **kwargs):
        if name == "elevenlabs" or name.startswith("elevenlabs."):
            raise ImportError("no elevenlabs")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_elevenlabs)
    assert elevenlabs_tts.available() is False
