"""Tests for the Faster Whisper provider's pure helpers and wiring (#617 S4)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from quill.core.speech import catalog
from quill.core.speech.provider import SpeechModelInfo
from quill.core.speech.providers import fasterwhisper as fw
from quill.core.speech.service import default_registry


@dataclass
class _Seg:
    start: float
    end: float
    text: str


def test_segments_from_faster_whisper_maps_and_drops_empty() -> None:
    raw = [_Seg(0.0, 1.5, " Hello "), _Seg(1.5, 2.0, "   "), _Seg(2.0, 3.0, "world")]
    segs = fw.segments_from_faster_whisper(raw)
    assert [s.text for s in segs] == ["Hello", "world"]
    assert segs[0].start_seconds == 0.0
    assert segs[1].end_seconds == 3.0
    # Faster Whisper does not attribute speakers.
    assert all(s.speaker == "" for s in segs)


def test_pick_device_and_compute_returns_known_pair() -> None:
    device, compute = fw.pick_device_and_compute()
    assert device in {"cpu", "cuda"}
    assert compute in {"int8", "float16"}


def test_progress_tqdm_survives_no_console_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirrors the same regression guard in test_whispercpp.py: QUILL's bundled
    quill.exe is a windowed pythonw.exe with no console, so sys.stderr is None
    there. tqdm's own bar rendering defaults to writing to sys.stderr; update()
    must not crash with "'NoneType' object has no attribute 'write'"."""
    pytest.importorskip("tqdm")
    monkeypatch.setattr("sys.stderr", None)
    calls: list[tuple[float, str]] = []
    info = SpeechModelInfo(
        id="small",
        display_name="Small",
        language_mode="multilingual",
        approximate_size_mb=465,
        accuracy_tier="medium",
        speed_tier="medium",
        recommended_use="test",
    )
    tqdm_cls = fw._make_progress_tqdm(info, lambda f, m: calls.append((f, m)))
    assert tqdm_cls is not None
    bar = tqdm_cls(total=100, disable=False)
    try:
        bar.update(10)
        expected_fraction = 0.02 + 0.95 * min(10 / (465 * 1024 * 1024), 1.0)
        assert calls == [(pytest.approx(expected_fraction), "Downloading Small...")]
    finally:
        bar.close()


def test_catalog_has_recommended_and_distil() -> None:
    ids = {m.id for m in catalog.FASTER_WHISPER_MODELS}
    assert catalog.FASTER_WHISPER_RECOMMENDED_MODEL_ID in ids
    assert "distil-large-v3" in ids
    small = catalog.fw_model_by_id("small")
    assert small is not None
    # download_url carries the Hugging Face repo id, not a file URL.
    assert small.download_url == "Systran/faster-whisper-small"


def test_provider_identity_and_unsupported_lookup() -> None:
    provider = fw.FasterWhisperProvider()
    assert provider.id == "fasterwhisper"
    assert "Faster Whisper" in provider.display_name
    assert catalog.fw_model_by_id("does-not-exist") is None


def test_registry_registers_faster_whisper_when_available() -> None:
    """faster_whisper is installed in the dev env, so it should register."""
    registry = default_registry()
    ids = registry.ids()
    assert "whispercpp" in ids  # bundled engine always present
    if fw.FasterWhisperProvider().is_available():
        assert "fasterwhisper" in ids
