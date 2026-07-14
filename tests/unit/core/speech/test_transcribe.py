"""Tests for the offline file-transcription helper (WATCH-9)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.speech.provider import (
    InstalledSpeechModel,
    SpeechError,
    TranscriptionRequest,
    TranscriptionResult,
)
from quill.core.speech.registry import SpeechProviderRegistry
from quill.core.speech.transcribe import (
    has_installed_offline_model,
    transcribe_audio_file,
)


class _FakeProvider:
    """Minimal SpeechToTextProvider stand-in for routing tests."""

    def __init__(
        self,
        provider_id: str,
        *,
        available: bool = True,
        installed: list[str] | None = None,
    ) -> None:
        self.id = provider_id
        self.display_name = provider_id
        self.description = ""
        self._available = available
        self._installed = installed or []
        self.last_request: TranscriptionRequest | None = None

    def is_available(self) -> bool:
        return self._available

    def list_installed_models(self) -> list[InstalledSpeechModel]:
        return [
            InstalledSpeechModel(
                id=mid,
                display_name=mid,
                path=Path(f"/models/{mid}"),
                size_mb=100,
                provider_id=self.id,
            )
            for mid in self._installed
        ]

    def transcribe_file(self, request: TranscriptionRequest, progress=None) -> TranscriptionResult:
        self.last_request = request
        return TranscriptionResult(
            full_text=f"transcript via {self.id}/{request.model_id}",
            provider_id=self.id,
            model_id=request.model_id,
        )


def _registry(*providers: _FakeProvider) -> SpeechProviderRegistry:
    registry = SpeechProviderRegistry()
    for provider in providers:
        registry.register(provider)
    return registry


def test_transcribe_uses_first_available_provider_with_a_model(tmp_path: Path) -> None:
    no_model = _FakeProvider("empty", installed=[])
    good = _FakeProvider("whispercpp", installed=["base", "small"])
    registry = _registry(no_model, good)

    result = transcribe_audio_file(tmp_path / "a.mp3", registry=registry)

    assert result.full_text == "transcript via whispercpp/base"
    assert good.last_request is not None
    assert good.last_request.model_id == "base"


def test_transcribe_prefers_requested_model_when_installed(tmp_path: Path) -> None:
    good = _FakeProvider("whispercpp", installed=["base", "small"])
    result = transcribe_audio_file(tmp_path / "a.wav", model_id="small", registry=_registry(good))
    assert result.model_id == "small"


def test_transcribe_falls_back_when_requested_model_absent(tmp_path: Path) -> None:
    good = _FakeProvider("whispercpp", installed=["base"])
    result = transcribe_audio_file(tmp_path / "a.wav", model_id="large", registry=_registry(good))
    # Requested model not installed -> first installed model is used, not an error.
    assert result.model_id == "base"


def test_transcribe_passes_language_through(tmp_path: Path) -> None:
    good = _FakeProvider("whispercpp", installed=["base"])
    transcribe_audio_file(tmp_path / "a.wav", language="es", registry=_registry(good))
    assert good.last_request is not None
    assert good.last_request.language == "es"


def test_transcribe_raises_when_no_model_installed(tmp_path: Path) -> None:
    registry = _registry(_FakeProvider("whispercpp", installed=[]))
    with pytest.raises(SpeechError, match="No offline speech model"):
        transcribe_audio_file(tmp_path / "a.mp3", registry=registry)


def test_transcribe_skips_unavailable_providers(tmp_path: Path) -> None:
    offline = _FakeProvider("down", available=False, installed=["base"])
    registry = _registry(offline)
    with pytest.raises(SpeechError):
        transcribe_audio_file(tmp_path / "a.mp3", registry=registry)


def test_has_installed_offline_model_reports_true_when_present() -> None:
    assert has_installed_offline_model(_registry(_FakeProvider("w", installed=["base"]))) is True


def test_has_installed_offline_model_reports_false_when_empty() -> None:
    assert has_installed_offline_model(_registry(_FakeProvider("w", installed=[]))) is False
