"""The speech model-download progress callback throttles UI updates to whole
percents so a chunk-frequent engine (Faster Whisper via huggingface_hub's
snapshot_download) cannot flood wx.CallAfter and freeze/crash the UI (#748)."""

from __future__ import annotations

from quill.core.speech.provider import download_progress_percent


def test_percent_clamps_and_floors() -> None:
    assert download_progress_percent(-0.5) == 0
    assert download_progress_percent(0.0) == 0
    assert download_progress_percent(0.025) == 2  # the classic "stuck at 2%" seed
    assert download_progress_percent(0.999) == 99
    assert download_progress_percent(1.0) == 100
    assert download_progress_percent(1.5) == 100  # never exceeds 100


def test_whole_percent_throttle_collapses_chunk_storm() -> None:
    # Mirror the _on_chunk gate: emit only when the whole percent advances. A
    # storm of thousands of tiny fractions between 2% and 4% must collapse to a
    # handful of UI updates, not one per chunk.
    last = -1
    emitted: list[int] = []
    n = 3000
    for i in range(n + 1):
        fraction = 0.02 + (i / n) * 0.02  # 0.02 -> 0.04 inclusive
        percent = download_progress_percent(fraction)
        if percent != last:
            last = percent
            emitted.append(percent)
    # 2, 3, 4 -> three updates total, regardless of how many chunks arrived.
    assert emitted == [2, 3, 4]
