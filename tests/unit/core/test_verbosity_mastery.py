"""Tests for mastery-based step-down detection (§27)."""

from __future__ import annotations

from quill.core.verbosity.mastery import MasteryTracker


def test_offers_once_at_threshold_then_resets() -> None:
    tracker = MasteryTracker(threshold=3)
    assert tracker.record_use("edit.select_word_right") is False
    assert tracker.record_use("edit.select_word_right") is False
    assert tracker.record_use("edit.select_word_right") is True  # threshold crossed
    assert tracker.count_for("edit.select_word_right") == 0  # reset, no nag
    assert tracker.record_use("edit.select_word_right") is False


def test_disabled_globally_never_offers() -> None:
    tracker = MasteryTracker(threshold=1, enabled=False)
    assert tracker.record_use("doc.save") is False


def test_per_verb_disable() -> None:
    tracker = MasteryTracker(threshold=1)
    tracker.disable_verb("doc.save")
    assert tracker.is_disabled("doc.save")
    assert tracker.record_use("doc.save") is False
    assert tracker.record_use("doc.open") is True  # other verbs still offer


def test_reset_clears_counts_and_disables() -> None:
    tracker = MasteryTracker(threshold=5)
    tracker.record_use("doc.save")
    tracker.disable_verb("doc.open")
    tracker.reset()
    assert tracker.count_for("doc.save") == 0
    assert not tracker.is_disabled("doc.open")


def test_round_trip() -> None:
    tracker = MasteryTracker(threshold=10)
    tracker.record_use("doc.save")
    tracker.record_use("doc.save")
    tracker.disable_verb("doc.open")
    restored = MasteryTracker.from_dict(tracker.to_dict())
    assert restored.count_for("doc.save") == 2
    assert restored.is_disabled("doc.open")
    assert restored.to_dict() == tracker.to_dict()
