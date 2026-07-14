"""Tests for announcement anti-spam: repetition collapse (#409) + budget (#408)."""

from __future__ import annotations

from quill.core.verbosity.throttle import (
    AnnouncementThrottle,
    ThrottleConfig,
    config_from_settings,
)


class _Clock:
    """A manually-advanced monotonic clock for deterministic windows."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def test_collapses_identical_consecutive_speech_within_window() -> None:
    clock = _Clock()
    throttle = AnnouncementThrottle(ThrottleConfig(collapse_repeats=True), time_fn=clock)
    assert throttle.admit("No more results.").speak is True
    # Immediate repeat is collapsed.
    second = throttle.admit("No more results.")
    assert second.speak is False and second.reason == "repeat"
    # Still collapsed a moment later, inside the window.
    clock.advance(1.0)
    assert throttle.admit("No more results.").speak is False
    # After the window passes, it speaks again.
    clock.advance(2.0)
    assert throttle.admit("No more results.").speak is True


def test_different_messages_are_not_collapsed() -> None:
    clock = _Clock()
    throttle = AnnouncementThrottle(ThrottleConfig(collapse_repeats=True), time_fn=clock)
    assert throttle.admit("Line 1").speak is True
    assert throttle.admit("Line 2").speak is True
    assert throttle.admit("Line 1").speak is True  # not the immediately previous one


def test_collapse_can_be_disabled() -> None:
    throttle = AnnouncementThrottle(ThrottleConfig(collapse_repeats=False))
    assert throttle.admit("same").speak is True
    assert throttle.admit("same").speak is True


def test_budget_caps_spoken_announcements_per_window() -> None:
    clock = _Clock()
    cfg = ThrottleConfig(collapse_repeats=False, max_per_window=3, budget_window_s=5.0)
    throttle = AnnouncementThrottle(cfg, time_fn=clock)
    # Distinct messages so collapse never interferes; 3 admitted, 4th over budget.
    assert throttle.admit("a").speak is True
    assert throttle.admit("b").speak is True
    assert throttle.admit("c").speak is True
    fourth = throttle.admit("d")
    assert fourth.speak is False and fourth.reason == "budget"
    # Once the window drains, speaking resumes.
    clock.advance(5.1)
    assert throttle.admit("e").speak is True


def test_budget_zero_means_no_cap() -> None:
    throttle = AnnouncementThrottle(ThrottleConfig(collapse_repeats=False, max_per_window=0))
    for i in range(50):
        assert throttle.admit(f"msg {i}").speak is True


def test_empty_speech_always_admitted_and_uncounted() -> None:
    cfg = ThrottleConfig(collapse_repeats=True, max_per_window=1)
    throttle = AnnouncementThrottle(cfg)
    assert throttle.admit("").speak is True
    assert throttle.admit("").speak is True
    # The empty admits did not consume the budget.
    assert throttle.admit("real").speak is True


def test_reset_clears_history() -> None:
    throttle = AnnouncementThrottle(ThrottleConfig(collapse_repeats=True))
    assert throttle.admit("x").speak is True
    throttle.reset()
    assert throttle.admit("x").speak is True  # no longer seen as a repeat


def test_config_from_settings_reads_knobs() -> None:
    class _S:
        verbosity_collapse_repeats = False
        verbosity_max_announcements_per_window = 7

    cfg = config_from_settings(_S())
    assert cfg.collapse_repeats is False and cfg.max_per_window == 7

    class _Bad:
        verbosity_collapse_repeats = True
        verbosity_max_announcements_per_window = "nope"

    cfg2 = config_from_settings(_Bad())
    assert cfg2.collapse_repeats is True and cfg2.max_per_window == 0
