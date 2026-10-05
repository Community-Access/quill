"""Transcribe a Recording: dictation's engines on a recording, in the background.

Shared by QUILL and QUILL Lite, like every dictation command: QUILL Lite mixes
it in through :class:`~quill.ui.windows_dictation_commands.WindowsDictationMixin`,
and QUILL reaches it on the same key (Shift+F5) through its adapter, which
answers two hooks and has no command of its own.

**What happens.** The window (:mod:`quill.ui.dictation_transcribe_dialog`)
asks for the recording, the model, the language and where the text goes. The
work runs on the editor's task manager -- never on the interface thread -- in
:class:`~quill.core.windows_dictation.file_transcribe.FileTranscriber`, so the
person keeps editing while it runs. Several recordings wait their turn and run
one after another.

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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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


_QUEUE = _Queue()


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

    def _dictation_new_document(self, text: str, name: str) -> None:
        """Open *text* as a new untitled document (QUILL Lite: a new window)."""
        app = self.app  # type: ignore[attr-defined]
        window = app.new_window(app.settings.default_mode)
        window.control.SetValue(text)
        window.control.SetInsertionPoint(0)
        window._set_modified(True)
        window._touch_status()

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
        if choice.model.cloud and not self._transcribe_consent():
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
                destination=choice.destination,
                keywords=keywords,
            )
            _QUEUE.waiting.append(_Entry(job, self, preferences.rewrite))
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
        waiting = len(_QUEUE.waiting)
        _QUEUE.waiting.clear()
        current = _QUEUE.current
        if current is None:
            self._dictation_say("Nothing is being transcribed.")  # type: ignore[attr-defined]
            return
        current.cancel.set()
        plural = "s" if waiting != 1 else ""
        extra = f", and {waiting} waiting recording{plural} forgotten" if waiting else ""
        self._dictation_say(f"Stopping the transcription of {current.job.path.name}{extra}.")  # type: ignore[attr-defined]

    def _transcribe_deliver(self, text: str, job: Any) -> str:
        """Put *text* where *job* asked; returns where it went, for the sentence."""
        name = Path(job.path).stem
        if job.destination == "cursor":
            reason = self._transcribe_cursor_problem()
            if not reason:
                self._transcribe_insert(text)
                return "at the cursor"
            self._dictation_new_document(text, name)
            return f"in a new document, because {reason}"
        self._dictation_new_document(text, name)
        return "in a new document"

    def _transcribe_cursor_problem(self) -> str:
        try:
            control = self._dictation_control()  # type: ignore[attr-defined]
            if not control:
                return "the document it was meant for has been closed"
            if not control.IsEditable():
                return "that document is read-only"
        except Exception:  # noqa: BLE001 - a window that has gone away
            return "the document it was meant for has been closed"
        return ""

    def _transcribe_insert(self, text: str) -> None:
        """The transcript at the cursor, as paragraphs of its own, in one undo step."""
        from quill.ui.atomic_edit import replace_as_one_undo

        control = self._dictation_control()  # type: ignore[attr-defined]
        start, end = (int(value) for value in control.GetSelection())
        before = control.GetRange(max(0, start - 1), start)
        after = control.GetRange(end, min(end + 1, control.GetLastPosition()))
        if before and before not in "\r\n":
            text = "\n\n" + text
        if after and after not in "\r\n":
            text += "\n\n"
        replace_as_one_undo(control, start, end, text)
        self._dictation_after_edit()  # type: ignore[attr-defined]


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
        def cancelled() -> bool:
            token_says = bool(cancellation_token is not None and cancellation_token.is_cancelled)
            return entry.cancel.is_set() or token_says

        def progress(fraction: float | None, seconds: float) -> None:
            if progress_callback is not None:
                progress_callback((fraction, seconds))

        return FileTranscriber(entry.job, rewrite=entry.rewrite).run(progress, cancelled)

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
    """Deliver or report one recording, then start the next."""
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
    if isinstance(error, TranscriptionCancelled):
        keep_outcome(_ACTION, f"Stopped transcribing {name}.", object_name=name)
        host._dictation_say(f"Stopped transcribing {name}.")
    elif error is not None:
        reason = plain(error)
        summary = f"Could not transcribe {name}."
        keep_outcome(_ACTION, summary, object_name=name, failed=True, reason=reason)
        host._dictation_cue(SoundEvent.WINDOWS_DICTATION_ERROR)
        host._dictation_say(f"Could not transcribe {name}. {reason}")
    else:
        sentence = done_sentence(name, transcript)
        text = transcript.text(entry.job.timestamps)
        if text.strip():
            try:
                where = host._transcribe_deliver(text, entry.job)
            except Exception as problem:  # noqa: BLE001 - the text must not be lost
                where = ""
                host._dictation_copy(text)
                sentence += (
                    f" It could not be put in a document ({plain(problem)}), "
                    "so it is on the clipboard."
                )
            if where:
                sentence = sentence[:-1] + f", {where}."
        if transcript.notice:
            sentence += " " + transcript.notice
        keep_outcome(_ACTION, sentence, object_name=name)
        host._dictation_say(sentence)
    _start_next()
