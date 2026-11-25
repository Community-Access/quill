"""Durable queue for file transcription, shared by QUILL's three hosts.

The queue contains recording paths and transcription choices, never the
transcript, API key or document text. One JSON file is written atomically and
guarded by a short cross-process lock; a separate stale-checked runner lock
lets QUILL and QUILL Transcribe view the same jobs without both transcribing.
QUILL Lite uses its own data root, so its queue remains portable and private to
Lite.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from quill.core.storage import read_json, write_json_atomic

QUEUED = "queued"
TRANSCRIBING = "transcribing"
DONE = "done"
FAILED = "failed"
STOPPED = "stopped"

ACTIVE = frozenset({QUEUED, TRANSCRIBING})
FINISHED = frozenset({DONE, FAILED, STOPPED})
STATE_WORDS = {
    QUEUED: "Queued",
    TRANSCRIBING: "Transcribing",
    DONE: "Done",
    FAILED: "Failed",
    STOPPED: "Stopped",
}

SCHEMA_VERSION = 1
_EDIT_STALE_SECONDS = 10.0
_RUNNER_STALE_SECONDS = 20.0


@dataclass(slots=True)
class TranscriptionJob:
    """One recording and the non-secret choices needed to run it again."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    app: str = ""
    source_path: str = ""
    model: str = ""
    language: str = "en"
    timestamps: bool = False
    obey_commands: bool = False
    remove_fillers: bool = False
    dash: str = "em"
    translate: bool = False
    keywords: list[str] = field(default_factory=list)
    cloud_approved: bool = False
    batch: str = ""
    state: str = QUEUED
    progress: float = 0.0
    message: str = ""
    output_id: str = ""
    output_path: str = ""
    attempts: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    finished_at: float = 0.0

    @property
    def name(self) -> str:
        return Path(self.source_path).name or "Recording"

    @property
    def state_words(self) -> str:
        return STATE_WORDS.get(self.state, self.state)

    @classmethod
    def from_mapping(cls, value: Any) -> TranscriptionJob | None:
        if not isinstance(value, dict) or not value.get("id"):
            return None
        known = {item.name for item in fields(cls)}
        values = {key: item for key, item in value.items() if key in known}
        state = str(values.get("state", QUEUED))
        if state not in STATE_WORDS:
            state = QUEUED
        values["state"] = state
        values["keywords"] = [
            str(word) for word in values.get("keywords", ()) or () if str(word).strip()
        ]
        values["progress"] = max(0.0, min(1.0, _float(values.get("progress"))))
        for key in ("attempts",):
            values[key] = max(0, _int(values.get(key)))
        for key in ("created_at", "started_at", "finished_at"):
            values[key] = max(0.0, _float(values.get(key)))
        try:
            return cls(**values)
        except TypeError:
            return None

    def file_job(self) -> Any:
        from quill.core.windows_dictation.file_transcribe import FileJob

        return FileJob(
            path=Path(self.source_path),
            model=self.model,
            language=self.language,
            timestamps=self.timestamps,
            obey_commands=self.obey_commands,
            remove_fillers=self.remove_fillers,
            dash=self.dash,
            keywords=tuple(self.keywords),
            translate=self.translate,
        )


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        result = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return result if result == result and result not in (float("inf"), float("-inf")) else 0.0


class TranscriptionQueue:
    """Atomic, process-safe file-transcription queue."""

    def __init__(
        self,
        data_dir: Path,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.folder = Path(data_dir) / "dictation"
        self.path = self.folder / "transcription-queue.json"
        self._edit_lock = self.folder / "transcription-queue.lock"
        self._runner = self.folder / "transcription-runner.json"
        self._clock = clock
        self._local = threading.RLock()
        self.token = f"{os.getpid()}-{uuid.uuid4().hex[:8]}"

    @contextmanager
    def _editing(self) -> Iterator[None]:
        self.folder.mkdir(parents=True, exist_ok=True)
        with self._local:
            deadline = time.monotonic() + 5.0
            while True:
                try:
                    handle = os.open(self._edit_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.close(handle)
                    break
                except FileExistsError:
                    try:
                        if self._clock() - self._edit_lock.stat().st_mtime > _EDIT_STALE_SECONDS:
                            self._edit_lock.unlink(missing_ok=True)
                            continue
                    except OSError:
                        pass
                    if time.monotonic() >= deadline:
                        raise TimeoutError("the transcription queue is busy") from None
                    time.sleep(0.01)
            try:
                yield
            finally:
                self._edit_lock.unlink(missing_ok=True)

    def _read(self) -> dict[str, Any]:
        data = read_json(self.path, {"version": SCHEMA_VERSION, "jobs": []})
        return data if isinstance(data, dict) else {"version": SCHEMA_VERSION, "jobs": []}

    def _jobs_unlocked(self) -> list[TranscriptionJob]:
        parsed = [TranscriptionJob.from_mapping(item) for item in self._read().get("jobs", [])]
        return [item for item in parsed if item is not None]

    def _write(self, jobs: list[TranscriptionJob]) -> None:
        write_json_atomic(
            self.path,
            {"version": SCHEMA_VERSION, "jobs": [asdict(job) for job in jobs]},
        )

    def jobs(self) -> list[TranscriptionJob]:
        with self._local:
            return self._jobs_unlocked()

    def get(self, job_id: str) -> TranscriptionJob | None:
        return next((job for job in self.jobs() if job.id == job_id), None)

    def add(self, jobs: list[TranscriptionJob]) -> list[TranscriptionJob]:
        if not jobs:
            return []
        with self._editing():
            stored = self._jobs_unlocked()
            stored.extend(jobs)
            self._write(stored)
        return jobs

    def update(self, job_id: str, **changes: Any) -> TranscriptionJob | None:
        with self._editing():
            jobs = self._jobs_unlocked()
            found = next((job for job in jobs if job.id == job_id), None)
            if found is None:
                return None
            for name, value in changes.items():
                if hasattr(found, name):
                    setattr(found, name, value)
            self._write(jobs)
            return found

    def claim_next(self) -> TranscriptionJob | None:
        with self._editing():
            jobs = self._jobs_unlocked()
            found = next(
                (
                    job
                    for job in sorted(jobs, key=lambda item: item.created_at)
                    if job.state == QUEUED
                ),
                None,
            )
            if found is None:
                return None
            found.state = TRANSCRIBING
            found.started_at = self._clock()
            found.finished_at = 0.0
            found.attempts += 1
            found.progress = 0.0
            found.message = "Preparing recording"
            self._write(jobs)
            return found

    def recover_interrupted(self) -> list[TranscriptionJob]:
        with self._editing():
            jobs = self._jobs_unlocked()
            recovered = [job for job in jobs if job.state == TRANSCRIBING]
            for job in recovered:
                job.state = QUEUED
                job.progress = 0.0
                job.message = "Ready to carry on"
                job.started_at = 0.0
                job.finished_at = 0.0
            if recovered:
                self._write(jobs)
            return recovered

    def requeue(self, job_id: str, message: str = "Ready to carry on") -> bool:
        job = self.update(
            job_id,
            state=QUEUED,
            progress=0.0,
            message=message,
            started_at=0.0,
            finished_at=0.0,
        )
        return job is not None

    def retry(self, job_id: str) -> bool:
        job = self.get(job_id)
        if job is None or job.state not in {FAILED, STOPPED}:
            return False
        return self.requeue(job_id, "Queued to try again")

    def stop(self, job_id: str, message: str = "Stopped") -> bool:
        job = self.get(job_id)
        if job is None or job.state in FINISHED:
            return False
        changed = self.update(
            job_id,
            state=STOPPED,
            message=message,
            finished_at=self._clock(),
        )
        return changed is not None

    def remove(self, job_id: str) -> bool:
        with self._editing():
            jobs = self._jobs_unlocked()
            found = next((job for job in jobs if job.id == job_id), None)
            if found is None or found.state not in FINISHED:
                return False
            self._write([job for job in jobs if job.id != job_id])
            return True

    def waiting_count(self) -> int:
        return sum(1 for job in self.jobs() if job.state in ACTIVE)

    def describe(self) -> str:
        jobs = self.jobs()
        current = next((job for job in jobs if job.state == TRANSCRIBING), None)
        if current is None:
            return ""
        waiting = sum(1 for job in jobs if job.state == QUEUED)
        text = f"{current.name}, {round(current.progress * 100)} percent done."
        if waiting:
            noun = "recording" if waiting == 1 else "recordings"
            text += f" {waiting} more {noun} waiting."
        return text

    # -- runner lock ---------------------------------------------------------

    def holder(self) -> dict[str, Any] | None:
        data = read_json(self._runner, None)
        if not isinstance(data, dict):
            return None
        if self._clock() - _float(data.get("beat")) > _RUNNER_STALE_SECONDS:
            return None
        return data

    def try_acquire(self, app_name: str) -> bool:
        with self._editing():
            current = self.holder()
            if current and current.get("token") != self.token:
                return False
            write_json_atomic(
                self._runner,
                {"token": self.token, "app": app_name, "beat": self._clock()},
            )
            return True

    def is_holder(self) -> bool:
        current = self.holder()
        return bool(current and current.get("token") == self.token)

    def heartbeat(self, app_name: str) -> bool:
        return self.try_acquire(app_name)

    def release(self) -> None:
        with self._editing():
            current = read_json(self._runner, None)
            if isinstance(current, dict) and current.get("token") == self.token:
                self._runner.unlink(missing_ok=True)


__all__ = [
    "ACTIVE",
    "DONE",
    "FAILED",
    "FINISHED",
    "QUEUED",
    "SCHEMA_VERSION",
    "STATE_WORDS",
    "STOPPED",
    "TRANSCRIBING",
    "TranscriptionJob",
    "TranscriptionQueue",
]
