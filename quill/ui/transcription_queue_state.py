"""In-memory state shared by the durable transcription queue runtime."""

from __future__ import annotations

import threading
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Any

from quill.core.windows_dictation.file_queue import TranscriptionJob


@dataclass
class Entry:
    job: Any
    host: Any
    rewrite: Any = None
    cancel: threading.Event = field(default_factory=threading.Event)
    operation: str = ""
    percent: int = 0
    notice_id: str = ""
    notified_percent: int = 0
    notice_error: str = ""
    notice_future: Future[bool] | None = None
    queue_job: TranscriptionJob | None = None
    suspended: bool = False


@dataclass
class RuntimeQueue:
    """The current and waiting records in this process."""

    current: Entry | None = None
    waiting: list[Entry] = field(default_factory=list)

    def describe(self) -> str:
        if self.current is None:
            return ""
        name = self.current.job.path.name
        text = f"{name}, {self.current.percent} percent done."
        if self.waiting:
            count = len(self.waiting)
            text += f" {count} more recording{'s' if count != 1 else ''} waiting."
        return text


class TranscriptPersistenceError(Exception):
    """Transcription succeeded, but its saved transcript could not be recorded."""


@dataclass(frozen=True, slots=True)
class Result:
    transcript: Any = None
    error: BaseException | None = None
    notice_error: str = ""
    output_id: str = ""
    output_path: str = ""


__all__ = ["Entry", "Result", "RuntimeQueue", "TranscriptPersistenceError"]
