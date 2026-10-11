"""Tools > Dictation > Transcribe a Recording in QUILL Lite, through the handler
the menu binds (Shift+F5).

Nothing here decodes a file or loads a model: the window, the task manager and
the transcriber are replaced, and what is exercised is everything the command
itself decides -- what is queued, what is said and how often, where the text
goes, what Activity keeps, and that OpenAI asks first.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import pytest
import wx

from quill.core import activity, notifications
from quill.core.sound_events import SoundEvent
from quill.core.windows_dictation import file_transcribe
from quill.core.windows_dictation.file_models import FileModel
from quill.core.windows_dictation.file_transcribe import (
    FileTranscribeError,
    FileTranscript,
    Paragraph,
    TranscriptionCancelled,
)
from quill.stability.task_manager import CancellationToken, TaskManager
from quill.ui import dictation_transcribe_dialog as dialog_module
from quill.ui import windows_dictation_commands as shared
from quill.ui import windows_dictation_transcribe as runner
from quill.ui.dictation_transcribe_dialog import STOP_TRANSCRIBING, TranscribeChoice

_MOONSHINE = FileModel("moonshine", "Moonshine tiny (built in, fastest)", "", ("en",), 1.0)
_OPENAI = FileModel("openai:gpt-transcribe", "OpenAI gpt-transcribe", "", ("en", "es"), None)


class _FakeDialog:
    """The Transcribe a Recording window, answering what the test set."""

    answer: int = wx.ID_CANCEL
    chosen: TranscribeChoice | None = None
    made: list[dict[str, Any]] = []

    def __init__(self, parent: Any, **kwargs: Any) -> None:
        type(self).made.append(kwargs)
        self.destroyed = False

    def choice(self) -> TranscribeChoice | None:
        return type(self).chosen

    def Destroy(self) -> None:  # noqa: N802 - wx API shape
        self.destroyed = True


class _NowManager:
    """A task manager that runs the job at once, on this thread, and reports
    progress the way the real one delivers it."""

    def __init__(self) -> None:
        self.submitted: list[str] = []
        self.token = CancellationToken()

    def submit(self, name: str, func: Any, **callbacks: Any) -> None:
        self.submitted.append(name)
        on_progress = callbacks.get("on_progress")

        def progress(payload: Any) -> None:
            if on_progress is not None:
                on_progress(name, payload)

        try:
            result = func(
                cancellation_token=self.token, operation_id=name, progress_callback=progress
            )
        except BaseException as error:  # noqa: BLE001 - delivered like the real one
            callbacks["on_failure"](name, error)
            return
        callbacks["on_success"](name, result)


class _FakeTranscriber:
    """Stands in for FileTranscriber: reports every percent, then answers."""

    outcome: Any = None
    jobs: list[Any] = []

    def __init__(self, job: Any, rewrite: Any = None) -> None:
        self.job = job
        type(self).jobs.append(job)

    def run(self, progress: Any, cancelled: Any) -> FileTranscript:
        for percent in range(100):
            if cancelled():
                raise TranscriptionCancelled("Transcription stopped.")
            progress(percent / 100, percent * 0.6)
        if isinstance(type(self).outcome, BaseException):
            raise type(self).outcome
        return type(self).outcome or FileTranscript(
            (Paragraph(0.0, "Can you send me the report?"), Paragraph(83.0, "The meeting moved.")),
            audio_seconds=720.0,
            elapsed_seconds=180.0,
        )


@pytest.fixture
def transcribe(monkeypatch, lite_window, tmp_path):
    _FakeDialog.answer = wx.ID_CANCEL
    _FakeDialog.chosen = None
    _FakeDialog.made = []
    _FakeTranscriber.outcome = None
    _FakeTranscriber.jobs = []
    monkeypatch.setattr(dialog_module, "TranscribeFileDialog", _FakeDialog)
    monkeypatch.setattr(file_transcribe, "FileTranscriber", _FakeTranscriber)
    monkeypatch.setattr(runner, "_QUEUE", runner._Queue())
    monkeypatch.setattr(
        shared.WindowsDictationMixin,
        "_dictation_run_modal",
        lambda self, dialog, label: _FakeDialog.answer,
    )
    recording = tmp_path / "meeting.mp3"
    recording.write_bytes(b"not really sound")
    win = lite_window("Notes.", cursor=6)
    win.app.task_manager = _NowManager()
    opened: list[Any] = []

    def new_window(mode: str) -> Any:
        other = lite_window("")
        opened.append(other)
        return other

    win.app.new_window = new_window
    return win, recording, opened


def _choose(recording: Path, **changes: Any) -> None:
    values: dict[str, Any] = {
        "paths": (recording,),
        "model": _MOONSHINE,
        "language": "en",
        "timestamps": False,
        "obey_commands": False,
    }
    values.update(changes)
    _FakeDialog.answer = wx.ID_OK
    _FakeDialog.chosen = TranscribeChoice(**values)


def _stored_notices(win):
    return notifications.load_notifications(path=win._dictation_notification_path())


def test_transcript_is_private_and_opens_only_from_its_notification(transcribe):
    win, recording, opened = transcribe
    original = win.control.GetValue()
    selection = win.control.GetSelection()
    transcript_paths: list[Path] = []
    win._dictation_open_transcript = transcript_paths.append
    _choose(recording)
    win.cmd_transcribe_audio_file()
    assert opened == []
    assert win.control.GetValue() == original
    assert win.control.GetSelection() == selection
    assert transcript_paths == []
    notices = _stored_notices(win)
    assert len(notices) == 1
    notice = notices[0]
    assert notice.app == "QUILL Lite"
    assert notice.category == "success"
    assert notice.title == "Transcription complete: meeting.mp3"
    assert notice.target.startswith("dictation-transcript:")
    identifier = notice.target.removeprefix("dictation-transcript:")
    saved = Path(win.app.data_dir) / "dictation" / "transcripts" / f"{identifier}.txt"
    assert saved.read_text(encoding="utf-8") == "Can you send me the report?\n\nThe meeting moved."
    win.open_notification_target(notice.target)
    assert transcript_paths == [saved]
    said = " | ".join(win.announcements)
    assert "Transcribing meeting.mp3 in the background." in said
    assert "Transcribed meeting.mp3: 12 minutes, 9 words, in 3 minutes." in said
    assert "Open Notifications to read the transcript." in said
    kept = activity.LOG.recent()[0]
    assert kept.object_name == "meeting.mp3"
    assert not kept.is_problem
    assert runner._QUEUE.current is None


def test_notification_writes_run_off_the_ui_thread(transcribe, monkeypatch):
    win, recording, opened = transcribe
    app = wx.GetApp() or wx.App()
    manager = TaskManager(max_workers=1)
    win.app.task_manager = manager
    write_threads: list[int] = []
    ui_threads: list[int] = []
    original_add = notifications.add_notice
    original_update = notifications.update_notice

    def add_notice(**kwargs):
        write_threads.append(threading.get_ident())
        return original_add(**kwargs)

    def update_notice(*args, **kwargs):
        write_threads.append(threading.get_ident())
        return original_update(*args, **kwargs)

    monkeypatch.setattr(notifications, "add_notice", add_notice)
    monkeypatch.setattr(notifications, "update_notice", update_notice)
    original_status = win._dictation_status
    win._dictation_status = lambda text: (
        ui_threads.append(threading.get_ident()),
        original_status(text),
    )
    _choose(recording)
    try:
        win.cmd_transcribe_audio_file()
        deadline = time.monotonic() + 5
        while runner._QUEUE.current is not None and time.monotonic() < deadline:
            app.Yield()
            time.sleep(0.01)
        assert runner._QUEUE.current is None
        assert opened == []
        assert write_threads
        assert all(thread != threading.get_ident() for thread in write_threads)
        assert all(thread == threading.get_ident() for thread in ui_threads)
        assert any(line.startswith("Transcribed meeting.mp3:") for line in win.announcements)
    finally:
        manager.shutdown()


def test_notification_store_failure_does_not_fail_or_hide_the_transcript(transcribe, monkeypatch):
    win, recording, opened = transcribe

    def fail_write(*_args, **_kwargs):
        raise OSError("notification store unavailable")

    monkeypatch.setattr(notifications, "add_notice", fail_write)
    monkeypatch.setattr(notifications, "update_notice", fail_write)
    original = win.control.GetValue()
    _choose(recording)
    win.cmd_transcribe_audio_file()

    assert opened == []
    assert win.control.GetValue() == original
    assert not activity.LOG.recent()[0].is_problem
    assert any(
        "transcript was saved privately, but its completion could not be recorded" in line
        for line in win.announcements
    )
    assert _stored_notices(win) == []
    transcript_dir = Path(win.app.data_dir) / "dictation" / "transcripts"
    assert len(list(transcript_dir.glob("*.txt"))) == 1


def test_terminal_notice_retries_create_if_queued_notice_write_failed(transcribe, monkeypatch):
    win, recording, _opened = transcribe
    add_notice = notifications.add_notice
    writes = 0

    def fail_first_write(**kwargs):
        nonlocal writes
        writes += 1
        if writes == 1:
            raise OSError("notification store temporarily unavailable")
        return add_notice(**kwargs)

    monkeypatch.setattr(notifications, "add_notice", fail_first_write)
    _choose(recording)
    win.cmd_transcribe_audio_file()

    notices = _stored_notices(win)
    assert len(notices) == 1
    assert notices[0].title == "Transcription complete: meeting.mp3"
    assert notices[0].target.startswith("dictation-transcript:")
    assert writes == 2


def test_timestamp_option_is_saved_without_changing_the_editor(transcribe):
    win, recording, opened = transcribe
    original = win.control.GetValue()
    _choose(recording, timestamps=True)
    win.cmd_transcribe_audio_file()
    assert opened == []
    assert win.control.GetValue() == original
    notice = _stored_notices(win)[0]
    identifier = notice.target.removeprefix("dictation-transcript:")
    saved = Path(win.app.data_dir) / "dictation" / "transcripts" / f"{identifier}.txt"
    assert saved.read_text(encoding="utf-8") == (
        "[00:00:00] Can you send me the report?\n\n[00:01:23] The meeting moved."
    )


def test_progress_is_heard_at_quarters_only_and_shown_as_it_moves(transcribe):
    win, recording, _opened = transcribe
    _choose(recording)
    win.cmd_transcribe_audio_file()
    spoken = [line for line in win.announcements if line.startswith("meeting.mp3:")]
    assert spoken == [
        "meeting.mp3: 25 percent",
        "meeting.mp3: 50 percent",
        "meeting.mp3: 75 percent",
    ]
    shown = [line for line in win.status_messages if line.startswith("Transcribing meeting.mp3:")]
    assert len(shown) >= 90  # the status bar follows every percent


def test_cancel_in_the_window_queues_nothing(transcribe):
    win, _recording, opened = transcribe
    win.cmd_transcribe_audio_file()
    assert _FakeTranscriber.jobs == []
    assert opened == []
    assert win.app.task_manager.submitted == []


def test_a_failure_is_said_with_its_reason_and_kept_in_activity(transcribe):
    win, recording, opened = transcribe
    _FakeTranscriber.outcome = FileTranscribeError("meeting.mp3 could not be read as a recording.")
    _choose(recording)
    win.cmd_transcribe_audio_file()
    assert opened == []
    assert SoundEvent.WINDOWS_DICTATION_ERROR in win.cues
    assert any(
        "Could not transcribe meeting.mp3. meeting.mp3 could not be read" in line
        for line in win.announcements
    )
    kept = activity.LOG.recent()[0]
    assert kept.is_problem
    assert "could not be read" in kept.reason
    notice = _stored_notices(win)[0]
    assert notice.category == "error"
    assert notice.title == "Transcription failed: meeting.mp3"
    assert "could not be read" in notice.body


def test_stopping_is_retained_as_a_notification(transcribe):
    win, recording, opened = transcribe
    _FakeTranscriber.outcome = TranscriptionCancelled("Transcription stopped.")
    _choose(recording)
    win.cmd_transcribe_audio_file()
    assert opened == []
    assert "Stopped transcribing meeting.mp3." in win.announcements
    notice = _stored_notices(win)[0]
    assert notice.category == "warning"
    assert notice.title == "Transcription canceled: meeting.mp3"


def test_a_cancelled_task_token_stops_without_writing(transcribe):
    win, recording, opened = transcribe
    win.app.task_manager.token.cancel()
    _choose(recording)
    win.cmd_transcribe_audio_file()
    assert opened == []
    assert "Stopped transcribing meeting.mp3." in win.announcements
    assert runner._QUEUE.current is None


def test_stop_transcribing_cancels_the_running_one_and_forgets_the_rest(transcribe):
    win, recording, _opened = transcribe
    from quill.core.windows_dictation.file_transcribe import FileJob

    running = runner._Entry(FileJob(recording, "moonshine"), win)
    waiting = runner._Entry(FileJob(recording, "moonshine"), win)
    runner._QUEUE.current = running
    runner._QUEUE.waiting.append(waiting)
    _FakeDialog.answer = STOP_TRANSCRIBING
    win.cmd_transcribe_audio_file()
    assert _FakeDialog.made[0]["running"].startswith("meeting.mp3, 0 percent done. 1 more")
    assert running.cancel.is_set()
    assert runner._QUEUE.waiting == []
    assert any(
        "Stopping the transcription of meeting.mp3, and 1 waiting recording canceled" in line
        for line in win.announcements
    )
    assert waiting.notice_future is not None
    assert waiting.notice_future.result()
    queued_notice = _stored_notices(win)[0]
    assert queued_notice.title == "Transcription canceled: meeting.mp3"


def test_several_recordings_run_one_after_another(transcribe, tmp_path):
    win, recording, opened = transcribe
    second = tmp_path / "lecture.m4a"
    second.write_bytes(b"x")
    _choose(recording, paths=(recording, second))
    win.cmd_transcribe_audio_file()
    assert [job.path.name for job in _FakeTranscriber.jobs] == ["meeting.mp3", "lecture.m4a"]
    assert opened == []
    assert [notice.title for notice in _stored_notices(win)] == [
        "Transcription complete: meeting.mp3",
        "Transcription complete: lecture.m4a",
    ]


def test_openai_asks_first_and_no_sends_nothing(transcribe, monkeypatch):
    win, recording, _opened = transcribe
    import quill.ui.dialog_contract as contract

    asked: list[str] = []

    def answer(message: str, caption: str, style: int, parent: Any = None, **_k: Any) -> int:
        asked.append(message)
        assert style & wx.NO_DEFAULT  # No is the default
        return wx.NO

    monkeypatch.setattr(contract, "show_message_box", answer)
    monkeypatch.setattr("quill.core.windows_dictation.openai_models.load_key", lambda: "key")
    _choose(recording, model=_OPENAI)
    win.cmd_transcribe_audio_file()
    assert asked and "sends this recording to OpenAI" in asked[0]
    assert _FakeTranscriber.jobs == []


def test_openai_yes_sends_with_my_words(transcribe, monkeypatch):
    win, recording, _opened = transcribe
    import quill.ui.dialog_contract as contract

    monkeypatch.setattr(contract, "show_message_box", lambda *a, **k: wx.YES)
    monkeypatch.setattr("quill.core.windows_dictation.openai_models.load_key", lambda: "key")
    (Path(win.app.data_dir) / "dictation.md").write_text(
        "# Vocabulary\n\n- Okonkwo\n", encoding="utf-8"
    )
    _choose(recording, model=_OPENAI)
    win.cmd_transcribe_audio_file()
    job = _FakeTranscriber.jobs[0]
    assert job.model == "openai:gpt-transcribe"
    assert isinstance(job.keywords, tuple)


def test_safe_mode_blocks_openai_before_consent_or_submission(transcribe, monkeypatch):
    win, recording, _opened = transcribe
    asked: list[bool] = []
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    monkeypatch.setattr(
        win,
        "_transcribe_consent",
        lambda: (asked.append(True), True)[1],
    )
    _choose(recording, model=_OPENAI)
    win.cmd_transcribe_audio_file()
    assert asked == []
    assert win.app.task_manager.submitted == []
    assert any("Safe Mode is on" in line for line in win.announcements)
