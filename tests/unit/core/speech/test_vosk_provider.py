"""Tests for the optional Vosk (Kaldi) speech provider."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from quill.core.speech import catalog
from quill.core.speech.provider import SpeechError, TranscriptionRequest
from quill.core.speech.providers import vosk as vk

# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #


def test_result_from_vosk_builds_text_and_segments() -> None:
    chunks = [
        {
            "text": "hello world",
            "result": [
                {"word": "hello", "start": 0.0, "end": 0.5},
                {"word": "world", "start": 0.5, "end": 1.0},
            ],
        },
        {"text": ""},  # silence chunk - dropped
        {"text": "again", "result": [{"word": "again", "start": 2.0, "end": 2.4}]},
    ]
    text, segments = vk.result_from_vosk(chunks)
    assert text == "hello world again"
    assert len(segments) == 2
    assert segments[0].start_seconds == 0.0 and segments[0].end_seconds == 1.0
    assert segments[1].text == "again"


def test_result_from_vosk_handles_missing_word_timings() -> None:
    text, segments = vk.result_from_vosk([{"text": "no times"}])
    assert text == "no times"
    assert len(segments) == 1
    assert segments[0].start_seconds == 0.0 and segments[0].end_seconds == 0.0


def test_safe_extract_accepts_normal_zip(tmp_path: Path) -> None:
    archive = tmp_path / "ok.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("vosk-model/conf/model.conf", "x")
    dest = tmp_path / "out"
    dest.mkdir()
    with zipfile.ZipFile(archive) as zf:
        vk._safe_extract(zf, dest)
    assert (dest / "vosk-model" / "conf" / "model.conf").is_file()


def test_safe_extract_rejects_zip_slip(tmp_path: Path) -> None:
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.txt", "pwned")
    dest = tmp_path / "out"
    dest.mkdir()
    with zipfile.ZipFile(archive) as zf, pytest.raises(SpeechError, match="unsafe path"):
        vk._safe_extract(zf, dest)


def test_vosk_model_root_finds_nested_model(tmp_path: Path) -> None:
    (tmp_path / "vosk-model-small" / "conf").mkdir(parents=True)
    assert vk._vosk_model_root(tmp_path) == tmp_path / "vosk-model-small"
    # Flattened layout (conf directly under the model dir) also works.
    flat = tmp_path / "flat"
    (flat / "conf").mkdir(parents=True)
    assert vk._vosk_model_root(flat) == flat
    assert vk._vosk_model_root(tmp_path / "missing") is None


# --------------------------------------------------------------------------- #
# Provider
# --------------------------------------------------------------------------- #


def test_provider_identity_and_offline() -> None:
    p = vk.VoskProvider()
    assert p.id == "vosk"
    assert p.requires_network is False
    assert {m.id for m in p.list_supported_models()} == {
        "vosk-model-small-en-us-0.15",
        "vosk-model-en-us-0.22",
    }


def test_is_available_reflects_vosk_presence(monkeypatch) -> None:
    import importlib.util

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert vk.VoskProvider().is_available() is False
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    assert vk.VoskProvider().is_available() is True


def test_download_blocked_in_safe_mode(monkeypatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(SpeechError, match="Safe Mode"):
        vk.VoskProvider().download_model("vosk-model-small-en-us-0.15")


def test_ensure_model_missing_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(vk, "_model_dir", lambda model_id: tmp_path / model_id)
    with pytest.raises(SpeechError, match="not installed"):
        vk.VoskProvider()._ensure_model("vosk-model-small-en-us-0.15")


def test_transcribe_file_maps_recognizer_output(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"x")
    monkeypatch.setattr(
        vk,
        "_recognize",
        lambda model, path, progress: [
            {
                "text": "recognized text",
                "result": [{"word": "recognized", "start": 0.0, "end": 1.1}],
            }
        ],
    )
    provider = vk.VoskProvider()
    provider._ensure_model = lambda model_id: object()  # type: ignore[method-assign]
    provider._prepare_audio = lambda source, tmp_dir, progress: source  # type: ignore[method-assign]

    result = provider.transcribe_file(
        TranscriptionRequest(source_path=audio, model_id="vosk-model-small-en-us-0.15")
    )
    assert result.full_text == "recognized text"
    assert result.provider_id == "vosk"
    assert result.language == "en"
    assert len(result.segments) == 1


def test_vosk_catalog_pins_md5_and_https() -> None:
    assert catalog.VOSK_MODELS
    for model in catalog.VOSK_MODELS:
        assert model.download_url.startswith("https://alphacephei.com/"), model.id
        assert model.md5 and len(model.md5) == 32, f"{model.id} must pin a 32-char MD5"
        assert model.language_mode == "english"
