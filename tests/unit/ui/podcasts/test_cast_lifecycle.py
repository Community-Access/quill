from __future__ import annotations

from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")


def test_destroying_the_native_frame_invalidates_delivery_and_releases_undo(monkeypatch) -> None:
    from quill.ui import undo_last_ui
    from quill.ui.podcasts.lifecycle import install

    app = wx.GetApp() or wx.App()
    loop = wx.GUIEventLoop()
    previous = wx.EventLoop.GetActive()
    wx.EventLoop.SetActive(loop)
    frame = wx.Frame(None)
    host = SimpleNamespace(frame=frame, _wx=wx)
    released: list[object] = []
    monkeypatch.setattr(undo_last_ui, "deactivate", released.append)
    try:
        install(host)
        child = wx.Panel(frame)
        child.Destroy()
        loop.ProcessIdle()
        assert not host._cast_closed
        assert host._cast_ui_lifetime.is_alive
        frame.Destroy()
        app.ProcessPendingEvents()
        loop.ProcessIdle()
        assert host._cast_closed
        assert not host._cast_ui_lifetime.is_alive
        # Pumping events also delivers the destroy of any frame an earlier test
        # left behind, and those release their own hosts; this host is released
        # exactly once.
        assert [item for item in released if item is host] == [host]
    finally:
        wx.EventLoop.SetActive(previous)


@pytest.mark.parametrize("closing", [False, True])
def test_queued_selection_and_notes_callbacks_do_not_touch_a_destroying_frame(closing) -> None:
    from quill.ui.podcasts.main_panel import CastMainPanelMixin

    app = wx.GetApp() or wx.App()
    frame = wx.Frame(None)
    touched = []
    event = SimpleNamespace(Skip=lambda: touched.append("skip"))
    host = SimpleNamespace(
        frame=frame,
        _cast_closing=closing,
        _cast_closed=False,
        _notes_pane=object(),
        _refresh_selection_buttons=lambda: pytest.fail("Selection touched a closing window"),
        _selected_episode=lambda: pytest.fail("Notes touched a closing window"),
    )
    try:
        frame.Destroy()
        CastMainPanelMixin._on_cast_content_selected(host, event)
        CastMainPanelMixin._refresh_notes_pane(host)
        assert touched == ["skip"]
        app.ProcessPendingEvents()
    finally:
        if frame:
            frame.Destroy()


def test_programmatic_list_selection_waits_for_the_final_button_and_notes_refresh() -> None:
    from quill.ui.podcasts.main_panel import CastMainPanelMixin

    app = wx.GetApp() or wx.App()
    frame = wx.Frame(None)
    skipped = []
    host = SimpleNamespace(
        frame=frame,
        _cast_list_mutating=True,
        _cast_cursor_revision=2,
        _refresh_selection_buttons=lambda: pytest.fail("List publication refreshed buttons twice"),
    )
    try:
        CastMainPanelMixin._on_cast_content_selected(
            host, SimpleNamespace(Skip=lambda: skipped.append(True))
        )
        assert skipped == [True]
        assert host._cast_cursor_revision == 2
    finally:
        frame.Destroy()
        app.ProcessPendingEvents()


def test_close_keeps_detached_input_retirement_running_without_waiting(monkeypatch) -> None:
    from quill.ui.podcasts import library_tree_updates
    from quill.ui.podcasts.lifecycle import cancel_preparations

    steps = []
    monkeypatch.setattr(library_tree_updates, "cancel_tree_update", lambda _host: None)
    host = SimpleNamespace()

    def cancel_view():
        steps.append("cancel")
        host._cast_view_retirement_pool = SimpleNamespace(
            shutdown=lambda **kwargs: steps.append(kwargs)
        )

    host._cancel_cast_view_preparation = cancel_view
    cancel_preparations(host)
    assert steps == ["cancel", {"wait": False, "cancel_pending": False}]
