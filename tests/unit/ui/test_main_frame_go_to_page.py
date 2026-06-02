"""Source-contract test for go_to_page migration to show_web_form (DLG-1).

The live wx.Dialog is not runtime-instantiated in tests; the repo validates
dialog wiring through source contracts. This asserts that go_to_page now uses
show_web_form instead of wx.TextEntryDialog.
"""

from __future__ import annotations

from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)


def test_go_to_page_imports_show_web_form() -> None:
    # The go_to_page method must import show_web_form from web_form module
    assert "def go_to_page(self)" in SOURCE
    go_to_page_start = SOURCE.index("def go_to_page(self)")
    # Find next method after go_to_page
    go_to_page_end = SOURCE.index("def open_quick_nav(self)")
    go_to_page_body = SOURCE[go_to_page_start:go_to_page_end]
    assert "from quill.ui.web_form import show_web_form" in go_to_page_body


def test_go_to_page_uses_web_form() -> None:
    # The go_to_page method must call show_web_form, not wx.TextEntryDialog
    go_to_page_start = SOURCE.index("def go_to_page(self)")
    go_to_page_end = SOURCE.index("def open_quick_nav(self)")
    go_to_page_body = SOURCE[go_to_page_start:go_to_page_end]

    assert "show_web_form(" in go_to_page_body
    assert 'title="Go To Page"' in go_to_page_body
    assert 'save_label="Go"' in go_to_page_body
    assert '"page_number"' in go_to_page_body

    # Must NOT use old wx.TextEntryDialog pattern
    assert "wx.TextEntryDialog" not in go_to_page_body


def test_go_to_page_preserves_behavior() -> None:
    # The method must preserve the original behavior:
    # - Get page starts from text
    # - Show page count in intro
    # - Default value "1"
    # - Handle cancellation (values is None)
    # - Parse page number
    # - Validate page range
    # - Move to position and announce
    go_to_page_start = SOURCE.index("def go_to_page(self)")
    go_to_page_end = SOURCE.index("def open_quick_nav(self)")
    go_to_page_body = SOURCE[go_to_page_start:go_to_page_end]

    assert "starts = page_starts(text)" in go_to_page_body
    assert "if values is None:" in go_to_page_body
    assert "int(" in go_to_page_body
    assert "except ValueError:" in go_to_page_body
    assert "page_start_for_number(text, page_num)" in go_to_page_body
    assert "if target is None:" in go_to_page_body
    assert "self._move_point(target)" in go_to_page_body
    assert "self.editor.SetFocus()" in go_to_page_body
    assert 'f"Moved to page {page_num}"' in go_to_page_body
