"""Tests for podcast show-notes HTML-to-plain-text conversion and the
image-stripping sanitizer (pure functions, no network)."""

from __future__ import annotations

from quill.core.podcasts.show_notes import html_to_plain_text, strip_html_images


def test_html_to_plain_text_returns_plain_input_unchanged() -> None:
    assert html_to_plain_text("Just plain text, no markup.") == "Just plain text, no markup."


def test_html_to_plain_text_strips_tags() -> None:
    result = html_to_plain_text("<p>Hello <b>world</b></p>")
    assert result == "Hello world"


def test_html_to_plain_text_paragraphs_become_real_newlines() -> None:
    html = "<p>First paragraph.</p><p>Second paragraph.</p>"
    result = html_to_plain_text(html)
    assert result == "First paragraph.\nSecond paragraph."


def test_html_to_plain_text_br_becomes_newline() -> None:
    html = "Line one<br>Line two"
    result = html_to_plain_text(html)
    assert result == "Line one\nLine two"


def test_html_to_plain_text_list_items_become_lines() -> None:
    html = "<ul><li>First</li><li>Second</li></ul>"
    result = html_to_plain_text(html)
    assert result.splitlines() == ["First", "Second"]


def test_html_to_plain_text_links_become_text_with_url_in_parens() -> None:
    html = '<p>Check out <a href="https://example.com">our site</a> for more.</p>'
    result = html_to_plain_text(html)
    assert result == "Check out our site (https://example.com) for more."


def test_html_to_plain_text_link_without_href_has_no_parens() -> None:
    html = '<a name="anchor">Anchor text</a>'
    result = html_to_plain_text(html)
    assert result == "Anchor text"


def test_html_to_plain_text_collapses_blank_line_runs() -> None:
    html = "<p>First</p><p></p><p></p><p>Second</p>"
    result = html_to_plain_text(html)
    assert result == "First\nSecond"


def test_html_to_plain_text_tolerates_malformed_markup() -> None:
    html = "<p>Unclosed paragraph <b>bold text"
    result = html_to_plain_text(html)
    assert "Unclosed paragraph" in result
    assert "bold text" in result


def test_strip_html_images_removes_img_tags() -> None:
    html = '<p>Text</p><img src="https://example.com/tracker.png"><p>More text</p>'
    result = strip_html_images(html)
    assert "<img" not in result
    assert "Text" in result and "More text" in result


def test_strip_html_images_handles_self_closing_and_attributes() -> None:
    html = '<img src="a.png" alt="desc" />text<img src="b.png">'
    result = strip_html_images(html)
    assert "<img" not in result
    assert "text" in result


def test_strip_html_images_no_images_returns_unchanged() -> None:
    html = "<p>No images here.</p>"
    assert strip_html_images(html) == html
