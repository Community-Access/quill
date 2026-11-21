"""The family queue: one Scribe document at a time, per Windows user (PRD 7.4).

Every running QUILL app reads one queue file in the shared QUILL data folder
(``scribe/queue.json``). Writes are atomic and made under a short edit lock
(``scribe/queue.lock``), so two apps never lose each other's changes, and
only the app holding the **runner lock** (``scribe/runner.json``, kept alive
by a heartbeat) uploads, converts, downloads and speaks (7.4a). When that app
closes, the next app to start takes the lock, reconnects and downloads: a
job survives closing the app.

A job is one document; each format is a step within it, because Scribe runs
one conversion per document at a time. Until Pneuma grants the batch
exception, only the first of several files is queued; the rest wait in the
``waiting_you`` state for Send Next File, so every upload follows a choice
the person made (SCR-POL-3).

No password, token or document text is ever written to the queue file.

wx-free.
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

# Job states. "Waiting for you" states need the person; the runner skips them.
WAITING_YOU = "waiting_you"  # Send Next File (no batch exception)
QUEUED = "queued"
UPLOADING = "uploading"
CONVERTING = "converting"
DOWNLOADING = "downloading"
BUSY = "busy"  # rate limited; tries again at not_before
NEEDS_PASSWORD = "needs_password"
NEEDS_SIGNIN = "needs_signin"
DONE = "done"
FAILED = "failed"
GONE = "gone"
STOPPED = "stopped"  # Cancel Waiting

ACTIVE = frozenset({QUEUED, UPLOADING, CONVERTING, DOWNLOADING, BUSY})
NEEDS_PERSON = frozenset({WAITING_YOU, NEEDS_PASSWORD, NEEDS_SIGNIN})
FINISHED = frozenset({DONE, FAILED, GONE, STOPPED})

#: The words for a row's Stage column, which changes only with the stage.
STATE_WORDS: dict[str, str] = {
    WAITING_YOU: "Waiting for you: Send Next File",
    QUEUED: "Queued",
    UPLOADING: "Uploading",
    CONVERTING: "Converting",
    DOWNLOADING: "Downloading",
    BUSY: "Waiting: Scribe asked to slow down",
    NEEDS_PASSWORD: "Waiting for you: needs its password",
    NEEDS_SIGNIN: "Waiting for you: sign in again",
    DONE: "Done",
    FAILED: "Failed",
    GONE: "No longer in your Scribe account",
    STOPPED: "Stopped waiting",
}

_RUNNER_STALE_S = 20.0
_EDIT_STALE_S = 10.0


@dataclass(slots=True)
class Job:
    """One document on its way through Scribe."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    app: str = "QUILL"
    file_name: str = ""
    source_path: str = ""
    source_url: str = ""
    size: int = 0
    title: str = ""
    formats: list[str] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    save_as_defaults: bool = False
    #: Set once uploaded (or from the start, for a document already in the account).
    document_id: str = ""
    reuse: bool = False
    state: str = QUEUED
    format: str = ""  # the format converting now
    stage: str = ""  # Scribe's stage for it
    progress: float = 0.0  # of the whole job, 0..1
    eta_seconds: int | None = None
    message: str = ""
    error_code: str = ""
    purchase_url: str = ""
    folder: str = ""
    outputs: dict[str, str] = field(default_factory=dict)
    password_tries: int = 0
    not_before: float = 0.0
    created: float = field(default_factory=time.time)
    #: How the result opens when it is ready ("tab", "window", "braille"...),
    #: chosen by the entry point that queued it (8.x).
    open_as: str = ""

    @property
    def state_words(self) -> str:
        return STATE_WORDS.get(self.state, self.state)

    @property
    def display_name(self) -> str:
        return self.file_name or self.title or "Scribe document"

    @classmethod
    def from_mapping(cls, data: Any) -> Job | None:
        if not isinstance(data, dict) or not data.get("id"):
            return None
        known = {f.name for f in fields(cls)}
        try:
            return cls(**{k: v for k, v in data.items() if k in known})
        except TypeError:
            return None


def queue_dir() -> Path:
    from quill.core.paths import app_data_dir

    return app_data_dir() / "scribe"


class FamilyQueue:
    """The shared queue file and the two locks. Safe across processes."""

    def __init__(self, folder: Path | None = None, *, now: Callable[[], float] = time.time) -> None:
        self.folder = folder or queue_dir()
        self._queue = self.folder / "queue.json"
        self._edit_lock = self.folder / "queue.lock"
        self._runner = self.folder / "runner.json"
        self._now = now
        self._local = threading.Lock()
        self.token = f"{os.getpid()}-{uuid.uuid4().hex[:8]}"

    # -------------------------------------------------------------- editing

    @contextmanager
    def _editing(self) -> Iterator[None]:
        """A short cross-process lock around read-modify-write."""
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
                        age = self._now() - self._edit_lock.stat().st_mtime
                        if age > _EDIT_STALE_S:
                            self._edit_lock.unlink(missing_ok=True)
                            continue
                    except OSError:
                        continue
                    if time.monotonic() >= deadline:
                        raise TimeoutError("the Scribe queue is busy") from None
                    time.sleep(0.01)
            try:
                yield
            finally:
                self._edit_lock.unlink(missing_ok=True)

    def jobs(self) -> list[Job]:
        data = read_json(self._queue, {})
        items = data.get("jobs") if isinstance(data, dict) else None
        parsed = [Job.from_mapping(item) for item in (items or [])]
        return [job for job in parsed if job is not None]

    def _write(self, jobs: list[Job]) -> None:
        write_json_atomic(self._queue, {"version": 1, "jobs": [asdict(job) for job in jobs]})

    def get(self, job_id: str) -> Job | None:
        return next((job for job in self.jobs() if job.id == job_id), None)

    def add(self, new_jobs: list[Job], *, batch_exception: bool = False) -> list[Job]:
        """Queue *new_jobs*. Without the batch exception, only the first is
        queued and the rest wait for Send Next File."""
        with self._editing():
            jobs = self.jobs()
            for index, job in enumerate(new_jobs):
                if index > 0 and not batch_exception and job.state == QUEUED:
                    job.state = WAITING_YOU
                jobs.append(job)
            self._write(jobs)
        return new_jobs

    def update(self, job_id: str, *, respect_stop: bool = True, **changes: Any) -> Job | None:
        """Change a job. A job the person stopped stays stopped: the runner's
        later writes cannot undo Cancel Waiting (only Retry passes
        ``respect_stop=False``)."""
        with self._editing():
            jobs = self.jobs()
            found = None
            for job in jobs:
                if job.id == job_id:
                    if respect_stop and job.state == STOPPED:
                        changes.pop("state", None)
                    for key, value in changes.items():
                        if hasattr(job, key):
                            setattr(job, key, value)
                    found = job
            if found is not None:
                self._write(jobs)
            return found

    def remove(self, job_id: str) -> bool:
        with self._editing():
            jobs = self.jobs()
            kept = [job for job in jobs if job.id != job_id]
            if len(kept) == len(jobs):
                return False
            self._write(kept)
            return True

    def send_next(self) -> Job | None:
        """Send Next File: the oldest ``waiting_you`` job becomes queued."""
        with self._editing():
            jobs = self.jobs()
            for job in jobs:
                if job.state == WAITING_YOU:
                    job.state = QUEUED
                    self._write(jobs)
                    return job
        return None

    def next_runnable(self) -> Job | None:
        """The job the runner should take: one already under way first (it was
        interrupted by an app closing), then the oldest queued one."""
        now = self._now()
        jobs = sorted(self.jobs(), key=lambda job: job.created)
        for job in jobs:
            if job.state in (UPLOADING, CONVERTING, DOWNLOADING):
                return job
        for job in jobs:
            if job.state == QUEUED or (job.state == BUSY and job.not_before <= now):
                return job
        return None

    def waiting_count(self) -> int:
        return sum(1 for job in self.jobs() if job.state in ACTIVE or job.state in NEEDS_PERSON)

    # ------------------------------------------------------------- runner lock

    def holder(self) -> dict[str, Any] | None:
        """Who holds the runner lock, if anyone does and is alive."""
        data = read_json(self._runner, None)
        if not isinstance(data, dict):
            return None
        if self._now() - float(data.get("beat", 0) or 0) > _RUNNER_STALE_S:
            return None
        return data

    def is_holder(self) -> bool:
        current = self.holder()
        return bool(current and current.get("token") == self.token)

    def try_acquire(self, app_name: str) -> bool:
        """Take the runner lock if it is free or stale. Idempotent for the holder."""
        with self._editing():
            current = self.holder()
            if current and current.get("token") != self.token:
                return False
            write_json_atomic(
                self._runner, {"token": self.token, "app": app_name, "beat": self._now()}
            )
            return True

    def heartbeat(self, app_name: str) -> bool:
        """Keep the lock alive; False if somebody else holds it now."""
        return self.try_acquire(app_name)

    def release(self) -> None:
        with self._editing():
            current = read_json(self._runner, None)
            if isinstance(current, dict) and current.get("token") == self.token:
                self._runner.unlink(missing_ok=True)


__all__ = [
    "ACTIVE",
    "BUSY",
    "CONVERTING",
    "DONE",
    "DOWNLOADING",
    "FAILED",
    "FINISHED",
    "GONE",
    "NEEDS_PASSWORD",
    "NEEDS_PERSON",
    "NEEDS_SIGNIN",
    "QUEUED",
    "STATE_WORDS",
    "STOPPED",
    "UPLOADING",
    "WAITING_YOU",
    "FamilyQueue",
    "Job",
    "queue_dir",
]
