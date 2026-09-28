"""The batch runner: many conversions across worker threads, stoppable at once.

Extracted from :mod:`quill.core.audio.convert` (GATE-11) when Quill Converter
1.0.0 gained progress inside a file and a Stop that stops the file in
progress. Both used to be missing for the same reason -- the runner only knew
about whole files -- so a one-file batch of a long audiobook said nothing
until it ended, and Stop waited for it. Every name here is re-exported from
``convert``, so callers keep importing from there.

Pure of ``wx`` and of any UI; ``single_runner`` is injectable so the fan-out
is testable without spawning FFmpeg.
"""

from __future__ import annotations

import inspect
import os
import threading
from collections.abc import Callable, Sequence

from quill.core.audio.convert import BatchResult, ConversionJob, JobResult
from quill.core.audio.ffmpeg_live import LiveHooks

# A single-job runner: (ffmpeg, job) -> JobResult. Injectable for tests; the
# default one shells out with a temp-then-move write. A runner that also takes
# a ``hooks`` keyword gets live progress and an immediate stop.
SingleJobRunner = Callable[..., JobResult]

ProgressCallback = Callable[[int, int, ConversionJob], None]  # (done, total, current)

# (job, fraction 0.0-1.0 of that one file) -- from the worker thread.
FileProgressCallback = Callable[[ConversionJob, float], None]


class CancelToken:
    """A thread-safe cooperative cancel flag (a thin ``threading.Event`` wrapper)."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


def run_conversion_batch(
    ffmpeg: str,
    jobs: Sequence[ConversionJob],
    *,
    workers: int = 0,
    on_progress: ProgressCallback | None = None,
    on_file_progress: FileProgressCallback | None = None,
    cancel: CancelToken | None = None,
    single_runner: SingleJobRunner | None = None,
) -> BatchResult:
    """Convert ``jobs`` across up to ``workers`` threads, reporting progress (§8).

    ``workers`` <= 0 auto-picks ``max(1, cpu-1)``. ``on_progress`` hears each
    finished file; ``on_file_progress`` hears how far each running file has
    got. A stop takes effect at once: a file not yet started is skipped, and
    one being encoded is killed, its partial output removed, and reported as
    skipped.
    """
    from concurrent.futures import ThreadPoolExecutor

    from quill.core.audio.convert_runner import _default_single_runner

    runner = single_runner if single_runner is not None else _default_single_runner
    token = cancel if cancel is not None else CancelToken()
    n_workers = workers if workers > 0 else max(1, (os.cpu_count() or 2) - 1)
    total = len(jobs)
    result = BatchResult()
    done = 0

    if total == 0:
        return result

    live = "hooks" in inspect.signature(runner).parameters
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = []
        for job in jobs:
            if token.is_cancelled():
                result.results.append(JobResult(job=job, ok=False, skipped=True))
                continue
            hooks = _hooks_for(job, on_file_progress, token) if live else None
            futures.append((job, pool.submit(_guarded_run, runner, ffmpeg, job, token, hooks)))
        for job, fut in futures:
            job_result = fut.result()
            result.results.append(job_result)
            done += 1
            if on_progress is not None:
                on_progress(done, total, job)
    result.cancelled = token.is_cancelled()
    return result


def _hooks_for(
    job: ConversionJob, on_file_progress: FileProgressCallback | None, token: CancelToken
) -> LiveHooks:
    report = None
    if on_file_progress is not None:
        callback = on_file_progress

        def report(fraction: float) -> None:
            callback(job, fraction)

    return LiveHooks(on_fraction=report, cancel=token)


def _guarded_run(
    runner: SingleJobRunner,
    ffmpeg: str,
    job: ConversionJob,
    token: CancelToken,
    hooks: LiveHooks | None,
) -> JobResult:
    # Every job is queued at once, so a stop has to be honoured here, when a
    # worker picks the job up -- checking only while queueing never skipped
    # anything.
    if token.is_cancelled():
        return JobResult(job=job, ok=False, skipped=True)
    try:
        if hooks is not None:
            return runner(ffmpeg, job, hooks=hooks)
        return runner(ffmpeg, job)
    except Exception as exc:  # noqa: BLE001 - one bad file must never sink the batch
        return JobResult(job=job, ok=False, error=str(exc))


def default_worker_count() -> int:
    """A sensible default worker count: one per core, minus one for the UI (§8)."""
    return max(1, (os.cpu_count() or 2) - 1)
