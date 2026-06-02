"""Source-contract test for go_to_line migration to show_web_form (DLG-1).

The live wx.Dialog is not runtime-instantiated in tests; the repo validates
dialog wiring through source contracts. This asserts that go_to_line now uses
show_web_form instead of wx.TextEntryDialog.
"""

from __future__ import annotations

from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)


def test_go_to_line_imports_show_web_form() -> None:
    # The go_to_line method must import show_web_form from web_form module
    assert "def go_to_line(self)" in SOURCE
    go_to_line_start = SOURCE.index("def go_to_line(self)")
    go_to_line_end = SOURCE.index("def go_to_page(self)")
    go_to_line_body = SOURCE[go_to_line_start:go_to_line_end]
    assert "from quill.ui.web_form import show_web_form" in go_to_line_body


def test_go_to_line_uses_web_form() -> None:
    # The go_to_line method must call show_web_form, not wx.TextEntryDialog
    go_to_line_start = SOURCE.index("def go_to_line(self)")
    go_to_line_end = SOURCE.index("def go_to_page(self)")
    go_to_line_body = SOURCE[go_to_line_start:go_to_line_end]

    assert "show_web_form(" in go_to_line_body
    assert 'title="Go To Line"' in go_to_line_body
    assert 'save_label="Go"' in go_to_line_body
    assert '"line_ref"' in go_to_line_body

    # Must NOT use old wx.TextEntryDialog pattern
    assert "wx.TextEntryDialog" not in go_to_line_body


def test_go_to_line_preserves_behavior() -> None:
    # The method must preserve the original behavior:
    # - Default value "1"
    # - Handle cancellation (values is None)
    # - Parse line,column format
    # - Validate line and column numbers
    # - Move to position and announce
    go_to_line_start = SOURCE.index("def go_to_line(self)")
    go_to_line_end = SOURCE.index("def go_to_page(self)")
    go_to_line_body = SOURCE[go_to_line_start:go_to_line_end]

    assert "if values is None:" in go_to_line_body
    assert "parse_line_column(" in go_to_line_body
    assert "except ValueError:" in go_to_line_body
    assert "if target_line < 1:" in go_to_line_body
    assert "if target_column is not None and target_column < 1:" in go_to_line_body
    assert "self._move_point(insertion_point)" in go_to_line_body
    assert "self.editor.SetFocus()" in go_to_line_body
    assert 'f"Moved to line {target_line}"' in go_to_line_body
