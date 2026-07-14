"""Tests for the live footprint probe core (degradation, timing shape, merge).

These run with no speech engines installed — which is exactly the point: the
probe must degrade to notes with no fabricated timings, never crash.
"""

from __future__ import annotations

import wave

from quill.core.footprint.live_probe import (
    EngineTiming,
    list_speech_engine_ids,
    merge_timings_into_baseline,
    probe_speech_provider,
    run_engine_probe,
    write_silent_wav,
)


def test_write_silent_wav(tmp_path) -> None:
    path = write_silent_wav(tmp_path / "s.wav", seconds=1, rate=16000)
    assert path.is_file()
    with wave.open(str(path), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 16000
        assert wav.getnframes() == 16000


class _UnavailableProvider:
    id = "fake_unavailable"
    display_name = "Fake (unavailable)"

    def is_available(self) -> bool:
        return False

    def unload(self) -> None:
        pass


class _NoModelProvider:
    id = "fake_nomodel"
    display_name = "Fake (no model)"

    def is_available(self) -> bool:
        return True

    def list_installed_models(self) -> list:
        return []

    def unload(self) -> None:
        pass


class _WorkingProvider:
    id = "fake_ok"
    display_name = "Fake (ok)"

    def __init__(self) -> None:
        self.unloaded = False

    def is_available(self) -> bool:
        return True

    def list_installed_models(self) -> list:
        from pathlib import Path as _P

        from quill.core.speech.provider import InstalledSpeechModel

        return [
            InstalledSpeechModel(
                id="tiny", display_name="Tiny", path=_P("."), size_mb=1, provider_id="fake_ok"
            )
        ]

    def warm(self, model_id: str) -> None:
        pass

    def transcribe_file(self, request, progress=None):
        from quill.core.speech.provider import TranscriptionResult

        return TranscriptionResult(full_text="", model_id=request.model_id, provider_id="fake_ok")

    def unload(self) -> None:
        self.unloaded = True


def test_probe_unavailable_engine_records_note_no_timings() -> None:
    t = probe_speech_provider(_UnavailableProvider())
    assert t.available is False
    assert t.cold_start_s is None and t.first_output_s is None
    assert "not available" in t.note


def test_probe_no_model_records_note() -> None:
    t = probe_speech_provider(_NoModelProvider())
    assert t.available is True
    assert t.model_id is None and t.first_output_s is None
    assert "no model" in t.note.lower()


def test_probe_working_engine_times_and_unloads() -> None:
    provider = _WorkingProvider()
    t = probe_speech_provider(provider)
    assert t.available is True and t.model_id == "tiny"
    assert t.cold_start_s is not None and t.first_output_s is not None
    assert t.total_s is not None
    assert provider.unloaded is True  # always unloaded, even on the happy path


def test_probe_never_raises_on_broken_provider() -> None:
    class _Boom:
        id = "boom"
        display_name = "Boom"

        def is_available(self) -> bool:
            raise RuntimeError("kaboom")

        def unload(self) -> None:
            pass

    t = probe_speech_provider(_Boom())
    assert t.available is False and "probe failed" in t.note


def test_run_engine_probe_unregistered_id() -> None:
    t = run_engine_probe("definitely_not_a_real_engine")
    assert t.available is False
    assert t.note  # a note explaining why, no timings
    assert t.cold_start_s is None


def test_list_speech_engine_ids_is_a_list() -> None:
    # Never raises even if the speech stack is partly absent.
    assert isinstance(list_speech_engine_ids(), list)


def test_merge_timings_into_baseline_is_pure() -> None:
    baseline = {"generated_at": "x", "components": []}
    timings = [EngineTiming(engine_id="e", display_name="E", available=True, cold_start_s=1.5)]
    merged = merge_timings_into_baseline(baseline, timings)
    assert "engine_timings" not in baseline  # original untouched
    assert merged["engine_timings"][0]["engine_id"] == "e"
    assert merged["engine_timings"][0]["cold_start_s"] == 1.5
