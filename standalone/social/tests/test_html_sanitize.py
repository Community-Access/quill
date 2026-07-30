"""HTML sanitizer: safe, readable article text from untrusted feed HTML."""

from __future__ import annotations

from quill_social.services.html_sanitize import sanitize_to_text


def test_drops_script_and_style_content():
    html = (
        "<p>Real body.</p>"
        "<script>alert('xss'); var steal=1;</script>"
        "<style>.a{color:red}</style>"
        "<p>More body.</p>"
    )
    out = sanitize_to_text(html)
    assert "Real body." in out
    assert "More body." in out
    # The dangerous element *content* must not leak into the text.
    assert "alert" not in out
    assert "xss" not in out
    assert "color:red" not in out


def test_inlines_links_and_images():
    html = '<p>See <a href="https://x.example/a">the docs</a>.</p><img src="i.png" alt="A chart">'
    out = sanitize_to_text(html)
    assert "the docs (https://x.example/a)" in out
    assert "[Image: A chart]" in out


def test_resolves_relative_link_against_base():
    out = sanitize_to_text('<a href="/page">Page</a>', base_url="https://site.example/blog/")
    assert "Page (https://site.example/page)" in out


def test_image_without_alt():
    assert "[Image]" in sanitize_to_text('<img src="x.png">')


def test_block_structure_becomes_line_breaks():
    out = sanitize_to_text("<h2>Heading</h2><p>Para one.</p><ul><li>a</li><li>b</li></ul>")
    assert "Heading" in out
    assert "Para one." in out
    assert "- a" in out and "- b" in out


def test_plain_text_passthrough_and_empty():
    assert sanitize_to_text("just text") == "just text"
    assert sanitize_to_text("") == ""


def test_malformed_does_not_raise():
    assert isinstance(sanitize_to_text("<p>oops <a href="), str)
