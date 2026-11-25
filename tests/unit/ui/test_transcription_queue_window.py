from __future__ import annotations

from pathlib import Path

import wx

from quill.core.windows_dictation.file_queue import (
    DONE,
    FAILED,
    QUEUED,
    STOPPED,
    TranscriptionJob,
    TranscriptionQueue,
)
from quill.ui import transcription_queue_runtime as runtime
from quill.ui import transcription_queue_window as queue_window


class _Host:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.said: list[str] = []
        self.opened: list[Path] = []

    def _dictation_data_dir(self) -> Path:
        return self.data_dir

    def _dictation_app_name(self) -> str:
        return "QUILL"

    def _dictation_say(self, text: str) -> None:
        self.said.append(text)

    def _dictation_open_transcript(self, path: Path) -> None:
        self.opened.append(path)


def test_modeless_queue_lists_and_runs_each_job_action(
    wx_session_app, tmp_path: Path, monkeypatch
) -> None:
    host = _Host(tmp_path)
    transcript = tmp_path / "saved.txt"
    transcript.write_text("The transcript.", encoding="utf-8")
    queue = TranscriptionQueue(tmp_path)
    queued = TranscriptionJob(
        app="QUILL", source_path=str(tmp_path / "queued.mp3"), state=QUEUED, batch="Interview"
    )
    failed = TranscriptionJob(app="QUILL", source_path=str(tmp_path / "failed.mp3"), state=FAILED)
    done = TranscriptionJob(
        app="QUILL",
        source_path=str(tmp_path / "done.mp3"),
        state=DONE,
        progress=1.0,
        output_path=str(transcript),
    )
    queue.add([queued, failed, done])
    monkeypatch.setattr(runtime, "resume", lambda _host: 0)
    window = queue_window.TranscriptionsWindow(None, host)
    try:
        assert window.list.GetItemCount() == 3
        assert "3 transcription jobs" in window.summary.GetLabel()

        window.list.Select(2, True)
        window._sync_selected()
        assert window.open_button.IsEnabled()
        window._open()
        assert host.opened == [transcript]

        window.list.Select(1, True)
        window._sync_selected()
        assert window.retry_button.IsEnabled()
        window._retry()
        assert queue.get(failed.id).state == QUEUED

        window.list.Select(0, True)
        window._sync_selected()
        assert window.stop_button.IsEnabled()
        window._stop()
        assert queue.get(queued.id).state == STOPPED
        window._sync_selected()
        assert window.forget_button.IsEnabled()
        window._forget()
        assert queue.get(queued.id) is None
    finally:
        window._timer.Stop()
        window.Destroy()
        wx_session_app.Yield()


def test_queue_window_is_modeless_and_has_a_real_close_path(wx_session_app, tmp_path: Path) -> None:
    window = queue_window.TranscriptionsWindow(None, _Host(tmp_path))
    timer = window._timer
    try:
        assert not window.IsModal()
        assert window.close_button.GetId() == wx.ID_CLOSE
        assert window.list.GetName() == "Transcription jobs"
    finally:
        window.Close()
        wx_session_app.Yield()
        assert not timer.IsRunning()
