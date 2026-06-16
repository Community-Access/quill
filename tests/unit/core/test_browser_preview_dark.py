from quill.core.browser_preview import render_preview_body, render_preview_html


def test_render_preview_body_light_has_no_dark_style() -> None:
    body = render_preview_body("# Title\n\nHello", "markdown")
    assert "background:#1e1e1e" not in body
    assert "<h1" in body


def test_render_preview_body_dark_injects_dark_stylesheet() -> None:
    # Issue #83: in dark mode the preview WebView must render dark too, so the
    # split view is not half dark, half bright.
    body = render_preview_body("# Title\n\nHello", "markdown", dark=True)
    assert "background:#1e1e1e" in body
    assert "color:#e6e6e6" in body
    # The rendered content still follows the injected style.
    assert "<h1" in body


def test_render_preview_body_dark_applies_to_html_and_plain() -> None:
    html_body = render_preview_body("<h1>Hi</h1>", "html", dark=True)
    assert "background:#1e1e1e" in html_body
    plain_body = render_preview_body("just text", "plain", dark=True)
    assert "background:#1e1e1e" in plain_body
    assert "<pre>" in plain_body


def test_render_preview_html_adapts_links_for_dark_browsers() -> None:
    # Issue #126: the standalone browser preview must follow the OS colour
    # scheme so links are not the default blue (which fails contrast) on a dark
    # background.
    page = render_preview_html("Doc", "[link](https://x)", "markdown")
    assert "color-scheme:light dark" in page
    assert "@media (prefers-color-scheme: dark)" in page
    # A light-blue link colour, not the default #0000ee, on dark backgrounds.
    assert "a{color:#6cb6ff;}" in page


def test_render_preview_html_includes_mathjax() -> None:
    page = render_preview_html("Doc", "$E = mc^2$", "markdown")
    assert "window.MathJax" in page
    assert "tex-mml-chtml.js" in page
    assert "inlineMath" in page


def test_export_markdown_to_html_includes_mathjax() -> None:
    from quill.io.export import markdown_to_html

    html_doc = markdown_to_html("$E = mc^2$", "Math Doc")
    assert "window.MathJax" in html_doc
    assert "tex-mml-chtml.js" in html_doc
