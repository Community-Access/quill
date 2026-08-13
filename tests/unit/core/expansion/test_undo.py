"""Unit tests for taking back a system-wide expansion."""

from __future__ import annotations

from quill.core.expansion.undo import UNDO_WINDOW_SECONDS, UndoTracker


def _armed(tracker: UndoTracker, *, now: float = 100.0, hwnd: int = 7) -> None:
    tracker.record(
        abbreviation="btw",
        expanded_text="by the way",
        trailing_space=False,
        window_handle=hwnd,
        now=now,
    )


def test_nothing_to_undo_before_an_expansion() -> None:
    tracker = UndoTracker()
    assert tracker.armed is False
    assert tracker.take_undo(window_handle=7, now=100.0) is None


def test_backspace_right_after_an_expansion_puts_the_abbreviation_back() -> None:
    tracker = UndoTracker()
    _armed(tracker)
    plan = tracker.take_undo(window_handle=7, now=100.2)
    assert plan is not None
    assert plan.backspaces == len("by the way")
    assert plan.text == "btw"


def test_a_trailing_space_is_erased_too() -> None:
    tracker = UndoTracker()
    tracker.record(
        abbreviation="co",
        expanded_text="Company",
        trailing_space=True,
        window_handle=7,
        now=100.0,
    )
    plan = tracker.take_undo(window_handle=7, now=100.1)
    assert plan is not None
    assert plan.backspaces == len("Company") + 1


def test_undo_happens_only_once() -> None:
    tracker = UndoTracker()
    _armed(tracker)
    assert tracker.take_undo(window_handle=7, now=100.1) is not None
    assert tracker.take_undo(window_handle=7, now=100.2) is None


def test_the_window_closes_after_a_few_seconds() -> None:
    tracker = UndoTracker()
    _armed(tracker)
    assert tracker.take_undo(window_handle=7, now=100.0 + UNDO_WINDOW_SECONDS + 0.1) is None


def test_undo_never_fires_in_a_different_window() -> None:
    tracker = UndoTracker()
    _armed(tracker, hwnd=7)
    assert tracker.take_undo(window_handle=99, now=100.1) is None


def test_an_unknown_window_does_not_block_the_undo() -> None:
    # The platform layer can fail to read the foreground window; a missing
    # answer must not cost the user their undo.
    tracker = UndoTracker()
    _armed(tracker, hwnd=7)
    assert tracker.take_undo(window_handle=0, now=100.1) is not None


def test_clearing_disarms_it() -> None:
    tracker = UndoTracker()
    _armed(tracker)
    tracker.clear()
    assert tracker.armed is False
    assert tracker.take_undo(window_handle=7, now=100.1) is None


def test_a_later_expansion_replaces_the_earlier_one() -> None:
    tracker = UndoTracker()
    _armed(tracker)
    tracker.record(
        abbreviation="sig",
        expanded_text="Regards",
        trailing_space=False,
        window_handle=7,
        now=101.0,
    )
    plan = tracker.take_undo(window_handle=7, now=101.1)
    assert plan is not None
    assert plan.text == "sig"
