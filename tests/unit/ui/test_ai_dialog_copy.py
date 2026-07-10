from __future__ import annotations

import pytest
import wx

from quill.ui.ai_grammar_check_dialog import AIGrammarCheckDialog
from quill.ui.ai_spell_check_dialog import AISpellCheckDialog


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_ai_grammar_dialog_copy_does_not_advertise_alt_letter_shortcuts(wx_app) -> None:
    dialog = AIGrammarCheckDialog(None, "text", [], lambda *args, **kwargs: None)
    try:
        summary = next(
            child
            for child in dialog.dialog.GetChildren()
            if isinstance(child, wx.StaticText) and "AI found" in child.GetLabel()
        )
        assert "Alt" not in summary.GetLabel()
        assert "Accept" in dialog._accept_btn.GetLabel()
        assert "Skip" in dialog._skip_btn.GetLabel()
    finally:
        dialog.dialog.Destroy()


def test_ai_spell_dialog_copy_does_not_advertise_alt_letter_shortcuts(wx_app) -> None:
    dialog = AISpellCheckDialog(None, "text", [], lambda *args, **kwargs: None)
    try:
        summary = next(
            child
            for child in dialog.dialog.GetChildren()
            if isinstance(child, wx.StaticText) and "AI found" in child.GetLabel()
        )
        assert "Alt" not in summary.GetLabel()
        assert "Accept" in dialog._accept_btn.GetLabel()
        assert "Skip" in dialog._skip_btn.GetLabel()
    finally:
        dialog.dialog.Destroy()
