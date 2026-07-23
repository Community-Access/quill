"""Tests for inline image alt-text descriptions (#899)."""

from __future__ import annotations

from quill.core.inline_image_alt import (
    build_image_html,
    build_image_markdown,
    describe_image,
    image_at_position,
)


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


def test_build_image_html_basic_has_alt_and_lazy_by_default() -> None:
    html = build_image_html("cat.png", "a sleeping cat")
    assert html == '<img src="cat.png" alt="a sleeping cat" loading="lazy" />'


def test_build_image_html_decorative_is_empty_alt_and_presentation_role() -> None:
    html = build_image_html("divider.png", "ignored", decorative=True)
    assert 'alt=""' in html
    assert 'role="presentation"' in html


def test_build_image_html_dimensions_prevent_layout_shift() -> None:
    html = build_image_html("cat.png", "a cat", width=640, height=480)
    assert 'width="640"' in html
    assert 'height="480"' in html


def test_build_image_html_responsive_caps_width() -> None:
    html = build_image_html("cat.png", "a cat", responsive=True)
    assert 'style="max-width:100%;height:auto;"' in html


def test_build_image_html_caption_wraps_in_figure() -> None:
    html = build_image_html("cat.png", "a cat", caption="Our office cat")
    assert html.startswith("<figure>")
    assert "<figcaption>Our office cat</figcaption>" in html
    assert html.strip().endswith("</figure>")


def test_build_image_html_escapes_attribute_and_caption() -> None:
    html = build_image_html('a&b".png', 'quote " and & amp', caption="1 < 2 & 3 > 0")
    assert "&quot;" in html and "&amp;" in html
    assert "&lt; 2 &amp; 3 &gt;" in html
    # A raw double-quote must never survive inside an attribute value.
    assert 'alt="quote " and' not in html


def test_build_image_html_can_disable_lazy() -> None:
    html = build_image_html("cat.png", "a cat", lazy=False)
    assert "loading=" not in html
