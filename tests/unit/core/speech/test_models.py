from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.speech import models
from quill.core.speech.provider import InstalledSpeechModel


@pytest.fixture(autouse=True)
def _isolated_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "app_data_dir", lambda: tmp_path)


def _model(model_id: str = "small", provider: str = "whispercpp") -> InstalledSpeechModel:
    return InstalledSpeechModel(
        id=model_id,
        display_name=model_id.title(),
        path=Path("/models") / f"{model_id}.bin",
        size_mb=465,
        provider_id=provider,
        sha256="abc",
        installed_at="2026-06-21T00:00:00Z",
    )


def test_load_empty_when_no_file() -> None:
    assert models.load_installed_models() == []


def test_record_and_load_round_trip() -> None:
    models.record_installed_model(_model())
    loaded = models.load_installed_models()
    assert len(loaded) == 1
    assert loaded[0].id == "small"
    assert loaded[0].path == Path("/models/small.bin")


def test_record_replaces_same_provider_and_id() -> None:
    models.record_installed_model(_model())
    models.record_installed_model(_model())  # same key -> replace, not duplicate
    assert len(models.load_installed_models()) == 1


def test_same_id_different_provider_coexist() -> None:
    models.record_installed_model(_model(provider="whispercpp"))
    models.record_installed_model(_model(provider="faster_whisper"))
    assert len(models.load_installed_models()) == 2


def test_remove_installed_model() -> None:
    models.record_installed_model(_model())
    assert models.remove_installed_model("small", "whispercpp") is True
    assert models.load_installed_models() == []
    assert models.remove_installed_model("small", "whispercpp") is False


def test_malformed_metadata_reads_as_empty(tmp_path: Path) -> None:
    path = models.models_root() / "installed.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ not json", encoding="utf-8")
    assert models.load_installed_models() == []
