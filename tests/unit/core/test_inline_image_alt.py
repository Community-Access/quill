"""Tests for inline image alt-text descriptions (#899)."""

from __future__ import annotations

from quill.core.inline_image_alt import build_image_markdown, describe_image, image_at_position


def test_image_at_position_finds_markdown_image_with_alt_text() -> None:
    text = "Look at this: ![a sunset over the lake](sunset.png) it's nice."
    pos = text.index("sunset.png")
    record = image_at_position(text, pos)
    assert record is not None
    assert record.source == "sunset.png"
    assert record.alt_text == "a sunset over the lake"


def test_image_at_position_finds_markdown_image_with_missing_alt_text() -> None:
    text = "![](photo.jpg)"
    record = image_at_position(text, 2)
    assert record is not None
    assert record.alt_text == ""


def test_image_at_position_returns_none_outside_any_image() -> None:
    text = "Just a paragraph, no images here."
    assert image_at_position(text, 5) is None


def test_image_at_position_finds_html_image_with_alt_attribute() -> None:
    text = '<img src="cat.png" alt="a sleeping cat">'
    record = image_at_position(text, 10)
    assert record is not None
    assert record.source == "cat.png"
    assert record.alt_text == "a sleeping cat"


def test_image_at_position_html_image_missing_alt_attribute() -> None:
    text = '<img src="cat.png">'
    record = image_at_position(text, 5)
    assert record is not None
    assert record.alt_text == ""


def test_image_at_position_html_image_without_src_is_ignored() -> None:
    text = '<img alt="orphan">'
    assert image_at_position(text, 5) is None


def test_describe_image_reports_present_alt_text() -> None:
    record = image_at_position("![a cat](path/to/cat.png)", 5)
    assert record is not None
    assert describe_image(record) == "Image: cat.png, alt text: a cat"


def test_describe_image_reports_missing_alt_text_loudly() -> None:
    record = image_at_position("![](cat.png)", 2)
    assert record is not None
    assert describe_image(record) == "Image: cat.png, alt text MISSING"


def test_build_image_markdown_includes_alt_text() -> None:
    assert build_image_markdown("cat.png", "a sleeping cat") == "![a sleeping cat](cat.png)"


def test_build_image_markdown_decorative_is_empty_alt() -> None:
    result = build_image_markdown("divider.png", "ignored text", decorative=True)
    assert result == "![](divider.png)"


def test_build_image_markdown_strips_whitespace() -> None:
    assert build_image_markdown("cat.png", "  a cat  ") == "![a cat](cat.png)"
