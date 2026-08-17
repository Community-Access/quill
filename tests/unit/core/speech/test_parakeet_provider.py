"""Parakeet 3: catalog honesty, the mirror pin, and the dictation ladder.

The provider itself needs sherpa-onnx and a 650 MB model; what must hold
without either is everything around it — the catalog says what the model can
do, the mirror is genuinely pinned, and the preference ladder promotes
Parakeet only when installed and never over an explicit choice.
"""

from __future__ import annotations

from quill.core.speech import catalog, model_mirrors
from quill.core.speech.providers.parakeet_onnx import result_from_text
from quill.core.speech.registry import SpeechProviderRegistry
from quill.core.speech.service import (
    DEFAULT_PROVIDER_ID,
    describe_models,
    preferred_dictation_provider_id,
)


class _FakeProvider:
    def __init__(self, provider_id: str, installed: bool) -> None:
        self.id = provider_id
        self.display_name = provider_id
        self._installed = installed

    def list_installed_models(self):
        return [object()] if self._installed else []

    def list_supported_models(self):
        return []


def _registry(*providers: _FakeProvider) -> SpeechProviderRegistry:
    registry = SpeechProviderRegistry()
    for provider in providers:
        registry.register(provider)  # type: ignore[arg-type]
    return registry


# -- catalog + mirror ---------------------------------------------------------


def test_parakeet_is_in_the_catalog_with_honest_capabilities() -> None:
    info = catalog.parakeet_model_by_id(catalog.PARAKEET_RECOMMENDED_MODEL_ID)
    assert info is not None
    assert info.language_mode == "multilingual"
    assert "language-detect" in info.capabilities
    assert "silence-safe" in info.capabilities
    assert info.license_name == "CC-BY-4.0"


def test_parakeet_mirror_is_genuinely_pinned() -> None:
    asset = model_mirrors.mirror_for("parakeet", "parakeet-tdt-0.6b-v3")
    assert asset is not None
    assert asset.filename == "sherpa-onnx-parakeet-tdt-0.6b-v3-int8.zip"
    assert len(asset.sha256) == 64
    assert asset.archive_member == "tokens.txt"


def test_result_from_text_maps_to_one_segment() -> None:
    text, segments = result_from_text("  bonjour tout le monde  ", 2.5)
    assert text == "bonjour tout le monde"
    assert len(segments) == 1 and segments[0].end_seconds == 2.5
    assert result_from_text("   ", 2.0) == ("", ())


# -- the dictation preference ladder -----------------------------------------


def test_explicit_choice_always_wins() -> None:
    registry = _registry(
        _FakeProvider("whispercpp", True),
        _FakeProvider("parakeet", True),
        _FakeProvider("vosk", True),
    )
    assert preferred_dictation_provider_id(registry, "vosk") == "vosk"


def test_installed_parakeet_outranks_the_default() -> None:
    registry = _registry(_FakeProvider("whispercpp", True), _FakeProvider("parakeet", True))
    assert preferred_dictation_provider_id(registry) == "parakeet"


def test_uninstalled_parakeet_never_promotes() -> None:
    registry = _registry(_FakeProvider("whispercpp", True), _FakeProvider("parakeet", False))
    assert preferred_dictation_provider_id(registry) == DEFAULT_PROVIDER_ID


def test_absent_parakeet_falls_back_to_default() -> None:
    registry = _registry(_FakeProvider("whispercpp", True))
    assert preferred_dictation_provider_id(registry) == DEFAULT_PROVIDER_ID


def test_unknown_explicit_choice_falls_through_the_ladder() -> None:
    registry = _registry(_FakeProvider("whispercpp", True), _FakeProvider("parakeet", True))
    assert preferred_dictation_provider_id(registry, "gone-engine") == "parakeet"


# -- capability text in the model manager -------------------------------------


class _CatalogProvider:
    id = "parakeet"
    display_name = "Parakeet 3"

    def list_supported_models(self):
        return [catalog.PARAKEET_MODELS[0]]

    def list_installed_models(self):
        return []


def test_model_rows_speak_capabilities_before_download() -> None:
    rows = describe_models(_CatalogProvider(), total_ram_gb=32.0, has_gpu=False)  # type: ignore[arg-type]
    assert len(rows) == 1
    label = rows[0].label
    assert "detects the spoken language" in label
    assert "never invents text from silence" in label
