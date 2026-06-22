"""Tests for Quillin-contributed cloud transcription providers (host adapters)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.quillins.model import TranscriptionProviderContribution
from quill.core.speech import quillin_providers as qp
from quill.core.speech.provider import SpeechError, TranscriptionRequest
from quill.core.speech.registry import SpeechProviderRegistry


def _contribution(**kw) -> TranscriptionProviderContribution:
    base = dict(
        id="ext.acme.openai-whisper",
        display_name="Acme Whisper",
        kind="openai_whisper",
    )
    base.update(kw)
    return TranscriptionProviderContribution(**base)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _clear_active():
    qp.clear_quillin_transcription_providers()
    yield
    qp.clear_quillin_transcription_providers()


def test_build_provider_known_and_unknown_kind() -> None:
    assert isinstance(qp.build_provider(_contribution()), qp.OpenAiWhisperProvider)
    assert qp.build_provider(_contribution(kind="nope")) is None


def test_set_and_clear_active_set() -> None:
    qp.set_quillin_transcription_providers([_contribution(), _contribution(id="ext.b.x")])
    assert len(qp.quillin_transcription_providers()) == 2
    qp.clear_quillin_transcription_providers()
    assert qp.quillin_transcription_providers() == []


def test_unknown_kind_is_skipped_in_active_set() -> None:
    qp.set_quillin_transcription_providers([_contribution(kind="nope")])
    assert qp.quillin_transcription_providers() == []


def test_provider_is_network_backed() -> None:
    assert qp.OpenAiWhisperProvider(_contribution()).requires_network is True


def test_is_available_requires_key_and_not_safe_mode(monkeypatch) -> None:
    provider = qp.OpenAiWhisperProvider(_contribution())
    monkeypatch.setattr(qp, "_safe_mode_active", lambda: False)

    monkeypatch.setattr(qp, "_resolve_api_key", lambda _label: None)
    assert provider.is_available() is False
    assert provider.list_installed_models() == []

    monkeypatch.setattr(qp, "_resolve_api_key", lambda _label: "sk-test")
    assert provider.is_available() is True
    models = provider.list_installed_models()
    assert len(models) == 1 and models[0].provider_id == "ext.acme.openai-whisper"


def test_is_available_false_in_safe_mode(monkeypatch) -> None:
    monkeypatch.setattr(qp, "_safe_mode_active", lambda: True)
    monkeypatch.setattr(qp, "_resolve_api_key", lambda _label: "sk-test")
    assert qp.OpenAiWhisperProvider(_contribution()).is_available() is False


def test_transcribe_file_routes_to_ai_transcription(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "clip.mp3"
    audio.write_bytes(b"x")
    seen: dict[str, object] = {}

    def fake_transcribe(path, api_key, *, language=None):  # noqa: ANN001, ANN202
        seen["path"] = path
        seen["api_key"] = api_key
        seen["language"] = language
        return "cloud transcript"

    monkeypatch.setattr("quill.core.ai.transcription.transcribe_file", fake_transcribe)
    monkeypatch.setattr(qp, "_resolve_api_key", lambda _label: "sk-test")

    provider = qp.OpenAiWhisperProvider(_contribution())
    result = provider.transcribe_file(
        TranscriptionRequest(source_path=audio, model_id="cloud", language="es")
    )
    assert result.full_text == "cloud transcript"
    assert seen["api_key"] == "sk-test"
    assert seen["language"] == "es"


def test_transcribe_file_without_key_raises(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "clip.mp3"
    audio.write_bytes(b"x")
    monkeypatch.setattr(qp, "_resolve_api_key", lambda _label: None)
    provider = qp.OpenAiWhisperProvider(_contribution())
    with pytest.raises(SpeechError, match="No API key"):
        provider.transcribe_file(TranscriptionRequest(source_path=audio, model_id="cloud"))


def test_transcribe_file_over_size_limit_raises(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "big.mp3"
    audio.write_bytes(b"x" * 2048)
    monkeypatch.setattr(qp, "_resolve_api_key", lambda _label: "sk-test")
    provider = qp.OpenAiWhisperProvider(_contribution(max_file_mb=0.001))  # ~1 KB ceiling
    with pytest.raises(SpeechError, match="over the"):
        provider.transcribe_file(TranscriptionRequest(source_path=audio, model_id="cloud"))


# ---------------------------------------------------------------------------
# Offline-safety: the offline path must never pick a network provider.
# ---------------------------------------------------------------------------


class _FakeNetworkProvider:
    requires_network = True
    id = "ext.cloud.x"
    display_name = "Cloud X"
    description = ""

    def is_available(self) -> bool:
        return True

    def list_installed_models(self):  # noqa: ANN201
        from quill.core.speech.provider import InstalledSpeechModel

        return [
            InstalledSpeechModel(
                id="cloud", display_name="Cloud", path=Path("x"), size_mb=0, provider_id=self.id
            )
        ]


def test_offline_transcribe_skips_network_provider() -> None:
    from quill.core.speech.transcribe import (
        has_installed_offline_model,
        transcribe_audio_file,
    )

    registry = SpeechProviderRegistry()
    registry.register(_FakeNetworkProvider())  # type: ignore[arg-type]

    # A network provider with an "installed" model must NOT satisfy the offline path.
    assert has_installed_offline_model(registry) is False
    with pytest.raises(SpeechError, match="No offline speech model"):
        transcribe_audio_file(Path("a.mp3"), registry=registry)


def test_default_registry_includes_active_quillin_providers(monkeypatch) -> None:
    monkeypatch.setattr(qp, "_resolve_api_key", lambda _label: "sk-test")
    qp.set_quillin_transcription_providers([_contribution()])
    from quill.core.speech.service import default_registry

    registry = default_registry()
    assert registry.get("ext.acme.openai-whisper") is not None


class _StubContributes:
    def __init__(self, providers):
        self.transcription_providers = tuple(providers)


class _StubManifest:
    def __init__(self, providers):
        self.contributes = _StubContributes(providers)


def test_register_from_manifests_collects_all_providers() -> None:
    manifests = [
        _StubManifest([_contribution(id="ext.a.w")]),
        _StubManifest([]),
        _StubManifest([_contribution(id="ext.b.w")]),
    ]
    qp.register_quillin_transcription_providers(manifests)
    assert len(qp.quillin_transcription_providers()) == 2


def test_register_from_empty_manifests_clears() -> None:
    qp.register_quillin_transcription_providers([_StubManifest([_contribution()])])
    assert qp.quillin_transcription_providers()
    qp.register_quillin_transcription_providers([])
    assert qp.quillin_transcription_providers() == []
