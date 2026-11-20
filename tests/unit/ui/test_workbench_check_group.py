"""The Properties check list: one real check box per choice (GitHub PRD 15.2, GH-A).

What a keyboard and a screen reader rely on, checked without one: every row
is an ordinary check box whose label is the choice and its state ("bug, on",
or over several items how many have it), Space-equivalent changes flip one
box once and the text follows without anything announced, a third-state box
that nobody touched sends nothing, and the change is exactly what was done
(GH-R-157).
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill.ui.workbench_check_group import CheckGroup  # noqa: E402


@pytest.fixture
def parent(wx_session_app):
    frame = wx.Frame(None)
    yield frame
    frame.Destroy()


def test_each_choice_is_a_check_box_that_says_its_state(parent) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)
    group = CheckGroup(parent, "Labels", ["bug", "docs"], have=("bug",), help_text="Labels.")
    assert all(isinstance(box, wx.CheckBox) for box in group.boxes.values())
    assert group.labels() == ["bug, on", "docs, off"]
    assert group.state("bug") == "on" and group.state("docs") == "off"
    assert group.boxes["docs"].GetHelpText() == "Labels."


def test_one_change_is_one_flip_and_the_delta_is_exactly_it(parent) -> None:
    group = CheckGroup(parent, "Labels", ["bug", "docs", "ui"], have=("bug",))
    group.boxes["docs"].SetValue(True)  # what Space does, once
    assert group.delta().added == ("docs",) and group.delta().removed == ()
    group.boxes["bug"].SetValue(False)
    assert group.delta().removed == ("bug",)
    group.boxes["docs"].SetValue(False)  # changed back: nothing to send for it
    assert group.delta().added == ()


def test_over_several_items_a_partial_choice_is_third_state_and_says_how_many(parent) -> None:
    group = CheckGroup(
        parent, "Labels", ["bug", "docs", "ui"], counts={"bug": 5, "docs": 3}, total=5
    )
    assert group.labels() == ["bug, on", "docs, on 3 of 5", "ui, off"]
    assert [group.state(i) for i in ("bug", "docs", "ui")] == ["on", "mixed", "off"]
    assert group.delta().added == () and group.delta().removed == ()
    group.set("docs", True)
    assert group.delta().added == ("docs",)


def test_after_saving_the_new_state_is_the_start(parent) -> None:
    group = CheckGroup(parent, "Labels", ["bug", "docs"], have=())
    group.set("bug", True)
    group.reset(("bug",))
    assert group.delta().added == () and group.checked() == ("bug",)


def test_an_empty_list_says_so_and_the_first_added_choice_replaces_it(parent) -> None:
    group = CheckGroup(parent, "Labels", [])
    texts = [child.GetLabel() for child in group.panel.GetChildren()]
    assert texts == ["(None to choose from yet.)"]
    group.add("new", on=True)
    assert [child.GetLabel() for child in group.panel.GetChildren()] == ["new, on"]
    group.SetFocus()


def _space(box) -> None:
    """What Space does to a focused check box: the native flip, then one EVT_CHECKBOX."""
    box.SetValue(not box.GetValue())
    event = wx.CommandEvent(wx.wxEVT_CHECKBOX, box.GetId())
    event.SetEventObject(box)
    event.SetInt(int(box.GetValue()))
    box.GetEventHandler().ProcessEvent(event)


def test_space_changes_the_row_once_and_its_text_says_the_new_state(parent) -> None:
    group = CheckGroup(parent, "Features", ["Issues", "Wiki"], have=("Issues",))
    _space(group.boxes["Issues"])
    assert group.state("Issues") == "off"  # one flip: the handler does not flip it again
    assert group.labels() == ["Issues, off", "Wiki, off"]
    _space(group.boxes["Issues"])
    assert group.labels()[0] == "Issues, on"


def test_no_key_handler_can_toggle_a_second_time(parent) -> None:
    """Space is the box's own key; a KEY_DOWN or CHAR handler here would flip it twice."""
    group = CheckGroup(parent, "Labels", ["bug"])
    box = group.boxes["bug"]
    for kind in (wx.wxEVT_KEY_DOWN, wx.wxEVT_CHAR):
        event = wx.KeyEvent(kind)
        event.SetEventObject(box)
        event.m_keyCode = wx.WXK_SPACE
        box.GetEventHandler().ProcessEvent(event)
    assert group.state("bug") == "off"


def test_a_name_with_an_ampersand_is_not_an_access_key(parent) -> None:
    group = CheckGroup(parent, "Labels", ["R&D"], have=("R&D",))
    assert group.labels() == ["R&D, on"]
