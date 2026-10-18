"""Radio history saves survive a vanished folder and a closed window, quietly.

Jeff, 2026-10-17: "Radio settings could not be saved" was spoken during test
runs. Three ways a save reached that sentence without anything being wrong
with the listener's settings: the data folder disappeared under the
background writer, a save arrived after the writer had been closed for
shutdown ("writer is closing"), and a failure arrived after the window was
gone. Each is covered here.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

from quill.core.radio.history import RadioHistory
from quill.core.radio.history_store import load_history
from quill.core.radio.history_writer import RadioHistorySnapshotWriter
from quill.ui.radio import history_save
from quill.ui.radio.history_save import RadioHistorySaveCoordinator


def test_a_data_folder_removed_under_the_writer_is_made_again(tmp_path: Path) -> None:
    data_dir = tmp_path / "quill-dev-data"
    calls: list[Path] = []

    def write(target: Path, snapshot: dict[str, object]) -> None:
        calls.append(target)
        if len(calls) == 1:
            shutil.rmtree(target, ignore_errors=True)
            raise FileNotFoundError(target)
        from quill.core.radio.history_store import save_history_snapshot

        save_history_snapshot(target, snapshot)

    data_dir.mkdir()
    writer = RadioHistorySnapshotWriter(write)
    failures: list[int] = []
    try:
        writer.submit(
            data_dir, {"resume_on_launch": True}, on_failure=lambda g, _e: failures.append(g)
        )
        assert writer.flush(3)
    finally:
        writer.close(2)
    assert failures == []
    assert load_history(data_dir).resume_on_launch is True


def test_a_save_after_shutdown_is_written_now_and_never_announced(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    said: list[str] = []
    history = RadioHistory()
    host = SimpleNamespace(_announce=said.append, _radio_history=history)
    assert history_save.save_history_async(host)
    assert history_save.close_history_writer(host)

    history.resume_on_launch = True
    assert history_save.save_history_async(host)  # used to raise "writer is closing"

    assert said == []
    assert load_history(tmp_path).resume_on_launch is True


def test_a_failure_after_the_window_closed_is_logged_not_spoken(tmp_path) -> None:
    said: list[str] = []
    window = SimpleNamespace()
    host = SimpleNamespace(_announce=said.append, frame=window)

    def fail(_dir: Path, _snapshot: dict[str, object]) -> None:
        raise OSError("disk unavailable")

    coordinator = RadioHistorySaveCoordinator(
        history_save._announcer_for(host),
        writer=RadioHistorySnapshotWriter(fail),
        dispatch=lambda work: work(),
    )
    coordinator.close()  # the window has gone before the failure lands
    coordinator._report_failure(1, OSError("late"))
    assert said == []


def test_a_destroyed_wx_window_is_not_open(wx_session_app) -> None:
    import wx

    frame = wx.Frame(None)
    host = SimpleNamespace(frame=frame)
    assert history_save._host_is_open(host)
    frame.Destroy()
    wx_session_app.ProcessPendingEvents()
    wx.SafeYield()
    assert not history_save._host_is_open(host)
