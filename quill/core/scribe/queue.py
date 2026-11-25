"""The family queue: one Scribe document at a time, per Windows user (PRD 7.4).

Every running QUILL app reads one queue file in the person's own QUILL data
folder (``scribe/queue.json``), never a folder shared between Windows users
(10.2.7). Writes are atomic and made under a short edit lock
(``scribe/queue.lock``), so two apps never lose each other's changes, and
only the app holding the **runner lock** (``scribe/runner.json``, kept alive
by a heartbeat) uploads, converts, downloads and speaks (7.4a). When that app
closes, the next app to start takes the lock, reconnects and downloads: a
job survives closing the app.

A job is one document; each format is a step within it, because Scribe runs
one conversion per document at a time. Several files the person chose in one
Convert dialog are one **batch**, sent strictly one after another under the
exception Pneuma approved on 2026-11-21: the next upload starts only after
the previous document's ``conversion_complete`` or error (SCR-POL-3).
When the person named the batch, it is also a **set**
(:class:`quill.core.batch_sets.BatchSet`), stored beside the jobs so every app
shows it as one row and writes to one log (:mod:`quill.core.scribe.sets`).

**The family's pace** (3.5). Scribe allows 10 actions a minute per person in
fixed 60-second windows -- uploads, ``start_conversion`` and password tries
share one counter, and the person's own use of the website counts too, with
no Retry-After. The queue file counts every app's actions, so the family
keeps to :data:`ACTION_LIMIT` in any rolling minute
(:meth:`FamilyQueue.reserve_action`), and after ``rate_limited`` every app
waits :data:`RATE_LIMITED_WAIT_S` (:meth:`FamilyQueue.pause_for_rate_limit`).

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

from quill.core.batch_sets import BatchSet
from quill.core.storage import read_json, write_json_atomic

# Job states. "Waiting for you" states need the person; the runner skips them.
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
NEEDS_PERSON = frozenset({NEEDS_PASSWORD, NEEDS_SIGNIN})
FINISHED = frozenset({DONE, FAILED, GONE, STOPPED})

#: The words for a row's Stage column, which changes only with the stage.
STATE_WORDS: dict[str, str] = {
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

#: The family's actions in any rolling minute: under Scribe's 10, leaving
#: room for the person's own use of the website (3.5).
ACTION_LIMIT = 8
ACTION_WINDOW_S = 60.0
#: After ``rate_limited``: Scribe sends no Retry-After, and its window is 60 s.
RATE_LIMITED_WAIT_S = 60.0
#: A queue file from before the batch exception may hold this state; it now
#: simply means queued.
_OLD_WAITING_YOU = "waiting_you"


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
    #: The files chosen together in one Convert dialog share a batch, so the
    #: last one to finish can say what was made and what was not (7.4).
    batch: str = ""
    #: Fields "Also save as my Scribe account defaults" leaves as they are:
    #: Scribe's email, unless the person changed it in the dialog (F8).
    defaults_leave_out: list[str] = field(default_factory=list)
    #: When this document's run began; a named set's log says how long it took.
    started_at: float = 0.0

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
        values = {k: v for k, v in data.items() if k in known}
        if values.get("state") == _OLD_WAITING_YOU:
            values["state"] = QUEUED
        try:
            return cls(**values)
        except TypeError:
            return None


def queue_dir() -> Path:
    """``<QUILL data>\\scribe``: the person's own, never another Windows user's.

    The data folder is normally ``%APPDATA%\\QUILL``, which is per user. A
    custom or portable data folder may sit outside the profile, on a drive
    other people use too, so there the queue, its downloads record and the
    options go in a folder of this Windows user's own (10.2.7).
    """
    from quill.core.paths import app_data_dir

    base = app_data_dir() / "scribe"
    try:
        inside_profile = base.resolve().is_relative_to(Path.home().resolve())
    except (OSError, RuntimeError):
        inside_profile = False
    if inside_profile:
        return base
    from quill.core.scribe.library import safe_file_name

    user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    return base / safe_file_name(user, fallback="user")


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

    def _read(self) -> dict[str, Any]:
        data = read_json(self._queue, {})
        return data if isinstance(data, dict) else {}

    def jobs(self) -> list[Job]:
        items = self._read().get("jobs")
        parsed = [Job.from_mapping(item) for item in (items or [])]
        return [job for job in parsed if job is not None]

    def _write(self, jobs: list[Job], **extra: Any) -> None:
        """Write *jobs*, preserving sets, action counts and newer fields."""
        data = self._read()
        body: dict[str, Any] = dict(data)
        body.update({
            "version": 1,
            "jobs": [asdict(job) for job in jobs],
            "actions": data.get("actions", []),
            "paused_until": data.get("paused_until", 0.0),
        })
        body.update(extra)
        write_json_atomic(self._queue, body)

    def now(self) -> float:
        """The queue's clock (wall time, the same in every app)."""
        return self._now()

    def get(self, job_id: str) -> Job | None:
        return next((job for job in self.jobs() if job.id == job_id), None)

    def add(self, new_jobs: list[Job], *, batch_set: BatchSet | None = None) -> list[Job]:
        """Queue *new_jobs*, in order. Several are one batch, sent one after
        another without asking again (the approved exception, 7.4). A
        *batch_set* records that named batch in the same durable write."""
        if batch_set is not None:
            batch_set.members = [job.id for job in new_jobs]
            for job in new_jobs:
                job.batch = batch_set.id
        elif len(new_jobs) > 1:
            batch = uuid.uuid4().hex
            for job in new_jobs:
                job.batch = job.batch or batch
        with self._editing():
            jobs = self.jobs()
            jobs.extend(new_jobs)
            if batch_set is None:
                self._write(jobs)
            else:
                kept = [made.to_dict() for made in self.sets() if made.id != batch_set.id]
                self._write(jobs, sets=[*kept, batch_set.to_dict()])
        return new_jobs

    # ----------------------------------------------------------------- sets

    def sets(self) -> list[BatchSet]:
        """Every named set, oldest first."""
        items = self._read().get("sets")
        parsed = [BatchSet.from_mapping(item) for item in (items or [])]
        return [made for made in parsed if made is not None]

    def get_set(self, set_id: str) -> BatchSet | None:
        if not set_id:
            return None
        return next((made for made in self.sets() if made.id == set_id), None)

    def update_set(
        self,
        set_id: str,
        *,
        only_if: Callable[[BatchSet], bool] | None = None,
        **changes: Any,
    ) -> BatchSet | None:
        """Change a set under the edit lock, optionally after an atomic check."""
        with self._editing():
            found = None
            items: list[dict[str, Any]] = []
            for made in self.sets():
                if made.id == set_id and (only_if is None or only_if(made)):
                    for key, value in changes.items():
                        if hasattr(made, key) and key != "extra":
                            setattr(made, key, value)
                    found = made
                items.append(made.to_dict())
            if found is not None:
                self._write(self.jobs(), sets=items)
            return found

    def remove_set(self, set_id: str) -> bool:
        """Take a set and all its jobs off the list; its folder and log stay."""
        with self._editing():
            named = self.sets()
            kept = [made for made in named if made.id != set_id]
            if len(kept) == len(named):
                return False
            jobs = [job for job in self.jobs() if job.batch != set_id]
            self._write(jobs, sets=[made.to_dict() for made in kept])
            return True

    def batch_jobs(self, batch: str) -> list[Job]:
        """Every job of one batch, in the order chosen."""
        if not batch:
            return []
        return sorted((job for job in self.jobs() if job.batch == batch), key=lambda j: j.created)

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
        """Take one job off the list; a set left with no jobs goes too."""
        with self._editing():
            jobs = self.jobs()
            kept = [job for job in jobs if job.id != job_id]
            if len(kept) == len(jobs):
                return False
            batches = {job.batch for job in kept}
            named = [made.to_dict() for made in self.sets() if made.id in batches]
            self._write(kept, sets=named)
            return True

    # ------------------------------------------------------------ the pace

    def reserve_action(self) -> float:
        """Count one action (an upload, a ``start_conversion``, a password try)
        for the whole family, or say how long to wait first.

        Returns ``0.0`` when the action is counted and may go now, otherwise
        the seconds until there is room (nothing is counted then)."""
        with self._editing():
            data = self._read()
            now = self._now()
            paused = float(data.get("paused_until", 0.0) or 0.0)
            if paused > now:
                return paused - now
            recent = sorted(
                float(t)
                for t in data.get("actions", []) or []
                if isinstance(t, (int, float)) and 0 <= now - float(t) < ACTION_WINDOW_S
            )
            if len(recent) >= ACTION_LIMIT:
                return max(0.05, recent[-ACTION_LIMIT] + ACTION_WINDOW_S - now)
            recent.append(now)
            self._write(self.jobs(), actions=recent)
            return 0.0

    def pace(self) -> tuple[int, float]:
        """Read only, for Scribe Status: the family's actions in the last
        minute, and when a ``rate_limited`` pause ends (``0.0`` if none)."""
        data = self._read()
        now = self._now()
        recent = [
            t
            for t in data.get("actions", []) or []
            if isinstance(t, (int, float)) and 0 <= now - float(t) < ACTION_WINDOW_S
        ]
        paused = float(data.get("paused_until", 0.0) or 0.0)
        return len(recent), paused if paused > now else 0.0

    def pause_for_rate_limit(self) -> float:
        """``rate_limited``: no app sends anything for a minute. Returns the wait."""
        with self._editing():
            until = self._now() + RATE_LIMITED_WAIT_S
            self._write(self.jobs(), paused_until=until)
        return RATE_LIMITED_WAIT_S

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
    "ACTION_LIMIT",
    "ACTION_WINDOW_S",
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
    "RATE_LIMITED_WAIT_S",
    "STATE_WORDS",
    "STOPPED",
    "UPLOADING",
    "FamilyQueue",
    "Job",
    "queue_dir",
]
