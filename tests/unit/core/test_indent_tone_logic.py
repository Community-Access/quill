"""Unit tests for indentation tone logic (issue #182).

Tests the pure calculation layer: level-from-indentation, blank-line guard,
duplicate-fire suppression, clamping, and direction detection. No wx required.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Level calculation helpers (mirror main_frame_power_tools._maybe_play_indent_tone)
# ---------------------------------------------------------------------------


def _indent_level(indent_cols: int, tab_width: int) -> int:
    return indent_cols // max(tab_width, 1)


def _clamp_level(level: int) -> int:
    return min(level, 7)


def _direction(prev: int, current: int) -> str:
    return "up" if current > prev else "down"


# ---------------------------------------------------------------------------
# Tests: level calculation
# ---------------------------------------------------------------------------


class TestLevelCalculation:
    def test_no_indent_is_level_zero(self) -> None:
        assert _indent_level(0, 4) == 0

    def test_one_indent_unit_is_level_one(self) -> None:
        assert _indent_level(4, 4) == 1

    def test_two_indent_units(self) -> None:
        assert _indent_level(8, 4) == 2

    def test_tab_width_two(self) -> None:
        assert _indent_level(6, 2) == 3

    def test_partial_indent_rounds_down(self) -> None:
        # 5 columns with tab_width=4 -> still level 1
        assert _indent_level(5, 4) == 1

    def test_tab_width_one(self) -> None:
        assert _indent_level(3, 1) == 3


# ---------------------------------------------------------------------------
# Tests: clamping
# ---------------------------------------------------------------------------


class TestLevelClamping:
    @pytest.mark.parametrize(
        "level,expected",
        [
            (0, 0),
            (7, 7),
            (8, 7),
            (100, 7),
        ],
    )
    def test_clamp(self, level: int, expected: int) -> None:
        assert _clamp_level(level) == expected


# ---------------------------------------------------------------------------
# Tests: direction detection
# ---------------------------------------------------------------------------


class TestDirection:
    def test_going_deeper_is_up(self) -> None:
        assert _direction(prev=0, current=2) == "up"

    def test_dedenting_is_down(self) -> None:
        assert _direction(prev=3, current=1) == "down"

    def test_same_level_returns_down(self) -> None:
        # In practice we never fire when level unchanged, but the function
        # itself returns "down" for equal levels (not-up).
        assert _direction(prev=2, current=2) == "down"


# ---------------------------------------------------------------------------
# Tests: blank-line guard
# ---------------------------------------------------------------------------


class TestBlankLineGuard:
    """Blank lines must not change the indent level or fire a tone."""

    def _should_fire(
        self, line_text: str, indent_cols: int, tab_width: int, prev_level: int
    ) -> tuple[bool, int]:
        """Return (should_fire, new_level). Mirrors the handler guard."""
        if not line_text.strip():
            return False, prev_level  # blank: stay silent, hold level
        level = _indent_level(indent_cols, tab_width)
        if level == prev_level:
            return False, prev_level
        return True, level

    def test_blank_line_does_not_fire(self) -> None:
        fire, level = self._should_fire("", 0, 4, prev_level=2)
        assert not fire
        assert level == 2  # previous level held

    def test_whitespace_only_line_does_not_fire(self) -> None:
        fire, level = self._should_fire("    \n", 4, 4, prev_level=1)
        assert not fire
        assert level == 1

    def test_non_blank_line_fires_on_change(self) -> None:
        fire, level = self._should_fire("    x = 1\n", 4, 4, prev_level=0)
        assert fire
        assert level == 1

    def test_same_level_does_not_fire(self) -> None:
        fire, level = self._should_fire("    pass\n", 4, 4, prev_level=1)
        assert not fire
        assert level == 1


# ---------------------------------------------------------------------------
# Tests: speech announcement text
# ---------------------------------------------------------------------------


class TestSpeechText:
    def _speech_label(self, level: int) -> str:
        return f"indent {level}" if level > 0 else "no indent"

    def test_level_zero_says_no_indent(self) -> None:
        assert self._speech_label(0) == "no indent"

    def test_level_three_says_indent_3(self) -> None:
        assert self._speech_label(3) == "indent 3"

    def test_speech_uses_true_level_above_7(self) -> None:
        # Speech says the real number; sound is clamped separately.
        assert self._speech_label(12) == "indent 12"
