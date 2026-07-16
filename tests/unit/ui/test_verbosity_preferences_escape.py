"""#1056: Escape must close the Verbosity Preferences dialog.

apply_modal_ids(dialog) was called with no id arguments at all, so nothing
ever set the dialog's escape id -- Escape did nothing and the only way out
was tabbing to the Close button, contravening Quill's "always Escape out"
design principle. Constructs the real dialog (mirrors
test_ai_progress_dialog_close.py's approach for the same class of bug)
rather than a source-text check, since the bug is specifically about
runtime Escape behavior.
"""

from __future__ import annotations

import pytest
import wx

from quill.ui.main_frame_verbosity import VerbosityCommandsMixin


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_verbosity_preferences_dialog_escape_id_is_the_close_button(wx_app) -> None:
    parent = wx.Frame(None)
    frame = VerbosityCommandsMixin.__new__(VerbosityCommandsMixin)
    frame._wx = wx
    frame.frame = parent
    frame._announce_text = lambda _msg: None
    captured: dict[str, int] = {}

    def fake_show_modal_dialog(dialog: wx.Dialog, _label: str) -> int:
        captured["escape_id"] = dialog.GetEscapeId()
        return wx.ID_CLOSE

    frame._show_modal_dialog = fake_show_modal_dialog  # type: ignore[method-assign]

    frame.open_verbosity_preferences()

    assert captured["escape_id"] == wx.ID_CLOSE, (
        "Escape must dismiss the dialog the same way the Close button does"
    )
    parent.Destroy()
