"""The speed dropdown, and the bug where it disagreed with what was playing.

A show carries a speed as a number. The dropdown carried it as a string, and
derived one from the other with ``f"{speed:g}x"`` -- which turns 2.0 into
``"2x"`` while the list was spelled ``"2.0x"``. The lookup missed, the control
fell back to normal speed, and the episode carried on at 2x. The control was
lying about what you were hearing, which is the worst thing a control can do
for somebody who cannot see the waveform to check.

So: the values are the source of truth and the labels are derived from them.
"""

from __future__ import annotations

import pytest

from quill.ui.podcasts.manager_dialog import (
    _SPEED_CHOICES,
    _SPEED_VALUES,
    _nearest_speed_index,
)


class TestTheOfferedSpeeds:
    def test_faster_than_two_times_is_offered(self):
        """The model always permitted it; only the dropdown stopped at 2x."""
        from quill.core.podcasts.models_settings import SPEED_MAX, SPEED_MIN

        assert max(_SPEED_VALUES) > 2.0
        assert min(_SPEED_VALUES) < 0.75, "slow matters as much as fast"
        assert SPEED_MIN <= min(_SPEED_VALUES)
        assert max(_SPEED_VALUES) <= SPEED_MAX

    def test_normal_speed_is_always_there(self):
        assert 1.0 in _SPEED_VALUES

    def test_they_are_in_order_with_no_repeats(self):
        assert list(_SPEED_VALUES) == sorted(set(_SPEED_VALUES))

    def test_a_label_exists_for_every_value(self):
        assert len(_SPEED_CHOICES) == len(_SPEED_VALUES)

    def test_the_labels_read_cleanly(self):
        """Spoken aloud, so no trailing zero on a whole number."""
        assert "1x" in _SPEED_CHOICES
        assert "2x" in _SPEED_CHOICES
        assert "1.25x" in _SPEED_CHOICES
        assert not any(label.endswith(".0x") for label in _SPEED_CHOICES)


class TestFindingTheRightRow:
    @pytest.mark.parametrize("speed", list(_SPEED_VALUES))
    def test_every_offered_speed_finds_itself(self, speed):
        """The regression: 2.0 used to land on 1.0x while playing at 2x."""
        assert _SPEED_VALUES[_nearest_speed_index(speed)] == speed

    def test_a_speed_that_is_not_offered_snaps_to_the_nearest(self):
        """A show may carry any speed the model allows, typed in elsewhere."""
        assert _SPEED_VALUES[_nearest_speed_index(0.9)] == 1.0
        assert _SPEED_VALUES[_nearest_speed_index(2.4)] == 2.5

    def test_a_speed_beyond_the_list_lands_at_the_end_not_at_normal(self):
        assert _SPEED_VALUES[_nearest_speed_index(5.0)] == max(_SPEED_VALUES)
        assert _SPEED_VALUES[_nearest_speed_index(0.1)] == min(_SPEED_VALUES)

    def test_the_selection_is_read_back_as_a_number_not_a_string(self):
        """Parsing the label back was the other half of the same mistake."""
        import inspect

        from quill.ui.podcasts import manager_dialog

        source = inspect.getsource(manager_dialog.PodcastManagerDialog._on_speed_choice)
        assert "_SPEED_VALUES[" in source
        assert 'rstrip("x")' not in source


def test_audio_studio_offers_the_same_range():
    """Two players in one suite that disagree about speed is a bug in waiting."""
    from quill.ui.audio_studio.player_panel import PLAYBACK_RATES

    assert tuple(PLAYBACK_RATES) == tuple(_SPEED_VALUES)
