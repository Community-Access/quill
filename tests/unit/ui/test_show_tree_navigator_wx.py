"""Real-wx regression test for #885: TreeCtrl hidden-root Expand() crash.

``_show_tree_navigator`` builds its tree with ``wx.TR_HIDE_ROOT`` and used to
call ``tree.Expand(root)`` unconditionally, which wx disallows for a hidden
root (``wxAssertionError: "!IsHiddenRoot(item)" ... Can't expand/collapse
hidden root node!``). This exercises the real wx.TreeCtrl so a regression
here fails loudly instead of only being caught by a manual repro.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

import quill.ui.main_frame as main_frame_module  # noqa: E402
from quill.ui.main_frame import MainFrame  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_show_tree_navigator_does_not_crash_on_hidden_root(wx_app) -> None:
    frame = MainFrame.__new__(MainFrame)
    frame._wx = wx
    frame.frame = wx.Frame(None)
    frame._show_modal_dialog = lambda dialog, title, **_kwargs: wx.ID_CANCEL  # type: ignore[method-assign]
    nodes = [
        main_frame_module._NavigatorNode(
            label="Heading 1",
            preview="preview text",
            payload=object(),
            action_label="Jump to Heading",
            children=[],
        )
    ]
    try:
        result = frame._show_tree_navigator(
            title="Outline Navigator", root_label="Headings", nodes=nodes
        )
    finally:
        frame.frame.Destroy()
    assert result is None


def test_show_tree_navigator_accepts_unhashable_payloads(wx_app) -> None:
    # #1109: "Go to Entry in Notebook" builds nodes whose payload is a
    # NotebookEntry -- an unhashable dataclass. The navigator used to key an
    # internal dict by node.payload, so opening it raised
    # "TypeError: unhashable type: 'NotebookEntry'". A dict payload stands in
    # for any unhashable object here.
    frame = MainFrame.__new__(MainFrame)
    frame._wx = wx
    frame.frame = wx.Frame(None)
    frame._show_modal_dialog = lambda dialog, title, **_kwargs: wx.ID_CANCEL  # type: ignore[method-assign]
    nodes = [
        main_frame_module._NavigatorNode(
            label="Entry A",
            preview="entry A body",
            payload={"entry": "A"},  # unhashable, like a NotebookEntry
            action_label="Go to Entry",
            children=[
                main_frame_module._NavigatorNode(
                    label="Entry A.1",
                    preview="child body",
                    payload={"entry": "A.1"},
                    action_label="Go to Entry",
                    children=[],
                )
            ],
        )
    ]
    try:
        result = frame._show_tree_navigator(
            title="Go to Entry in Notebook", root_label="Notebook", nodes=nodes
        )
    finally:
        frame.frame.Destroy()
    assert result is None
