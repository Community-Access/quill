"""Message routing for the source-mapped side preview (#1257).

The heavy widget construction needs a WebView backend, so these tests exercise
the pure routing/injection surface without building a real control.
"""

from __future__ import annotations

from quill.ui.preview_dialog import _SOURCE_NAV_JS, SourceMappedSidePreview


def _bare_preview() -> SourceMappedSidePreview:
    # Skip __init__ (which builds an AccessibleWebView / needs a WebView backend);
    # we only want the message-routing methods.
    obj = SourceMappedSidePreview.__new__(SourceMappedSidePreview)
    return obj


def test_handle_message_forwards_goto_source() -> None:
    seen: list[dict] = []
    preview = _bare_preview()
    preview._on_goto_source = seen.append
    preview._handle_message({
        "type": "quill-goto-source",
        "trigger": "context",
        "src": 4,
        "label": "Intro",
    })
    assert seen == [{"type": "quill-goto-source", "trigger": "context", "src": 4, "label": "Intro"}]


def test_handle_message_ignores_other_types() -> None:
    seen: list[dict] = []
    preview = _bare_preview()
    preview._on_goto_source = seen.append
    preview._handle_message({"type": "__return"})
    preview._handle_message({"type": "something-else", "src": 1})
    assert seen == []


def test_handle_message_without_callback_is_safe() -> None:
    preview = _bare_preview()
    preview._on_goto_source = None
    # Must not raise even when nothing is wired up.
    preview._handle_message({"type": "quill-goto-source", "src": 0})


def test_injected_js_targets_the_bridge_and_data_src() -> None:
    # The listener must post through the AccessibleWebView bridge object and key
    # off the renderer's data-src attribute, and be idempotent across re-renders.
    assert "window.awv.postMessage" in _SOURCE_NAV_JS
    assert "data-src" in _SOURCE_NAV_JS
    assert "quill-goto-source" in _SOURCE_NAV_JS
    assert "__quillSrcNav" in _SOURCE_NAV_JS  # re-injection guard
    assert "contextmenu" in _SOURCE_NAV_JS
    assert "preventDefault" in _SOURCE_NAV_JS
