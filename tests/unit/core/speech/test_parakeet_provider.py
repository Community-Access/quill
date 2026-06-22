"""Tests for the optional Parakeet (NVIDIA NeMo) speech provider."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.speech import catalog
from quill.core.speech.provider import SpeechError, TranscriptionRequest
from quill.core.speech.providers import parakeet as pk

# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #


def test_pick_device_falls_back_to_cpu_without_torch(monkeypatch) -> None:
    # No torch importable -> cpu (the import inside pick_device raises ImportError).
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "torch":
            raise ImportError("no torch")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert pk.pick_device() == "cpu"


def test_coerce_hypotheses_handles_list_and_tuple_and_single() -> None:
    assert pk._coerce_hypotheses(["a", "b"]) == ["a", "b"]
    assert pk._coerce_hypotheses((["best"], ["all"])) == ["best"]
    assert pk._coerce_hypotheses("solo") == ["solo"]


def test_result_from_parakeet_plain_string() -> None:
    text, segments = pk.result_from_parakeet("  hello world  ")
    assert text == "hello world"
    assert segments == ()


class _FakeHypothesis:
    def __init__(self, text, timestamp=None):
        self.text = text
        self.timestamp = timestamp


def test_result_from_parakeet_with_segments() -> None:
    hyp = _FakeHypothesis(
        "hello world",
        timestamp={
            "segment": [
                {"segment": "hello", "start": 0.0, "end": 1.0},
                {"segment": "world", "start": 1.0, "end": 2.0},
            ]
        },
    )
    text, segments = pk.result_from_parakeet(hyp)
    assert text == "hello world"
    assert [s.text for s in segments] == ["hello", "world"]
    assert segments[1].start_seconds == 1.0 and segments[1].end_seconds == 2.0


def test_result_from_parakeet_text_only_no_timestamps() -> None:
    text, segments = pk.result_from_parakeet(_FakeHypothesis("just text"))
    assert text == "just text"
    assert segments == ()


def test_result_from_parakeet_derives_text_from_segments_when_text_missing() -> None:
    hyp = _FakeHypothesis(
        "", timestamp={"segment": [{"text": "a", "start_offset": 0, "end_offset": 1}]}
    )
    text, segments = pk.result_from_parakeet(hyp)
    assert text == "a"
    assert len(segments) == 1


# --------------------------------------------------------------------------- #
# Provider
# --------------------------------------------------------------------------- #


def test_provider_identity_and_offline() -> None:
    p = pk.ParakeetProvider()
    assert p.id == "parakeet"
    assert p.requires_network is False
    assert {m.id for m in p.list_supported_models()} == {
        "parakeet-tdt-0.6b-v2",
        "parakeet-tdt-1.1b",
    }


def test_is_available_reflects_nemo_presence(monkeypatch) -> None:
    import importlib.util

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert pk.ParakeetProvider().is_available() is False
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    assert pk.ParakeetProvider().is_available() is True


def test_estimate_model_size_uses_catalog() -> None:
    est = pk.ParakeetProvider().estimate_model_size("parakeet-tdt-0.6b-v2")
    assert (
        est.download_mb == catalog.parakeet_model_by_id("parakeet-tdt-0.6b-v2").approximate_size_mb
    )


def test_download_blocked_in_safe_mode(monkeypatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(SpeechError, match="Safe Mode"):
        pk.ParakeetProvider().download_model("parakeet-tdt-0.6b-v2")


def test_ensure_model_missing_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pk, "_model_dir", lambda model_id: tmp_path / model_id)
    with pytest.raises(SpeechError, match="not installed"):
        pk.ParakeetProvider()._ensure_model("parakeet-tdt-0.6b-v2")


def test_transcribe_file_maps_engine_output(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"x")

    class _FakeModel:
        def transcribe(self, paths, timestamps=False):  # noqa: ARG002
            return [
                _FakeHypothesis(
                    "transcribed",
                    timestamp={"segment": [{"segment": "transcribed", "start": 0.0, "end": 1.2}]},
                )
            ]

    provider = pk.ParakeetProvider()
    # Avoid the real NeMo load and ffmpeg transcode.
    provider._ensure_model = lambda model_id: _FakeModel()  # type: ignore[method-assign]
    provider._prepare_audio = lambda source, tmp_dir, progress: source  # type: ignore[method-assign]

    result = provider.transcribe_file(
        TranscriptionRequest(source_path=audio, model_id="parakeet-tdt-0.6b-v2")
    )
    assert result.full_text == "transcribed"
    assert result.provider_id == "parakeet"
    assert result.language == "en"
    assert len(result.segments) == 1


def test_transcribe_warns_on_non_english_and_diarize(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"x")

    class _FakeModel:
        def transcribe(self, paths, timestamps=False):  # noqa: ARG002
            return ["ok"]

    provider = pk.ParakeetProvider()
    provider._ensure_model = lambda model_id: _FakeModel()  # type: ignore[method-assign]
    provider._prepare_audio = lambda source, tmp_dir, progress: source  # type: ignore[method-assign]

    result = provider.transcribe_file(
        TranscriptionRequest(
            source_path=audio, model_id="parakeet-tdt-0.6b-v2", language="es", diarize=True
        )
    )
    assert any("English only" in w for w in result.warnings)
    assert any("speaker" in w.lower() for w in result.warnings)


def test_parakeet_catalog_pins_revisions_and_repos() -> None:
    # Supply-chain hardening parity with the other engines: every Parakeet model
    # must pin a Hub repo and a commit revision.
    assert catalog.PARAKEET_MODELS
    for model in catalog.PARAKEET_MODELS:
        assert model.download_url.startswith("nvidia/parakeet"), model.id
        assert model.revision, f"{model.id} must pin a commit revision"
        assert model.language_mode == "english"
