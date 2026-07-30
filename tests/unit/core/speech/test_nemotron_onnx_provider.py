"""Tests for the optional Nemotron ONNX (sherpa-onnx) speech provider."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.speech import catalog
from quill.core.speech.provider import SpeechError, TranscriptionRequest
from quill.core.speech.providers import nemotron_onnx as nem

# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #


def _make_model_files(root: Path, *, int8: bool = False, tokens: bool = True) -> None:
    suffix = ".int8.onnx" if int8 else ".onnx"
    for stem in ("encoder", "decoder", "joiner"):
        (root / f"{stem}{suffix}").write_bytes(b"x")
    if tokens:
        (root / "tokens.txt").write_text("a 0\n", encoding="utf-8")


def test_resolve_model_files_flat_layout(tmp_path: Path) -> None:
    _make_model_files(tmp_path)
    files = nem.resolve_model_files(tmp_path)
    assert files is not None
    assert files["encoder"].name == "encoder.onnx"
    assert files["tokens"].name == "tokens.txt"


def test_resolve_model_files_nested_layout(tmp_path: Path) -> None:
    nested = tmp_path / "sherpa-onnx-nemotron"
    nested.mkdir()
    _make_model_files(nested)
    files = nem.resolve_model_files(tmp_path)
    assert files is not None
    assert files["joiner"].parent == nested


def test_resolve_model_files_prefers_int8(tmp_path: Path) -> None:
    _make_model_files(tmp_path)  # full-precision
    _make_model_files(tmp_path, int8=True)  # + int8 twins
    files = nem.resolve_model_files(tmp_path)
    assert files is not None
    assert "int8" in files["encoder"].name


def test_resolve_model_files_incomplete_returns_none(tmp_path: Path) -> None:
    _make_model_files(tmp_path, tokens=False)  # missing tokens.txt
    assert nem.resolve_model_files(tmp_path) is None
    assert nem.resolve_model_files(tmp_path / "missing") is None


def test_result_from_text_single_segment() -> None:
    text, segments = nem.result_from_text("  hello world  ", 2.5)
    assert text == "hello world"
    assert len(segments) == 1
    assert segments[0].start_seconds == 0.0 and segments[0].end_seconds == 2.5
    assert segments[0].speaker == ""


def test_result_from_text_empty_yields_no_segments() -> None:
    text, segments = nem.result_from_text("   ", None)
    assert text == ""
    assert segments == ()


# --------------------------------------------------------------------------- #
# Provider
# --------------------------------------------------------------------------- #


def test_provider_identity_and_offline() -> None:
    p = nem.NemotronOnnxProvider()
    assert p.id == "nemotron"
    assert p.requires_network is False
    assert {m.id for m in p.list_supported_models()} == {"nemotron-streaming-en-0.6b"}


def test_is_available_reflects_sherpa_presence(monkeypatch) -> None:
    import importlib.util

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    assert nem.NemotronOnnxProvider().is_available() is False
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    assert nem.NemotronOnnxProvider().is_available() is True


def test_download_blocked_in_safe_mode(monkeypatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(SpeechError, match="Safe Mode"):
        nem.NemotronOnnxProvider().download_model("nemotron-streaming-en-0.6b")


def test_download_unavailable_when_mirror_not_pinned(monkeypatch) -> None:
    # When no mirror is pinned (mirror_for returns None), the provider must fail
    # clean ("not yet available") rather than fetch an unverifiable artifact --
    # the inert-until-hosted safety property, independent of the real manifest.
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(nem.model_mirrors, "mirror_for", lambda *_a, **_k: None)
    with pytest.raises(SpeechError, match="not yet available"):
        nem.NemotronOnnxProvider().download_model("nemotron-streaming-en-0.6b")


def test_ensure_recognizer_missing_model_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(nem, "_model_dir", lambda model_id: tmp_path / model_id)
    with pytest.raises(SpeechError, match="not installed"):
        nem.NemotronOnnxProvider()._ensure_recognizer("nemotron-streaming-en-0.6b")


def test_transcribe_file_maps_recognizer_output(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"x")
    monkeypatch.setattr(nem, "_recognize", lambda rec, path, progress: ("recognized text", 1.2))
    provider = nem.NemotronOnnxProvider()
    provider._ensure_recognizer = lambda model_id: object()  # type: ignore[method-assign]
    provider._prepare_audio = lambda source, tmp_dir, progress: source  # type: ignore[method-assign]

    result = provider.transcribe_file(
        TranscriptionRequest(source_path=audio, model_id="nemotron-streaming-en-0.6b")
    )
    assert result.full_text == "recognized text"
    assert result.provider_id == "nemotron"
    assert result.language == "en"
    assert result.duration_seconds == 1.2
    assert len(result.segments) == 1


def test_transcribe_file_missing_audio_raises(tmp_path: Path) -> None:
    with pytest.raises(SpeechError, match="not found"):
        nem.NemotronOnnxProvider().transcribe_file(
            TranscriptionRequest(source_path=tmp_path / "nope.wav", model_id="x")
        )


def test_nemotron_catalog_is_english_and_licensed() -> None:
    assert catalog.NEMOTRON_MODELS
    for model in catalog.NEMOTRON_MODELS:
        assert model.language_mode == "english"
        assert model.license_name == "NVIDIA Open Model License"
