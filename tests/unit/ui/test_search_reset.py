"""Clearing a search field clears its results (quill/ui/search_reset.py).

The rule the module exists for: a results list must never keep showing
matches for text that is no longer in the field. One binding, used by every
search surface with a separate results list.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui.search_reset import bind_empty_query_reset  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _pump() -> None:
    # EVT_TEXT from SetValue is synchronous on wxMSW; this drains anything
    # a port chose to queue instead.
    wx.GetApp().ProcessPendingEvents()


def test_emptying_the_field_fires_the_reset(wx_app):
    frame = wx.Frame(None)
    try:
        ctrl = wx.TextCtrl(frame)
        fired: list[int] = []
        bind_empty_query_reset(ctrl, lambda: fired.append(1))
        ctrl.SetValue("query")
        _pump()
        assert fired == []  # text present: nothing to reset
        ctrl.SetValue("")
        _pump()
        assert fired == [1]
    finally:
        frame.Destroy()


def test_whitespace_counts_as_empty(wx_app):
    frame = wx.Frame(None)
    try:
        ctrl = wx.TextCtrl(frame)
        fired: list[int] = []
        bind_empty_query_reset(ctrl, lambda: fired.append(1))
        ctrl.SetValue("   ")
        _pump()
        assert fired == [1]
    finally:
        frame.Destroy()


def test_reset_waits_for_every_bound_field_to_empty(wx_app):
    # The station browser binds name AND tag: results stay while either
    # still holds a query.
    frame = wx.Frame(None)
    try:
        name, tag = wx.TextCtrl(frame), wx.TextCtrl(frame)
        fired: list[int] = []
        bind_empty_query_reset(name, lambda: fired.append(1), also=(tag,))
        name.SetValue("jazz")
        tag.SetValue("blues")
        _pump()
        name.SetValue("")
        _pump()
        assert fired == []  # the tag still carries a query
        tag.SetValue("")
        _pump()
        assert fired == [1]
    finally:
        frame.Destroy()
