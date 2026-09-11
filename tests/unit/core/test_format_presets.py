"""The fixed choices the Format menu offers, checkable without a display.

They were menu code until 2026-09-10 and are data now, which is the whole point
of the move: "no two colours share a name" and "every spacing preset comes in a
before/after pair" are assertions about a tuple, and neither needed a menu bar to
make. A duplicate in any of these lists is a menu row that reads identically to
the one above it and does something different -- invisible on screen, and
indistinguishable to a listener.
"""

from __future__ import annotations

import pytest

from quill.core.format_presets import (
    COLOR_PRESETS,
    FONT_PRESETS,
    HIGHLIGHT_PRESETS,
    INDENT_PRESETS,
    NAMED_STYLE_PRESETS,
    SIZE_PRESETS,
    SPACING_PRESETS,
)

_PAIRED = {
    "colors": COLOR_PRESETS,
    "highlights": HIGHLIGHT_PRESETS,
    "named styles": NAMED_STYLE_PRESETS,
}


@pytest.mark.parametrize(("name", "presets"), sorted(_PAIRED.items()))
def test_no_two_rows_share_a_label(name: str, presets: tuple) -> None:
    """Two rows reading alike is a menu a listener cannot tell apart."""
    labels = [label for label, *_rest in presets]
    assert len(set(labels)) == len(labels), name


@pytest.mark.parametrize(("name", "presets"), sorted(_PAIRED.items()))
def test_no_two_rows_share_a_value(name: str, presets: tuple) -> None:
    """Two labels for one value is two ways to do the same thing."""
    values = [value for _label, value, *_rest in presets]
    assert len(set(values)) == len(values), name


def test_fonts_are_distinct_and_named() -> None:
    assert len(set(FONT_PRESETS)) == len(FONT_PRESETS)
    assert all(family.strip() for family in FONT_PRESETS)


def test_sizes_are_distinct_and_ascending() -> None:
    """A size list out of order is one nobody can scan."""
    assert list(SIZE_PRESETS) == sorted(set(SIZE_PRESETS))


def test_every_size_is_a_plausible_point_size() -> None:
    assert all(isinstance(points, int) and 4 <= points <= 200 for points in SIZE_PRESETS)


def test_every_colour_is_a_six_digit_hex() -> None:
    """The renderer writes it verbatim; a typo is a colour nothing shows."""
    for name, value in COLOR_PRESETS:
        assert value.startswith("#") and len(value) == 7, name
        int(value[1:], 16)


def test_highlights_are_named_colours_not_hex() -> None:
    """Word's and RTF's highlight attributes take a name, not a value."""
    assert all(not value.startswith("#") for _name, value in HIGHLIGHT_PRESETS)


def test_paragraph_spacing_comes_in_before_and_after_pairs() -> None:
    before = {points for _label, kind, points in SPACING_PRESETS if kind == "before"}
    after = {points for _label, kind, points in SPACING_PRESETS if kind == "after"}
    assert before == after and before, (before, after)


def test_every_spacing_row_says_what_it_does_in_its_label() -> None:
    """The label is all a listener gets; "6 points" alone would not say of what."""
    for label, kind, points in SPACING_PRESETS:
        assert kind in label.lower(), label
        assert str(points) in label, label


def test_indent_rows_name_their_kind_and_amount() -> None:
    for label, kind, points in INDENT_PRESETS:
        assert str(points) in label, label
        assert ("first" in label.lower()) == (kind == "first"), label


@pytest.mark.parametrize(
    "presets",
    [
        FONT_PRESETS,
        SIZE_PRESETS,
        COLOR_PRESETS,
        HIGHLIGHT_PRESETS,
        NAMED_STYLE_PRESETS,
        SPACING_PRESETS,
        INDENT_PRESETS,
    ],
)
def test_every_list_is_a_tuple_and_not_empty(presets: tuple) -> None:
    """Immutable, because a menu built from a list somebody appended to at
    runtime is a menu whose rows differ between two windows."""
    assert isinstance(presets, tuple)
    assert presets
