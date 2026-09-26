"""The player window: it must construct, and Go to Player must raise it.

Regression coverage for the 2026-08-23 report "the player for quill radio is
not showing":

- ``bind_close_button`` grew a required ``modeless`` keyword when the radio
  window model landed, and the player panel was the one caller not updated --
  so every summon raised TypeError before the window ever appeared, and the
  key looked simply dead. The construction tests exist so a signature change
  in the dialog contract can never again take the player down silently.
- With a WindowManager present the player is now a modeless peer frame:
  summoning it twice must raise the open window, not stack a second one, and
  closing it must unregister it from the shared window list.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui.radio import player_panel  # noqa: E402
from quill.ui.window_menu import WindowManager  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Host:
    """Just enough host for the panel: announcements and (optionally) windows."""

    def __init__(self, *, windows: WindowManager | None = None) -> None:
        self.said: list[str] = []
        if windows is not None:
            self._windows = windows

    def _announce(self, message: str) -> None:
        self.said.append(message)


@pytest.fixture(autouse=True)
def _reset_open_refs():
    yield
    player_panel._OPEN = None
    player_panel._OPEN_WINDOW = None


def test_modal_player_panel_constructs_without_raising(wx_app) -> None:
    # The whole bug: PlayerPanel.__init__ raised TypeError (bind_close_button's
    # required ``modeless`` keyword was missing), so the player never showed.
    frame = wx.Frame(None)
    try:
        panel = player_panel.PlayerPanel(frame, _Host())
        assert isinstance(panel.dialog, wx.Dialog)
        panel.dialog.Destroy()
    finally:
        frame.Destroy()


def test_modeless_player_panel_constructs_as_a_parentless_frame(wx_app) -> None:
    windows = WindowManager(wx)
    panel = player_panel.PlayerPanel(None, _Host(windows=windows), windows=windows)
    try:
        assert isinstance(panel.window, wx.Frame)
        assert panel.window.GetParent() is None, "a peer window, not an overlay"
        assert panel.window.GetTitle() == "Player"
    finally:
        panel.window.Destroy()


def test_summon_with_windows_opens_once_then_raises_the_open_window(wx_app) -> None:
    windows = WindowManager(wx)
    host = _Host(windows=windows)

    player_panel.summon(host)
    first = player_panel._OPEN_WINDOW
    assert first is not None
    assert len(windows) == 1, "the player registered itself in the window list"

    player_panel.summon(host)
    assert player_panel._OPEN_WINDOW is first, "already open means raise, not a second copy"
    assert len(windows) == 1

    first.window.Destroy()


def test_closing_the_modeless_player_unregisters_it(wx_app) -> None:
    windows = WindowManager(wx)
    host = _Host(windows=windows)

    player_panel.summon(host)
    panel = player_panel._OPEN_WINDOW
    assert panel is not None and len(windows) == 1

    panel.window.Close()
    assert len(windows) == 0, "a closed player must leave the shared window list"
    assert player_panel._OPEN_WINDOW is None
    assert "Exited Player." in host.said


def test_refresh_open_is_safe_with_nothing_open(wx_app) -> None:
    player_panel.refresh_open()  # must never raise


def test_the_now_playing_readout_is_wide_enough_to_read(wx_app) -> None:
    """Reported 2026-09-14: "one word is appearing on lines frequently".

    The readout had no minimum worth the name, so in a small window it wrapped
    a station name and a song title one word to a line. It now asks for a
    readable measure in *characters* -- which also makes the window that holds
    it at least that wide.
    """
    from quill.ui.dialog_contract import READABLE_COLUMNS

    frame = wx.Frame(None)
    try:
        panel = player_panel.PlayerPanel(frame, _Host())
        try:
            char_width, _height = panel.dialog.GetTextExtent("M")
            assert panel._status.GetMinSize()[0] >= char_width * READABLE_COLUMNS
        finally:
            panel.dialog.Destroy()
    finally:
        frame.Destroy()


# -- embedded as the main view (2026-09-25) ---------------------------------------


class _KeyEvent:
    """The two questions ``_on_char_hook`` asks, and whether it skipped."""

    def __init__(self, code: int, *, ctrl: bool = False) -> None:
        self._code = code
        self._ctrl = ctrl
        self.skipped = False

    def GetKeyCode(self) -> int:
        return self._code

    def ControlDown(self) -> bool:
        return self._ctrl

    def Skip(self, skip: bool = True) -> None:
        self.skipped = skip


def _embedded(monkeypatch):
    from quill.ui.radio import transport_keys

    installed_on: list[object] = []
    real_install = transport_keys.install

    def _recording_install(window, *args, **kwargs):
        installed_on.append(window)
        return real_install(window, *args, **kwargs)

    monkeypatch.setattr(transport_keys, "install", _recording_install)
    frame = wx.Frame(None)
    page = wx.Panel(frame)
    panel = player_panel.PlayerPanel(None, _Host(), embed_in=page)
    return frame, page, panel, installed_on


def test_the_embedded_player_has_no_close_button(wx_app, monkeypatch) -> None:
    # A hosted view is not a window; a Close button on it closed the app.
    frame, page, _panel, _installed = _embedded(monkeypatch)
    try:
        buttons = [c for c in page.GetChildren() if isinstance(c, wx.Button)]
        assert all(b.GetId() != wx.ID_CANCEL for b in buttons)
        assert all("Close" not in b.GetLabel().replace("&", "") for b in buttons)
    finally:
        frame.Destroy()


def test_escape_on_the_embedded_player_does_not_close_the_main_window(wx_app, monkeypatch) -> None:
    frame, _page, panel, _installed = _embedded(monkeypatch)
    try:
        closed: list[bool] = []
        monkeypatch.setattr(panel._win, "Close", lambda *a, **k: closed.append(True))
        for event in (_KeyEvent(wx.WXK_ESCAPE), _KeyEvent(wx.WXK_F4, ctrl=True)):
            panel._on_char_hook(event)
            assert event.skipped, "the key goes on to the main window's own handling"
        assert closed == []
    finally:
        frame.Destroy()


def test_the_embedded_player_puts_its_keys_on_the_page_not_the_frame(wx_app, monkeypatch) -> None:
    # A frame has one accelerator table; replacing it cost the app Ctrl+Tab.
    frame, page, _panel, installed_on = _embedded(monkeypatch)
    try:
        assert installed_on == [page]
    finally:
        frame.Destroy()
