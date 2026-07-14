"""Unit tests for the wx-free in-app footprint sampler (Phase 0)."""

from __future__ import annotations

from quill.core.footprint_sampler import sample_peak_rss, time_to_first


def test_sample_peak_rss_returns_work_result_and_a_peak() -> None:
    readings = iter([100, 250, 180, 300, 120])

    def reader() -> int:
        try:
            return next(readings)
        except StopIteration:
            return 120

    result, peak = sample_peak_rss(lambda: "done", rss_reader=reader, interval_s=0.001)
    assert result == "done"
    assert peak >= 250  # captured at least the up-front + some polled samples


def test_sample_peak_rss_unavailable_reader_yields_minus_one() -> None:
    result, peak = sample_peak_rss(lambda: 42, rss_reader=lambda: -1, interval_s=0.001)
    assert result == 42
    assert peak == -1


def test_sample_peak_rss_failing_reader_does_not_break_work() -> None:
    def boom() -> int:
        raise RuntimeError("no /proc")

    result, peak = sample_peak_rss(lambda: "ok", rss_reader=boom, interval_s=0.001)
    assert result == "ok"
    assert peak == -1


def test_time_to_first_measures_and_preserves_stream() -> None:
    ticks = iter([10.0, 10.5])  # start, first-item

    def clock() -> float:
        return next(ticks)

    def stream():
        yield "a"
        yield "b"
        yield "c"

    elapsed, rest = time_to_first(stream, clock=clock)
    assert elapsed == 0.5
    assert list(rest) == ["a", "b", "c"]  # first item pushed back, nothing lost


def test_time_to_first_empty_stream() -> None:
    elapsed, rest = time_to_first(lambda: iter(()))
    assert elapsed == -1.0
    assert list(rest) == []
