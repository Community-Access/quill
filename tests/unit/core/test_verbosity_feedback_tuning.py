"""Tests for "Too Much / Too Little / Just Right" feedback tuning (§26)."""

from __future__ import annotations

from quill.core.verbosity.feedback_tuning import FeedbackSignal, FeedbackStore


def test_repeated_too_much_suggests_reduce() -> None:
    store = FeedbackStore(threshold=3)
    for _ in range(3):
        store.record("edit.select_word_right", FeedbackSignal.TOO_MUCH)
    assert store.suggestion_for("edit.select_word_right") == "reduce"


def test_repeated_too_little_suggests_increase() -> None:
    store = FeedbackStore(threshold=2)
    store.record("doc.save", FeedbackSignal.TOO_LITTLE)
    store.record("doc.save", FeedbackSignal.TOO_LITTLE)
    assert store.suggestion_for("doc.save") == "increase"


def test_just_right_resets_running_tally() -> None:
    store = FeedbackStore(threshold=2)
    store.record("doc.save", FeedbackSignal.TOO_MUCH)
    store.record("doc.save", FeedbackSignal.JUST_RIGHT)
    store.record("doc.save", FeedbackSignal.TOO_MUCH)
    assert store.suggestion_for("doc.save") is None  # tally was reset


def test_opposite_signal_resets() -> None:
    store = FeedbackStore(threshold=2)
    store.record("doc.save", FeedbackSignal.TOO_MUCH)
    store.record("doc.save", FeedbackSignal.TOO_LITTLE)
    assert store.suggestion_for("doc.save") is None


def test_decline_silences_suggestions() -> None:
    store = FeedbackStore(threshold=1)
    store.record("doc.save", FeedbackSignal.TOO_MUCH)
    assert store.suggestion_for("doc.save") == "reduce"
    store.decline("doc.save")
    assert store.suggestion_for("doc.save") is None


def test_reset_clears_everything() -> None:
    store = FeedbackStore(threshold=1)
    store.record("doc.save", FeedbackSignal.TOO_MUCH)
    store.decline("doc.open")
    store.reset()
    assert store.suggestion_for("doc.save") is None
    assert store.to_dict() == {"too_much": {}, "too_little": {}, "declined": []}


def test_round_trip() -> None:
    store = FeedbackStore(threshold=5)
    store.record("doc.save", FeedbackSignal.TOO_MUCH)
    store.decline("doc.open")
    restored = FeedbackStore.from_dict(store.to_dict())
    assert restored.to_dict() == store.to_dict()
