"""The runner half of the pre-roll guard: reference connections and trims.

``recording_preroll`` decides, from loudness outlines alone, how much of each
part is the station's connection insert (its pre-roll advert or welcome). This
module does the work around that verdict: it opens the late *reference*
connection when a recording starts, decodes openings with ffmpeg, and cuts the
insert from the front of each finished part before the recorder joins them.
Split from the pure half under GATE-11, and so the tests can drive the guard
with a fake decoder and a fake trimmer: no network, no ffmpeg.

wx-free, strict-typed.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.radio.recording_preroll import (
    ALL_INSERT_MARGIN_SECONDS,
    ANALYSE_SECONDS,
    DECODE_SLACK_SECONDS,
    HOP_SECONDS,
    MIN_TRIMMED_BYTES,
    REFERENCE_DELAY_SECONDS,
    Opening,
    build_opening_decode_command,
    build_trim_command,
    describe_trims,
    envelope_from_pcm,
    guard_applies,
    plan_trims,
)
from quill.core.radio.recording_winjob import assign_kill_on_close_job, close_job_handle
from quill.stability.redaction import format_args_for_log

logger = logging.getLogger(__name__)

__all__ = ["Decoder", "OpeningGuard", "Trimmer", "decode_opening", "trim_start"]

#: Seconds a trim (a stream copy of the whole part) may take.
_TRIM_TIMEOUT_SECONDS = 600.0

#: decode(source) -> the opening, or None when it could not be decoded.
Decoder = Callable[[str], "Opening | None"]
#: trim(path, seconds) -> whether the file now starts *seconds* later.
Trimmer = Callable[[Path, float], bool]


class _Processes:
    """The decoders in flight, so a shutdown can end them."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._live: set[subprocess.Popen[bytes]] = set()

    def add(self, process: subprocess.Popen[bytes]) -> None:
        with self._lock:
            self._live.add(process)

    def remove(self, process: subprocess.Popen[bytes]) -> None:
        with self._lock:
            self._live.discard(process)

    def kill_all(self) -> None:
        with self._lock:
            live = list(self._live)
        for process in live:
            try:
                process.kill()
            except OSError:
                pass


_PROCESSES = _Processes()


def decode_opening(source: str) -> Opening | None:
    """Decode the opening of *source* (a stream URL or a recorded file)."""
    from quill.core import http_client
    from quill.core.speech.ffmpeg import find_ffmpeg

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        return None
    args = build_opening_decode_command(ffmpeg, source, user_agent=http_client.user_agent())
    extra: dict[str, Any] = {}
    if os.name == "nt":
        extra["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        process = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            **extra,
        )
    except OSError as exc:
        logger.debug("pre-roll guard: decoder did not start: %s", exc)
        return None
    win_job = assign_kill_on_close_job(process)
    _PROCESSES.add(process)
    try:
        pcm, _ = process.communicate(timeout=ANALYSE_SECONDS + DECODE_SLACK_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        pcm, _ = process.communicate()
    finally:
        _PROCESSES.remove(process)
        if win_job is not None:
            close_job_handle(win_job)
    envelope = envelope_from_pcm(pcm or b"")
    if not envelope:
        return None
    complete = len(envelope) * HOP_SECONDS < ANALYSE_SECONDS - 1.0
    return Opening(envelope=envelope, complete=complete)


def trim_start(path: Path, seconds: float) -> bool:
    """Cut the first *seconds* from *path* in place. Never loses the file: the
    trimmed copy replaces the original only once it exists and holds audio."""
    from quill.core.speech.ffmpeg import find_ffmpeg
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        return False
    temp = path.with_name(f"{path.stem}.trimming{path.suffix}")
    try:
        result = run_subprocess_safely(
            build_trim_command(ffmpeg, path, temp, seconds),
            timeout_seconds=_TRIM_TIMEOUT_SECONDS,
        )
        if result.returncode != 0 or temp.stat().st_size < MIN_TRIMMED_BYTES:
            raise OSError(f"ffmpeg exited {result.returncode}")
        os.replace(temp, path)
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning(
            "pre-roll guard: could not trim %s (%s); keeping it as recorded.",
            format_args_for_log([str(path)]),
            exc,
        )
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        return False


class _Reference:
    """One recording's reference connection: started late, decoded in memory."""

    def __init__(self, source: str, decode: Decoder, delay_seconds: float) -> None:
        self.opening: Opening | None = None
        self.done = threading.Event()
        self.cancelled = threading.Event()
        self._source = source
        self._decode = decode
        self._delay = delay_seconds
        threading.Thread(target=self._run, daemon=True, name="quill-radio-preroll-ref").start()

    def _run(self) -> None:
        try:
            if self.cancelled.wait(self._delay):
                return
            self.opening = self._decode(self._source)
        except Exception:  # noqa: BLE001 - a failed reference only means no trim
            logger.debug("pre-roll guard: reference connection failed", exc_info=True)
        finally:
            self.done.set()


class OpeningGuard:
    """Owns the reference connections and the trim at the end (see module doc).

    The recorder calls :meth:`begin` when a recording's first connection opens,
    :meth:`strip` with the finished parts just before it joins them, and
    :meth:`discard` / :meth:`cancel_all` when a recording ends with nothing to
    keep or the app closes.
    """

    def __init__(
        self,
        *,
        decode: Decoder | None = None,
        trim: Trimmer | None = None,
        delay_seconds: float = REFERENCE_DELAY_SECONDS,
        wait_seconds: float = REFERENCE_DELAY_SECONDS + ANALYSE_SECONDS + DECODE_SLACK_SECONDS,
    ) -> None:
        # None means the module's own runners, looked up at the moment of use
        # rather than bound here, so the test suite can swap them for fakes
        # (tests/conftest.py) and a reference thread started under a fake
        # keeps that fake even after the test has finished.
        self._decode_with = decode
        self._trim_with = trim
        self._delay = delay_seconds
        self._wait = wait_seconds
        self._lock = threading.Lock()
        self._references: dict[str, _Reference | None] = {}

    def begin(self, job_id: str, stream_url: str, capture_url: str) -> None:
        """A recording's first connection just opened: listen to a second one."""
        reference = (
            _Reference(capture_url, self._decode_with or decode_opening, self._delay)
            if guard_applies(stream_url, capture_url)
            else None
        )
        with self._lock:
            self._references[job_id] = reference

    def discard(self, job_id: str) -> None:
        with self._lock:
            reference = self._references.pop(job_id, None)
        if reference is not None:
            reference.cancelled.set()

    def cancel_all(self) -> None:
        with self._lock:
            references = list(self._references.values())
            self._references.clear()
        for reference in references:
            if reference is not None:
                reference.cancelled.set()
        _PROCESSES.kill_all()

    def strip(self, job_id: str, parts: list[Path]) -> tuple[list[Path], str]:
        """Cut the connection insert from the front of every part.

        Returns the parts that still hold a recording (one that was nothing but
        the insert is removed, as long as another part survives) and a sentence
        for the listener, ``""`` when nothing was cut. Never raises: any failure
        leaves the parts as they were recorded.
        """
        with self._lock:
            known = job_id in self._references
            reference = self._references.pop(job_id, None)
        if not parts or not known:
            return parts, ""
        try:
            return self._strip(reference, parts)
        except Exception:  # noqa: BLE001 - the recording itself is safe either way
            logger.warning(
                "pre-roll guard: comparison failed; parts kept as recorded", exc_info=True
            )
            return parts, ""

    def _strip(self, reference: _Reference | None, parts: list[Path]) -> tuple[list[Path], str]:
        ref_opening: Opening | None = None
        if reference is not None:
            if len(parts) == 1 and not reference.done.is_set():
                reference.done.wait(self._wait)
            ref_opening = reference.opening
            reference.cancelled.set()
        if ref_opening is None and len(parts) < 2:
            return parts, ""
        decode = self._decode_with or decode_opening
        trim = self._trim_with or trim_start
        openings = [decode(str(part)) for part in parts]
        trims = plan_trims(ref_opening, openings)
        kept: list[Path] = []
        applied: list[float] = []
        dropped = 0
        for index, (part, opening, seconds) in enumerate(zip(parts, openings, trims, strict=True)):
            if seconds <= 0 or opening is None:
                kept.append(part)
                continue
            all_insert = opening.complete and seconds >= opening.seconds - ALL_INSERT_MARGIN_SECONDS
            # Only a continuation part is ever removed whole: part one carries
            # the recording's name, which the join keeps.
            if all_insert and index > 0:
                try:
                    part.unlink()
                    dropped += 1
                    logger.info("pre-roll guard: removed an all-insert part %s", part.name)
                    continue
                except OSError:
                    kept.append(part)
                    continue
            if trim(part, seconds):
                applied.append(seconds)
                logger.info("pre-roll guard: trimmed %.1fs from %s", seconds, part.name)
            kept.append(part)
        return kept, describe_trims(applied, dropped)
