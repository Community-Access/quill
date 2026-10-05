"""Tools > Dictation > Transcribe a Recording in QUILL Lite, through the handler
the menu binds (Shift+F5).

Nothing here decodes a file or loads a model: the window, the task manager and
the transcriber are replaced, and what is exercised is everything the command
itself decides -- what is queued, what is said and how often, where the text
goes, what Activity keeps, and that OpenAI asks first.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import wx

from quill.core import activity
from quill.core.sound_events import SoundEvent
from quill.core.windows_dictation import file_transcribe
from quill.core.windows_dictation.file_models import FileModel
from quill.core.windows_dictation.file_transcribe import (
    FileTranscribeError,
    FileTranscript,
    Paragraph,
    TranscriptionCancelled,
)
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

    def submit(self, name: str, func: Any, **callbacks: Any) -> None:
        self.submitted.append(name)
        on_progress = callbacks.get("on_progress")

        def progress(payload: Any) -> None:
            if on_progress is not None:
                on_progress(name, payload)

        try:
            result = func(cancellation_token=None, operation_id=name, progress_callback=progress)
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
        "destination": "new",
        "timestamps": False,
        "obey_commands": False,
    }
    values.update(changes)
    _FakeDialog.answer = wx.ID_OK
    _FakeDialog.chosen = TranscribeChoice(**values)


def test_the_transcript_opens_in_a_new_document_with_one_sentence(transcribe):
    win, recording, opened = transcribe
    _choose(recording)
    win.cmd_transcribe_audio_file()
    assert len(opened) == 1
    assert opened[0].control.GetValue() == "Can you send me the report?\n\nThe meeting moved."
    assert opened[0].modified
    assert win.control.GetValue() == "Notes."  # this document is untouched
    said = " | ".join(win.announcements)
    assert "Transcribing meeting.mp3 in the background." in said
    assert "Transcribed meeting.mp3: 12 minutes, 9 words, in 3 minutes, in a new document." in said
    kept = activity.LOG.recent()[0]
    assert kept.object_name == "meeting.mp3"
    assert not kept.is_problem
    assert runner._QUEUE.current is None


def test_at_the_cursor_it_is_its_own_paragraphs_and_one_undo(transcribe):
    win, recording, opened = transcribe
    _choose(recording, destination="cursor", timestamps=True)
    win.cmd_transcribe_audio_file()
    assert opened == []
    assert win.control.GetValue() == (
        "Notes.\n\n[00:00:00] Can you send me the report?\n\n[00:01:23] The meeting moved."
    )
    assert any(line.endswith("at the cursor.") for line in win.announcements)


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


def test_stopping_is_said_and_writes_nothing(transcribe):
    win, recording, opened = transcribe
    _FakeTranscriber.outcome = TranscriptionCancelled("Transcription stopped.")
    _choose(recording)
    win.cmd_transcribe_audio_file()
    assert opened == []
    assert "Stopped transcribing meeting.mp3." in win.announcements


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
        "Stopping the transcription of meeting.mp3, and 1 waiting recording forgotten" in line
        for line in win.announcements
    )


def test_several_recordings_run_one_after_another(transcribe, tmp_path):
    win, recording, opened = transcribe
    second = tmp_path / "lecture.m4a"
    second.write_bytes(b"x")
    _choose(recording, paths=(recording, second))
    win.cmd_transcribe_audio_file()
    assert [job.path.name for job in _FakeTranscriber.jobs] == ["meeting.mp3", "lecture.m4a"]
    assert len(opened) == 2


def test_openai_asks_first_and_no_sends_nothing(transcribe, monkeypatch):
    win, recording, _opened = transcribe
    import quill.ui.dialog_contract as contract

    asked: list[str] = []

    def answer(message: str, caption: str, style: int, parent: Any = None, **_k: Any) -> int:
        asked.append(message)
        assert style & wx.NO_DEFAULT  # No is the default
        return wx.NO

    monkeypatch.setattr(contract, "show_message_box", answer)
    _choose(recording, model=_OPENAI)
    win.cmd_transcribe_audio_file()
    assert asked and "sends this recording to OpenAI" in asked[0]
    assert _FakeTranscriber.jobs == []


def test_openai_yes_sends_with_my_words(transcribe, monkeypatch):
    win, recording, _opened = transcribe
    import quill.ui.dialog_contract as contract

    monkeypatch.setattr(contract, "show_message_box", lambda *a, **k: wx.YES)
    (Path(win.app.data_dir) / "dictation.md").write_text(
        "# Vocabulary\n\n- Okonkwo\n", encoding="utf-8"
    )
    _choose(recording, model=_OPENAI)
    win.cmd_transcribe_audio_file()
    job = _FakeTranscriber.jobs[0]
    assert job.model == "openai:gpt-transcribe"
    assert isinstance(job.keywords, tuple)
