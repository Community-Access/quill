"""The recordings play queue (x.md item 12).

``winamp_keys.py`` left R, S and Ctrl+V unbound on purpose: all three describe
a play queue the recordings player did not have, and binding them to something
that only pretended to work would have been worse than leaving them unbound.
This is the model that earns them.

Three decisions carry most of the weight, and each has tests that would fail
if it were quietly reversed:

* shuffle is a **fixed permutation**, not a dice roll per step, so Z goes back
  to what you just heard and nothing repeats before everything has played;
* **repeat-one applies to a natural end, not to Next**, or Next looks broken;
* **stop-after-current outranks repeat**, and clears itself when it fires.
"""

from __future__ import annotations

import pytest

from quill.core.radio.play_queue import (
    NO_ROW,
    REPEAT_ALL,
    REPEAT_LABELS,
    REPEAT_MODES,
    REPEAT_OFF,
    REPEAT_ONE,
    PlayQueue,
    next_repeat_mode,
    normalize_repeat_mode,
)


def _reverse(items: list[int]) -> None:
    """A deterministic stand-in for random.shuffle."""
    items.reverse()


def _queue(rows: list[int] | None = None, **kwargs: object) -> PlayQueue:
    queue = PlayQueue(**kwargs)  # type: ignore[arg-type]
    queue.set_rows(rows if rows is not None else [0, 1, 2, 3], shuffler=_reverse)
    return queue


# -- order -------------------------------------------------------------------


def test_with_shuffle_off_the_order_is_simply_the_list() -> None:
    """The queue is invisible until asked for."""
    assert _queue().order == [0, 1, 2, 3]


def test_with_shuffle_on_the_order_is_a_permutation_of_the_same_rows() -> None:
    queue = _queue(shuffle=True)
    assert queue.order == [3, 2, 1, 0]
    assert sorted(queue.order) == [0, 1, 2, 3], "every row appears exactly once"


def test_a_single_recording_is_never_shuffled() -> None:
    queue = _queue([5], shuffle=True)
    assert queue.order == [5]


def test_toggling_shuffle_rebuilds_the_order_both_ways() -> None:
    queue = _queue()
    assert queue.toggle_shuffle([0, 1, 2, 3], shuffler=_reverse) is True
    assert queue.order == [3, 2, 1, 0]
    assert queue.toggle_shuffle([0, 1, 2, 3], shuffler=_reverse) is False
    assert queue.order == [0, 1, 2, 3]


# -- the refresh timer must not reshuffle ------------------------------------


def test_an_unchanged_list_does_not_rebuild_the_order() -> None:
    """The recordings list refreshes every two seconds. Rebuilding then would
    reshuffle constantly, and Z would stop going back to what you just heard."""
    queue = _queue(shuffle=True)
    before = list(queue.order)

    assert queue.set_rows_if_changed([0, 1, 2, 3], shuffler=_reverse) is False
    assert queue.order == before


def test_the_same_rows_in_a_different_list_order_are_not_new_content() -> None:
    queue = _queue(shuffle=True)
    before = list(queue.order)
    assert queue.set_rows_if_changed([3, 1, 0, 2], shuffler=_reverse) is False
    assert queue.order == before


def test_a_genuinely_changed_list_does_rebuild() -> None:
    queue = _queue(shuffle=True)
    assert queue.set_rows_if_changed([0, 1, 2, 3, 4], shuffler=_reverse) is True
    assert sorted(queue.order) == [0, 1, 2, 3, 4]


# -- stepping ----------------------------------------------------------------


def test_next_and_previous_walk_the_list_in_order() -> None:
    queue = _queue()
    assert queue.next_row(1) == 2
    assert queue.previous_row(1) == 0


def test_previous_is_the_exact_inverse_of_next_under_shuffle() -> None:
    """The whole reason shuffle is a permutation rather than a dice roll."""
    queue = _queue(shuffle=True)  # order [3, 2, 1, 0]
    landed = queue.next_row(3)
    assert landed == 2
    assert queue.previous_row(landed) == 3


def test_the_ends_report_no_row_with_repeat_off() -> None:
    queue = _queue()
    assert queue.next_row(3) == NO_ROW
    assert queue.previous_row(0) == NO_ROW


def test_repeat_all_wraps_at_both_ends() -> None:
    queue = _queue(repeat=REPEAT_ALL)
    assert queue.next_row(3) == 0
    assert queue.previous_row(0) == 3


def test_nothing_playing_starts_at_the_end_you_are_heading_towards() -> None:
    queue = _queue()
    assert queue.next_row(-1) == 0
    assert queue.previous_row(-1) == 3


def test_a_row_no_longer_in_the_list_is_treated_as_nothing_playing() -> None:
    """A recording deleted while it was the queue's position must not strand
    the queue."""
    queue = _queue()
    assert queue.next_row(99) == 0


def test_an_empty_queue_has_nowhere_to_go() -> None:
    queue = _queue([])
    assert queue.next_row(0) == NO_ROW
    assert queue.previous_row(0) == NO_ROW


def test_next_ignores_repeat_one() -> None:
    """Pressing Next while one recording repeats must still move on, or Next
    looks broken."""
    queue = _queue(repeat=REPEAT_ONE)
    assert queue.next_row(1) == 2


# -- what happens when a recording ends on its own ---------------------------


def test_a_finished_recording_is_followed_by_the_next_one() -> None:
    assert _queue().row_after_finishing(1) == 2


def test_the_last_recording_ends_playback_with_repeat_off() -> None:
    assert _queue().row_after_finishing(3) == NO_ROW


def test_repeat_all_carries_on_from_the_top() -> None:
    assert _queue(repeat=REPEAT_ALL).row_after_finishing(3) == 0


def test_repeat_one_replays_the_same_recording() -> None:
    assert _queue(repeat=REPEAT_ONE).row_after_finishing(2) == 2


def test_stop_after_current_beats_repeat_and_then_clears_itself() -> None:
    """A one-shot the listener asked for just now outranks a standing
    preference -- and never survives to surprise them later."""
    queue = _queue(repeat=REPEAT_ALL)
    queue.stop_after_current = True

    assert queue.row_after_finishing(1) == NO_ROW
    assert queue.stop_after_current is False
    assert queue.row_after_finishing(1) == 2, "the next recording follows normally again"


def test_stop_after_current_beats_repeat_one_too() -> None:
    queue = _queue(repeat=REPEAT_ONE)
    queue.stop_after_current = True
    assert queue.row_after_finishing(2) == NO_ROW


def test_toggling_stop_after_current_reports_the_new_state() -> None:
    queue = _queue()
    assert queue.toggle_stop_after_current() is True
    assert queue.toggle_stop_after_current() is False


# -- repeat modes ------------------------------------------------------------


def test_s_cycles_off_then_all_then_one_then_back() -> None:
    queue = _queue()
    assert queue.cycle_repeat() == REPEAT_ALL
    assert queue.cycle_repeat() == REPEAT_ONE
    assert queue.cycle_repeat() == REPEAT_OFF


def test_every_mode_has_words_to_say() -> None:
    assert set(REPEAT_LABELS) == set(REPEAT_MODES)
    for label in REPEAT_LABELS.values():
        assert label[0].isupper() and ":" not in label


def test_an_unknown_mode_restarts_the_cycle() -> None:
    assert next_repeat_mode("something-new") == REPEAT_OFF


@pytest.mark.parametrize("raw", ["", None, "sideways", 7, "  ALL  "])
def test_a_stored_mode_is_normalized_on_the_way_in(raw: object) -> None:
    """A settings file from a later build (or edited by hand) must never leave
    the queue in a mode this build cannot explain."""
    assert normalize_repeat_mode(raw) in REPEAT_MODES


def test_normalizing_keeps_a_valid_mode() -> None:
    assert normalize_repeat_mode("all") == REPEAT_ALL
    assert normalize_repeat_mode("ALL") == REPEAT_ALL
    assert normalize_repeat_mode("one") == REPEAT_ONE
