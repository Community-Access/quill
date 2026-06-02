"""Source-contract test for start_macro_recording migration to show_web_form (DLG-1).

The live wx.Dialog is not runtime-instantiated in tests; the repo validates
dialog wiring through source contracts. This asserts that start_macro_recording now uses
show_web_form instead of wx.TextEntryDialog.
"""

from __future__ import annotations

from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)


def test_start_macro_recording_imports_show_web_form() -> None:
    # The start_macro_recording method must import show_web_form from web_form module
    assert "def start_macro_recording(self)" in SOURCE
    start_macro_start = SOURCE.index("def start_macro_recording(self)")
    start_macro_end = SOURCE.index("def stop_macro_recording(self)")
    start_macro_body = SOURCE[start_macro_start:start_macro_end]
    assert "from quill.ui.web_form import show_web_form" in start_macro_body


def test_start_macro_recording_uses_web_form() -> None:
    # The start_macro_recording method must call show_web_form, not wx.TextEntryDialog
    start_macro_start = SOURCE.index("def start_macro_recording(self)")
    start_macro_end = SOURCE.index("def stop_macro_recording(self)")
    start_macro_body = SOURCE[start_macro_start:start_macro_end]

    assert "show_web_form(" in start_macro_body
    assert 'title="Start Macro Recording"' in start_macro_body
    assert 'save_label="Start"' in start_macro_body
    assert '"name"' in start_macro_body

    # Must NOT use old wx.TextEntryDialog pattern
    assert "wx.TextEntryDialog" not in start_macro_body


def test_start_macro_recording_preserves_behavior() -> None:
    # The method must preserve the original behavior:
    # - Check if already recording
    # - Default name "My Macro"
    # - Handle cancellation (values is None)
    # - Strip and validate name
    # - Call macros.start_recording
    # - Handle ValueError (duplicate name)
    # - Announce result
    start_macro_start = SOURCE.index("def start_macro_recording(self)")
    start_macro_end = SOURCE.index("def stop_macro_recording(self)")
    start_macro_body = SOURCE[start_macro_start:start_macro_end]

    assert "if self.macros.recording_name is not None:" in start_macro_body
    assert '"Already recording macro' in start_macro_body
    assert "if values is None:" in start_macro_body
    assert '"Macro recording cancelled"' in start_macro_body
    assert ".strip()" in start_macro_body
    assert '"Macro name cannot be empty"' in start_macro_body
    assert "self.macros.start_recording(name)" in start_macro_body
    assert "except ValueError as error:" in start_macro_body
    assert 'f"Recording macro {name}"' in start_macro_body
