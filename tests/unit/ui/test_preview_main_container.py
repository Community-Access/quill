"""#1818: the side preview's content sits in a div with the main role, not <main>.

The side preview replaces its content with ``content.innerHTML = ...`` on every
update, and Internet Explorer's engine (wx.html2's fallback when Edge WebView2
is not chosen) refuses that on a ``<main>`` element with "Error: Unknown runtime
error". The page is built without a window here: ``_skeleton`` is plain string
work.
"""

from __future__ import annotations

import pytest

pytest.importorskip("wx_accessible_webview")

from quill.ui import preview_dialog  # noqa: E402


def _page() -> str:
    view_class = preview_dialog._PreviewWebView
    view = view_class.__new__(view_class)
    view._live_region = False
    view._handler_name = "quill"
    view._title = "Preview"
    view._lang = "en"
    view._styles = ""
    view._on_return = None
    view._escape_to_close = False
    view._open_links_externally = True
    return view._skeleton("<h1>Hello</h1>")


def test_the_content_is_a_div_with_the_main_role() -> None:
    page = _page()
    assert "<main" not in page and "</main>" not in page
    assert '<div role="main" id="content"' in page
    assert "<h1>Hello</h1>" in page


def test_the_update_script_still_finds_the_content_by_id() -> None:
    page = _page()
    assert "document.getElementById('content')" in page
    assert "content.innerHTML=h" in page


def test_the_side_preview_uses_it() -> None:
    import inspect

    source = inspect.getsource(preview_dialog.SourceMappedSidePreview.__init__)
    assert "_PreviewWebView(" in source
