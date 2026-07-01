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


def test_render_preview_html_never_emits_a_refresh_tag() -> None:
    # A preview page must never force-reload itself on a timer. The old
    # <meta http-equiv="refresh"> poll re-rendered the whole page once a
    # second, which flickered the tab and, for a screen-reader/braille user
    # reading the preview, re-announced from the top constantly. The external
    # browser preview now reloads only when the user re-runs the command, and
    # the in-app preview is updated by pushing fresh HTML to the WebView.
    page = render_preview_html("Doc", "hello", "markdown")
    assert "http-equiv" not in page
    assert "refresh" not in page.lower()
