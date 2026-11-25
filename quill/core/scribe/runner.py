"""Running the family queue: one job at a time, upload to downloads (PRD 3.5, 7.4).

:class:`QueueService` runs on a background thread in every app. It takes the
queue's runner lock when it is free (a heartbeat thread keeps it while a long
upload runs), and then -- only then -- runs the oldest job:

1. **Upload** (``POST /api/documents``) with the full settings set as form
   fields, unless the document is already in the account (Documents in My Scribe
   Account). Only the 23 types Scribe takes, up to 500 MB, are ever sent
   (:mod:`.inputs`). A password from the convert dialog is held in memory for
   this one job and never written anywhere.
2. **Settings**: for a document already in the account, ``PATCH`` its settings
   (all but the ones its upload fixed); the account defaults only when asked.
3. **Each format in Scribe's order**, over the document channel: start it,
   follow ``status`` events, wait for ``conversion_complete``. A drop
   reconnects and joins again without uploading again; 15 quiet seconds poll
   the outputs, so a missed event never strands a job.
4. **Download** each into the job's folder, recorded in the library; a DAISY
   zip is unpacked beside itself so its ``.ncx`` can be opened.

The jobs of a batch run strictly one after another: a job runs to its last
download or its error before the next upload (the exception Pneuma approved
on 2026-11-21). Every upload and ``start_conversion`` first takes a turn from
the family's pace (:meth:`quill.core.scribe.queue.FamilyQueue.reserve_action`),
and ``rate_limited`` pauses the whole family a minute.

Whatever happens is reported to the app's ``listener(kind, job)`` on this
thread; the app marshals to its UI thread and decides what to say through
:class:`quill.core.scribe.sentences.Speaker`.

wx-free.
"""

from __future__ import annotations

import logging
import threading
import time
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.scribe import queue as q
from quill.core.scribe.channel import ChannelEvent, DocumentChannel, default_channel_opener
from quill.core.scribe.client import ScribeClient
from quill.core.scribe.errors import (
    ScribeBusyError,
    ScribeCancelled,
    ScribeError,
    ScribeGoneError,
    ScribeInProgressError,
    ScribeNotDocumentError,
    ScribeOfflineError,
    ScribePagesError,
    ScribePasswordError,
    ScribeSaveError,
    ScribeSignInError,
)
from quill.core.scribe.inputs import check as check_input
from quill.core.scribe.inputs import not_a_document_sentence
from quill.core.scribe.library import Library, document_folder, unique_path
from quill.core.scribe.model import (
    HTML_SHAPING_FIELDS,
    ScribeSettings,
    format_label,
    ordered_for_conversion,
)
from quill.core.scribe.options import quill_base
from quill.core.scribe.results import daisy_entry
from quill.core.scribe.runner_progress import (
    conversion_message,
    handle_event,
    poll_complete,
    wait_for_any_complete,
)

logger = logging.getLogger(__name__)

Listener = Callable[[str, "q.Job | None"], None]

_QUIET_POLL_S = 15.0
_ETA_POLL_S = 1.0
_OFFLINE_SAY_AFTER_S = 5.0
_IN_PROGRESS_WAIT_S = 120.0
_HEARTBEAT_S = 5.0
_MAX_PASSWORD_TRIES = 3


class QueueService:
    """The per-app runner of the family queue."""

    def __init__(
        self,
        app_name: str,
        *,
        queue: q.FamilyQueue,
        client_factory: Callable[[], ScribeClient],
        channel_opener: Callable[[ScribeClient, str], DocumentChannel] | None = None,
        library: Library | None = None,
        download_root: Callable[[], str] = lambda: "",
        listener: Listener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        idle_s: float = 1.0,
    ) -> None:
        self.app_name = app_name
        self.queue = queue
        self._client_factory = client_factory
        self._channel_opener = channel_opener or default_channel_opener()
        self._library = library or Library(queue.folder / "library.json")
        self._download_root = download_root
        self._listener = listener or (lambda _kind, _job: None)
        self._sleep = sleep
        self._clock = clock
        self._idle = idle_s
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._passwords: dict[str, str] = {}
        self.holding = False
        self.current_id = ""
        self._resumed: set[str] = set()
        self._resumed_done: list[str] = []
        self._threads: list[threading.Thread] = []
        self._last_write = 0.0
        self._last_cancel_check = 0.0
        self._cancel_cached = False

    # ---------------------------------------------------------------- control

    def start(self) -> None:
        self.note_resumed()
        for target, name in ((self._loop, "scribe-queue"), (self._beat, "scribe-heartbeat")):
            thread = threading.Thread(target=target, name=name, daemon=True)
            thread.start()
            self._threads.append(thread)

    def note_resumed(self) -> None:
        """Remember the jobs under way when the app last closed (7.4)."""
        self._resumed = {
            job.id
            for job in self.queue.jobs()
            if job.state in (q.UPLOADING, q.CONVERTING, q.DOWNLOADING)
        }

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        try:
            self.queue.release()
        except (OSError, TimeoutError):
            pass

    def wake(self) -> None:
        """Look at the queue now (a job was added, a password, Retry)."""
        self._wake.set()

    def provide_password(self, job_id: str, password: str) -> None:
        """A password for *job_id*, held in memory only, then the job queues again."""
        self._passwords[job_id] = password
        self.queue.update(job_id, state=q.QUEUED, message="", error_code="")
        self.wake()

    def _beat(self) -> None:
        while not self._stop.wait(_HEARTBEAT_S):
            if self.holding:
                try:
                    self.holding = self.queue.heartbeat(self.app_name)
                except (OSError, TimeoutError):
                    pass

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:  # noqa: BLE001 - the loop must outlive any one failure
                logger.exception("Scribe queue loop failed")
            self._wake.wait(self._idle)
            self._wake.clear()

    def tick(self) -> bool:
        """One look at the queue; runs at most one job. True if a job ran."""
        was = self.holding
        try:
            self.holding = self.queue.try_acquire(self.app_name)
        except TimeoutError:
            return False
        if self.holding != was:
            self._listener("holder", None)
        if not self.holding:
            return False
        job = self.queue.next_runnable()
        if job is None:
            self._report_resumed()
            return False
        self.current_id = job.id
        try:
            self.run_job(job)
        finally:
            self.current_id = ""
            if self._job_finished(job.id):
                self._passwords.pop(job.id, None)
        return True

    def _job_finished(self, job_id: str) -> bool:
        job = self.queue.get(job_id)
        return job is None or job.state in q.FINISHED

    def _report_resumed(self) -> None:
        unfinished = [j for j in self._resumed if not self._job_finished(j)]
        if self._resumed_done and not unfinished:
            titles = list(self._resumed_done)
            self._resumed_done = []
            self._resumed = set()
            self._listener("closed_while", q.Job(title="|".join(titles)))

    # ------------------------------------------------------------------ a job

    def _set(self, job: q.Job, *, force: bool = True, **changes: Any) -> q.Job:
        state = changes.get("state")
        if state is not None and state != q.CONVERTING:
            changes.setdefault("eta_seconds", None)
        for key, value in changes.items():
            setattr(job, key, value)
        now = self._clock()
        if force or now - self._last_write >= 1.0:
            # Throttled writes (progress) carry every field changed since, so
            # nothing set between two writes is lost.
            self._last_write = now
            self.queue.update(job.id, **_persisted(job))
        return job

    def _check_cancel(self, job: q.Job) -> None:
        now = self._clock()
        if now - self._last_cancel_check >= 0.5:
            self._last_cancel_check = now
            stored = self.queue.get(job.id)
            self._cancel_cached = stored is None or stored.state == q.STOPPED
        if self._cancel_cached or self._stop.is_set():
            raise ScribeCancelled("QUILL stopped waiting.")

    def _wait(self, job: q.Job, seconds: float) -> None:
        end = self._clock() + seconds
        while self._clock() < end:
            self._check_cancel(job)
            self._sleep(min(0.5, max(0.0, end - self._clock())))

    def run_job(self, job: q.Job) -> None:
        self._cancel_cached = False
        self._last_cancel_check = 0.0
        try:
            self._run(job)
        except ScribeCancelled:
            logger.info("Scribe job stopped id=%s", job.document_id or "-")
            return
        except ScribeSignInError as error:
            self._set(job, state=q.NEEDS_SIGNIN, message=error.message, error_code=error.code)
            self._listener("needs_you", job)
        except ScribePasswordError as error:
            tries = job.password_tries + (1 if error.reason == "invalid_password" else 0)
            self._passwords.pop(job.id, None)
            if tries >= _MAX_PASSWORD_TRIES:
                self._set(
                    job,
                    state=q.FAILED,
                    password_tries=tries,
                    message=f"{job.display_name} was not sent: password not accepted",
                    error_code=error.code,
                )
                self._listener("error", job)
            else:
                self._set(
                    job,
                    state=q.NEEDS_PASSWORD,
                    password_tries=tries,
                    message=error.message,
                    error_code=error.code,
                )
                self._listener("needs_you", job)
        except ScribePagesError as error:
            self._set(
                job,
                state=q.FAILED,
                message=error.message,
                error_code=error.code,
                purchase_url=error.purchase_url,
            )
            self._listener("error", job)
        except ScribeGoneError as error:
            self._set(job, state=q.GONE, message=error.message, error_code=error.code)
            self._listener("error", job)
        except ScribeNotDocumentError as error:
            # Scribe's not_a_document gets the sentence that says what it takes.
            checked = error.reason == "checked_before_upload"
            message = error.message if checked else not_a_document_sentence(job.display_name)
            self._set(job, state=q.FAILED, message=message, error_code=error.code)
            self._listener("error", job)
        except (ScribeSaveError, ScribeError) as error:
            self._set(job, state=q.FAILED, message=error.message, error_code=error.code)
            self._listener("error", job)
        except OSError as error:
            self._set(
                job,
                state=q.FAILED,
                message=f"A file could not be read or written: {error}",
                error_code=ScribeSaveError.code,
            )
            self._listener("error", job)

    def _offline(self, job: q.Job, since: float) -> None:
        """Say a drop once, after it has lasted a few seconds; then wait a little."""
        if self._clock() - since >= _OFFLINE_SAY_AFTER_S:
            self._listener("offline", job)
        self._wait(job, 3.0)

    def _run(self, job: q.Job) -> None:
        client = self._client_factory()
        fresh = not job.document_id or job.state == q.QUEUED
        if fresh:
            self._listener("started", job)
        settings = ScribeSettings.from_mapping(job.settings) if job.settings else None
        if job.open_as == "watch" and not job.document_id:
            settings = self._watch_settings(client, job)
        if not job.document_id:
            if job.source_path:
                check_input(Path(job.source_path))  # 23 types, 500 MB: else nothing is sent
            self._set(job, state=q.UPLOADING, stage="", message="Uploading")
            self._listener("changed", job)
            down_since = 0.0
            while True:
                self._take_turn(job)
                try:
                    document_id = client.create_document(
                        path=Path(job.source_path) if job.source_path else None,
                        url=job.source_url,
                        password=self._passwords.get(job.id, ""),
                        settings=settings,  # the full set, at upload (3.3)
                    )
                    break
                except ScribeOfflineError:
                    down_since = down_since or self._clock()
                    self._offline(job, down_since)
                except ScribeBusyError:
                    self._rate_limited(job, q.UPLOADING)
            self._set(job, document_id=document_id)
        if fresh and settings is not None:
            if job.reuse:  # only formats not made yet; the upload fixed the rest
                client.update_settings(job.document_id, settings, leave_out=HTML_SHAPING_FIELDS)
            if job.save_as_defaults:  # only ever because the person ticked it
                client.update_default_settings(settings, leave_out=job.defaults_leave_out)
        outputs, needs_password = client.list_outputs(job.document_id)
        if needs_password and not self._passwords.get(job.id):
            raise ScribePasswordError(
                f"{job.display_name} needs its password.", reason="password_required"
            )
        complete = {o.format for o in outputs if o.is_complete}
        ordered = ordered_for_conversion(job.formats)
        total = max(1, len(ordered))
        channel: DocumentChannel | None = None
        try:
            for position, format_id in enumerate(ordered):
                if format_id in job.outputs and Path(job.outputs[format_id]).exists():
                    continue
                if format_id not in complete:
                    channel = self._convert(job, client, channel, format_id, position, total)
                self._download(job, client, format_id, position, total)
        finally:
            if channel is not None:
                channel.close()
        self._set(
            job,
            state=q.DONE,
            progress=1.0,
            stage="complete",
            eta_seconds=None,
            message="Done",
        )
        if job.id in self._resumed:
            self._resumed_done.append(job.title or job.display_name)
        self._listener("done", job)

    def _watch_settings(self, client: ScribeClient, job: q.Job) -> ScribeSettings | None:
        """A watch-folder file: the person's Scribe account defaults, read now, with
        the profile's (or Options') own fields on top, as the dialog starts (3.3)."""
        try:
            merged = quill_base(client.default_settings())  # no per-format emails (F8)
        except ScribeError:
            merged = {}
        merged.update(job.settings)
        return ScribeSettings.from_mapping(merged) if merged else None

    def _take_turn(self, job: q.Job) -> None:
        """Wait, silently, until the family has room for one more action (3.5)."""
        while True:
            self._check_cancel(job)
            try:
                wait = self.queue.reserve_action()
            except TimeoutError:
                wait = 0.5
            if wait <= 0:
                return
            self._wait(job, min(wait, 5.0))

    def _rate_limited(self, job: q.Job, resume: str) -> None:
        """``rate_limited``: every app waits a minute (no Retry-After is sent).
        Said once per job; the time to the next try shows silently in the job."""
        wait = self.queue.pause_for_rate_limit()
        self._set(
            job,
            state=q.BUSY,
            not_before=self.queue.now() + wait,
            message="Scribe asked to slow down; trying again in a minute.",
        )
        self._listener("busy", job)
        self._wait(job, wait)
        self._set(job, state=resume, not_before=0.0, message="")

    def _open_channel(self, job: q.Job, client: ScribeClient) -> DocumentChannel:
        down_since = 0.0
        while True:
            self._check_cancel(job)
            try:
                return self._channel_opener(client, job.document_id)
            except ScribeOfflineError:
                down_since = down_since or self._clock()
                self._offline(job, down_since)

    def _poll_complete(
        self,
        job: q.Job,
        client: ScribeClient,
        format_id: str,
        position: int,
        total: int,
    ) -> bool:
        return poll_complete(self, job, client, format_id, position, total)

    def _convert(
        self,
        job: q.Job,
        client: ScribeClient,
        channel: DocumentChannel | None,
        format_id: str,
        position: int,
        total: int,
    ) -> DocumentChannel:
        started = False
        last_rest_poll = self._clock()
        down_since = 0.0
        while True:
            self._check_cancel(job)
            if channel is None:
                channel = self._open_channel(job, client)
                if down_since:
                    down_since = 0.0
                    self._listener("online", job)
                started = False
            try:
                if not started:
                    self._take_turn(job)
                    channel.start_conversion(format_id, self._passwords.get(job.id, ""))
                    started = True
                    self._set(
                        job,
                        state=q.CONVERTING,
                        format=format_id,
                        stage="queue",
                        eta_seconds=None,
                        message=conversion_message(format_id, "queue", 0.0),
                    )
                    self._listener("changed", job)
                    if self._poll_complete(job, client, format_id, position, total):
                        return channel
                    last_rest_poll = self._clock()
                event = channel.next_event(1.0)
            except ScribeInProgressError:
                self._wait_for_any_complete(job, channel)
                continue
            except ScribeBusyError:
                self._rate_limited(job, q.CONVERTING)
                started = False  # start this format again after the pause
                continue
            except ScribeOfflineError:
                channel.close()
                channel = None
                down_since = down_since or self._clock()
                self._offline(job, down_since)
                continue
            now = self._clock()
            if event is None:
                interval = _ETA_POLL_S if format_id == "mp3" else _QUIET_POLL_S
                if now - last_rest_poll >= interval:
                    last_rest_poll = now
                    if self._poll_complete(job, client, format_id, position, total):
                        return channel
                continue
            if self._handle(job, event, format_id, position, total):
                return channel
            # Pneuma's WebSocket status frames have no ETA. Keep refreshing the
            # REST outputs row while live MP3 events keep arriving instead of
            # waiting for 15 seconds of channel silence.
            if format_id == "mp3" and now - last_rest_poll >= _ETA_POLL_S:
                last_rest_poll = now
                if self._poll_complete(job, client, format_id, position, total):
                    return channel

    def _wait_for_any_complete(self, job: q.Job, channel: DocumentChannel) -> None:
        """``conversion_in_progress``: wait for the running format (often the free
        preview) to finish, then start again. Never shown as an error."""
        wait_for_any_complete(self, job, channel, _IN_PROGRESS_WAIT_S)

    def _handle(
        self, job: q.Job, event: ChannelEvent, format_id: str, position: int, total: int
    ) -> bool:
        """Apply one event; True when *format_id* is complete."""
        return handle_event(self, job, event, format_id, position, total)

    def _download(
        self, job: q.Job, client: ScribeClient, format_id: str, position: int, total: int
    ) -> None:
        title = job.title or Path(job.file_name).stem or job.document_id
        folder = Path(job.folder) if job.folder else document_folder(title, self._download_root())
        self._set(
            job,
            state=q.DOWNLOADING,
            format=format_id,
            stage="",
            eta_seconds=None,
            message=f"Downloading {format_label(format_id)}.",
            folder=str(folder),
        )
        self._listener("changed", job)

        def progress(done: int, size: int | None) -> None:
            if size:
                fraction = (position + 0.9 + 0.1 * done / size) / total
                self._set(job, force=False, progress=max(job.progress, fraction))

        saved = client.download(
            job.document_id,
            format_id,
            folder,
            name_for=lambda name: unique_path(folder / name),
            on_progress=progress,
            cancel_requested=lambda: self._cancel_requested(job),
            stem=title,  # our name, never the title Scribe read from the document (F6)
        )
        if format_id == "daisy":
            # DAISY 3 as a zip: unpack beside it now, so Open Result finds the .ncx.
            try:
                daisy_entry(saved)
            except (OSError, zipfile.BadZipFile):
                logger.info("Scribe DAISY unpack failed id=%s", job.document_id)
        outputs = dict(job.outputs)
        outputs[format_id] = str(saved)
        self._set(
            job,
            outputs=outputs,
            progress=(position + 1) / total,
            eta_seconds=None,
            message=f"Downloaded {format_label(format_id)}.",
        )
        try:
            self._library.record(job.document_id, title, format_id, saved)
        except OSError:
            logger.info("Scribe library record failed id=%s", job.document_id)

    def _cancel_requested(self, job: q.Job) -> bool:
        try:
            self._check_cancel(job)
        except ScribeCancelled:
            return True
        return False


_RUN_FIELDS = (
    "state",
    "format",
    "stage",
    "progress",
    "eta_seconds",
    "message",
    "error_code",
    "purchase_url",
    "folder",
    "outputs",
    "password_tries",
    "not_before",
    "document_id",
)


def _persisted(job: q.Job) -> dict[str, Any]:
    """The fields the runner changes, as they are now."""
    return {name: getattr(job, name) for name in _RUN_FIELDS}


__all__ = ["Listener", "QueueService", "default_channel_opener"]
