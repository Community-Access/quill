"""Tests for the Header/Footer Builder's core token model (#892)."""

from __future__ import annotations

from quill.core.header_footer import (
    PRESETS,
    HeaderFooterSpec,
    PageNumberStyle,
    page_number_text,
    render_zone,
)


def test_page_number_text_arabic() -> None:
    assert page_number_text(4, PageNumberStyle.ARABIC) == "4"


def test_page_number_text_roman() -> None:
    assert page_number_text(4, PageNumberStyle.ROMAN) == "IV"
    assert page_number_text(9, PageNumberStyle.ROMAN) == "IX"
    assert page_number_text(1, PageNumberStyle.ROMAN) == "I"


def test_page_number_text_roman_clamps_below_one() -> None:
    assert page_number_text(0, PageNumberStyle.ROMAN) == "I"


def test_render_zone_substitutes_all_tokens() -> None:
    result = render_zone(
        "{title} - {filename} - {date} - page {page}",
        title="My Report",
        filename="report.md",
        date="2026-07-08",
        page_number=3,
    )
    assert result == "My Report - report.md - 2026-07-08 - page 3"


def test_render_zone_roman_page_number() -> None:
    result = render_zone("{page}", page_number=5, page_number_style=PageNumberStyle.ROMAN)
    assert result == "V"


def test_render_zone_literal_text_with_no_tokens() -> None:
    assert render_zone("Confidential") == "Confidential"


def test_blank_preset_has_no_tokens_anywhere() -> None:
    spec = PRESETS["Blank"]
    assert spec == HeaderFooterSpec()


def test_title_left_page_right_preset() -> None:
    spec = PRESETS["Title left, page number right"]
    assert spec.header_left == "{title}"
    assert spec.footer_right == "{page}"
    assert spec.footer_left == ""


def test_filename_and_date_preset() -> None:
    spec = PRESETS["Filename and date"]
    assert spec.footer_left == "{filename}"
    assert spec.footer_right == "{date}"


def test_roman_numerals_preset_uses_roman_style() -> None:
    spec = PRESETS["Roman numerals for front matter"]
    assert spec.page_number_style == PageNumberStyle.ROMAN
    assert spec.footer_center == "{page}"


def test_first_page_different_defaults_to_false() -> None:
    assert HeaderFooterSpec().first_page_different is False


def test_start_page_number_defaults_to_one() -> None:
    assert HeaderFooterSpec().start_page_number == 1
