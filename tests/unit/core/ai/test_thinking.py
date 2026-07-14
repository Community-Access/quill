"""ThinkingIndicator: cue timing, repeat cadence, reset."""

from __future__ import annotations

from quill.core.ai.thinking import ThinkingIndicator


def test_no_cue_before_patience() -> None:
    ind = ThinkingIndicator(patience_seconds=4.0, repeat_seconds=8.0)
    ind.start(now=100.0)
    assert ind.active is True
    assert ind.due_for_cue(101.0) is False
    assert ind.due_for_cue(103.9) is False


def test_first_cue_at_patience() -> None:
    ind = ThinkingIndicator(patience_seconds=4.0, repeat_seconds=8.0)
    ind.start(now=100.0)
    assert ind.due_for_cue(104.0) is True
    # Not again until the repeat interval elapses.
    assert ind.due_for_cue(105.0) is False


def test_repeat_cues_after_first() -> None:
    ind = ThinkingIndicator(patience_seconds=4.0, repeat_seconds=8.0)
    ind.start(now=0.0)
    assert ind.due_for_cue(4.0) is True  # first
    assert ind.due_for_cue(11.9) is False
    assert ind.due_for_cue(12.0) is True  # 4 + 8
    assert ind.due_for_cue(20.0) is True  # +8 again


def test_single_cue_when_repeat_disabled() -> None:
    ind = ThinkingIndicator(patience_seconds=2.0, repeat_seconds=0.0)
    ind.start(now=0.0)
    assert ind.due_for_cue(2.0) is True
    assert ind.due_for_cue(100.0) is False


def test_stop_resets_and_silences() -> None:
    ind = ThinkingIndicator(patience_seconds=1.0)
    ind.start(now=0.0)
    assert ind.due_for_cue(2.0) is True
    ind.stop()
    assert ind.active is False
    assert ind.due_for_cue(100.0) is False


def test_elapsed_tracks_from_start() -> None:
    ind = ThinkingIndicator()
    assert ind.elapsed(now=5.0) == 0.0  # not started
    ind.start(now=10.0)
    assert ind.elapsed(now=13.5) == 3.5
