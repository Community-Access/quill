"""Run one FFmpeg encode with live progress and a stop that stops it now.

``run_subprocess_safely`` waits for the whole encode and says nothing until
it ends, which is right for a probe and wrong for a two-hour audiobook: the
listener heard "Converting 1 file" and then silence until it finished, and
Stop could only take effect between files. This runner asks FFmpeg for its
machine-readable progress (``-progress pipe:1``), turns ``out_time`` into a
fraction of the expected length, and kills the process the moment the cancel
flag is set -- the caller then deletes the temp file, so a stopped encode
leaves nothing behind.

Pure of ``wx``. The fraction callback runs on the worker thread; UI callers
marshal it themselves (``wx.CallAfter``), as the family threading rule says.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from quill.stability.redaction import format_args_for_log

logger = logging.getLogger(__name__)

#: How often the watcher checks the stop flag and the clock, in seconds.
_POLL_SECONDS = 0.2


class _Cancellable(Protocol):
    def is_cancelled(self) -> bool: ...


@dataclass(slots=True)
class LiveHooks:
    """What a caller wants to hear about one encode while it runs.

    ``on_fraction`` receives 0.0 to 1.0 as the output grows (never above 1.0,
    and not at all when the length is unknown). ``cancel`` is polled while the
    process runs; once set, the process is killed.
    """

    on_fraction: Callable[[float], None] | None = None
    cancel: _Cancellable | None = None

    def cancelled(self) -> bool:
        return self.cancel is not None and self.cancel.is_cancelled()


@dataclass(slots=True)
class LiveResult:
    """The shape of ``subprocess.CompletedProcess`` the runner reads, plus a stop."""

    returncode: int
    stderr: str
    cancelled: bool = False
    timed_out: bool = False


def with_progress_args(command: Sequence[str]) -> list[str]:
    """``command`` with ``-progress pipe:1 -nostats`` right after the executable."""
    args = list(command)
    return args[:1] + ["-progress", "pipe:1", "-nostats"] + args[1:]


def parse_out_time(line: str) -> float | None:
    """Seconds of output written, from one ``-progress`` line -- or None.

    FFmpeg reports ``out_time_us`` and (despite the name, also microseconds)
    ``out_time_ms``; ``out_time`` is ``HH:MM:SS.micro``. Before the first
    packet it prints ``N/A``, which is not progress.
    """
    key, _, value = line.strip().partition("=")
    value = value.strip()
    if not value or value.upper() == "N/A":
        return None
    try:
        if key in ("out_time_us", "out_time_ms"):
            return max(0.0, int(value) / 1_000_000)
        if key == "out_time":
            hours, minutes, seconds = value.split(":")
            return max(0.0, int(hours) * 3600 + int(minutes) * 60 + float(seconds))
    except ValueError:
        return None
    return None


def run_ffmpeg_live(
    command: Sequence[str],
    *,
    duration_s: float,
    hooks: LiveHooks,
    timeout_seconds: float,
) -> LiveResult:
    """Run ``command`` (an FFmpeg argv), reporting progress and honouring a stop.

    ``duration_s`` is the length the output should have; 0 means unknown, and
    then no fraction is reported. Stderr goes to a temp file rather than a
    pipe, so a chatty failure can never fill a pipe nobody is reading and
    deadlock the encode.
    """
    args = with_progress_args(command)
    logger.info("Running ffmpeg live %s timeout=%s", format_args_for_log(args), timeout_seconds)
    creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    err_file: Any = tempfile.TemporaryFile()
    try:
        try:
            child = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=err_file,
                creationflags=creationflags,
            )
        except OSError as error:
            raise OSError(f"Could not run {args[0]!r}: {error}") from error
        stopped = {"cancelled": False, "timed_out": False}
        watcher = threading.Thread(
            target=_watch,
            args=(child, hooks, timeout_seconds, stopped),
            daemon=True,
            name="ffmpeg-live-watch",
        )
        watcher.start()
        _read_progress(child, duration_s, hooks)
        child.wait()
        watcher.join(timeout=5.0)
        err_file.seek(0)
        stderr = err_file.read().decode("utf-8", "replace")
    finally:
        err_file.close()
    if stopped["timed_out"]:
        stderr = (stderr + "\nThe conversion took too long and was stopped.").strip()
    return LiveResult(
        returncode=int(child.returncode if child.returncode is not None else 1),
        stderr=stderr,
        cancelled=stopped["cancelled"],
        timed_out=stopped["timed_out"],
    )


def _read_progress(child: subprocess.Popen[bytes], duration_s: float, hooks: LiveHooks) -> None:
    """Read ``-progress`` lines until FFmpeg closes stdout (it ends, or is killed)."""
    stream = child.stdout
    if stream is None:
        return
    last = -1.0
    for raw in stream:
        if hooks.on_fraction is None or duration_s <= 0:
            continue
        seconds = parse_out_time(raw.decode("ascii", "replace"))
        if seconds is None:
            continue
        # An effect that changes the tempo makes the output shorter or longer
        # than the source; never claim to be done before FFmpeg says so.
        fraction = min(0.99, seconds / duration_s)
        if fraction > last:
            last = fraction
            try:
                hooks.on_fraction(fraction)
            except Exception:  # noqa: BLE001 - a listener must never break an encode
                logger.debug("progress listener failed", exc_info=True)
    stream.close()


def _watch(
    child: subprocess.Popen[bytes],
    hooks: LiveHooks,
    timeout_seconds: float,
    stopped: dict[str, bool],
) -> None:
    """Kill ``child`` on a stop or when it outlives ``timeout_seconds``."""
    started = time.monotonic()
    while child.poll() is None:
        if hooks.cancelled():
            stopped["cancelled"] = True
        elif time.monotonic() - started > timeout_seconds:
            stopped["timed_out"] = True
        if stopped["cancelled"] or stopped["timed_out"]:
            try:
                child.kill()
            except OSError:
                pass
            return
        time.sleep(_POLL_SECONDS)
