"""Source-contract test for set_bookmark migration to show_web_form (DLG-1).

The live wx.Dialog is not runtime-instantiated in tests; the repo validates
dialog wiring through source contracts. This asserts that set_bookmark now uses
show_web_form instead of wx.TextEntryDialog.
"""

from __future__ import annotations

from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)


def test_set_bookmark_imports_show_web_form() -> None:
    # The set_bookmark method must import show_web_form from web_form module
    assert "def set_bookmark(self)" in SOURCE
    set_bookmark_start = SOURCE.index("def set_bookmark(self)")
    set_bookmark_end = SOURCE.index("def go_to_bookmark(self)")
    set_bookmark_body = SOURCE[set_bookmark_start:set_bookmark_end]
    assert "from quill.ui.web_form import show_web_form" in set_bookmark_body


def test_set_bookmark_uses_web_form() -> None:
    # The set_bookmark method must call show_web_form, not wx.TextEntryDialog
    set_bookmark_start = SOURCE.index("def set_bookmark(self)")
    set_bookmark_end = SOURCE.index("def go_to_bookmark(self)")
    set_bookmark_body = SOURCE[set_bookmark_start:set_bookmark_end]

    assert "show_web_form(" in set_bookmark_body
    assert 'title="Set Bookmark"' in set_bookmark_body
    assert 'save_label="Set"' in set_bookmark_body
    assert '"name"' in set_bookmark_body

    # Must NOT use old wx.TextEntryDialog pattern
    assert "wx.TextEntryDialog" not in set_bookmark_body


def test_set_bookmark_preserves_behavior() -> None:
    # The method must preserve the original behavior:
    # - Default name based on bookmark count
    # - Handle cancellation (values is None)
    # - Strip and validate name
    # - Store position from editor
    # - Announce result
    set_bookmark_start = SOURCE.index("def set_bookmark(self)")
    set_bookmark_end = SOURCE.index("def go_to_bookmark(self)")
    set_bookmark_body = SOURCE[set_bookmark_start:set_bookmark_end]

    assert 'default_name = f"Bookmark {len(self._bookmarks) + 1}"' in set_bookmark_body
    assert "if values is None:" in set_bookmark_body
    assert ".strip()" in set_bookmark_body
    assert '"Set bookmark cancelled"' in set_bookmark_body
    assert "self.editor.GetInsertionPoint()" in set_bookmark_body
    assert "set_bookmark(self._bookmarks, name, position)" in set_bookmark_body
    assert 'Set bookmark "{name}"' in set_bookmark_body
