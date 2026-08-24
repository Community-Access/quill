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
