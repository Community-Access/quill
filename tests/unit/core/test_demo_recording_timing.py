"""When the mix stretches a drifted sound source (REC-022, mix half)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.demo_recording_timing import drift_correction, segment_timing


def _fix(timing, duration=600.0):
    return drift_correction(timing, label="Microphone", segment=2, duration=duration)


def test_missing_or_unusable_measurements_mean_no_stretch():
    for timing in (None, {}, "1.01", {"drift_ratio": None}, {"drift_ratio": "fast"}):
        assert _fix(timing) is None
    assert _fix({"drift_ratio": float("nan")}) is None
    assert _fix({"drift_ratio": True}) is None
    # Far outside any real sound card: a broken measurement, not a clock.
    assert _fix({"drift_ratio": 1.5}) is None


def test_within_20_ms_is_left_alone():
    assert _fix({"drift_ratio": 1.00003}) is None  # 18 ms over ten minutes
    assert _fix({"drift_ratio": 1.0, "drift_ms": 0.0}) is None


def test_a_fast_clock_is_played_faster_and_worded_for_the_report():
    # 48,010 Hz against 48,000: REC-022's own fixture, 125 ms over ten minutes.
    correction = _fix({"drift_ratio": 48_010 / 48_000})
    assert correction is not None
    assert correction.tempo == pytest.approx(1.000208, abs=1e-6)
    assert correction.drift_ms == pytest.approx(125.0, abs=0.1)
    sentence = correction.sentence()
    assert sentence.startswith("Microphone, segment 2: its clock ran fast, 125 ms over 600")
    assert correction.to_dict()["segment"] == 2


def test_the_measured_span_and_drift_win_over_the_segment_length():
    correction = _fix(
        {"drift_ratio": 0.9995, "drift_ms": -30.0, "monotonic_seconds": 60.0}, duration=5.0
    )
    assert correction is not None and correction.seconds == 60.0
    assert "ran slow, 30 ms" in correction.sentence()


def test_segment_timing_reads_defensively():
    assert segment_timing(SimpleNamespace()) == {}
    assert segment_timing(SimpleNamespace(audio_timing=None)) == {}
    row = {"mic": {"drift_ratio": 1.0}}
    assert segment_timing(SimpleNamespace(audio_timing=row)) is row
