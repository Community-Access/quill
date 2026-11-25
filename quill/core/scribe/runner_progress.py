"""Live conversion progress and quiet-channel fallback for the Scribe runner."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from quill.core.scribe import queue as q
from quill.core.scribe.channel import ChannelEvent, DocumentChannel
from quill.core.scribe.client import ScribeClient
from quill.core.scribe.errors import ScribeOfflineError, ScribePasswordError, error_from_server
from quill.core.scribe.model import format_label, stage_words


class ProgressRunner(Protocol):
    _passwords: dict[str, str]
    _clock: Callable[[], float]
    _listener: Callable[[str, q.Job | None], None]

    def _set(self, job: q.Job, *, force: bool = True, **changes: Any) -> q.Job: ...

    def _check_cancel(self, job: q.Job) -> None: ...


def conversion_message(format_id: str, stage: str, progress: float) -> str:
    return f"{format_label(format_id)}: {stage_words(stage)}, {int(progress * 100)} percent."


def estimating_message(format_id: str) -> str:
    return f"{format_label(format_id)}: estimating time remaining."


def chunk_job(job: q.Job, event: ChannelEvent) -> q.Job:
    """A throwaway job carrying one streamed chunk in ``message`` (never stored)."""
    return q.Job(id=job.id, document_id=job.document_id, message=event.content, app=job.app)


def poll_complete(
    runner: ProgressRunner,
    job: q.Job,
    client: ScribeClient,
    format_id: str,
    position: int,
    total: int,
) -> bool:
    """Refresh progress from the REST fallback. Return True when this output is complete."""
    try:
        outputs, needs_password = client.list_outputs(job.document_id)
    except ScribeOfflineError:
        return False
    if needs_password and not runner._passwords.get(job.id):
        raise ScribePasswordError(
            f"{job.display_name} needs its password.", reason="password_required"
        )
    for output in outputs:
        if output.format == format_id:
            stage_changed = output.stage != job.stage
            progress = (position + output.progress * 0.9) / total
            runner._set(
                job,
                force=stage_changed,
                state=q.CONVERTING,
                format=format_id,
                stage=output.stage,
                progress=progress,
                eta_seconds=output.estimated_time_remaining,
                message=conversion_message(format_id, output.stage, output.progress),
            )
            if stage_changed:
                runner._listener("changed", job)
            return output.is_complete
    if job.eta_seconds is not None:
        runner._set(
            job,
            eta_seconds=None,
            message=estimating_message(format_id),
        )
        runner._listener("changed", job)
    return False


def wait_for_any_complete(
    runner: ProgressRunner,
    job: q.Job,
    channel: DocumentChannel,
    wait_seconds: float,
) -> None:
    """Wait while another format is converting, forwarding preview chunks."""
    end = runner._clock() + wait_seconds
    while runner._clock() < end:
        runner._check_cancel(job)
        event = channel.next_event(1.0)
        if event is not None and event.kind == "conversion_complete":
            if event.format == "html_stream":
                runner._listener("stream_done", chunk_job(job, event))
            return
        if event is not None and event.kind == "chunk":
            runner._listener("chunk", chunk_job(job, event))


def handle_event(
    runner: ProgressRunner,
    job: q.Job,
    event: ChannelEvent,
    format_id: str,
    position: int,
    total: int,
) -> bool:
    """Apply one channel event; return True when this format is complete."""
    if event.kind == "status":
        if event.format == "html_stream":
            return False
        stage_changed = event.stage != job.stage
        progress = (position + (event.progress if event.format == format_id else 0.0) * 0.9) / total
        is_current_output = event.format == format_id
        restarted = is_current_output and (
            progress < job.progress or event.stage in {"queue", "start", "complete"}
        )
        # WebSocket status frames have no ETA. Keep the last REST value for a
        # forward-moving frame, but discard it when the current output resets,
        # finishes, or moves backward.
        runner._set(
            job,
            force=stage_changed,
            state=q.CONVERTING,
            format=format_id,
            stage=event.stage,
            progress=progress if is_current_output else job.progress,
            eta_seconds=None if restarted else job.eta_seconds,
            message=conversion_message(event.format, event.stage, event.progress),
        )
        runner._listener("changed", job)
        return event.format == format_id and event.stage == "complete"
    if event.kind == "conversion_complete":
        if event.format == "html_stream":
            runner._listener("stream_done", chunk_job(job, event))
        return event.format == format_id
    if event.kind == "chunk":
        runner._listener("chunk", chunk_job(job, event))
        return False
    if event.kind == "password_required":
        if runner._passwords.get(job.id):
            return False
        raise ScribePasswordError(
            f"{job.display_name} needs its password.", reason="password_required"
        )
    if event.kind == "error":
        if event.reason == "invalid_password":
            raise ScribePasswordError("Password not accepted.", reason="invalid_password")
        raise error_from_server(event.reason, event.message, purchase_url=event.purchase_url)
    return False


__all__ = ["conversion_message", "handle_event", "poll_complete", "wait_for_any_complete"]
