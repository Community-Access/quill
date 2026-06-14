from __future__ import annotations

from pathlib import Path


def test_regex_helper_uses_accessible_dialog_controls() -> None:
    source = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
        encoding="utf-8"
    )
    assert "def show_regex_helper(self) -> None:" in source
    assert "wx.Dialog(" in source
    assert 'title="Regular Expression Helper"' in source
    assert "wx.ListBox(dialog, choices=[item[0] for item in recipes])" in source
    assert "wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)" in source
    assert 'wx.Button(dialog, label="Preview")' in source
    assert 'wx.Button(dialog, label="Copy Pattern")' in source


def test_regex_helper_supports_preview_and_copy_actions() -> None:
    source = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
        encoding="utf-8"
    )
    assert "matches = list(re.finditer(pattern, sample, re.MULTILINE))" in source
    assert "Pattern error:" in source
    assert "self._copy_to_clipboard(pattern)" in source
