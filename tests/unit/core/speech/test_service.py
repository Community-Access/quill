from __future__ import annotations

from pathlib import Path

from quill.core.speech import service
from quill.core.speech.provider import InstalledSpeechModel, SpeechModelInfo


class _Provider:
    id = "whispercpp"

    def __init__(self, installed: list[str]) -> None:
        self._installed = installed

    def list_supported_models(self) -> list[SpeechModelInfo]:
        return [
            SpeechModelInfo(
                id="small",
                display_name="Small",
                language_mode="multilingual",
                approximate_size_mb=465,
                accuracy_tier="medium",
                speed_tier="medium",
                recommended_use="Recommended starting point.",
            ),
            SpeechModelInfo(
                id="large-v3",
                display_name="Large (v3)",
                language_mode="multilingual",
                approximate_size_mb=3100,
                accuracy_tier="highest",
                speed_tier="slow",
                recommended_use="Best local quality.",
            ),
        ]

    def list_installed_models(self) -> list[InstalledSpeechModel]:
        return [
            InstalledSpeechModel(
                id=m, display_name=m, path=Path(m), size_mb=0, provider_id="whispercpp"
            )
            for m in self._installed
        ]


class _CloudProvider:
    """Shape of a cloud (Quillin-registered) provider: no downloadable models,
    since it's API-based -- the Dictation (Online) tab's "current" provider."""

    id = "cloud-stt"

    def list_supported_models(self) -> list[SpeechModelInfo]:
        return []

    def list_installed_models(self) -> list[InstalledSpeechModel]:
        return []


def test_default_registry_has_whispercpp() -> None:
    registry = service.default_registry()
    assert registry.get(service.DEFAULT_PROVIDER_ID) is not None


def test_describe_models_is_empty_for_a_modelless_cloud_provider() -> None:
    # Regression guard: Dictation (Online) reuses describe_models() for
    # whichever cloud provider is "current" there; a provider with no models
    # must produce an empty row list, not crash the hub.
    assert service.describe_models(_CloudProvider()) == []


def test_describe_models_marks_installed_and_sizes() -> None:
    rows = service.describe_models(_Provider(installed=["small"]))
    by_id = {r.id: r for r in rows}
    assert by_id["small"].installed is True
    assert "Installed" in by_id["small"].label
    assert "465 MB download" in by_id["small"].label
    assert by_id["large-v3"].installed is False
    assert "Not installed" in by_id["large-v3"].label
    assert "3.1 GB download" in by_id["large-v3"].label


def test_required_ram_gb_tiers() -> None:
    assert service.required_ram_gb(75) == 2  # tiny
    assert service.required_ram_gb(465) == 4  # small
    assert service.required_ram_gb(1500) == 6  # medium
    assert service.required_ram_gb(3100) == 8  # large


def test_describe_models_flags_models_that_exceed_ram() -> None:
    # 4 GB machine: small (needs ~4) fits; large-v3 (needs ~8) does not.
    rows = service.describe_models(_Provider(installed=[]), total_ram_gb=4.0)
    by_id = {r.id: r for r in rows}
    assert by_id["small"].fits is True
    assert by_id["small"].ram_warning == ""
    assert by_id["large-v3"].fits is False
    assert "May not run" in by_id["large-v3"].ram_warning
    assert "May not run" in by_id["large-v3"].label


def test_describe_models_all_fit_on_large_machine() -> None:
    rows = service.describe_models(_Provider(installed=[]), total_ram_gb=64.0)
    assert all(r.fits for r in rows)
    assert all(r.ram_warning == "" for r in rows)


def test_recommend_model_id_scales_with_ram_and_gpu() -> None:
    ids = ["tiny", "base", "small", "medium", "large-v3"]
    assert service.recommend_model_id(ids, total_ram_gb=2.0, has_gpu=False) == "tiny"
    assert service.recommend_model_id(ids, total_ram_gb=4.0, has_gpu=False) == "base"
    assert service.recommend_model_id(ids, total_ram_gb=8.0, has_gpu=False) == "small"
    assert service.recommend_model_id(ids, total_ram_gb=32.0, has_gpu=True) == "large-v3"
    # Always returns an offered id, even when preferences are missing.
    assert service.recommend_model_id(["small"], total_ram_gb=64.0, has_gpu=True) == "small"
    assert service.recommend_model_id([], total_ram_gb=8.0, has_gpu=False) == ""


def test_describe_models_marks_recommended_and_gpu_note() -> None:
    rows = service.describe_models(_Provider(installed=[]), total_ram_gb=8.0, has_gpu=False)
    by_id = {r.id: r for r in rows}
    # 8 GB, no GPU -> small is the recommendation; large-v3 gets a CPU-speed note.
    assert by_id["small"].recommended is True
    assert "Recommended for your computer" in by_id["small"].label
    assert by_id["large-v3"].recommended is False
    assert "No GPU detected" in by_id["large-v3"].gpu_note
    assert "No GPU detected" in by_id["large-v3"].label


def test_enough_disk_for() -> None:
    assert service.enough_disk_for(465, free_gb=10.0) is True
    assert service.enough_disk_for(3100, free_gb=2.0) is False  # 3.1 GB + buffer > 2
    assert service.enough_disk_for(3100, free_gb=-1.0) is True  # unknown -> allow


def test_machine_summary_is_speakable() -> None:
    assert "16.0 GB RAM" in service.machine_summary(16.0, has_gpu=True)
    assert "GPU" in service.machine_summary(16.0, has_gpu=True)
    assert "no GPU" in service.machine_summary(8.0, has_gpu=False)


def test_describe_models_carries_license_and_card_url() -> None:
    rows = service.describe_models(_Provider(installed=[]), total_ram_gb=16.0, has_gpu=True)
    by_id = {r.id: r for r in rows}
    # _Provider's models have no license_name set, so license is empty here; the
    # label must not crash and the row fields exist.
    assert hasattr(by_id["small"], "license_name")
    assert hasattr(by_id["small"], "model_card_url")


def test_model_card_url_from_resolve_and_repo_forms() -> None:
    assert (
        service.model_card_url(
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
        )
        == "https://huggingface.co/ggerganov/whisper.cpp"
    )
    assert (
        service.model_card_url("Systran/faster-whisper-small")
        == "https://huggingface.co/Systran/faster-whisper-small"
    )
    assert service.model_card_url(None) == ""
    assert service.model_card_url("") == ""


def test_describe_models_label_includes_license_when_present() -> None:
    from quill.core.speech.provider import SpeechModelInfo

    class _Licensed:
        id = "whispercpp"

        def list_supported_models(self):
            return [
                SpeechModelInfo(
                    id="small",
                    display_name="Small",
                    language_mode="multilingual",
                    approximate_size_mb=465,
                    accuracy_tier="medium",
                    speed_tier="medium",
                    recommended_use="Recommended.",
                    download_url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
                    license_name="MIT",
                )
            ]

        def list_installed_models(self):
            return []

    rows = service.describe_models(_Licensed(), total_ram_gb=16.0, has_gpu=True)
    row = rows[0]
    assert row.license_name == "MIT"
    assert "MIT licensed" in row.label
    assert row.model_card_url == "https://huggingface.co/ggerganov/whisper.cpp"


def test_input_device_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(service, "app_data_dir", lambda: tmp_path)
    assert service.load_input_device() == -1  # default
    service.save_input_device(3)
    assert service.load_input_device() == 3
    service.save_input_device(-1)
    assert service.load_input_device() == -1
