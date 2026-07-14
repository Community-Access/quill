"""Regression test for issue #916: open_spell_language_chooser crashed with
TypeError: MainFrame._show_modal_dialog() missing 1 required positional
argument: 'label' -- the call site passed only the dialog, not the label
every other call site in the codebase already supplies.
"""

from __future__ import annotations

import pytest
import wx

from quill.core import spellcheck
from quill.ui.spell_language import open_spell_language_chooser


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_open_spell_language_chooser_passes_a_label(wx_app, monkeypatch) -> None:
    monkeypatch.setattr(spellcheck, "active_language", lambda: "en_US")
    monkeypatch.setattr(spellcheck, "installed_languages", lambda: ["en_US"])
    monkeypatch.setattr(spellcheck, "installable_languages", lambda: [])
    monkeypatch.setattr(spellcheck, "language_display_name", lambda lang: lang)

    frame = wx.Frame(None)
    seen: dict = {}

    class Host:
        def __init__(self) -> None:
            self.frame = frame

        def _show_modal_dialog(self, dialog, label, *, restore_editor_focus=True):
            seen["label"] = label
            return wx.ID_CANCEL

    open_spell_language_chooser(wx, Host())

    assert seen.get("label") == "Spell Check Language"
    frame.Destroy()
