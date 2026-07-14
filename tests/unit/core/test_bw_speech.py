from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from quill.core import bw_speech
from quill.core.bw_speech import (
    _reset_gpu_probe_cache_for_tests,
    downloaded_model_ids,
    faster_whisper_status,
    get_model,
    has_nvidia_gpu,
    list_models,
    machine_guidance,
    model_path,
    recommended_model_id,
    remove_model,
    speech_models_dir,
)


@pytest.fixture(autouse=True)
def _reset_gpu_cache() -> None:
    _reset_gpu_probe_cache_for_tests()
    yield
    _reset_gpu_probe_cache_for_tests()


def test_list_models_contains_whisper_defaults() -> None:
    model_ids = {model.id for model in list_models()}
    assert "whisper-tiny" in model_ids
    assert "whisper-base" in model_ids
    assert "whisper-small" in model_ids
    assert "whisper-large-v3-turbo" in model_ids


def test_recommended_model_is_known() -> None:
    model_ids = {model.id for model in list_models()}
    assert recommended_model_id() in model_ids


def test_machine_guidance_mentions_ram_and_gpu() -> None:
    text = machine_guidance().lower()
    assert "ram" in text
    assert "gpu" in text


def test_model_path_lives_under_speech_model_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    model = get_model("whisper-base")
    assert model is not None
    path = model_path(model)
    assert str(path).startswith(str(speech_models_dir()))
    assert path.name.startswith("models--")


def test_downloaded_model_ids_detects_local_markers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    model = get_model("whisper-base")
    assert model is not None
    cache_repo_dir = model_path(model)
    (cache_repo_dir / "snapshots" / "123").mkdir(parents=True, exist_ok=True)

    ids = downloaded_model_ids()
    assert "whisper-base" in ids


def test_remove_model_removes_marker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    model = get_model("whisper-base")
    assert model is not None
    cache_repo_dir = model_path(model)
    (cache_repo_dir / "snapshots" / "123").mkdir(parents=True, exist_ok=True)

    assert remove_model(model) is True
    assert cache_repo_dir.exists() is False


def test_faster_whisper_status_returns_message() -> None:
    ok, message = faster_whisper_status()
    assert isinstance(ok, bool)
    assert isinstance(message, str)
    assert message != ""


# --- #866/#870: GPU probe must be cached and never hang the caller -----------


def test_has_nvidia_gpu_caches_after_first_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bw_speech.shutil, "which", lambda _name: "nvidia-smi")
    calls = []

    def fake_run_safely(args, *, timeout_seconds=5.0):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="GPU 0: Fake\n", stderr="")

    monkeypatch.setattr("quill.stability.safe_subprocess.run_subprocess_safely", fake_run_safely)

    assert has_nvidia_gpu() is True
    assert has_nvidia_gpu() is True
    assert len(calls) == 1


def test_has_nvidia_gpu_treats_timeout_as_no_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bw_speech.shutil, "which", lambda _name: "nvidia-smi")

    def fake_run_safely(args, *, timeout_seconds=5.0):
        raise subprocess.TimeoutExpired(cmd=args, timeout=timeout_seconds)

    monkeypatch.setattr("quill.stability.safe_subprocess.run_subprocess_safely", fake_run_safely)

    assert has_nvidia_gpu() is False


def test_has_nvidia_gpu_false_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bw_speech.shutil, "which", lambda _name: None)

    assert has_nvidia_gpu() is False
