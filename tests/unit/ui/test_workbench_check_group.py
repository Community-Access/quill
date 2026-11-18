"""The Properties check list: one real check box per choice (GitHub PRD 15.2, GH-A).

What a keyboard and a screen reader rely on, checked without one: every row
is an ordinary check box whose label is the choice (and, over several items,
how many have it), Space-equivalent changes flip one box once, a third-state
box that nobody touched sends nothing, and the change is exactly what was
done.
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
    assert group.labels() == ["bug", "docs"]
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
    assert group.labels() == ["bug", "docs, on 3 of 5", "ui"]
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
    assert [child.GetLabel() for child in group.panel.GetChildren()] == ["new"]
    group.SetFocus()
