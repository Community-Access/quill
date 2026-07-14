"""Tests for the config-driven cloud transcription REST adapters (#669)."""

from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError

import pytest

from quill.core.quillins.model import TRANSCRIPTION_PROVIDER_KINDS
from quill.core.speech import cloud_transcribers as ct


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _capture_urlopen(monkeypatch, payload: bytes, captured: dict) -> None:
    def fake(request, context=None, timeout=None):  # noqa: ANN001, ANN202, ARG001
        captured["url"] = request.full_url
        captured["headers"] = {k.lower(): v for k, v in request.header_items()}
        captured["body"] = request.data
        return _FakeResponse(payload)

    monkeypatch.setattr(ct, "urlopen", fake)


def test_groq_multipart_call(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"AUDIO")
    captured: dict = {}
    _capture_urlopen(monkeypatch, b'{"text": "hello groq"}', captured)

    text = ct.transcribe_rest(ct.CLOUD_REST_SPECS["groq"], audio, "sk-key", language="en")
    assert text == "hello groq"
    assert captured["url"] == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert captured["headers"]["authorization"] == "Bearer sk-key"
    body = captured["body"]
    assert b"whisper-large-v3-turbo" in body  # model field
    assert b'name="language"' in body and b"en" in body
    assert b'filename="a.mp3"' in body and b"AUDIO" in body


def test_elevenlabs_uses_key_header_and_diarize(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    captured: dict = {}
    _capture_urlopen(monkeypatch, b'{"text": "hi", "language_code": "en"}', captured)

    text = ct.transcribe_rest(ct.CLOUD_REST_SPECS["elevenlabs"], audio, "el-key", diarize=True)
    assert text == "hi"
    assert captured["headers"]["xi-api-key"] == "el-key"
    assert "authorization" not in captured["headers"]
    body = captured["body"]
    assert b"scribe_v1" in body
    assert b'name="diarize"' in body and b"true" in body


def test_raw_body_mode_puts_language_and_diarize_in_query(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RAWAUDIO")
    spec = ct.RestSpec(
        host="example.com",
        endpoint="https://example.com/listen",
        key_header="Authorization",
        key_scheme="Token ",
        body_mode="raw",
        query=(("model", "nova"),),
        language_field="language",
        diarize_field="diarize",
        text_path=("results", "channels", 0, "alternatives", 0, "transcript"),
    )
    captured: dict = {}
    _capture_urlopen(
        monkeypatch,
        b'{"results": {"channels": [{"alternatives": [{"transcript": "raw text"}]}]}}',
        captured,
    )
    text = ct.transcribe_rest(spec, audio, "tok", language="es", diarize=True)
    assert text == "raw text"
    assert captured["body"] == b"RAWAUDIO"  # audio sent as the raw body
    assert "model=nova" in captured["url"]
    assert "language=es" in captured["url"]
    assert "diarize=true" in captured["url"]
    assert captured["headers"]["authorization"] == "Token tok"


def test_https_is_enforced(tmp_path: Path) -> None:
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    spec = ct.RestSpec(host="h", endpoint="http://insecure/", key_header="Authorization")
    with pytest.raises(ct.CloudTranscribeError, match="secure"):
        ct.transcribe_rest(spec, audio, "k")


def test_401_becomes_auth_error(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")

    def fake(request, context=None, timeout=None):  # noqa: ANN001, ANN202, ARG001
        raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(ct, "urlopen", fake)
    with pytest.raises(ct.CloudTranscribeError, match="Authentication failed"):
        ct.transcribe_rest(ct.CLOUD_REST_SPECS["groq"], audio, "bad")


def test_dig_returns_empty_for_missing_path() -> None:
    assert ct._dig({"a": {"b": "x"}}, ("a", "b")) == "x"
    assert ct._dig({"a": []}, ("a", 0)) == ""
    assert ct._dig({}, ("missing",)) == ""


def test_every_rest_spec_kind_is_a_known_provider_kind() -> None:
    # The validator's allowlist must include every host-vetted REST kind.
    for kind in ct.CLOUD_REST_SPECS:
        assert kind in TRANSCRIPTION_PROVIDER_KINDS
        spec = ct.CLOUD_REST_SPECS[kind]
        assert spec.endpoint.startswith("https://")
        assert spec.host in spec.endpoint
