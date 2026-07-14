"""Tests for the audiobook quality surfaces: preflight, estimate, verify, report."""

from __future__ import annotations

from pathlib import Path

from quill.core.speech.audiobook import (
    AudiobookChapter,
    PreflightReport,
    StreamStats,
    chapter_report_text,
    estimate_output,
    format_size,
    is_probable_master,
    preflight_check,
)
from quill.core.speech.loudness import AcxCheck, acx_check_from_measurement


def test_is_probable_master_matches_folder_and_master_names() -> None:
    folder = Path("C:/books/My Book")
    assert is_probable_master("My Book.mp3", folder)
    assert is_probable_master("My Book - Master.m4b", folder)
    assert is_probable_master("Anything - Master.mp3", folder)
    assert not is_probable_master("01 - Chapter One.mp3", folder)


def test_preflight_uniform_streams() -> None:
    stats = [
        StreamStats(path=Path("a.mp3"), sample_rate=44100, channels=2, codec="mp3"),
        StreamStats(path=Path("b.mp3"), sample_rate=44100, channels=2, codec="mp3"),
    ]
    report = preflight_check(stats)
    assert isinstance(report, PreflightReport)
    assert report.uniform and not report.notes


def test_preflight_mixed_rates_and_codecs_report_offenders() -> None:
    stats = [
        StreamStats(path=Path("a.mp3"), sample_rate=44100, channels=2, codec="mp3"),
        StreamStats(path=Path("b.wav"), sample_rate=48000, channels=1, codec="pcm_s16le"),
    ]
    report = preflight_check(stats)
    assert not report.uniform
    joined = " ".join(report.notes)
    assert "b.wav" in joined and "48000" in joined
    assert "Channel counts differ" in joined
    assert "Formats differ" in joined


def test_preflight_unknown_streams_pass() -> None:
    assert preflight_check([StreamStats(path=Path("a.mp3"))]).uniform


def test_estimate_output_counts_gaps_between_chapters() -> None:
    chapters = [
        AudiobookChapter(path=Path("a.mp3"), title="A", duration_ms=60_000),
        AudiobookChapter(path=Path("b.mp3"), title="B", duration_ms=60_000),
    ]
    total_ms, est_bytes = estimate_output(chapters, bitrate_kbps=96, gap_ms=1000)
    assert total_ms == 121_000
    assert est_bytes == int(96 * 1000 / 8 * 121.0)


def test_format_size_units() -> None:
    assert format_size(512) == "512 bytes"
    assert format_size(2048) == "2.0 KB"
    assert format_size(5 * 1024 * 1024) == "5.0 MB"
    assert format_size(3 * 1024**3) == "3.0 GB"


def test_chapter_report_text_reads_like_sentences() -> None:
    chapters = [
        AudiobookChapter(path=Path("a.mp3"), title="Intro", duration_ms=60_000),
        AudiobookChapter(path=Path("b.mp3"), title="Body", duration_ms=120_000),
    ]
    text = chapter_report_text(chapters, title="My Book")
    assert "Chapter report: My Book" in text
    assert "  1. Intro — starts 0:00, runs 1:00" in text
    assert "2 chapter(s), 3:00 total." in text


def test_acx_check_flags_and_recommendations() -> None:
    good = acx_check_from_measurement({
        "input_i": "-20.5",
        "input_tp": "-3.5",
        "input_thresh": "-70.0",
    })
    assert isinstance(good, AcxCheck)
    assert good.ok and good.recommendations() == []

    bad = acx_check_from_measurement({
        "input_i": "-12.0",
        "input_tp": "-1.0",
        "input_thresh": "-50.0",
    })
    assert not bad.ok
    recs = bad.recommendations()
    assert len(recs) == 3
    assert any("quieter" in r for r in recs)
    assert any("True peak" in r for r in recs)
    assert any("Noise floor" in r for r in recs)
