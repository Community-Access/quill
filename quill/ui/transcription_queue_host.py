"""Long-lived hosts for transcription work that can outlive an editor window."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from quill.core.notifications import notifications_path
from quill.ui.transcription_queue_state import TranscriptPersistenceError


def save_transcript(data_dir: Path, text: str) -> str:
    from quill.core.storage import write_text_atomic

    identifier = uuid4().hex
    path = Path(data_dir) / "dictation" / "transcripts" / f"{identifier}.txt"
    write_text_atomic(path, text, encoding="utf-8", newline="")
    return identifier


class LiteTranscriptionHost:
    """A QUILL Lite app survives every document, so queue work belongs to it."""

    def __init__(self, app: Any) -> None:
        self.app = app

    def _current(self) -> Any | None:
        frames = list(getattr(self.app, "frames", ()) or ())
        active = getattr(self.app, "active_frame", None)
        if active in frames:
            return active
        return frames[-1] if frames else None

    def _dictation_data_dir(self) -> Path:
        return Path(self.app.data_dir)

    def _dictation_notification_path(self) -> Path:
        return notifications_path(self._dictation_data_dir())

    def _dictation_app_name(self) -> str:
        return "QUILL Lite"

    def _dictation_task_manager(self) -> Any:
        manager = getattr(self.app, "task_manager", None)
        if manager is None:
            from quill.stability.task_manager import TaskManager

            manager = TaskManager(max_workers=2)
            self.app.task_manager = manager
        return manager

    def _dictation_file_rewrite(self) -> Any:
        current = self._current()
        preferences = getattr(current, "_dictation_preferences", None)
        if not callable(preferences):
            return None
        try:
            return preferences().rewrite
        except Exception:  # noqa: BLE001 - a damaged profile must not stop queued work
            return None

    def _dictation_save_transcript(self, text: str) -> str:
        try:
            return save_transcript(self._dictation_data_dir(), text)
        except Exception as error:
            raise TranscriptPersistenceError(str(error)) from error

    def _dictation_open_transcript(self, path: Path) -> None:
        current = self._current()
        opener = getattr(current, "_dictation_open_transcript", None)
        if callable(opener):
            opener(Path(path))
            return
        self.app.open_path(Path(path))

    def _dictation_say(self, text: str) -> None:
        current = self._current()
        say = getattr(current, "_dictation_say", None)
        if callable(say):
            say(text)
            return
        voice = getattr(self.app, "voice", None)
        speak = getattr(voice, "speak", None)
        if callable(speak):
            speak(text)

    def _dictation_say_quietly(self, text: str) -> None:
        current = self._current()
        say = getattr(current, "_dictation_say_quietly", None)
        if callable(say):
            say(text)
            return
        self._dictation_say(text)

    def _dictation_status(self, text: str) -> None:
        current = self._current()
        status = getattr(current, "_dictation_status", None)
        if callable(status):
            status(text)

    def _dictation_cue(self, event: str) -> None:
        current = self._current()
        cue = getattr(current, "_dictation_cue", None)
        if callable(cue):
            cue(event)


def durable_host(host: Any) -> Any:
    """Use QUILL Lite's app as the owner; other apps already outlive their jobs."""
    app = host
    if not (hasattr(app, "frames") and hasattr(app, "data_dir") and hasattr(app, "voice")):
        app = getattr(host, "app", None)
    if app is None or not (
        hasattr(app, "frames") and hasattr(app, "data_dir") and hasattr(app, "voice")
    ):
        return host
    found = getattr(app, "_transcription_host", None)
    if found is None:
        found = LiteTranscriptionHost(app)
        app._transcription_host = found
    return found


def safe_mode(host: Any) -> bool:
    return bool(os.environ.get("QUILL_SAFE_MODE") or getattr(host, "_safe_mode", False))


__all__ = ["LiteTranscriptionHost", "durable_host", "safe_mode", "save_transcript"]
