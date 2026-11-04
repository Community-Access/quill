"""Contrast ratios and colour words (quill.core.wordpress.contrast)."""

from __future__ import annotations

import pytest

from quill.core.error_codes import CodedError
from quill.core.wordpress.contrast import (
    Colour,
    ColourParseError,
    contrast_ratio,
    describe_choice,
    format_ratio,
    nearest_colour_name,
    palette_report,
    parse_colour,
    rating,
    relative_luminance,
)

# -- parsing ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("#000", Colour(0, 0, 0)),
        ("#FFF", Colour(255, 255, 255)),
        ("#1a2b3c", Colour(0x1A, 0x2B, 0x3C)),
        ("1a2b3c", Colour(0x1A, 0x2B, 0x3C)),
        ("  #ABCDEF  ", Colour(0xAB, 0xCD, 0xEF)),
        ("rgb(10, 20, 30)", Colour(10, 20, 30)),
        ("RGB(10,20,30)", Colour(10, 20, 30)),
        ("rgb(100%, 0%, 50%)", Colour(255, 0, 128)),
        ("rgb(10 20 30)", Colour(10, 20, 30)),
        ("white", Colour(255, 255, 255)),
        ("DarkGreen", Colour(0, 100, 0)),
        ("rebeccapurple", Colour(0x66, 0x33, 0x99)),
        ("grey", Colour(128, 128, 128)),
    ],
)
def test_parse_opaque(text: str, expected: Colour) -> None:
    assert parse_colour(text) == expected


@pytest.mark.parametrize(
    ("text", "alpha"),
    [
        ("#00000080", 128 / 255),
        ("#0008", 0x88 / 255),
        ("rgba(0, 0, 0, 0.5)", 0.5),
        ("rgba(0,0,0,50%)", 0.5),
        ("rgb(0 0 0 / 25%)", 0.25),
    ],
)
def test_parse_alpha(text: str, alpha: float) -> None:
    assert parse_colour(text).alpha == pytest.approx(alpha)


@pytest.mark.parametrize("bad", ["", "#12", "#12345", "notacolour", "rgb(1,2)", "rgb(a,b,c)"])
def test_parse_rejects(bad: str) -> None:
    with pytest.raises(ColourParseError) as info:
        parse_colour(bad)
    assert isinstance(info.value, CodedError)
    assert isinstance(info.value, ValueError)
    assert info.value.code == "QUILL-WORDPRESS-CHECKS-BAD-COLOUR"


def test_parse_passes_a_colour_through() -> None:
    c = Colour(1, 2, 3)
    assert parse_colour(c) is c


def test_hex_round_trip() -> None:
    assert parse_colour("#AbC").hex() == "#aabbcc"


# -- luminance and ratio ------------------------------------------------------------


def test_luminance_extremes() -> None:
    assert relative_luminance("#000") == 0.0
    assert relative_luminance("#fff") == pytest.approx(1.0)


def test_black_on_white_is_21() -> None:
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)


def test_ratio_is_symmetric() -> None:
    assert contrast_ratio("#ffffff", "#000000") == pytest.approx(21.0)


def test_same_colour_is_1() -> None:
    assert contrast_ratio("#336699", "#336699") == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("fg", "bg", "expected"),
    [
        ("#777777", "#ffffff", 4.48),
        ("#767676", "#ffffff", 4.54),
        ("#0000ff", "#ffffff", 8.59),
        ("#ff0000", "#ffffff", 4.00),
        ("#006400", "#ffffff", 7.44),
    ],
)
def test_known_pairs(fg: str, bg: str, expected: float) -> None:
    assert contrast_ratio(fg, bg) == pytest.approx(expected, abs=0.01)


def test_translucent_foreground_is_composited() -> None:
    # Half-transparent black on white reads as mid grey.
    assert contrast_ratio("rgba(0,0,0,0.5)", "#fff") == pytest.approx(
        contrast_ratio("#808080", "#fff"), abs=0.05
    )


def test_fully_transparent_foreground_vanishes() -> None:
    assert contrast_ratio("rgba(0,0,0,0)", "#123456") == pytest.approx(1.0)


# -- rating and formatting ----------------------------------------------------------


@pytest.mark.parametrize(
    ("ratio", "large", "expected"),
    [
        (21.0, False, "passes"),
        (4.5, False, "passes"),
        (4.49, False, "passes for large text only"),
        (3.0, False, "passes for large text only"),
        (2.99, False, "too faint for text"),
        (3.0, True, "passes"),
        (2.99, True, "too faint for text"),
        (1.0, True, "too faint for text"),
    ],
)
def test_rating(ratio: float, large: bool, expected: str) -> None:
    assert rating(ratio, large_text=large) == expected


@pytest.mark.parametrize(
    ("ratio", "text"),
    [(21.0, "21 to 1"), (7.24, "7.2 to 1"), (4.48, "4.4 to 1"), (4.5, "4.5 to 1"), (1.0, "1 to 1")],
)
def test_format_ratio_rounds_down(ratio: float, text: str) -> None:
    assert format_ratio(ratio) == text


# -- colour words -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("colour", "word"),
    [
        ("#000000", "black"),
        ("#ffffff", "white"),
        ("#777777", "grey"),
        ("#333333", "dark grey"),
        ("#dddddd", "light grey"),
        ("#006400", "dark green"),
        ("#2e7d32", "green"),
        ("#90ee90", "light green"),
        ("#ffffcc", "pale yellow"),
        ("#ffff00", "yellow"),
        ("#ff0000", "red"),
        ("#8b0000", "dark red"),
        ("#ffa500", "orange"),
        ("#8b4513", "brown"),
        ("#3e1f0a", "dark brown"),
        ("navy", "dark blue"),
        ("#0000ff", "blue"),
        ("#add8e6", "light blue"),
        ("#008080", "dark teal"),
        ("#20b2aa", "teal"),
        ("#800080", "dark purple"),
        ("#9932cc", "purple"),
        ("#ffc0cb", "pale pink"),
        ("#ff69b4", "light pink"),
        ("#708090", "greyish blue"),
    ],
)
def test_nearest_colour_name(colour: str, word: str) -> None:
    assert nearest_colour_name(colour) == word


# -- describe and report --------------------------------------------------------------


def test_describe_choice_with_name() -> None:
    assert (
        describe_choice("Accent", "#006400", "#ffffff") == "Accent (dark green), 7.4 to 1, passes"
    )


def test_describe_choice_name_already_the_colour_word() -> None:
    assert describe_choice("Pale yellow", "#ffffcc", "#fff") == (
        "Pale yellow, 1 to 1, too faint for text"
    )


def test_describe_choice_without_name() -> None:
    assert describe_choice("", "#777", "#fff") == "Grey, 4.4 to 1, passes for large text only"


def test_palette_report_every_pairing() -> None:
    palette = [("Primary", "#000000"), ("Accent", "#006400"), ("Base", "#ffffff")]
    backgrounds = [("Base", "#ffffff"), ("Contrast", "#000000")]
    lines = palette_report(palette, backgrounds)
    assert lines == [
        "Primary (black) on Base (white), 21 to 1, passes",
        "Accent (dark green) on Base (white), 7.4 to 1, passes",
        # Primary on Contrast is black on black: the colour on itself, left out.
        "Accent (dark green) on Contrast (black), 2.8 to 1, too faint for text",
        "Base (white) on Contrast (black), 21 to 1, passes",
    ]


def test_palette_report_skips_a_colour_on_itself() -> None:
    lines = palette_report([("Base", "#fff")], [("Base", "#ffffff")])
    assert lines == []


def test_palette_report_empty() -> None:
    assert palette_report([], [("Base", "#fff")]) == []
    assert palette_report([("A", "#000")], []) == []
