"""Details stays inside the Workbench, and the Workbench stays on the screen.

Jeff, testing the QUILL Lite portable: the WordPress Workbench's Details text
(Start Here, then "You have 1 site connected.") ran past what he could see, so
he had to scroll right to read the last word of a line. Details wraps at its
own width, so a line can only run off the screen when the control itself is
outside the visible window: the right pane laid out past the splitter in a
narrow window, or the window bigger than (or hanging off) the display.

These build the real shared frame through the same door QUILL Lite uses, put
the long Start Here text in Details, and check every rectangle from Details up
to the frame at several sizes and sash positions, and that a window bigger than
the screen, default or remembered, is pulled back inside the work area.
"""

from __future__ import annotations

import sys
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.apps.lite_window_wordpress_host import LiteWordPressHost  # noqa: E402
from quill.core.wordpress import sites as st  # noqa: E402
from quill.core.wordpress.workbench_help import START_HERE  # noqa: E402
from quill.core.wordpress.workbench_tree import START_NODE  # noqa: E402
from quill.ui import dpi  # noqa: E402
from quill.ui import wordpress_workbench_window as window  # noqa: E402
from quill.ui.wordpress_commands import WordPressCommands  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402


@pytest.fixture
def opened(wx_session_app, tmp_path, monkeypatch):
    """Open the WordPress Workbench with one site, the way both editors do."""
    monkeypatch.setattr(window, "_OPEN", {})
    parent = wx.Frame(None)
    parent._announce = lambda _text: None  # type: ignore[attr-defined]
    commands = WordPressCommands(LiteWordPressHost(parent), data_dir=tmp_path)
    store = st.SiteStore([st.SiteProfile("s1", "Radio", "https://radio.example", "jeff")], "s1")
    st.save_sites(store, tmp_path)
    monkeypatch.setattr(window.WordPressWorkbenchProvider, "start", lambda self: None)

    def open_it() -> WorkbenchFrame:
        commands.cmd_workbench()
        bench = window._OPEN["wordpress"]
        bench.select(NodeRef("", START_NODE))
        bench._show_node(NodeRef("", START_NODE), remember=True)
        return bench

    yield open_it
    for bench in list(window._OPEN.values()):
        bench.frame.Destroy()
    parent.Destroy()


def _settle(bench: WorkbenchFrame) -> None:
    bench.frame.SendSizeEvent()
    bench.frame.Layout()


def _inside(child: Any, parent: Any) -> bool:
    """*child*'s rectangle lies within *parent*'s client area."""
    rect = child.GetRect()
    width, height = parent.GetClientSize()
    return (
        rect.x >= 0
        and rect.y >= 0
        and rect.x + rect.width <= width
        and rect.y + rect.height <= height
    )


def _assert_details_visible(bench: WorkbenchFrame, where: str) -> None:
    details = bench.details
    window_ = details
    while window_ is not bench.frame:  # Details, its pane, the splitter, the panel
        parent = window_.GetParent()
        assert _inside(window_, parent), (
            f"{where}: {window_.GetName()} {window_.GetRect()} is outside "
            f"{parent.GetName()}'s client area {parent.GetClientSize()}"
        )
        window_ = parent
    on_screen = details.GetScreenRect()
    client = wx.Rect(bench.frame.ClientToScreen(wx.Point(0, 0)), bench.frame.GetClientSize())
    assert client.Contains(on_screen), f"{where}: Details {on_screen} past the frame {client}"
    assert details.GetSize().width > 0, f"{where}: Details has no width"


def _assert_wraps(details: Any) -> None:
    assert not details.HasFlag(wx.HSCROLL), "Details must wrap, not scroll sideways"
    if sys.platform == "win32":
        import ctypes

        style = ctypes.windll.user32.GetWindowLongW(details.GetHandle(), -16)
        ws_hscroll, es_autohscroll = 0x00100000, 0x0080
        assert not style & (ws_hscroll | es_autohscroll), hex(style)


@pytest.mark.parametrize(
    "size",
    [(980, 680), (700, 500), (480, 360), (300, 300), (200, 260), (120, 200)],
    ids=lambda size: f"{size[0]}x{size[1]}",
)
def test_details_stays_inside_the_window_at_every_size(opened, size) -> None:
    bench = opened()
    assert bench.details.GetValue().startswith(START_HERE)
    assert bench.details.GetValue().endswith("You have 1 site connected.")
    _assert_wraps(bench.details)
    bench.frame.SetSize(bench.frame.FromDIP(wx.Size(*size)))
    _settle(bench)
    _assert_details_visible(bench, f"{size}")


@pytest.mark.parametrize("sash", [60, 280, 520, 900], ids=lambda s: f"sash{s}")
def test_details_stays_inside_the_window_wherever_the_sash_goes(opened, sash) -> None:
    bench = opened()
    for size in ((700, 500), (360, 400)):
        bench.frame.SetSize(bench.frame.FromDIP(wx.Size(*size)))
        _settle(bench)
        bench._splitter.SetSashPosition(bench.frame.FromDIP(sash))
        _settle(bench)
        _assert_details_visible(bench, f"{size} {sash}")
        # narrowing the window after the sash moved must not push the pane out either
        bench.frame.SetSize(bench.frame.FromDIP(wx.Size(150, 300)))
        _settle(bench)
        _assert_details_visible(bench, f"{size} {sash} then narrow")


def test_the_status_cells_are_laid_out_with_height_once_they_have_words(opened) -> None:
    bench = opened()
    bench.status.refresh()
    assert bench.status.visible_cells(), "the WordPress bar always has a Filter cell"
    assert bench.status.panel.GetSize().height > 0
    _assert_details_visible(bench, "with the status cells shown")


def test_a_window_bigger_than_the_screen_is_pulled_inside_the_work_area(
    opened, monkeypatch
) -> None:
    # A small display, or 200 percent: the default 980 x 680 DIPs does not fit.
    area = (0, 0, 640, 480)
    monkeypatch.setattr(dpi, "work_area", lambda _window=None: area, raising=False)
    bench = opened()
    rect = bench.frame.GetRect()
    assert rect.x >= 0 and rect.y >= 0
    assert rect.x + rect.width <= 640 and rect.y + rect.height <= 480, rect
    _assert_details_visible(bench, "fitted")


def test_a_remembered_size_bigger_than_the_display_is_clamped(
    wx_session_app, quill_data_dir, monkeypatch
) -> None:
    from quill.ui.github_workbench_window import GitHubWorkbenchProvider
    from tests.unit.ui.test_github_workbench_window import _Items

    area = (100, 50, 800, 600)
    monkeypatch.setattr(dpi, "work_area", lambda _window=None: area, raising=False)
    provider = GitHubWorkbenchProvider(_Items(), "owner/repo", announce=lambda _t: None)
    monkeypatch.setattr(provider, "recall_layout", lambda: ((4000, 3000), 300))
    monkeypatch.setattr(provider, "remember_layout", lambda *_a: None)
    monkeypatch.setattr(provider, "remember_place", lambda *_a: None)
    bench = WorkbenchFrame(provider, run_background=lambda *_a: None)
    try:
        bench.frame.SetPosition(wx.Point(2000, 1500))  # and left somewhere off the screen
        bench.restore_layout()
        rect = bench.frame.GetRect()
        assert (rect.x, rect.y) >= (100, 50), rect
        assert rect.x + rect.width <= 900 and rect.y + rect.height <= 650, rect
        _settle(bench)
        _assert_details_visible(bench, "remembered")
    finally:
        bench.frame.Destroy()


def test_fit_rect_shrinks_then_moves_inside() -> None:
    assert dpi.fit_rect((0, 0, 500, 400), (0, 0, 1920, 1080)) == (0, 0, 500, 400)
    assert dpi.fit_rect((1800, 900, 500, 400), (0, 0, 1920, 1080)) == (1420, 680, 500, 400)
    assert dpi.fit_rect((-50, -20, 2400, 1300), (0, 0, 1920, 1040)) == (0, 0, 1920, 1040)
    assert dpi.fit_rect((10, 10, 300, 200), (1920, 0, 1280, 1024)) == (1920, 10, 300, 200)


def test_a_main_window_remembered_wider_than_the_display_opens_inside_it(
    wx_session_app, quill_data_dir, monkeypatch
) -> None:
    """The family's shared window memory fits the same way (window_state.py)."""
    from quill.core.window_geometry import WindowGeometry, save_geometry
    from quill.ui import window_state

    monkeypatch.setattr(dpi, "work_area", lambda _window=None: (0, 0, 800, 600), raising=False)
    save_geometry(
        window_state._data_dir(),
        "fit-probe",
        WindowGeometry(maximized=False, width=3000, height=2000),
    )
    frame = wx.Frame(None)
    try:
        window_state.apply_window_geometry(frame, "fit-probe")
        rect = frame.GetRect()
        assert rect.x + rect.width <= 800 and rect.y + rect.height <= 600, rect
    finally:
        frame.Destroy()
