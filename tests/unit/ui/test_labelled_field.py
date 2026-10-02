"""``labelled`` builds the label first and leaves help to the caller.

Help set inside a helper is invisible to the help audits, which read
``SetHelpText`` at the construction site -- so the helper may not take one
(qc.md Cast Phase 1, 2026-10-01). And the label must exist before the control,
because on wxMSW that creation order *is* the accessible name.
"""

from __future__ import annotations

import inspect

import pytest

from quill.ui import labelled_field


def test_labelled_takes_no_help_argument() -> None:
    assert "help" not in inspect.signature(labelled_field.labelled).parameters


def test_the_label_is_created_before_the_control_and_added_first() -> None:
    wx = pytest.importorskip("wx")
    app = wx.App()  # noqa: F841 - a window needs one
    frame = wx.Frame(None)
    sizer = wx.BoxSizer(wx.HORIZONTAL)
    made: list[str] = []

    def factory(parent):
        made.append("control")
        return wx.TextCtrl(parent)

    control = labelled_field.labelled(frame, sizer, "&Name:", factory)
    children = list(frame.GetChildren())
    assert isinstance(children[0], wx.StaticText)
    assert children[0].GetLabel() == "&Name:"
    assert children[1] is control
    items = [item.GetWindow() for item in sizer.GetChildren()]
    assert items == [children[0], control]
    assert control.GetHelpText() == ""
    frame.Destroy()
