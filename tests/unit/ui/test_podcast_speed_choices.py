"""The speed dropdown, and the bug where it disagreed with what was playing.

A show carries a speed as a number. The dropdown carried it as a string, and
derived one from the other with ``f"{speed:g}x"`` -- which turns 2.0 into
``"2x"`` while the list was spelled ``"2.0x"``. The lookup missed, the control
fell back to normal speed, and the episode carried on at 2x. The control was
lying about what you were hearing, which is the worst thing a control can do
for somebody who cannot see the waveform to check.

So: the values are the source of truth and the labels are derived from them.

The constants moved to ``core/podcasts/speed_choices.py`` under R21, which also
replaced the snap-to-nearest with a real Custom row -- snapping was honest until
Speed Up and Speed Down started stepping 0.05, after which it silently overwrote
a speed the listener had set with a key. The tests below follow them; the
snap-to-nearest ones become the Custom-row ones, because that is the same
question with the answer corrected.
"""

from __future__ import annotations

import pytest

from quill.core.podcasts.speed_choices import OFFERED as _SPEED_VALUES
from quill.core.podcasts.speed_choices import choices_for, index_for, speed_at

_SPEED_CHOICES = choices_for(1.0)


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
        assert speed_at(index_for(speed), speed) == speed

    def test_a_speed_that_is_not_offered_gets_its_own_row_instead_of_snapping(self):
        """R21. Snapping overwrote a speed the keyboard had set: 1.15 became 1.25.

        A speed the keys can reach and the list cannot now has a Custom row, and
        selecting it changes nothing.
        """
        assert index_for(0.9) == len(_SPEED_VALUES)
        assert speed_at(index_for(0.9), 0.9) == 0.9
        assert choices_for(2.4)[-1] == "2.4x (custom)"

    def test_a_speed_beyond_the_range_is_clamped_rather_than_invented(self):
        assert speed_at(index_for(9.0), 9.0) <= max(5.0, max(_SPEED_VALUES))
        assert speed_at(index_for(0.1), 0.1) >= 0.5

    def test_the_selection_is_read_back_as_a_number_not_a_string(self):
        """Parsing the label back was the other half of the same mistake."""
        import inspect

        from quill.ui.podcasts import manager_dialog

        source = inspect.getsource(manager_dialog.PodcastManagerDialog._on_speed_choice)
        # speed_at maps a row index to a number; the label is never parsed back.
        assert "speed_choices.speed_at(" in source
        assert 'rstrip("x")' not in source


def test_audio_studio_offers_the_same_range():
    """Two players in one suite that disagree about speed is a bug in waiting."""
    from quill.ui.audio_studio.player_panel import PLAYBACK_RATES

    assert tuple(PLAYBACK_RATES) == tuple(_SPEED_VALUES)
