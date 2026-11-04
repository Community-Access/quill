"""A dimmed menu row's key reaches something that says why, in both editors.

Reported 2026-11-02: in a blank document, "issuing commands produces no feedback
at all". A new document is plain, a plain document dims every Format and markup
row, and Windows never fires the accelerator of a disabled menu row -- so Ctrl+B
and the headings were dead keys with nothing said (:mod:`quill.ui.dimmed_row_keys`).

These hold the routing: the dimmed row's keys move onto an id no menu carries,
and that id reaches QUILL Lite's own command (whose refusal is already written)
or QUILL's one-sentence refusal. ``test_lite_no_silent_command_on_empty_document``
holds the other half, that every handler says something once reached.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
import wx

from quill.ui.dimmed_row_keys import DimmedRowKeys, routed_entries


class _Window:
    """What the keeper touches on a window: Bind and SetAcceleratorTable."""

    def __init__(self) -> None:
        self.bound: dict[int, Any] = {}
        self.tables = 0

    def Bind(self, _event: Any, handler: Any, id: int) -> None:  # noqa: A002, N802 - wx API
        self.bound[int(id)] = handler

    def SetAcceleratorTable(self, _table: Any) -> None:  # noqa: N802 - wx API shape
        self.tables += 1


@pytest.fixture
def menu(wx_session_app):
    menu = wx.Menu()
    yield menu
    menu.Destroy()


def _keys(entries: list[Any]) -> dict[tuple[int, int], int]:
    return {(e.GetFlags(), e.GetKeyCode()): e.GetCommand() for e in entries}


def test_a_dimmed_rows_label_key_and_alias_move_to_its_shadow(menu) -> None:
    bold = menu.Append(wx.ID_ANY, "&Bold\tCtrl+B")
    live = menu.Append(wx.ID_ANY, "&Find\tCtrl+F")
    bold.Enable(False)
    alias = wx.AcceleratorEntry(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord("B"), bold.GetId())
    other = wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_F3, live.GetId())
    entries = routed_entries(wx, [alias, other], {bold.GetId(): bold}, lambda _id: 9001)
    keys = _keys(entries)
    assert keys[(wx.ACCEL_CTRL, ord("B"))] == 9001  # the label's own key
    assert keys[(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord("B"))] == 9001  # the alias
    assert keys[(wx.ACCEL_CTRL, wx.WXK_F3)] == live.GetId()  # an enabled row untouched


def test_the_shadow_is_bound_once_per_row_however_often_it_is_applied(menu) -> None:
    bold = menu.Append(wx.ID_ANY, "&Bold\tCtrl+B")
    bold.Enable(False)
    window = _Window()
    ran: list[str] = []
    keeper = DimmedRowKeys(wx, window, lambda name: lambda _e: ran.append(name))
    keeper.set_base([])
    keeper.apply({"cmd_bold": bold})
    keeper.apply({"cmd_bold": bold})  # unchanged: no second table
    assert window.tables == 1
    assert len(window.bound) == 1
    next(iter(window.bound.values()))(None)
    assert ran == ["cmd_bold"]


def test_lite_dimmed_row_key_runs_the_command_which_says_why(lite_window, menu) -> None:
    from quill.apps.lite_window_menus import _route_dimmed_keys

    window = lite_window("")
    host = _Window()
    window.Bind = host.Bind
    window.SetAcceleratorTable = host.SetAcceleratorTable
    bold = menu.Append(wx.ID_ANY, "&Bold\tCtrl+B")
    bold.Enable(False)
    window._menu_items = {"cmd_bold": bold}
    _route_dimmed_keys(window)
    assert host.tables == 1
    (handler,) = host.bound.values()
    handler(None)
    assert window.announcements, "Ctrl+B in a plain document said nothing"
    assert "no formatting" in window.announcements[-1]


def test_quill_dimmed_markup_key_says_what_the_command_needs(wx_session_app) -> None:
    from quill.ui.main_frame import MainFrame

    bar = wx.MenuBar()
    insert = wx.Menu()
    heading = insert.Append(wx.ID_ANY, "Heading &1\tCtrl+Alt+1")
    table = insert.Append(wx.ID_ANY, "Insert &Table...")
    html = insert.Append(wx.ID_ANY, "I&nsert HTML Tag...	Ctrl+Alt+O")
    bar.Append(insert, "&Insert")
    heading.Enable(False)
    html.Enable(False)
    host = _Window()
    frame = MainFrame.__new__(MainFrame)
    frame.frame = SimpleNamespace(
        GetMenuBar=lambda: bar, Bind=host.Bind, SetAcceleratorTable=host.SetAcceleratorTable
    )
    said: list[str] = []
    frame._announce_result = said.append
    frame._route_dimmed_markup_keys((), (heading.GetId(), table.GetId()), (html.GetId(),))
    assert len(host.bound) == 2  # the enabled table row keeps its own key
    for handler in host.bound.values():
        handler(None)
    assert sorted(said) == [
        "Heading 1 needs a Markdown or HTML document.",
        "Insert HTML Tag needs an HTML document.",
    ]
    bar.Destroy()


def test_a_real_lite_menu_bar_routes_ctrl_b_in_a_plain_document(wx_app) -> None:
    """The whole path on a real ``wx.Frame``: build, dim, route, fire.

    The menu is built by the shipped ``_build_menus``; a frame with no document
    language is plain, so Bold is dimmed -- and the shadow id the build bound
    for it must reach the command by name.
    """
    from quill.apps.lite_window_menus import DocumentMenuMixin
    from quill.core.lite.keymap import default_keymap

    class _Settings:
        theme = "light"
        word_wrap = True
        show_status_bar = True
        recent_files: list[str] = []

    class _App:
        keymap = default_keymap()
        frames: list[object] = []
        settings = _Settings()

        def feature_enabled(self, _area: str) -> bool:
            return True

    ran: list[str] = []

    class _Frame(wx.Frame, DocumentMenuMixin):
        def __init__(self) -> None:
            super().__init__(None)
            self.app = _App()
            self._selection_anchor = None
            self._build_menus()

        def extend_selection_active(self) -> bool:
            return False

        def sound_is_quiet(self) -> bool:
            return False

        def run_unless_read_only(self, handler: str) -> None:
            ran.append(handler)

    frame = _Frame()
    try:
        bold = frame._menu_items["cmd_bold"]
        assert not bold.IsEnabled(), "a plain document should dim Bold"
        shadow = frame._dimmed_row_keys.shadow_id("cmd_bold")
        assert shadow != bold.GetId()
        assert frame.GetMenuBar().FindItemById(shadow) is None  # no menu carries it
        frame.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, shadow))
        assert ran == ["cmd_bold"]
    finally:
        frame.Destroy()
