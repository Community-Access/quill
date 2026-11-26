"""Runtime and durable persistence for Transcribe a Recording jobs."""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any

import wx

from quill.core.windows_dictation.file_queue import (
    ACTIVE,
    DONE,
    FAILED,
    QUEUED,
    STOPPED,
    TRANSCRIBING,
)
from quill.ui.transcription_queue_host import durable_host, safe_mode
from quill.ui.transcription_queue_notices import (
    cancel_notice,
    queue_notice,
    report_notice_failure,
)
from quill.ui.transcription_queue_poll import after_lock
from quill.ui.transcription_queue_poll import cancel as cancel_poll
from quill.ui.transcription_queue_record import stored_job
from quill.ui.transcription_queue_repository import repository_for
from quill.ui.transcription_queue_state import (
    Entry,
    Result,
    RuntimeQueue,
    TranscriptPersistenceError,
)
from quill.ui.transcription_queue_state import (
    runtime_queue as _runtime_queue,
)

_ids = itertools.count(1)
_ACTION = "Transcribe"
_TASK = "dictation-transcribe-file"


_HEARTBEATS: set[Path] = set()


def queue_text(host: Any | None = None) -> str:
    current = _runtime_queue().describe()
    if current or host is None:
        return current
    try:
        return repository_for(host).describe()
    except OSError:
        return ""


def enqueue_many(
    jobs: list[Any],
    host: Any,
    rewrite: Any = None,
    *,
    cloud_approved: bool = False,
) -> list[Entry]:
    """Persist several files once, then start the first and keep the rest queued."""
    if not jobs:
        return []
    host = durable_host(host)
    batch = ""
    if len(jobs) > 1:
        batch = f"{jobs[0].path.name} plus {len(jobs) - 1} more"
    made = [stored_job(job, host, batch=batch, cloud_approved=cloud_approved) for job in jobs]
    repository_for(host).add(made)
    runtime = _runtime_queue()
    entries = [
        Entry(job, host, rewrite=rewrite, queue_job=stored)
        for job, stored in zip(jobs, made, strict=True)
    ]
    for entry in entries:
        runtime.waiting.append(entry)
        queue_notice(
            entry,
            title=f"Transcription queued: {entry.job.path.name}",
            body="Waiting for the recordings ahead of it.",
            category="progress",
            create=True,
        )
    if runtime.current is None:
        _start_next()
    return entries


def stop(host: Any) -> tuple[int, bool]:
    """Cancel one host's current job and everything waiting for this process."""
    requested = host
    owner = durable_host(host)
    runtime = _runtime_queue()
    waiting = [entry for entry in runtime.waiting if entry.host is requested or entry.host is owner]
    runtime.waiting = [
        entry
        for entry in runtime.waiting
        if entry.host is not requested and entry.host is not owner
    ]
    for entry in waiting:
        _persist_stop(entry, "Stopped waiting.")
        cancel_notice(entry)
    current = (
        runtime.current
        if runtime.current is not None
        and (runtime.current.host is requested or runtime.current.host is owner)
        else None
    )
    if current is not None:
        current.cancel.set()
        _persist_stop(current, "Stopped.")
    if current is None and not waiting:
        return 0, False
    return len(waiting), current is not None


def retry(job_id: str, host: Any) -> bool:
    runtime = _runtime_queue()
    if any(
        entry.queue_job is not None and entry.queue_job.id == job_id
        for entry in [
            *runtime.waiting,
            *(([runtime.current]) if runtime.current else []),
        ]
    ):
        return False
    if not repository_for(host).retry(job_id):
        return False
    resume(host)
    return True


def remove(job_id: str, host: Any) -> bool:
    return repository_for(host).remove(job_id)


def cancel_waiting(job_id: str, host: Any) -> bool:
    repository = repository_for(host)
    changed = repository.stop(job_id, "Stopped waiting.")
    if not changed:
        return False
    runtime = _runtime_queue()
    for entry in list(runtime.waiting):
        if entry.queue_job is not None and entry.queue_job.id == job_id:
            runtime.waiting.remove(entry)
            entry.cancel.set()
    current = runtime.current
    if current is not None and current.queue_job is not None and current.queue_job.id == job_id:
        current.cancel.set()
    return True


def resume(host: Any) -> int:
    """Recover interrupted jobs and start the next one when this app may own the runner."""
    host = durable_host(host)
    repository = repository_for(host)
    if not repository.try_acquire(host._dictation_app_name()):  # type: ignore[attr-defined]
        after_lock(host, repository.path, resume)
        return 0
    cancel_poll(repository.path)
    runtime = _runtime_queue()
    known = {
        entry.queue_job.id
        for entry in [*runtime.waiting, *(([runtime.current]) if runtime.current else [])]
        if entry.queue_job is not None
    }
    repository.recover_interrupted(excluding=known)
    jobs = [job for job in repository.jobs() if job.state in ACTIVE]
    if not jobs:
        repository.release()
        return 0
    added = 0
    for stored in jobs:
        if stored.id in known:
            continue
        if stored.model.startswith("openai:") and (not stored.cloud_approved or safe_mode(host)):
            repository.update(
                stored.id,
                message="Waiting for a cloud transcription consent outside Safe Mode.",
            )
            continue
        rewrite = getattr(host, "_dictation_file_rewrite", None)
        entry = Entry(
            stored.file_job(),
            host,
            rewrite=rewrite() if callable(rewrite) else None,
            queue_job=stored,
        )
        runtime.waiting.append(entry)
        added += 1
    if runtime.current is None and runtime.waiting:
        _start_next()
    if runtime.current is None and not runtime.waiting:
        _HEARTBEATS.discard(repository.path)
        repository.release()
    if runtime.current is not None:
        _schedule_heartbeat(host)
    return added


def suspend(host: Any) -> None:
    """Requeue current work while an app closes, so the next app can carry on."""
    requested = host
    host = durable_host(host)
    runtime = _runtime_queue()
    repository = repository_for(host)
    current = runtime.current
    if current is not None and (current.host is requested or current.host is host):
        current.suspended = True
        current.cancel.set()
        if current.queue_job is not None:
            repository.requeue(current.queue_job.id, "Will carry on after the next start")
    runtime.waiting = [
        entry for entry in runtime.waiting if entry.host is not requested and entry.host is not host
    ]
    if current is not None and (current.host is requested or current.host is host):
        runtime.current = None
    _HEARTBEATS.discard(repository.path)
    cancel_poll(repository.path)
    repository.release()


def _schedule_heartbeat(host: Any) -> None:
    repository = repository_for(host)
    if repository.path in _HEARTBEATS:
        return
    get_app = getattr(wx, "GetApp", None)
    call_later = getattr(wx, "CallLater", None)
    if not callable(call_later) or (callable(get_app) and get_app() is None):
        return

    def beat() -> None:
        if repository.path not in _HEARTBEATS:
            return
        if repository.try_acquire(host._dictation_app_name()):  # type: ignore[attr-defined]
            try:
                call_later(10000, beat)
            except Exception:  # noqa: BLE001 - heartbeat loss must not break transcription
                _HEARTBEATS.discard(repository.path)
            return
        _HEARTBEATS.discard(repository.path)

    try:
        _HEARTBEATS.add(repository.path)
        call_later(10000, beat)
    except Exception:  # noqa: BLE001 - a timer is optional in headless/test hosts
        _HEARTBEATS.discard(repository.path)


def _persist_stop(entry: Entry, message: str) -> None:
    if entry.queue_job is None:
        return
    repository_for(entry.host).stop(entry.queue_job.id, message)
    entry.queue_job.state = STOPPED


def _start_next() -> None:
    runtime = _runtime_queue()
    if runtime.current is not None or not runtime.waiting:
        return
    entry = runtime.waiting.pop(0)
    runtime.current = entry
    host = entry.host
    name = entry.job.path.name
    repository = repository_for(host)
    if entry.queue_job is None:
        [stored] = [
            stored_job(entry.job, host, batch="", cloud_approved=False),
        ]
        repository.add([stored])
        entry.queue_job = stored
    if not repository.try_acquire(host._dictation_app_name()):  # type: ignore[attr-defined]
        runtime.waiting.insert(0, entry)
        runtime.current = None
        repository.update(
            entry.queue_job.id, state=QUEUED, message="Another QUILL app is running it"
        )
        return
    stored = repository.get(entry.queue_job.id)
    attempts = (stored.attempts if stored is not None else entry.queue_job.attempts) + 1
    repository.update(
        entry.queue_job.id,
        state=TRANSCRIBING,
        progress=0.0,
        message="Preparing recording",
        started_at=repository._clock(),
        finished_at=0.0,
        attempts=attempts,
    )
    from quill.core import activity

    entry.operation = f"transcribe-{next(_ids)}"
    message = f"Transcribing {name}"
    announcer = activity.ProgressAnnouncer(step=25)
    first = activity.Progress(entry.operation, "transcribing", message, 0, 100, can_cancel=True)
    activity.LOG.begin(first)
    announcer.next_sentence(first)
    host._dictation_say(f"Transcribing {name} in the background.")
    host._dictation_status(f"{message}...")
    _schedule_heartbeat(host)

    from quill.core.windows_dictation.file_transcribe import FileTranscriber

    def work(cancellation_token: Any = None, progress_callback: Any = None, **_kwargs: Any) -> Any:
        if entry.notice_future is None:
            queue_notice(
                entry,
                title=f"Transcription queued: {name}",
                body="Waiting to start.",
                category="progress",
                create=True,
            )
        queue_notice(
            entry,
            title=f"Transcribing: {name}",
            body="Transcription is running.",
            category="progress",
        )

        def cancelled() -> bool:
            token_says = bool(cancellation_token is not None and cancellation_token.is_cancelled())
            stored = repository.get(entry.queue_job.id) if entry.queue_job is not None else None
            return (
                entry.cancel.is_set()
                or token_says
                or bool(stored is not None and stored.state == STOPPED)
            )

        def progress(fraction: float | None, seconds: float) -> None:
            if fraction is not None:
                percent = int(fraction * 100)
                if percent >= entry.notified_percent + 25 and percent < 100:
                    entry.notified_percent = percent - (percent % 25)
                    queue_notice(
                        entry,
                        title=f"Transcribing: {name}",
                        body=f"{entry.notified_percent} percent complete.",
                        category="progress",
                    )
                    if entry.queue_job is not None:
                        entry.queue_job = repository.update(
                            entry.queue_job.id,
                            progress=max(0.0, min(1.0, fraction)),
                            message=f"Transcribing, {entry.notified_percent} percent",
                        )
            if progress_callback is not None:
                progress_callback((fraction, seconds))

        from quill.core.windows_dictation.file_transcribe import TranscriptionCancelled, plain

        try:
            transcript = FileTranscriber(entry.job, rewrite=entry.rewrite).run(progress, cancelled)
            if entry.cancel.is_set():
                raise TranscriptionCancelled("Transcription stopped.")
        except Exception as error:  # noqa: BLE001 - persist terminal state without failing the worker
            canceled = isinstance(error, TranscriptionCancelled)
            notice_saved = queue_notice(
                entry,
                title=f"Transcription {'canceled' if canceled else 'failed'}: {name}",
                body=plain(error),
                category="warning" if canceled else "error",
            ).result()
            return Result(error=error, notice_error="" if notice_saved else entry.notice_error)

        text = transcript.text(entry.job.timestamps)
        from quill.core.windows_dictation.file_transcribe import done_sentence

        sentence = done_sentence(name, transcript)
        transcript_id = ""
        transcript_path = ""
        storage_error: BaseException | None = None
        if text.strip():
            try:
                transcript_id = host._dictation_save_transcript(text)
                transcript_path = str(
                    Path(host._dictation_data_dir())
                    / "dictation"
                    / "transcripts"
                    / f"{transcript_id}.txt"
                )
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
        notice_saved = queue_notice(
            entry,
            title=title,
            body=body,
            target=target,
            category=category,
        ).result()
        return Result(
            transcript=transcript,
            error=storage_error,
            notice_error="" if notice_saved else entry.notice_error,
            output_id=transcript_id,
            output_path=transcript_path,
        )

    def on_progress(_operation: str, payload: Any) -> None:
        fraction, seconds = payload
        if fraction is None:
            from quill.core.windows_dictation.file_models import spoken_length

            host._dictation_status(f"{message}: {spoken_length(seconds)} heard")
            return
        entry.percent = int(fraction * 100)
        from quill.core import activity

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
    except Exception as error:  # noqa: BLE001 - reported like any transcription failure
        _finish(entry, None, error)


def _persist_terminal(entry: Entry, result: Result, error: BaseException | None) -> None:
    if entry.queue_job is None:
        return
    repository = repository_for(entry.host)
    if isinstance(error, _transcription_cancelled_type()):
        repository.update(
            entry.queue_job.id,
            state=STOPPED,
            message="Stopped",
            progress=0.0,
            finished_at=repository._clock(),
        )
    elif error is not None:
        from quill.core.windows_dictation.file_transcribe import plain

        repository.update(
            entry.queue_job.id,
            state=FAILED,
            message=plain(error),
            finished_at=repository._clock(),
        )
    else:
        repository.update(
            entry.queue_job.id,
            state=DONE,
            progress=1.0,
            message="Done",
            output_id=result.output_id,
            output_path=result.output_path,
            finished_at=repository._clock(),
        )


def _transcription_cancelled_type() -> type[BaseException]:
    from quill.core.windows_dictation.file_transcribe import TranscriptionCancelled

    return TranscriptionCancelled


def _finish(entry: Entry, transcript: Any, error: BaseException | None) -> None:
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
    runtime = _runtime_queue()
    if runtime.current is entry:
        runtime.current = None
    host = entry.host
    name = entry.job.path.name
    host._dictation_status("")
    has_worker_result = isinstance(transcript, Result)
    result = transcript if has_worker_result else Result(transcript, error)
    transcript = result.transcript
    error = result.error
    if entry.suspended and isinstance(error, TranscriptionCancelled):
        _start_next()
        return
    _persist_terminal(entry, result, error)
    if entry.suspended:
        _start_next()
        return
    if isinstance(error, TranscriptionCancelled):
        if not has_worker_result:
            report_notice_failure(
                entry,
                queue_notice(
                    entry,
                    title=f"Transcription canceled: {name}",
                    body="Transcription stopped.",
                    category="warning",
                ),
                f"The canceled transcription of {name} could not be kept in Notifications.",
            )
        sentence = (
            f"Stopped transcribing {name}. No transcript was kept; "
            "transcribe it again to start over."
        )
        keep_outcome(_ACTION, sentence, object_name=name)
        if result.notice_error:
            sentence += f" It could not be kept in Notifications. {result.notice_error}"
        host._dictation_say(sentence)
    elif error is not None:
        reason = plain(error)
        if isinstance(error, TranscriptPersistenceError):
            summary = f"Transcribed {name}, but could not save the transcript."
            reason = (
                f"The recording was transcribed, but the transcript could not be saved: {reason}"
            )
        else:
            summary = f"Could not transcribe {name}."
        if not has_worker_result:
            report_notice_failure(
                entry,
                queue_notice(
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
    if runtime.current is None:
        _start_next()
        if runtime.current is None:
            try:
                repository = repository_for(host)
                _HEARTBEATS.discard(repository.path)
                repository.release()
            except OSError:
                pass


__all__ = [
    "Entry",
    "Result",
    "RuntimeQueue",
    "TranscriptPersistenceError",
    "cancel_waiting",
    "enqueue_many",
    "queue_text",
    "remove",
    "repository_for",
    "resume",
    "retry",
    "stop",
    "suspend",
]
