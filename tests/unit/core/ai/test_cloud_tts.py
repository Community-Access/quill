from __future__ import annotations

import io
import json
import wave

import pytest

from quill.core.ai import cloud_tts, gemini_tts
from quill.core.ai.tts import TTSAuthError, TTSError, TTSQuotaError
from quill.core.ai.tts_chunk import chunk_text

# ---------------------------------------------------------------------------
# Boundary-safe chunking (no "weird spots")
# ---------------------------------------------------------------------------


def test_chunk_text_returns_single_chunk_when_short() -> None:
    assert chunk_text("Hello there.", 1000) == ["Hello there."]


def test_chunk_text_splits_on_sentence_boundaries() -> None:
    text = "First sentence here. Second one follows! A third? And a final clause goes on."
    chunks = chunk_text(text, 40)
    assert len(chunks) > 1
    # Every chunk that contains a sentence end should end on one (never mid-word).
    for chunk in chunks:
        assert not chunk.endswith(" ")
        assert chunk == chunk.strip()
    # The join (ignoring the gaps we add only in audio) preserves all words.
    assert " ".join(chunks).split() == text.split()


def test_chunk_text_never_splits_mid_word() -> None:
    # A single over-long sentence falls back to word boundaries only.
    sentence = "alpha bravo charlie delta echo foxtrot golf hotel india juliet"
    chunks = chunk_text(sentence, 20)
    for chunk in chunks:
        for word in chunk.split():
            assert word in sentence.split(), "a word was split across chunks"


def test_chunk_text_normalizes_whitespace() -> None:
    chunks = chunk_text("Hello    world.\n\n   Next   line.", 1000)
    assert chunks == ["Hello world. Next line."]


def test_chunk_text_empty_input() -> None:
    assert chunk_text("   \n\n  ", 10) == []


def test_chunk_text_rejects_nonpositive_limit() -> None:
    with pytest.raises(ValueError):
        chunk_text("x", 0)


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


def test_estimate_cost_openai_per_character() -> None:
    cost = cloud_tts.estimate_cost_usd("openai", "tts-1", 1_000_000)
    assert cost == pytest.approx(15.0)


def test_estimate_cost_gemini_token_based() -> None:
    cost = cloud_tts.estimate_cost_usd("gemini", "gemini-2.5-flash-preview-tts", 4000)
    assert cost is not None and cost > 0


def test_estimate_cost_unknown_returns_none() -> None:
    assert cloud_tts.estimate_cost_usd("openai", "no-such-model", 1000) is None
    assert cloud_tts.estimate_cost_usd("nope", "x", 1000) is None


def test_format_cost() -> None:
    assert cloud_tts.format_cost(None) == "Estimated cost: unavailable"
    assert cloud_tts.format_cost(0.1234) == "Estimated cost: ~$0.1234"


# ---------------------------------------------------------------------------
# Catalog / defaults
# ---------------------------------------------------------------------------


def test_catalog_defaults() -> None:
    assert cloud_tts.PROVIDERS == ("openai", "gemini", "elevenlabs")
    assert cloud_tts.default_voice("gemini") == "Kore"
    assert cloud_tts.default_model("gemini") == gemini_tts.DEFAULT_MODEL
    assert len(cloud_tts.voices_for("gemini")) == 30
    assert cloud_tts.voices_for("nope") == []


def test_elevenlabs_catalog_and_cost() -> None:
    from quill.core.ai import elevenlabs_tts

    assert "elevenlabs" in cloud_tts.PROVIDERS
    assert cloud_tts.provider_label("elevenlabs") == "ElevenLabs"
    assert cloud_tts.default_voice("elevenlabs") == elevenlabs_tts.DEFAULT_VOICE
    assert cloud_tts.default_model("elevenlabs") == elevenlabs_tts.DEFAULT_MODEL
    assert cloud_tts.voices_for("elevenlabs"), "fallback voices should be non-empty"
    # Cost estimate is the conservative per-1000-char figure (approximate, not None).
    cost = cloud_tts.estimate_cost_usd("elevenlabs", elevenlabs_tts.DEFAULT_MODEL, 1000)
    assert cost == pytest.approx(elevenlabs_tts.PRICE_PER_1000_CHARS_USD)


def test_elevenlabs_speak_text_is_export_only() -> None:
    # Live Read Aloud via ElevenLabs is deferred (§4.2); it raises a clear message.
    with pytest.raises(TTSError, match="export"):
        cloud_tts.speak_text("elevenlabs", "hi", "key", model="m", voice="v")


def test_elevenlabs_export_dispatches_to_gateway(monkeypatch, tmp_path) -> None:
    from quill.core.ai import elevenlabs_tts

    seen = {}

    def _fake_export(text, out, api_key, **kwargs):
        seen.update(text=text, out=out, voice=kwargs.get("voice"))
        return out

    monkeypatch.setattr(elevenlabs_tts, "export_audio", _fake_export)
    out = cloud_tts.export_audio(
        "elevenlabs", "hello", tmp_path / "d.mp3", "key", model="m", voice="Rachel"
    )
    assert out == tmp_path / "d.mp3"
    assert seen["text"] == "hello" and seen["voice"] == "Rachel"


# ---------------------------------------------------------------------------
# Gemini REST request
# ---------------------------------------------------------------------------


def _gemini_response(pcm: bytes) -> bytes:
    import base64

    payload = {
        "candidates": [
            {"content": {"parts": [{"inlineData": {"data": base64.b64encode(pcm).decode()}}]}}
        ]
    }
    return json.dumps(payload).encode()


class _FakeResp:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_a) -> bool:
        return False


def test_gemini_request_speech_pcm_shape(monkeypatch) -> None:
    captured: dict = {}

    def fake_urlopen(req, **kwargs):
        captured["url"] = req.full_url
        captured["headers"] = req.headers
        captured["body"] = json.loads(req.data.decode())
        return _FakeResp(_gemini_response(b"\x01\x02\x03\x04"))

    monkeypatch.setattr(gemini_tts, "urlopen", fake_urlopen)
    pcm = gemini_tts.request_speech_pcm("Hi", "KEY123", gemini_tts.DEFAULT_MODEL, "Kore")
    assert pcm == b"\x01\x02\x03\x04"
    assert captured["url"].startswith("https://generativelanguage.googleapis.com")
    # Key travels in the header, never the URL.
    assert "KEY123" not in captured["url"]
    assert captured["headers"]["X-goog-api-key"] == "KEY123"
    vc = captured["body"]["generationConfig"]["speechConfig"]["voiceConfig"]
    assert vc["prebuiltVoiceConfig"]["voiceName"] == "Kore"


def test_gemini_request_maps_http_errors(monkeypatch) -> None:
    from urllib.error import HTTPError

    def make_raiser(code):
        def _raise(req, **kwargs):
            raise HTTPError(req.full_url, code, "err", {}, io.BytesIO(b"{}"))

        return _raise

    monkeypatch.setattr(gemini_tts, "urlopen", make_raiser(401))
    with pytest.raises(TTSAuthError):
        gemini_tts.request_speech_pcm("Hi", "k", gemini_tts.DEFAULT_MODEL, "Kore")

    monkeypatch.setattr(gemini_tts, "urlopen", make_raiser(429))
    with pytest.raises(TTSQuotaError):
        gemini_tts.request_speech_pcm("Hi", "k", gemini_tts.DEFAULT_MODEL, "Kore")

    monkeypatch.setattr(gemini_tts, "urlopen", make_raiser(500))
    with pytest.raises(TTSError):
        gemini_tts.request_speech_pcm("Hi", "k", gemini_tts.DEFAULT_MODEL, "Kore")


def test_gemini_synthesize_wav_has_header_and_tail(monkeypatch) -> None:
    # Two chunks -> we should see an inter-chunk gap plus a final tail of silence.
    monkeypatch.setattr(gemini_tts, "TTS_CHUNK_CHARS", 20)
    monkeypatch.setattr(
        gemini_tts,
        "request_speech_pcm",
        lambda text, key, model, voice: b"\x10\x20" * 100,
    )
    text = "First sentence here is long. Second sentence here is also long."
    wav_bytes = gemini_tts.synthesize_wav_bytes(text, "key")
    handle = wave.open(io.BytesIO(wav_bytes))
    assert handle.getframerate() == 24000
    assert handle.getnchannels() == 1
    assert handle.getsampwidth() == 2
    # Frames = 2 chunks * 100 + 1 inter-gap + 1 final tail of silence.
    expected_min = 200 + int(24000 * 0.18) + int(24000 * 0.35)
    assert handle.getnframes() >= expected_min


# ---------------------------------------------------------------------------
# Provider dispatch
# ---------------------------------------------------------------------------


def test_speak_text_routes_to_provider(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(cloud_tts.openai_tts, "speak_text", lambda *a, **k: calls.append("openai"))
    monkeypatch.setattr(cloud_tts.gemini_tts, "speak_text", lambda *a, **k: calls.append("gemini"))
    cloud_tts.speak_text("openai", "hi", "k", model="tts-1", voice="nova")
    cloud_tts.speak_text("gemini", "hi", "k", model=gemini_tts.DEFAULT_MODEL, voice="Kore")
    assert calls == ["openai", "gemini"]
    with pytest.raises(TTSError):
        cloud_tts.speak_text("bogus", "hi", "k", model="x", voice="y")


def test_export_audio_uses_wav_for_gemini(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        cloud_tts.gemini_tts, "export_to_wav", lambda *a, **k: a[1].write_bytes(b"RIFFxxxx")
    )
    out = cloud_tts.export_audio(
        "gemini", "hi", tmp_path / "doc.mp3", "k", model=gemini_tts.DEFAULT_MODEL, voice="Kore"
    )
    assert out.suffix == ".wav"
