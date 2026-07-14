from __future__ import annotations

from quill.core.heading_styles import HeadingStyle, apply_heading_style


def test_apply_heading_style_to_markdown_all_levels() -> None:
    source = "# Title\n## Child\nBody\n"
    updated, changed = apply_heading_style(
        source,
        markup_kind="markdown",
        style=HeadingStyle(font_family="Calibri", font_size_pt=20, text_align="center"),
        levels={1, 2},
    )
    assert changed == 2
    assert (
        '<h1 style="font-family: Calibri; font-size: 20pt; text-align: center">Title</h1>'
        in updated
    )
    assert (
        '<h2 style="font-family: Calibri; font-size: 20pt; text-align: center">Child</h2>'
        in updated
    )


def test_apply_heading_style_to_markdown_specific_level() -> None:
    source = "# Title\n## Child\n"
    updated, changed = apply_heading_style(
        source,
        markup_kind="markdown",
        style=HeadingStyle(text_align="right"),
        levels={2},
    )
    assert changed == 1
    assert "# Title" in updated
    assert '<h2 style="text-align: right">Child</h2>' in updated


def test_apply_heading_style_to_html_preserves_other_attributes() -> None:
    source = '<h2 id="intro" style="color: red; font-size: 12pt">Hello</h2>'
    updated, changed = apply_heading_style(
        source,
        markup_kind="html",
        style=HeadingStyle(font_family="Arial", font_size_pt=18, text_align="left"),
        levels={2},
    )
    assert changed == 1
    assert 'id="intro"' in updated
    assert 'style="color: red; font-size: 18pt; font-family: Arial; text-align: left"' in updated


def test_apply_heading_style_returns_original_when_no_style_requested() -> None:
    source = "# Title\n"
    updated, changed = apply_heading_style(
        source,
        markup_kind="markdown",
        style=HeadingStyle(),
        levels={1},
    )
    assert updated == source
    assert changed == 0


def test_text_align_rejects_css_injection() -> None:
    source = "# Title\n"
    updated, changed = apply_heading_style(
        source,
        markup_kind="markdown",
        style=HeadingStyle(font_family="Calibri", text_align="red; }body{display:none}"),
        levels={1},
    )
    assert changed == 1
    assert "display:none" not in updated
    assert "text-align" not in updated
    assert "font-family: Calibri" in updated


def test_font_family_is_html_escaped() -> None:
    source = "# Title\n"
    updated, changed = apply_heading_style(
        source,
        markup_kind="markdown",
        style=HeadingStyle(font_family='Arial"><script>alert(1)</script>'),
        levels={1},
    )
    assert changed == 1
    assert "<script>" not in updated
    assert "&lt;script&gt;" in updated
