"""The speed chooser, and the Custom row (ear.md R21).

The dropdown offered nine values and snapped anything else to the nearest one.
Honest while the dropdown was the only way to set a speed; not once Speed Up and
Speed Down started stepping 0.05, because a show set to 1.15x by the keyboard
displayed as 1.25x and was *saved* as 1.25x the moment anything else on the page
changed. The control overwrote a value the listener had set with a key.
"""

from __future__ import annotations

from quill.core.podcasts.speed_choices import OFFERED, choices_for, index_for, speed_at


def test_an_offered_speed_needs_no_custom_row() -> None:
    for value in OFFERED:
        assert len(choices_for(value)) == len(OFFERED)
        assert index_for(value) == OFFERED.index(value)


def test_a_keyboard_set_speed_gets_its_own_row() -> None:
    labels = choices_for(1.15)
    assert len(labels) == len(OFFERED) + 1
    assert labels[-1] == "1.15x (custom)"
    assert index_for(1.15) == len(OFFERED)


def test_custom_goes_last_so_the_familiar_positions_never_shift() -> None:
    assert choices_for(1.15)[: len(OFFERED)] == choices_for(1.0)


def test_selecting_custom_changes_nothing() -> None:
    """It is a statement about the current speed, not a command."""
    assert speed_at(index_for(1.15), 1.15) == 1.15


def test_selecting_an_offered_row_means_that_speed() -> None:
    assert speed_at(0, 1.15) == OFFERED[0]
    assert speed_at(4, 1.15) == OFFERED[4]


def test_nothing_is_ever_snapped_to_a_neighbour() -> None:
    """The bug this module exists to stop: 1.15 must not resolve to 1.25."""
    assert speed_at(index_for(1.15), 1.15) != 1.25


def test_labels_are_derived_from_numbers_and_never_parsed_back() -> None:
    """2.0 formats as "2x"; a list spelled "2.0x" is how a show at 2x displayed
    as 1x while the episode carried on playing at 2x."""
    assert "2x" in choices_for(2.0)
    assert "2.0x" not in choices_for(2.0)


def test_an_out_of_range_speed_is_clamped_before_it_is_offered() -> None:
    assert index_for(99) == OFFERED.index(3.0) if 5.0 in OFFERED else index_for(99) == len(OFFERED)
    assert speed_at(index_for(99), 99) <= 5.0
