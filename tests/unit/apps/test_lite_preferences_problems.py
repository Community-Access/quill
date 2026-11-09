"""QUILL Lite's Preferences check box for the Problems pane's default list
(quill/apps/lite_preferences_problems.py), on a real wx dialog."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")


def test_the_check_box_shows_and_writes_the_default(wx_session_app: Any) -> None:
    from quill.apps.lite_preferences_problems import LABEL, ProblemsPanePrefs
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)
    dialog = wx.Dialog(None)
    try:
        sizer = wx.BoxSizer(wx.VERTICAL)
        settings = SimpleNamespace(problems_all_open_files=False)
        prefs = ProblemsPanePrefs(dialog, sizer, settings)
        assert prefs.check.GetLabel() == LABEL and "&" not in LABEL
        assert prefs.check.GetHelpText()
        assert prefs.apply() is False
        prefs.check.SetValue(True)
        assert prefs.apply() is True
        assert settings.problems_all_open_files is True
    finally:
        dialog.Destroy()
