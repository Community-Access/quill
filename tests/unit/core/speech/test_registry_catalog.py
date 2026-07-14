from __future__ import annotations

from quill.core.speech import catalog
from quill.core.speech.registry import SpeechProviderRegistry


class _FakeProvider:
    def __init__(self, provider_id: str, available: bool = True, *, raises: bool = False) -> None:
        self.id = provider_id
        self.display_name = provider_id.title()
        self.description = ""
        self._available = available
        self._raises = raises

    def is_available(self) -> bool:
        if self._raises:
            raise RuntimeError("boom")
        return self._available


def test_register_get_and_ids() -> None:
    reg = SpeechProviderRegistry()
    reg.register(_FakeProvider("whispercpp"))
    reg.register(_FakeProvider("faster_whisper", available=False))
    assert reg.ids() == ["whispercpp", "faster_whisper"]
    assert reg.get("whispercpp") is not None
    assert reg.get("missing") is None
    assert len(reg.all()) == 2


def test_available_filters_unavailable_and_broken() -> None:
    reg = SpeechProviderRegistry()
    reg.register(_FakeProvider("ok", available=True))
    reg.register(_FakeProvider("off", available=False))
    reg.register(_FakeProvider("broken", raises=True))
    available_ids = [p.id for p in reg.available()]
    assert available_ids == ["ok"]


def test_register_replaces_same_id() -> None:
    reg = SpeechProviderRegistry()
    reg.register(_FakeProvider("whispercpp", available=True))
    reg.register(_FakeProvider("whispercpp", available=False))
    assert len(reg.all()) == 1
    assert reg.available() == []


def test_catalog_has_recommended_small_model() -> None:
    assert catalog.RECOMMENDED_MODEL_ID == "small"
    assert catalog.recommended_model().id == "small"
    assert catalog.model_by_id("large-v3") is not None
    assert catalog.model_by_id("nope") is None


def test_catalog_models_have_non_decreasing_size() -> None:
    sizes = [m.approximate_size_mb for m in catalog.WHISPER_CPP_MODELS]
    assert sizes == sorted(sizes)
    assert len(catalog.WHISPER_CPP_MODELS) == 6


def test_diarization_model_detected() -> None:
    assert catalog.is_diarization_model(catalog.DIARIZATION_MODEL_ID) is True
    assert catalog.is_diarization_model("small") is False
    assert catalog.model_by_id(catalog.DIARIZATION_MODEL_ID) is not None
