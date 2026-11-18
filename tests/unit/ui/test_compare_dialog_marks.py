"""Compare Files marks each changed line in the shared Diff Line Marks style."""

from __future__ import annotations

import pytest

pytest.importorskip("wx")

import wx  # noqa: E402

from quill.core.compare_service import CompareService  # noqa: E402
from quill.core.github import review_preferences  # noqa: E402
from quill.ui.compare_dialog import CompareDialog  # noqa: E402
from tests.wx_session import shared_wx_app  # noqa: E402


@pytest.fixture
def dialog(tmp_path, monkeypatch):
    shared_wx_app()
    monkeypatch.setattr(review_preferences, "app_data_dir", lambda: tmp_path)
    service = CompareService()
    service.compare("a\nb\nc\n", "a\nB\nc\n", left_label="old", right_label="new")
    frame = wx.Frame(None)
    made = CompareDialog(frame, service)
    yield made
    made.dialog.Destroy()
    frame.Destroy()


def test_detail_marks_lines_and_follows_the_chosen_style(dialog) -> None:
    assert "Removed: b\nAdded: B" in dialog._detail.GetValue()
    assert dialog._marks_note.GetLabel() == ""
    dialog._marks_choice.SetSelection(3)
    dialog._on_marks_changed(None)
    assert "!- b\n!+ B" in dialog._detail.GetValue()
    assert "punctuation" in dialog._marks_note.GetLabel()
    assert review_preferences.load_line_marks() == "changed"
    dialog._marks_choice.SetSelection(1)
    dialog._on_marks_changed(None)
    assert "Del b\nAdd B" in dialog._detail.GetValue()
