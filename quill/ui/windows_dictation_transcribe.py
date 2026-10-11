"""Transcribe a Recording: dictation's engines on a recording, in the background.

Shared by QUILL and QUILL Lite, like every dictation command: QUILL Lite mixes
it in through :class:`~quill.ui.windows_dictation_commands.WindowsDictationMixin`,
and QUILL reaches it on the same key (Shift+F5) through its adapter, which
answers two hooks and has no command of its own.

**What happens.** The window (:mod:`quill.ui.dictation_transcribe_dialog`)
asks for the recording, model, language and transcription options. The work
runs on the editor's task manager -- never on the interface thread -- in
:class:`~quill.core.windows_dictation.file_transcribe.FileTranscriber`, so the
person keeps editing while it runs. Several recordings wait their turn and run
one after another. Progress and outcomes are retained in Notifications. A
successful transcript is saved privately and opened only when its notice is
activated.

**What is heard** (GATE-13: only what the screen reader cannot know):

* one sentence when it starts ("Transcribing meeting.mp3 in the background");
* the percentage at each quarter, quietly, and the same percentage in the
  status bar as it moves (never spoken more often than that);
* one sentence when it finishes ("Transcribed meeting.mp3: 12 minutes, 1,804
  words, in 3 minutes.") or fails, with the plain reason;
* the error tone on failure.

Every result, finished or failed, is also kept in Activity, so a sentence said
while the person was elsewhere is still there to read.

**OpenAI** is offered only with the person's own key, outside Safe Mode, and
asks before each recording is sent
(:data:`~quill.core.windows_dictation.file_models.FILE_CONSENT_TEXT`; No is the
default).
"""

from __future__ import annotations

import itertools
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

import wx

__all__ = ["DictationTranscribeMixin", "queue_text"]

_ACTION = "Transcribe"
_TASK = "dictation-transcribe-file"
_ids = itertools.count(1)


@dataclass
class _Entry:
    job: Any  # FileJob
    host: Any
    rewrite: Callable[[str], str] | None = None
    cancel: threading.Event = field(default_factory=threading.Event)
    operation: str = ""
    percent: int = 0
    notice_id: str = ""
    notified_percent: int = 0
    notice_error: str = ""
    notice_future: Future[bool] | None = None


@dataclass
class _Queue:
    """The recording being transcribed, and the ones waiting after it."""

    current: _Entry | None = None
    waiting: list[_Entry] = field(default_factory=list)

    def describe(self) -> str:
        if self.current is None:
            return ""
        name = self.current.job.path.name
        text = f"{name}, {self.current.percent} percent done."
        if self.waiting:
            count = len(self.waiting)
            text += f" {count} more recording{'s' if count != 1 else ''} waiting."
        return text


class _TranscriptPersistenceError(Exception):
    """Transcription succeeded, but its saved transcript could not be recorded."""


_QUEUE = _Queue()
_NOTICE_WRITER = ThreadPoolExecutor(max_workers=1, thread_name_prefix="quill-transcription-notices")


@dataclass(frozen=True, slots=True)
class _Result:
    transcript: Any = None
    error: BaseException | None = None
    notice_error: str = ""


def queue_text() -> str:
    """What is being transcribed now, for the window's status line ("" when nothing)."""
    return _QUEUE.describe()


class DictationTranscribeMixin:
    """The Transcribe a Recording command and its background runner."""

    # -- hooks: QUILL Lite's answers; QUILL overrides them ------------------- #

    def _dictation_task_manager(self) -> Any:
        """The app's one task manager, made the first time it is needed."""
        app = getattr(self, "app", None)
        manager = getattr(app, "task_manager", None)
        if manager is None:
            from quill.stability.task_manager import TaskManager

            manager = TaskManager(max_workers=2)
            if app is not None:
                app.task_manager = manager
        return manager

    # -- the command ----------------------------------------------------------- #

    def cmd_transcribe_audio_file(self, paths: list[Path] | None = None) -> None:
        """Choose a recording and a model; the text arrives when it is ready."""
        from quill.ui.dictation_transcribe_dialog import STOP_TRANSCRIBING, TranscribeFileDialog

        preferences = self._dictation_preferences()  # type: ignore[attr-defined]
        dialog = TranscribeFileDialog(
            self._dictation_parent(),  # type: ignore[attr-defined]
            language=preferences.speech_language,
            paths=paths or (),
            running=queue_text(),
        )
        try:
            answer = self._dictation_run_modal(dialog, "Transcribe a Recording")  # type: ignore[attr-defined]
            choice = dialog.choice() if answer == wx.ID_OK else None
        finally:
            dialog.Destroy()
        if answer == STOP_TRANSCRIBING:
            self._transcribe_stop()
            return
        if choice is None:
            return
        if choice.model.cloud:
            from quill.core.windows_dictation.openai_models import cloud_problem

            problem = cloud_problem()
            if problem:
                self._dictation_say(problem)  # type: ignore[attr-defined]
                return
            if not self._transcribe_consent():
                return
        from quill.core.windows_dictation.file_transcribe import FileJob

        keywords: tuple[str, ...] = ()
        if choice.model.cloud:
            keywords = self._transcribe_keywords()
        for path in choice.paths:
            job = FileJob(
                path=path,
                model=choice.model.id,
                language=choice.language,
                timestamps=choice.timestamps,
                obey_commands=choice.obey_commands,
                remove_fillers=preferences.remove_fillers,
                dash=preferences.dash,
                keywords=keywords,
            )
            entry = _Entry(job, self, preferences.rewrite)
            _QUEUE.waiting.append(entry)
            _queue_notice(
                entry,
                title=f"Transcription queued: {path.name}",
                body="Waiting for the recordings ahead of it.",
                category="progress",
                create=True,
            )
        if _QUEUE.current is not None:
            count = len(_QUEUE.waiting)
            self._dictation_say(  # type: ignore[attr-defined]
                f"Added to the queue; {count} recording{'s' if count != 1 else ''} waiting."
            )
            return
        _start_next()

    # -- pieces ------------------------------------------------------------------ #

    def _transcribe_consent(self) -> bool:
        from quill.core.windows_dictation.file_models import FILE_CONSENT_TEXT
        from quill.ui.dialog_contract import show_message_box

        answer = show_message_box(
            FILE_CONSENT_TEXT,
            "Send this recording to OpenAI?",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self._dictation_parent(),  # type: ignore[attr-defined]
        )
        return bool(answer == wx.YES)

    def _transcribe_keywords(self) -> tuple[str, ...]:
        from quill.core.windows_dictation.profile import load

        try:
            return tuple(load(self._dictation_profile_path()).vocabulary)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - no words is a fine answer
            return ()

    def _transcribe_stop(self) -> None:
        waiting = list(_QUEUE.waiting)
        _QUEUE.waiting.clear()
        current = _QUEUE.current
        for entry in waiting:
            _cancel_notice(entry)
        if current is None:
            self._dictation_say("Nothing is being transcribed.")  # type: ignore[attr-defined]
            return
        current.cancel.set()
        plural = "s" if len(waiting) != 1 else ""
        extra = f", and {len(waiting)} waiting recording{plural} canceled" if waiting else ""
        self._dictation_say(f"Stopping the transcription of {current.job.path.name}{extra}.")  # type: ignore[attr-defined]

    def _dictation_data_dir(self) -> Path:
        app = getattr(self, "app", None)
        if getattr(app, "frames", None) is not None:
            app_data = getattr(app, "data_dir", None)
            if app_data is not None:
                return Path(app_data)
            from quill.core.lite.paths import data_dir

            return data_dir()
        from quill.core.paths import app_data_dir

        return app_data_dir()

    def _dictation_notification_path(self) -> Path:
        from quill.core.notifications import notifications_path

        return notifications_path(self._dictation_data_dir())

    def _dictation_app_name(self) -> str:
        if getattr(getattr(self, "app", None), "frames", None) is not None:
            from quill.core.lite import APP_NAME

            return APP_NAME
        return "QUILL"

    def _dictation_open_transcript(self, path: Path) -> None:
        self._dictation_open_file(path)  # type: ignore[attr-defined]

    def open_dictation_notifications(self) -> None:
        from quill.ui.notification_center import open_notification_center

        open_notification_center(
            self,
            on_open=self.open_notification_target,
            path=self._dictation_notification_path(),
        )

    def open_notification_target(self, target: str) -> None:
        """Open a saved dictation transcript only after its notice is activated."""
        prefix = "dictation-transcript:"
        target = str(target)
        identifier = target[len(prefix) :].lower() if target.startswith(prefix) else ""
        if len(identifier) != 32 or any(
            char not in "0123456789abcdef" for char in identifier.lower()
        ):
            self._dictation_say("This notification has no transcript to open.")  # type: ignore[attr-defined]
            return
        path = self._dictation_data_dir() / "dictation" / "transcripts" / f"{identifier}.txt"
        if not path.is_file():
            self._dictation_say("That transcript is no longer available.")  # type: ignore[attr-defined]
            return
        self._dictation_open_transcript(path)

    def _dictation_save_transcript(self, text: str) -> str:
        from quill.core.storage import write_text_atomic

        identifier = uuid4().hex
        path = self._dictation_data_dir() / "dictation" / "transcripts" / f"{identifier}.txt"
        try:
            write_text_atomic(path, text, encoding="utf-8", newline="")
        except Exception as error:
            raise _TranscriptPersistenceError(str(error)) from error
        return identifier


def _queue_notice(
    entry: _Entry,
    *,
    title: str,
    body: str,
    category: str,
    target: str = "",
    create: bool = False,
) -> Future[bool]:
    """Serialize notification-store I/O on a worker, never on the UI event path."""

    def write() -> bool:
        try:
            from quill.core.notifications import add_notice, update_notice

            path = entry.host._dictation_notification_path()
            if create or not entry.notice_id:
                notices = add_notice(
                    app=entry.host._dictation_app_name(),
                    title=title,
                    body=body,
                    target=target,
                    category=category,
                    path=path,
                )
                if not notices:
                    raise OSError("The notification was not saved.")
                entry.notice_id = notices[-1].id
            elif not entry.notice_id or not update_notice(
                entry.notice_id,
                title=title,
                body=body,
                target=target,
                category=category,
                path=path,
            ):
                raise OSError("The notification is no longer available.")
            entry.notice_error = ""
            return True
        except Exception as error:  # noqa: BLE001 - notification failure is separate from transcription
            entry.notice_error = f"{type(error).__name__}: notification could not be saved."
            return False

    try:
        future = _NOTICE_WRITER.submit(write)
    except RuntimeError:
        entry.notice_error = "RuntimeError: notification could not be saved."
        future = Future()
        future.set_result(False)
    entry.notice_future = future
    return future


def _cancel_notice(entry: _Entry) -> None:
    future = _queue_notice(
        entry,
        title=f"Transcription canceled: {entry.job.path.name}",
        body="Canceled before it started.",
        category="warning",
        create=entry.notice_future is None,
    )

    def report_failure(done: Future[bool]) -> None:
        if done.result():
            return
        wx.CallAfter(
            entry.host._dictation_say,
            f"The canceled transcription of {entry.job.path.name} could not be kept "
            f"in Notifications. {entry.notice_error}",
        )

    future.add_done_callback(report_failure)


def _start_next() -> None:
    """Start the first waiting recording, if nothing is running."""
    if _QUEUE.current is not None or not _QUEUE.waiting:
        return
    entry = _QUEUE.waiting.pop(0)
    _QUEUE.current = entry
    host = entry.host
    name = entry.job.path.name
    from quill.core import activity

    entry.operation = f"transcribe-{next(_ids)}"
    message = f"Transcribing {name}"
    announcer = activity.ProgressAnnouncer(step=25)
    first = activity.Progress(entry.operation, "transcribing", message, 0, 100, can_cancel=True)
    activity.LOG.begin(first)
    announcer.next_sentence(first)  # the phase is said below, once, in words of its own
    host._dictation_say(f"Transcribing {name} in the background.")
    host._dictation_status(f"{message}...")

    from quill.core.windows_dictation.file_transcribe import FileTranscriber

    def work(cancellation_token: Any = None, progress_callback: Any = None, **_kwargs: Any) -> Any:
        if entry.notice_future is None:
            _queue_notice(
                entry,
                title=f"Transcription queued: {name}",
                body="Waiting to start.",
                category="progress",
                create=True,
            )
        _queue_notice(
            entry,
            title=f"Transcribing: {name}",
            body="Transcription is running.",
            category="progress",
        )

        def cancelled() -> bool:
            token_says = bool(cancellation_token is not None and cancellation_token.is_cancelled())
            return entry.cancel.is_set() or token_says

        def progress(fraction: float | None, seconds: float) -> None:
            if fraction is not None:
                percent = int(fraction * 100)
                if percent >= entry.notified_percent + 25 and percent < 100:
                    entry.notified_percent = percent - (percent % 25)
                    _queue_notice(
                        entry,
                        title=f"Transcribing: {name}",
                        body=f"{entry.notified_percent} percent complete.",
                        category="progress",
                    )
            if progress_callback is not None:
                progress_callback((fraction, seconds))

        from quill.core.windows_dictation.file_transcribe import (
            TranscriptionCancelled,
            done_sentence,
            plain,
        )

        try:
            transcript = FileTranscriber(entry.job, rewrite=entry.rewrite).run(progress, cancelled)
            if entry.cancel.is_set():
                raise TranscriptionCancelled("Transcription stopped.")
        except Exception as error:  # noqa: BLE001 - persist terminal state without failing the worker
            canceled = isinstance(error, TranscriptionCancelled)
            notice_saved = _queue_notice(
                entry,
                title=f"Transcription {'canceled' if canceled else 'failed'}: {name}",
                body=plain(error),
                category="warning" if canceled else "error",
            ).result()
            return _Result(error=error, notice_error="" if notice_saved else entry.notice_error)

        text = transcript.text(entry.job.timestamps)
        sentence = done_sentence(name, transcript)
        transcript_id = ""
        storage_error: BaseException | None = None
        if text.strip():
            try:
                transcript_id = host._dictation_save_transcript(text)
            except Exception as error:  # noqa: BLE001 - transcription succeeded; delivery did not
                storage_error = error
        if transcript.notice:
            sentence += " " + transcript.notice
        if storage_error is not None:
            title = f"Transcript could not be saved: {name}"
            body = f"{sentence} The transcript could not be saved privately."
            target = ""
            category = "error"
        else:
            title = f"Transcription complete: {name}"
            body = sentence
            target = f"dictation-transcript:{transcript_id}" if transcript_id else ""
            category = "success"
        notice_saved = _queue_notice(
            entry,
            title=title,
            body=body,
            target=target,
            category=category,
        ).result()
        return _Result(
            transcript=transcript,
            error=storage_error,
            notice_error="" if notice_saved else entry.notice_error,
        )

    def on_progress(_operation: str, payload: Any) -> None:
        fraction, seconds = payload
        if fraction is None:
            from quill.core.windows_dictation.file_models import spoken_length

            host._dictation_status(f"{message}: {spoken_length(seconds)} heard")
            return
        entry.percent = int(fraction * 100)
        update = activity.Progress(
            entry.operation, "transcribing", message, entry.percent, 100, can_cancel=True
        )
        activity.LOG.update(update)
        host._dictation_status(f"{message}: {entry.percent} percent")
        sentence = announcer.next_sentence(update)
        if sentence and entry.percent < 100:
            host._dictation_say_quietly(f"{name}: {entry.percent} percent")

    def finished(_operation: str, transcript: Any) -> None:
        _finish(entry, transcript, None)

    def failed(_operation: str, error: BaseException) -> None:
        _finish(entry, None, error)

    try:
        host._dictation_task_manager().submit(
            _TASK, work, on_success=finished, on_failure=failed, on_progress=on_progress
        )
    except Exception as error:  # noqa: BLE001 - reported like any failure
        _finish(entry, None, error)


def _finish(entry: _Entry, transcript: Any, error: BaseException | None) -> None:
    """Report one recording without opening or changing an editor."""
    from quill.core import activity
    from quill.core.sound_events import SoundEvent
    from quill.core.windows_dictation.file_transcribe import (
        TranscriptionCancelled,
        done_sentence,
        plain,
    )
    from quill.ui.outcome_report import keep_outcome

    activity.LOG.end(entry.operation)
    _QUEUE.current = None
    host = entry.host
    name = entry.job.path.name
    host._dictation_status("")
    has_worker_result = isinstance(transcript, _Result)
    result = transcript if has_worker_result else _Result(transcript, error)
    transcript = result.transcript
    error = result.error
    if isinstance(error, TranscriptionCancelled):
        if not has_worker_result:
            _report_notice_failure(
                entry,
                _queue_notice(
                    entry,
                    title=f"Transcription canceled: {name}",
                    body="Transcription stopped.",
                    category="warning",
                ),
                f"The canceled transcription of {name} could not be kept in Notifications.",
            )
        keep_outcome(_ACTION, f"Stopped transcribing {name}.", object_name=name)
        sentence = f"Stopped transcribing {name}."
        if result.notice_error:
            sentence += f" It could not be kept in Notifications. {result.notice_error}"
        host._dictation_say(sentence)
    elif error is not None:
        reason = plain(error)
        if isinstance(error, _TranscriptPersistenceError):
            summary = f"Transcribed {name}, but could not save the transcript."
            reason = (
                f"The recording was transcribed, but the transcript could not be saved: {reason}"
            )
        else:
            summary = f"Could not transcribe {name}."
        if not has_worker_result:
            _report_notice_failure(
                entry,
                _queue_notice(
                    entry,
                    title=f"Transcription failed: {name}",
                    body=reason,
                    category="error",
                ),
                f"The outcome for {name} could not be kept in Notifications.",
            )
        if result.notice_error:
            reason += f" The outcome could not be kept in Notifications. {result.notice_error}"
        keep_outcome(_ACTION, summary, object_name=name, failed=True, reason=reason)
        host._dictation_cue(SoundEvent.WINDOWS_DICTATION_ERROR)
        host._dictation_say(f"{summary} {reason}")
    else:
        sentence = done_sentence(name, transcript)
        text = transcript.text(entry.job.timestamps)
        if transcript.notice:
            sentence += " " + transcript.notice
        if result.notice_error:
            sentence += (
                " The transcript was saved privately, but its completion could not "
                f"be recorded in Notifications. {result.notice_error}"
            )
        elif text.strip():
            sentence += " Open Notifications to read the transcript."
        else:
            sentence += " No transcript text was produced."
        keep_outcome(_ACTION, sentence, object_name=name)
        host._dictation_say(sentence)
    _start_next()


def _report_notice_failure(entry: _Entry, future: Future[bool], message: str) -> None:
    """Surface an asynchronous notice-write failure through the UI announcer."""

    def completed(done: Future[bool]) -> None:
        if not done.result():
            wx.CallAfter(entry.host._dictation_say, f"{message} {entry.notice_error}")

    future.add_done_callback(completed)
