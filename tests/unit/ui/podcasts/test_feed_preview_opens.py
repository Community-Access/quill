"""Preview in Add Podcast opens the preview, or says why it cannot (2026-11-27).

Users reported the Preview button "is not doing anything". It was not doing
nothing -- it was failing where nobody could hear it:

* ``FeedPreviewDialog`` passed ``wx.ID_CANCEL`` positionally to
  ``bind_close_button``, whose ``modeless`` is keyword-only. The constructor
  raised ``TypeError``, so the window was never once built.
* That happened in a task-manager success callback, and ``call_ui_safely``
  logs and swallows whatever such a callback raises. No window, no sound.

The earlier tests drove Preview with fakes and never built the real window,
which is how a constructor that always raised passed them. These build it.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.ui.podcasts import preview_command
from quill.ui.podcasts.preview_command import (
    CHOOSE_FIRST,
    current_result_index,
    preview_current_row,
)

REPO = Path(__file__).resolve().parents[4]


def _feed() -> SimpleNamespace:
    episode = SimpleNamespace(title="Pilot", published="2026-11-01", description="<p>Hi</p>")
    return SimpleNamespace(
        title="The Daily", author="Someone", description="A show.", episodes=[episode]
    )


class _Label:
    def __init__(self) -> None:
        self.text = ""

    def SetLabel(self, text: str) -> None:  # noqa: N802 - wx API shape
        self.text = text

    def GetLabel(self) -> str:  # noqa: N802 - say_status speaks only a change
        return self.text


class _Button:
    def __init__(self) -> None:
        self.enabled = True

    def Enable(self, on: bool = True) -> None:  # noqa: N802
        self.enabled = bool(on)


class _Results:
    def __init__(self, selected: int = -1, focused: int = -1) -> None:
        self.selected = selected
        self.focused = focused

    def GetFirstSelected(self) -> int:  # noqa: N802
        return self.selected

    def GetFocusedItem(self) -> int:  # noqa: N802
        return self.focused


def _dialog(frame: Any, submit: Any, **results: int) -> SimpleNamespace:
    spoken: list[str] = []
    rows = [
        SimpleNamespace(title="The Daily", feed_url="https://example.invalid/feed"),
        SimpleNamespace(title="Other Show", feed_url="https://example.invalid/other"),
    ]
    return SimpleNamespace(
        frame=frame,
        _status=_Label(),
        _preview_btn=_Button(),
        _announce=spoken.append,
        _task_manager=SimpleNamespace(submit=submit),
        _safe_mode=False,
        _search_results=rows,
        _results=_Results(**results),
        _subscribe_to_feed=lambda *a, **k: spoken.append("subscribed"),
        spoken=spoken,
    )


def _submit_like_the_task_manager(feed: Any) -> Any:
    """Deliver success the way QuillTaskManager does: through call_ui_safely,
    which swallows what the callback raises. That swallow is the point."""
    from quill.stability.wx_dispatch import call_ui_safely

    def submit(_name: str, _work: Any, *, on_success: Any, on_failure: Any) -> None:
        call_ui_safely(on_success, "op", feed)

    return submit


def test_the_preview_window_can_be_built(wx_session_app: Any) -> None:
    import wx

    from quill.ui.podcasts.feed_preview_dialog import FeedPreviewDialog

    frame = wx.Frame(None)
    try:
        preview = FeedPreviewDialog(frame, feed=_feed())
        assert preview.dialog.GetTitle() == "Preview -- The Daily"
        preview.dialog.Destroy()
    finally:
        frame.Destroy()


def test_preview_opens_the_window_through_the_real_callback_path(
    wx_session_app: Any, wx_call_after: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    from quill.ui import dialog_contract

    wx_call_after()
    shown: list[str] = []

    def fake_show(dialog: Any, _label: str, **_kw: Any) -> int:
        shown.append(dialog.GetTitle())
        return wx.ID_CANCEL

    monkeypatch.setattr(dialog_contract, "show_modal_dialog", fake_show)
    frame = wx.Frame(None)
    try:
        dialog = _dialog(frame, _submit_like_the_task_manager(_feed()), selected=0)
        preview_current_row(dialog)
    finally:
        frame.Destroy()
    assert shown == ["Preview -- The Daily"]
    assert dialog.spoken[0] == "Loading The Daily..."
    assert any(line.startswith("Previewing The Daily") for line in dialog.spoken)
    assert dialog._preview_busy is None


def test_a_preview_that_cannot_open_says_so(
    wx_session_app: Any, wx_call_after: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui.podcasts import feed_preview_dialog

    wx_call_after()

    def broken(*_a: Any, **_k: Any) -> Any:
        raise TypeError("as the real constructor did")

    monkeypatch.setattr(feed_preview_dialog, "FeedPreviewDialog", broken)
    dialog = _dialog(None, _submit_like_the_task_manager(_feed()), selected=0)
    preview_current_row(dialog)
    assert dialog.spoken[-1] == (
        "The preview of The Daily could not be opened. You can still follow it from Results."
    )
    assert dialog._status.text == dialog.spoken[-1]
    assert dialog._preview_btn.enabled is True
    assert dialog._preview_busy is None


def test_a_submit_that_raises_is_a_spoken_failure() -> None:
    def submit(*_a: Any, **_k: Any) -> None:
        raise RuntimeError("task manager shut down")

    dialog = _dialog(None, submit, selected=0)
    preview_current_row(dialog)
    assert dialog.spoken[-1].startswith("That podcast could not be loaded")
    assert dialog._preview_busy is None


def test_no_row_says_choose_a_podcast_first_every_time() -> None:
    """Every press is answered, even when the words are already on screen."""
    dialog = _dialog(None, lambda *a, **k: pytest.fail("nothing to fetch"))
    preview_current_row(dialog)
    preview_current_row(dialog)
    assert dialog.spoken == [CHOOSE_FIRST, CHOOSE_FIRST]


def test_the_focused_row_counts_when_none_is_selected() -> None:
    dialog = _dialog(None, lambda *a, **k: None, selected=-1, focused=0)
    assert current_result_index(dialog) == 0
    preview_current_row(dialog)
    assert dialog.spoken == ["Loading The Daily..."]


def test_a_second_press_while_loading_is_answered_not_doubled() -> None:
    submitted: list[str] = []
    dialog = _dialog(None, lambda name, *a, **k: submitted.append(name), selected=0)
    preview_current_row(dialog)
    dialog._results.selected = 1  # the cursor moves on while The Daily loads
    preview_current_row(dialog)
    preview_current_row(dialog)
    assert submitted == ["podcast-preview"]
    # Named for the show being loaded, and said on every press.
    assert dialog.spoken[-2:] == ["Still loading The Daily...", "Still loading The Daily..."]
    # Never disabled while focused: that drops focus to nowhere mid-wait.
    assert dialog._preview_btn.enabled is True


def test_a_preview_whose_callbacks_never_come_stops_counting_as_loading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submitted: list[str] = []
    dialog = _dialog(None, lambda name, *a, **k: submitted.append(name), selected=0)
    preview_current_row(dialog)
    title, since = dialog._preview_busy
    dialog._preview_busy = (title, since - preview_command.BUSY_SECONDS - 1)
    preview_current_row(dialog)
    assert submitted == ["podcast-preview", "podcast-preview"]


def test_focus_returns_where_preview_was_pressed(monkeypatch: pytest.MonkeyPatch) -> None:
    focused: list[str] = []
    window = SimpleNamespace(
        IsEnabled=lambda: True,
        IsShownOnScreen=lambda: True,
        SetFocus=lambda: focused.append("button"),
    )
    preview_command._focus_back(window)
    preview_command._focus_back(None)
    assert focused == ["button"]


def test_bind_close_button_is_never_called_with_a_positional_mode() -> None:
    """``modeless`` is keyword-only; a third positional is the TypeError that
    killed Preview. Any call shaped like that is caught here, not by users."""
    bad: list[str] = []
    # git grep, not rglob: walking every file of the tree costs seconds here.
    listed = subprocess.run(
        ["git", "grep", "-l", "bind_close_button(", "--", "quill", "standalone"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert listed, "git grep found no caller at all -- the scan is not looking"
    for rel in listed:
        if not rel.endswith(".py"):
            continue
        tree = ast.parse((REPO / rel).read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if called != "bind_close_button":
                continue
            keywords = {kw.arg for kw in node.keywords}
            if len(node.args) > 2 or "modeless" not in keywords:
                bad.append(f"{rel}:{node.lineno}")
    assert bad == []
