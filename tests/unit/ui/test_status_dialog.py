"""HelpStatusDialog: periodic refresh must not steal keyboard position.

Regression coverage for #969: the Application Status dialog's list controls
rebuild from scratch every 2 seconds (a live-update timer, so downloads and
task progress stay current). HelpStatusDialog.refresh() called
wx.ListCtrl.DeleteAllItems() and reinserted every row with no attempt to
restore the previously focused row, so a user who pressed Down to move to
row 3 found themselves back at row 0 (or with no focused row at all) the next
time the timer fired -- "Move down through the list. The focus will be put
back at the top of the list," making the dialog effectively unnavigable.
"""

from __future__ import annotations

import pytest
import wx

from quill.ui.status_dialog import HelpStatusDialog


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _status_data(rows: int) -> dict:
    return {
        "status_rows": [("Overview", f"Setting {i}", f"Value {i}") for i in range(rows)],
        "task_rows": [],
        "feature_rows": [],
        "actions": [],
    }


def test_refresh_preserves_the_focused_status_row(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = HelpStatusDialog(frame, wx, _status_data(5))

    # Simulate the user pressing Down to move to row 3, the way JAWS/NVDA
    # arrow navigation does on a wx.ListCtrl.
    state = wx.LIST_STATE_FOCUSED | wx.LIST_STATE_SELECTED
    dlg._status_list.SetItemState(3, state, state)
    assert dlg._status_list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_FOCUSED) == 3

    # A live-update tick rebuilds the list with fresh data (same row count).
    dlg.refresh(_status_data(5))

    focused = dlg._status_list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_FOCUSED)
    assert focused == 3, "the live-update refresh must not reset keyboard position to the top"

    frame.Destroy()


def test_refresh_clamps_focus_when_the_row_count_shrinks(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = HelpStatusDialog(frame, wx, _status_data(5))
    state = wx.LIST_STATE_FOCUSED | wx.LIST_STATE_SELECTED
    dlg._status_list.SetItemState(4, state, state)

    dlg.refresh(_status_data(2))  # fewer rows than the focused index

    focused = dlg._status_list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_FOCUSED)
    assert focused == 1  # clamped to the new last row, never left unset

    frame.Destroy()


def test_refresh_with_no_prior_focus_leaves_nothing_focused(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = HelpStatusDialog(frame, wx, _status_data(5))
    # Never navigated into the list -- refresh must not invent a focus.

    dlg.refresh(_status_data(5))

    focused = dlg._status_list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_FOCUSED)
    assert focused == -1

    frame.Destroy()


def test_refresh_preserves_focus_independently_per_list(wx_app) -> None:
    frame = wx.Frame(None)
    dlg = HelpStatusDialog(frame, wx, _status_data(5))
    state = wx.LIST_STATE_FOCUSED | wx.LIST_STATE_SELECTED

    dlg._tasks_list.InsertItem(0, "Task A")
    dlg._tasks_list.InsertItem(1, "Task B")
    dlg._tasks_list.InsertItem(2, "Task C")
    dlg._tasks_list.SetItemState(2, state, state)

    dlg.refresh({
        "status_rows": _status_data(5)["status_rows"],
        "task_rows": [
            ("Task A", "done", "", "", ""),
            ("Task B", "done", "", "", ""),
            ("Task C", "running", "50%", "", ""),
        ],
        "feature_rows": [],
        "actions": [],
    })

    focused = dlg._tasks_list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_FOCUSED)
    assert focused == 2
    # The status list, untouched by the user, stays unfocused.
    status_focused = dlg._status_list.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_FOCUSED)
    assert status_focused == -1

    frame.Destroy()
