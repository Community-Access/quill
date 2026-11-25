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

from pathlib import Path
from typing import Any

import wx

from quill.ui import transcription_queue_runtime as queue_runtime

__all__ = ["DictationTranscribeMixin", "queue_text"]

_Entry = queue_runtime.Entry
_Queue = queue_runtime.RuntimeQueue
_TranscriptPersistenceError = queue_runtime.TranscriptPersistenceError
_QUEUE = _Queue()


def queue_text(host: Any | None = None) -> str:
    """What is being transcribed now, for the window's status line ("" when nothing)."""
    return queue_runtime.queue_text(host)


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
        from quill.ui.dictation_transcribe_dialog import (
            STOP_TRANSCRIBING,
            TranscribeFileDialog,
            job_for,
        )

        preferences = self._dictation_preferences()  # type: ignore[attr-defined]
        dialog = TranscribeFileDialog(
            self._dictation_parent(),  # type: ignore[attr-defined]
            language=preferences.speech_language,
            paths=paths or (),
            running=queue_text(self),
            sample_job=lambda choice, path: (
                job_for(choice, path, preferences),
                preferences.rewrite,
            ),
            announce=self._dictation_say,  # type: ignore[attr-defined]
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
        keywords: tuple[str, ...] = ()
        if choice.model.cloud:
            keywords = self._transcribe_keywords()
        jobs = [job_for(choice, path, preferences, keywords) for path in choice.paths]
        queue_runtime.enqueue_many(
            jobs,
            self,
            preferences.rewrite,
            cloud_approved=choice.model.cloud,
        )
        if _QUEUE.current is not None:
            count = len(_QUEUE.waiting)
            self._dictation_say(  # type: ignore[attr-defined]
                f"Added to the queue; {count} recording{'s' if count != 1 else ''} waiting."
            )
            return
        queue_runtime.resume(self)

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
        current = _QUEUE.current
        name = current.job.path.name if current is not None and current.host is self else ""
        waiting, current = queue_runtime.stop(self)
        if not current and not waiting:
            self._dictation_say("Nothing is being transcribed.")  # type: ignore[attr-defined]
            return
        plural = "s" if waiting != 1 else ""
        extra = f", and {waiting} waiting recording{plural} canceled" if waiting else ""
        if current and name:
            self._dictation_say(f"Stopping the transcription of {name}{extra}.")  # type: ignore[attr-defined]
        elif waiting:
            self._dictation_say(  # type: ignore[attr-defined]
                f"Canceled {waiting} waiting recording{plural}."
            )

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

    def cmd_open_transcriptions(self) -> None:
        """Open the durable queue and saved transcripts for this computer."""
        from quill.ui.transcription_queue_window import open_transcriptions

        open_transcriptions(self)

    def open_notification_target(self, target: str) -> None:
        """Open a saved dictation transcript only after its notice is activated."""
        prefix = "dictation-transcript:"
        target = str(target)
        opener = getattr(self, "open_github_accounts_notice", None)  # github_token_expiry
        if target == "github-accounts" and callable(opener):
            return opener()
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
        from quill.ui.transcription_queue_host import save_transcript

        try:
            return save_transcript(self._dictation_data_dir(), text)
        except Exception as error:
            raise _TranscriptPersistenceError(str(error)) from error
