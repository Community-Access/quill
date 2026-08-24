"""The converted radio surfaces are real peer windows (2026-08-23).

Downloads, Song History, and Now Playing gained the modeless shape the window
model gave Browse and the managers: a parentless ``wx.Frame`` registered with
the shared WindowManager, closed by its own handler (which unregisters it and
raises the previous window). These tests construct each in its modeless shape
and pin the peer-window facts; the modal shapes are unchanged and covered by
the existing command-level tests.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.core.radio.download_queue import DownloadQueue  # noqa: E402
from quill.ui.radio import now_playing_dialog  # noqa: E402
from quill.ui.radio.download_queue_dialog import DownloadQueueDialog  # noqa: E402
from quill.ui.window_menu import WindowManager  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_downloads_modeless_is_a_parentless_registered_frame(wx_app) -> None:
    windows = WindowManager(wx)
    closed: list[bool] = []
    dlg = DownloadQueueDialog(
        None,
        queue=DownloadQueue(),
        windows=windows,
        on_closed=lambda: closed.append(True),
    )
    try:
        assert isinstance(dlg.dialog, wx.Frame)
        assert dlg.dialog.GetParent() is None, "a peer window, not an overlay"
        dlg.show()
        assert len(windows) == 1
        dlg.dialog.Close()
        assert len(windows) == 0, "closing leaves the shared window list"
        assert closed == [True], "the opener is told, so refreshes stop targeting it"
    finally:
        if dlg.dialog:
            dlg.dialog.Destroy()


def test_now_playing_modeless_replaces_the_open_snapshot(wx_app) -> None:
    windows = WindowManager(wx)
    first = now_playing_dialog.NowPlayingDialog(
        None, "Track A", lambda *_a: 0, lambda _t: True, None, windows=windows
    )
    first.show()
    assert len(windows) == 1
    second = now_playing_dialog.NowPlayingDialog(
        None, "Track B", lambda *_a: 0, lambda _t: True, None, windows=windows
    )
    second.show()
    try:
        # A snapshot viewer: the fresh one replaces the stale one rather than
        # stacking or raising old text under a new gesture.
        assert len(windows) == 1
        assert now_playing_dialog._OPEN is second
    finally:
        second.dialog.Close()
        assert now_playing_dialog._OPEN is None


def test_song_history_modeless_registers_and_unregisters(wx_app) -> None:
    from quill.core.radio.song_history import SongHistory
    from quill.ui.radio.song_history_dialog import SongHistoryDialog

    history = SongHistory()
    history.record("key-1", "WQXR", "Song One by Artist")
    windows = WindowManager(wx)
    said: list[str] = []
    dlg = SongHistoryDialog(
        None,
        history=history,
        current_station_key="key-1",
        show_modal_dialog=lambda *_a: 0,
        copy_to_clipboard=lambda _t: True,
        announce=said.append,
        send_to_clip_library=lambda _t, _n: True,
        request_background=lambda _s, _n, _d: None,
        on_changed=lambda: None,
        windows=windows,
    )
    try:
        assert isinstance(dlg.dialog, wx.Frame)
        assert dlg.dialog.GetParent() is None
        dlg.show()
        assert len(windows) == 1
        dlg.dialog.Close()
        assert len(windows) == 0
        assert any("Exited" in message for message in said)
    finally:
        if dlg.dialog:
            dlg.dialog.Destroy()


def test_recordings_manager_source_carries_the_peer_window_shape() -> None:
    """Pinned as source: constructing the real manager needs a recorder, a
    scheduler, a controller and a recordings folder. What is defended is the
    seam -- the modeless branch exists, registers under the title the open
    guard raises by, and never ships a Close button in the window shape."""
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[3]
        / "quill"
        / "ui"
        / "radio"
        / "recordings_manager_dialog.py"
    ).read_text(encoding="utf-8")
    assert 'wx.Frame(None, title="Radio Recordings"' in source
    assert 'self._windows.register(self._win, "Radio Recordings")' in source
    assert "if not self._modeless:" in source, "the Close button is modal-only"

    caller = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_radio.py"
    ).read_text(encoding="utf-8")
    assert 'windows.activate_title("Radio Recordings")' in caller, (
        "already open must mean raise, not a second copy"
    )
