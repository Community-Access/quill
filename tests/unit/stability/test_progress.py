"""Tests for the focus-free progress + ETA reporter (#1321)."""

from __future__ import annotations

import pytest

from quill.stability.progress import ProgressReporter, format_duration


def test_format_duration_scales_from_seconds_to_hours() -> None:
    assert format_duration(1) == "about 1 second"
    assert format_duration(45) == "about 45 seconds"
    assert format_duration(120) == "about 2 minutes"
    assert format_duration(3600) == "about 1 hour"
    assert format_duration(3600 + 20 * 60) == "about 1 hour 20 minutes"


def test_title_text_reads_count_and_app() -> None:
    reporter = ProgressReporter(247, label="Transcribing")
    reporter.start(0.0)
    reporter.advance(1.0)
    assert reporter.title_text() == "Transcribing 1 of 247 - QUILL"


def test_eta_is_estimating_until_the_second_unit() -> None:
    reporter = ProgressReporter(10, label="Transcribing")
    reporter.start(0.0)
    reporter.advance(100.0)  # first unit: warm-up-skewed, no ETA yet
    assert reporter.eta_seconds() is None
    assert "Estimating time remaining" in reporter.status_text()


def test_eta_from_second_unit_excludes_the_warmup_first_interval() -> None:
    reporter = ProgressReporter(10, label="Transcribing")
    reporter.start(0.0)
    reporter.advance(100.0)  # first unit took 100s (cold: model load, cache miss)
    reporter.advance(110.0)  # second unit took 10s (warm)
    # Rate is measured from the second unit (10s/unit), NOT the 100s cold start:
    # 8 units remain -> 80s, not 8 * (105s average).
    assert reporter.eta_seconds() == pytest.approx(80.0)
    assert "about 80 seconds remaining" in reporter.status_text().lower()


def test_hours_warning_fires_only_for_long_runs() -> None:
    short = ProgressReporter(10)
    short.start(0.0)
    short.advance(100.0)
    short.advance(110.0)  # ~10s/unit * 10 = 100s total
    assert short.hours_warning() == ""

    long = ProgressReporter(1000, label="Transcribing")
    long.start(0.0)
    long.advance(100.0)
    long.advance(110.0)  # 10s/unit * 1000 = 10000s (~2h47m)
    warning = long.hours_warning()
    assert warning.startswith("Heads up")
    assert "hour" in warning


def test_completion_text() -> None:
    reporter = ProgressReporter(3, label="Transcribing")
    for i in range(1, 4):
        reporter.advance(float(i))
    assert reporter.is_complete()
    assert reporter.title_text() == "Transcribing complete - QUILL"
    assert reporter.status_text() == "Transcribing complete: 3 of 3."


def test_validation() -> None:
    with pytest.raises(ValueError):
        ProgressReporter(-1)
    with pytest.raises(ValueError):
        ProgressReporter(5).advance(1.0, count=0)
