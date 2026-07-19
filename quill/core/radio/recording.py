"""Recording a live internet-radio stream to a local audio file.

A radio stream is indefinite -- unlike a podcast episode, there is no natural
end -- so recording needs a controllable start/stop rather than a single
blocking call. This launches ``ffmpeg`` via :class:`subprocess.Popen` (with
the same ``CREATE_NO_WINDOW`` / logged-args safety properties as
``stability.safe_subprocess.run_subprocess_safely``, which cannot be used
here because it blocks until the process exits) and stops it by writing the
``q`` keypress ffmpeg's own stdin-driven quit handler reads -- the same
graceful stop a person pressing "q" in a terminal gets, closing the output
file's container properly instead of a hard kill truncating it.

Recording reuses the existing, already-optional ``ffmpeg`` component
(``quill.core.speech.ffmpeg``) -- the same one Audio Studio exports and
transcription depend on -- rather than introducing a second ffmpeg
dependency path.

wx-free, strict-typed.
"""

from __future__ import annotations

import logging
import math
import os
import re
import shutil
import subprocess
import threading
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.radio import radio_logging
from quill.core.radio.recording_commands import (
    RECORD_FORMAT_LABELS,
    RECORD_FORMATS,
    build_filename,
    build_probe_codec_command,
    build_record_command,
    format_uses_bitrate,
    parse_probe_codec,
    raw_capture_extension,
    uniquify,
)
from quill.core.speech.ffmpeg import INSTALL_HINT, find_ffmpeg, find_ffprobe
from quill.stability.redaction import format_args_for_log, redact_source_tokens

# Re-exported for back-compat: callers still do `from ...recording import
# build_record_command` / `RECORD_FORMATS` etc. The pure builders now live in
# recording_commands (GATE-11 decomposition).
__all__ = [
    "RECORD_FORMATS",
    "RECORD_FORMAT_LABELS",
    "JobSnapshot",
    "RadioRecorder",
    "RecordingError",
    "RecordingLimitError",
    "RecordingSettings",
    "build_filename",
    "build_probe_codec_command",
    "build_record_command",
    "format_uses_bitrate",
    "load_recording_settings",
    "parse_probe_codec",
    "raw_capture_extension",
    "save_recording_settings",
    "uniquify",
]

logger = logging.getLogger(__name__)

#: A captured ffmpeg stderr line matching this is logged at WARNING (a real
#: problem worth seeing without debug mode); everything else logs at DEBUG.
_STDERR_ERROR_RE = re.compile(
    r"(?i)\b(error|failed|invalid|unable|no such|not found|denied|refused|timed out)\b"
)

#: R4/13.3 -- ffmpeg stderr markers that mean the failure is *fatal* (the stream
#: is gone for good or the disk is full), not a transient drop worth spending a
#: reconnect attempt on. Only genuinely-terminal HTTP codes count: 404 Not Found,
#: 410 Gone, 451 Unavailable. A 5xx, a network timeout, a bare EOF, and crucially
#: a transient 403 Forbidden (an expired/rotating CDN token -- common, and
#: recoverable) or a 408/409 are treated as transient and DO reconnect, so a
#: hiccup no longer cuts a recording short after a minute.
_FATAL_STDERR_RE = re.compile(
    r"(?i)(no space left|disk full|enospc|read-only|"
    r"server returned 4(?:04|10|51)|http error 4(?:04|10|51)|http/[0-9.]+ 4(?:04|10|51)|"
    r"404 not found|410 gone|451 unavailable)"
)

#: Evidence in ffmpeg's stderr that it (re)connected and is making forward
#: progress -- an ``Opening '...' for reading`` reconnect line or a progress stat
#: line. Any earlier error was recovered from, so the recent-stderr tail is
#: cleared on this signal, preventing a transient error ffmpeg already rode out
#: from poisoning the fatal/transient verdict of a later, unrelated drop.
_RECOVERY_STDERR_RE = re.compile(r"(?i)(opening .+ for reading|\btime=\d)")

_PROBE_TIMEOUT_SECONDS = 10.0
_DEFAULT_BITRATE_KBPS = 192
_DEFAULT_MAX_DURATION_MINUTES = 180
_DEFAULT_FILENAME_PATTERN = "{station} - {date} {time}"
_STOP_GRACE_SECONDS = 5.0


class RecordingError(CodedError):
    """A recording could not be started or ffmpeg is unavailable."""

    code = "QUILL-RADIO-RECORDING-FAILED"


class RecordingLimitError(RecordingError):
    """The concurrent-recording cap is already reached (a subclass so callers
    that only care about "could not start" still catch it, while the scheduler
    can tell "cap reached, hold and retry" apart from a hard failure).

    Only raised when ``RecordingSettings.max_concurrent_recordings`` is a
    positive number and that many recordings are already running; with the
    default of ``0`` (unlimited) it never fires.
    """

    code = "QUILL-RADIO-RECORDING-LIMIT"


@dataclass(slots=True)
class RecordingSettings:
    """Rich, global recording defaults (Preferences > Internet Radio > Recording)."""

    format: str = "mp3"  # one of RECORD_FORMATS
    bitrate_kbps: int = _DEFAULT_BITRATE_KBPS  # ignored for flac/wav (lossless)
    destination_root: str = ""  # "" = default (~/Music/Quill Radio Recordings)
    #: Where a recording is *written while in progress* (quill-radio #5). "" =
    #: write straight to destination_root (today's behavior). When set, ffmpeg
    #: writes here and the finished file is moved to destination_root on a clean
    #: stop, so a partial never litters the recordings folder and a scratch/SSD
    #: temp volume can absorb the churn. os.replace on the same volume, else
    #: copy+delete across volumes.
    temp_dir: str = ""
    filename_pattern: str = _DEFAULT_FILENAME_PATTERN  # tokens: {station} {date} {time}
    max_duration_minutes: int = _DEFAULT_MAX_DURATION_MINUTES  # safety cap on every recording
    # Auto-reconnect: when the internet hiccups mid-recording, ffmpeg first
    # rides out short gaps itself (reconnect flags below); if the process
    # still dies, the recorder waits and starts a continuation file, up to
    # this many attempts. All three knobs live in Recording Settings.
    reconnect_enabled: bool = True
    reconnect_max_attempts: int = 5
    reconnect_wait_seconds: int = 10
    #: Off by default -- preserves today's behavior (an unfiltered archival
    #: copy) even for a listener with Sound Enhancements on. When true, a new
    #: recording is filtered through the *current* EQ preset/compressor
    #: (Playback > Sound Enhancements) the same way live playback is, via
    #: build_record_command's filter_graph parameter -- this module itself
    #: stays decoupled from audio_enhance.py; the caller computes the graph.
    apply_sound_enhancements: bool = False
    #: How many recordings may run at the same time (quill-radio concurrent
    #: recording). ``0`` means *unlimited* -- the recorder starts every
    #: recording the user or the scheduler asks for, so five overlapping
    #: scheduled shows all record instead of one winning and the rest being
    #: dropped. A positive number caps concurrency: once that many are running,
    #: a further Record Now is refused with a friendly message and a scheduled
    #: fire is held pending (retried within its window) rather than burned.
    #: The default is unlimited by explicit product choice; a user on a modest
    #: machine or a metered connection can set a ceiling in Recording Settings.
    max_concurrent_recordings: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "format": self.format,
            "bitrate_kbps": self.bitrate_kbps,
            "destination_root": self.destination_root,
            "temp_dir": self.temp_dir,
            "filename_pattern": self.filename_pattern,
            "max_duration_minutes": self.max_duration_minutes,
            "reconnect_enabled": self.reconnect_enabled,
            "reconnect_max_attempts": self.reconnect_max_attempts,
            "reconnect_wait_seconds": self.reconnect_wait_seconds,
            "apply_sound_enhancements": self.apply_sound_enhancements,
            "max_concurrent_recordings": self.max_concurrent_recordings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> RecordingSettings:
        fmt = str(data.get("format", "mp3"))
        return cls(
            format=fmt if fmt in RECORD_FORMATS else "mp3",
            bitrate_kbps=_coerce_int(data.get("bitrate_kbps"), _DEFAULT_BITRATE_KBPS),
            destination_root=str(data.get("destination_root", "")),
            temp_dir=str(data.get("temp_dir", "")),
            filename_pattern=str(data.get("filename_pattern") or _DEFAULT_FILENAME_PATTERN),
            max_duration_minutes=_coerce_int(
                data.get("max_duration_minutes"), _DEFAULT_MAX_DURATION_MINUTES
            ),
            reconnect_enabled=bool(data.get("reconnect_enabled", True)),
            reconnect_max_attempts=max(0, _coerce_int(data.get("reconnect_max_attempts"), 5)),
            reconnect_wait_seconds=max(1, _coerce_int(data.get("reconnect_wait_seconds"), 10)),
            apply_sound_enhancements=bool(data.get("apply_sound_enhancements", False)),
            # 0 (unlimited) is the floor -- a negative saved value coerces to it.
            max_concurrent_recordings=max(
                0, _coerce_int(data.get("max_concurrent_recordings"), 0)
            ),
        )


def _coerce_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value)) if value.strip() else default
        except ValueError:
            return default
    return default


@dataclass(slots=True)
class JobSnapshot:
    """An immutable, lock-free view of one active recording.

    The multi-recording replacement for the recorder's old scalar
    ``current_*`` getters: :meth:`RadioRecorder.active_jobs` returns one of
    these per running recording so the Recordings list, the resume marker, and
    the tray can each see every capture, not just "the" one.
    """

    job_id: str
    station_name: str
    stream_url: str
    destination: Path
    final_destination: Path
    started_at: datetime
    minutes: int
    filter_graph: str
    entry_id: str = ""


@dataclass
class RecordingJob:
    """Everything one in-flight recording owns (concurrent recording).

    One recording == one job. Each job has its own ffmpeg process, its own
    recent-stderr tail (so two recordings can never cross-contaminate each
    other's fatal/transient reconnect verdict), its own reconnect counter and
    user-stopped flag, and its own Windows kill-on-close handle. Jobs live in
    :attr:`RadioRecorder._jobs` keyed by :attr:`job_id`. A reconnect reuses the
    same ``job_id`` (and the original ``started_at``/``scheduled_end``) so the
    Recordings row and the resume marker keep a stable identity across a drop.
    """

    job_id: str
    process: subprocess.Popen[bytes]
    destination: Path
    final_destination: Path
    station_name: str
    stream_url: str
    settings: RecordingSettings
    minutes: int
    filter_graph: str
    extension: str
    started_at: datetime
    scheduled_end: datetime
    entry_id: str = ""
    #: Recent ffmpeg stderr (R4/13.3), inspected on a drop to decide fatal vs
    #: transient. Per-job so a second recording's stderr never poisons this
    #: job's verdict.
    stderr_tail: deque[str] = field(default_factory=lambda: deque(maxlen=32))
    #: Windows kill-on-close job handle (R4/13.5); one per recording.
    win_job: object | None = None
    reconnect_attempt: int = 0
    user_stopped: bool = False

    def snapshot(self) -> JobSnapshot:
        return JobSnapshot(
            job_id=self.job_id,
            station_name=self.station_name,
            stream_url=self.stream_url,
            destination=self.destination,
            final_destination=self.final_destination,
            started_at=self.started_at,
            minutes=self.minutes,
            filter_graph=self.filter_graph,
            entry_id=self.entry_id,
        )


class RadioRecorder:
    """Owns any number of concurrent stream recordings (concurrent recording).

    Previously the recorder held one recording at a time; it now manages a set
    of independent :class:`RecordingJob` objects keyed by id, so overlapping
    scheduled shows and manual captures all record at once instead of one
    winning and the rest being dropped. ``RecordingSettings.
    max_concurrent_recordings`` caps how many may run (``0`` = unlimited, the
    default).

    ``on_state_changed(is_recording, destination, job_id)`` fires on a
    background thread when a recording starts or ends (naturally, via
    :meth:`stop`, or by hitting its duration cap); ``job_id`` identifies which
    recording changed so the caller can persist/clear exactly that one's resume
    marker. Callers that touch wx must marshal back to the UI thread themselves,
    the same contract QUILL's other background workers use.
    """

    def __init__(
        self,
        *,
        on_state_changed: Callable[[bool, Path | None, str], None] | None = None,
        on_reconnect: Callable[[int, int], None] | None = None,
    ) -> None:
        self._on_state_changed = on_state_changed or (lambda _recording, _dest, _job_id: None)
        #: (attempt, max_attempts) -- fired on a background thread each time a
        #: dropped recording is about to be resumed into a continuation file.
        self._on_reconnect = on_reconnect or (lambda _attempt, _maximum: None)
        #: Guards membership of the jobs dict; per-job fields are only mutated
        #: under it (or, for a job's own stderr tail, by that job's single drain
        #: thread, read back under the lock in _monitor).
        self._lock = threading.Lock()
        #: Every recording currently running, keyed by job id.
        self._jobs: dict[str, RecordingJob] = {}

    # -- read API ---------------------------------------------------------------

    def _live_jobs(self) -> list[RecordingJob]:
        """All jobs whose ffmpeg is still running, oldest first (caller holds no
        lock; this takes it)."""
        with self._lock:
            jobs = [j for j in self._jobs.values() if j.process.poll() is None]
        jobs.sort(key=lambda j: j.started_at)
        return jobs

    @property
    def is_recording(self) -> bool:
        """True while any recording is running (back-compat: "anything active")."""
        return bool(self._live_jobs())

    @property
    def active_count(self) -> int:
        """How many recordings are running right now."""
        return len(self._live_jobs())

    def active_jobs(self) -> list[JobSnapshot]:
        """A snapshot of every running recording, oldest first."""
        return [j.snapshot() for j in self._live_jobs()]

    def job(self, job_id: str) -> JobSnapshot | None:
        """A snapshot of one recording by id, or ``None`` if it is not running."""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.snapshot() if job is not None else None

    def _first(self) -> RecordingJob | None:
        jobs = self._live_jobs()
        return jobs[0] if jobs else None

    # Back-compat scalar getters -- report the oldest active recording. New code
    # uses active_jobs()/job(); these keep any remaining single-recording call
    # site (a status line, an old test) working.
    @property
    def current_destination(self) -> Path | None:
        job = self._first()
        return job.destination if job is not None else None

    @property
    def current_station_name(self) -> str:
        job = self._first()
        return job.station_name if job is not None else ""

    @property
    def current_stream_url(self) -> str:
        job = self._first()
        return job.stream_url if job is not None else ""

    @property
    def current_final_destination(self) -> Path | None:
        job = self._first()
        return job.final_destination if job is not None else None

    @property
    def current_minutes(self) -> int:
        job = self._first()
        return job.minutes if job is not None else 0

    @property
    def current_filter_graph(self) -> str:
        job = self._first()
        return job.filter_graph if job is not None else ""

    @property
    def current_started_at(self) -> datetime | None:
        job = self._first()
        return job.started_at if job is not None else None

    def start(
        self,
        *,
        station_name: str,
        stream_url: str,
        settings: RecordingSettings,
        duration_minutes: int | None = None,
        filter_graph: str = "",
        entry_id: str = "",
        _job_id: str = "",
        _continuation_part: int = 0,
        _forced_extension: str = "",
        _started_at: datetime | None = None,
        _scheduled_end: datetime | None = None,
    ) -> Path:
        """Start recording *stream_url* as a new concurrent job; returns where
        ffmpeg is writing. Raises :class:`RecordingError` if ffmpeg is
        unavailable, or :class:`RecordingLimitError` if the concurrency cap
        (``settings.max_concurrent_recordings``, ``0`` = unlimited) is already
        reached. A non-empty ``filter_graph`` records the Sound-Enhancements-
        filtered audio instead of a raw archival copy (see
        ``build_record_command``). Raw-capture mode (``settings.format ==
        "copy"``) ignores the filter and writes a container matching the
        stream's own codec.

        ``entry_id`` links the recording to a schedule entry (for the resume
        marker). The ``_``-prefixed parameters are internal to the reconnect
        path: a continuation reuses the dropped recording's ``_job_id`` and its
        original ``_started_at``/``_scheduled_end`` so identity and the
        remaining-time math survive a drop.
        """
        is_continuation = _continuation_part > 0
        with self._lock:
            # Concurrency cap (0 = unlimited). A continuation replaces a
            # recording that just dropped -- it reuses an existing job_id and so
            # is never counted against the cap.
            cap = max(0, getattr(settings, "max_concurrent_recordings", 0) or 0)
            if not is_continuation and cap:
                running = sum(1 for j in self._jobs.values() if j.process.poll() is None)
                if running >= cap:
                    raise RecordingLimitError(
                        f"The maximum of {cap} simultaneous "
                        f"recording{'s' if cap != 1 else ''} is already running. "
                        "Stop one to start another, or raise the limit in "
                        "Recording Settings."
                    )
            ffmpeg = find_ffmpeg()
            if ffmpeg is None:
                raise RecordingError(f"ffmpeg is not installed. {INSTALL_HINT}")
            dest_root = (
                Path(settings.destination_root) if settings.destination_root else _default_dir()
            )
            dest_root.mkdir(parents=True, exist_ok=True)
            # #5: record into a temp dir when one is set, then move the finished
            # file to dest_root on a clean stop. "" keeps today's behavior
            # (write straight to dest_root). A temp dir we cannot create falls
            # back to dest_root rather than failing the recording.
            record_root = dest_root
            if settings.temp_dir:
                temp_root = Path(settings.temp_dir)
                try:
                    temp_root.mkdir(parents=True, exist_ok=True)
                    record_root = temp_root
                except OSError as exc:
                    logger.warning(
                        "Recording temp dir %s is unusable (%s); recording to the "
                        "destination folder instead.",
                        format_args_for_log([str(temp_root)]),
                        exc,
                    )
            # R4/13.4: a continuation part keeps the *original* start timestamp in
            # its {date}/{time} tokens (so parts 1 and 2 group by name), not a
            # fresh now(). ``now`` is computed once and reused for both the
            # filename token and the job's started_at so they never diverge.
            now = datetime.now()
            when = _started_at if (is_continuation and _started_at is not None) else now
            filename = build_filename(settings.filename_pattern, station=station_name, when=when)
            if _continuation_part > 0:
                filename = f"{filename} (part {_continuation_part + 1})"
            # Raw capture: the file extension follows the server's own codec
            # (probed once, reused across continuations); a filter is impossible
            # without decoding, so it is dropped. Re-encode formats keep their
            # format name as the extension and honor the filter.
            if settings.format == "copy":
                extension = _forced_extension or _probe_capture_extension(stream_url)
                record_filter = ""
            else:
                extension = settings.format
                record_filter = filter_graph
            final_destination = uniquify(dest_root / f"{filename}.{extension}")
            # The temp file (if any) shares the unique name so the post-stop move
            # lands on the same final path; uniquify against the temp dir too.
            destination = (
                uniquify(record_root / f"{filename}.{extension}")
                if record_root != dest_root
                else final_destination
            )
            minutes = (
                duration_minutes if duration_minutes is not None else settings.max_duration_minutes
            )
            args = build_record_command(
                ffmpeg,
                stream_url,
                destination,
                format=settings.format,
                bitrate_kbps=settings.bitrate_kbps,
                duration_seconds=max(60, minutes * 60),
                reconnect_delay_max=(
                    settings.reconnect_wait_seconds if settings.reconnect_enabled else 0
                ),
                filter_graph=record_filter,
                user_agent=http_client.user_agent(),
                loglevel="verbose" if radio_logging.radio_debug_enabled() else "error",
            )
            extra_kwargs: dict = {}
            if os.name == "nt":
                extra_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            logger.info("Starting radio recording: %s", format_args_for_log(args))
            try:
                # stderr is a PIPE (not DEVNULL) so a drain thread can log
                # ffmpeg's own diagnostics (quill-radio #4/#5) -- and so the OS
                # pipe buffer can never fill and stall ffmpeg, the reader always
                # runs. stdout stays discarded (audio goes to the file).
                process = subprocess.Popen(
                    args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    **extra_kwargs,
                )
            except OSError as exc:
                raise RecordingError(f"Could not start ffmpeg: {exc}") from exc
            # R4/13.5: on Windows, put the ffmpeg child in a job object that dies
            # with the host (a crash/kill of QUILL closes the handle and the OS
            # kills the child), so a crashed host can no longer strand a bare
            # ffmpeg writing to the temp dir. Best-effort: a failure degrades to
            # the pre-job behavior, never blocks the recording.
            win_job = _assign_kill_on_close_job(process)
            job_id = _job_id or uuid.uuid4().hex
            started_at = _started_at if (is_continuation and _started_at is not None) else now
            # R4/13.1: the absolute end is preserved across reconnects so a
            # continuation records only the remaining time, not a fresh full
            # duration.
            scheduled_end = (
                _scheduled_end
                if (is_continuation and _scheduled_end is not None)
                else started_at + timedelta(minutes=minutes)
            )
            job = RecordingJob(
                job_id=job_id,
                process=process,
                destination=destination,
                final_destination=final_destination,
                station_name=station_name,
                stream_url=stream_url,
                settings=settings,
                minutes=minutes,
                filter_graph=record_filter,
                extension=extension,
                started_at=started_at,
                scheduled_end=scheduled_end,
                entry_id=entry_id,
                win_job=win_job,
                reconnect_attempt=_continuation_part,
            )
            self._jobs[job_id] = job
        self._on_state_changed(True, destination, job_id)
        threading.Thread(
            target=self._monitor, args=(job,), daemon=True, name="quill-radio-record-monitor"
        ).start()
        threading.Thread(
            target=self._drain_stderr,
            args=(job,),
            daemon=True,
            name="quill-radio-record-stderr",
        ).start()
        return destination

    def _drain_stderr(self, job: RecordingJob) -> None:
        """Log ffmpeg's live stderr for *job* (quill-radio #4/#5).

        Always runs so the OS pipe buffer cannot fill and stall ffmpeg. Each
        line is redacted (a stream URL can carry a token) and logged at DEBUG,
        except lines that look like a real error, which log at WARNING so a
        failing recording leaves a trail without debug mode. In debug mode
        ffmpeg runs at ``-loglevel verbose``, so the whole connection/codec
        story lands in ``quill.log``. The tail is the *job's own* deque, so a
        second recording's stderr never poisons this one's verdict.
        """
        process = job.process
        stream = getattr(process, "stderr", None)
        if stream is None:
            return
        try:
            for raw in iter(stream.readline, b""):
                line = raw.decode("utf-8", "replace").rstrip()
                if not line:
                    continue
                # R4/13.3: keep the recent stderr so _monitor can classify a drop
                # as fatal (disk full / gone-for-good HTTP) vs transient. When
                # ffmpeg shows it reconnected/made progress, clear the tail first
                # so an error it already recovered from cannot poison a later
                # verdict.
                if _RECOVERY_STDERR_RE.search(line):
                    job.stderr_tail.clear()
                job.stderr_tail.append(line)
                safe = redact_source_tokens(line)
                if _STDERR_ERROR_RE.search(line):
                    logger.warning("ffmpeg recording %s: %s", job.station_name, safe)
                else:
                    logger.debug("ffmpeg recording %s: %s", job.station_name, safe)
        except (OSError, ValueError):
            pass
        finally:
            try:
                stream.close()
            except OSError:
                pass

    def _monitor(self, job: RecordingJob) -> None:
        job.process.wait()
        with self._lock:
            # Drop this job from the active set (only if it is still the one
            # registered under its id -- a reconnect that already replaced it
            # inserts a distinct object under the same id).
            if self._jobs.get(job.job_id) is job:
                del self._jobs[job.job_id]
            failed = bool(job.process.returncode) and not job.user_stopped
            # R4/13.3: read the job's own stderr tail under the lock so a fatal
            # failure (disk full / HTTP 4xx) is not retried -- reconnecting a
            # stream the server took down with a 404 would only waste the attempt
            # budget and spam continuation files.
            fatal = failed and any(_FATAL_STDERR_RE.search(line) for line in job.stderr_tail)
            # R4/13.5: close this job's kill-on-close handle now the child has
            # exited (wait() returned), so a long session does not leak a handle
            # per recording.
            win_job = job.win_job
            job.win_job = None
        if win_job is not None:
            _close_job_handle(win_job)
        # Move the finished file from the temp dir to its home (#5). Done for
        # both a clean stop and a failed/partial recording, so a partial is
        # never stranded in temp -- it lands where the user looks for it, then
        # a reconnect (if any) records a fresh continuation.
        landed = job.destination
        if job.destination != job.final_destination:
            landed = _finalize_move(job.destination, job.final_destination)
        if landed is not None:
            # #5 observability: how a recording ended and where it finalized.
            logger.debug(
                "Recording finished (%s) -> %s",
                "dropped/partial" if failed else "stopped/complete",
                format_args_for_log([str(landed)]),
            )
            self._on_state_changed(False, landed, job.job_id)
        if failed and not fatal:
            self._maybe_reconnect(job)

    def _maybe_reconnect(self, job: RecordingJob) -> None:
        """*job* died without being asked to stop: wait, then resume into a
        continuation file (reusing the same job id), up to the attempt budget.

        R4/13.1: a continuation records only the *remaining* time to the
        original scheduled end (``job.scheduled_end``), never a fresh full
        duration -- a 60-minute show that drops at minute 50 records a ~10
        minute continuation, not another 60."""
        settings = job.settings
        if not settings.reconnect_enabled:
            return
        attempt = job.reconnect_attempt + 1
        scheduled_end = job.scheduled_end
        # R4/13.1: remaining minutes to the absolute end, floored at 1 so a
        # reconnect that fires just before the end still records something; a
        # drop discovered after the scheduled end gives up (the show is over).
        if scheduled_end is None:
            remaining = settings.max_duration_minutes
        else:
            remaining = math.ceil((scheduled_end - datetime.now()).total_seconds() / 60)
        if remaining <= 0:
            logger.info(
                "Radio recording of %s dropped past its scheduled end; not reconnecting.",
                job.station_name,
            )
            return
        if attempt > max(0, settings.reconnect_max_attempts):
            logger.warning(
                "Radio recording of %s gave up after %d reconnect attempt(s).",
                job.station_name,
                attempt - 1,
            )
            return
        self._on_reconnect(attempt, settings.reconnect_max_attempts)
        logger.info(
            "Radio recording of %s dropped; reconnect attempt %d/%d in %ds (remaining %d min).",
            job.station_name,
            attempt,
            settings.reconnect_max_attempts,
            settings.reconnect_wait_seconds,
            remaining,
        )
        stop_signal = threading.Event()
        stop_signal.wait(max(1, settings.reconnect_wait_seconds))
        with self._lock:
            existing = self._jobs.get(job.job_id)
            if job.user_stopped or (existing is not None and existing.process.poll() is None):
                return
        try:
            self.start(
                station_name=job.station_name,
                stream_url=job.stream_url,
                settings=settings,
                duration_minutes=remaining,
                filter_graph=job.filter_graph,
                entry_id=job.entry_id,
                _job_id=job.job_id,
                _continuation_part=attempt,
                _forced_extension=job.extension,
                _started_at=job.started_at,
                _scheduled_end=job.scheduled_end,
            )
        except RecordingError as error:
            logger.warning("Reconnect attempt %d could not start: %s", attempt, error)
            job.reconnect_attempt = attempt
            self._maybe_reconnect(job)

    def stop(self, job_id: str | None = None) -> None:
        """Ask a recording to finish cleanly; a no-op if it is not running.

        ``job_id`` names one recording to stop; ``None`` stops *all* of them
        (the close-path/back-compat behavior). R4/13.5: each wait-and-terminate
        fallback runs on its own daemon thread so a slow ffmpeg shutdown never
        blocks the UI thread. The 'q' keypress is sent synchronously -- it is
        just a pipe write -- and the thread only waits and, if needed,
        terminates."""
        with self._lock:
            if job_id is None:
                targets = list(self._jobs.values())
            else:
                one = self._jobs.get(job_id)
                targets = [one] if one is not None else []
            for target in targets:
                target.user_stopped = True
        for target in targets:
            process = target.process
            if process.poll() is not None:
                continue
            try:
                if process.stdin is not None:
                    process.stdin.write(b"q")
                    process.stdin.flush()
            except (OSError, ValueError):
                # Pipe already closed (ffmpeg gone); the thread's wait returns.
                pass
            threading.Thread(
                target=_await_stop,
                args=(process,),
                daemon=True,
                name="quill-radio-record-stop",
            ).start()

    def stop_all(self) -> None:
        """Stop every running recording (the Stop All action / shutdown)."""
        self.stop(None)

    def shutdown(self) -> None:
        """Called once, from the frame's close path: stop every recording."""
        self.stop(None)


def _await_stop(process: subprocess.Popen[bytes]) -> None:
    """Wait for *process* to exit after 'q' was written; terminate it if it
    does not land within the grace period (R4/13.5).

    Runs on a daemon thread so the caller (the UI thread / close path) is
    never blocked by a slow ffmpeg shutdown. The graceful 'q' was already
    sent synchronously by :meth:`RadioRecorder.stop`; this only owns the
    wait-and-terminate fallback."""
    try:
        process.wait(timeout=_STOP_GRACE_SECONDS)
    except Exception:  # noqa: BLE001 - wait timed out or pipe closed
        logger.warning("Graceful stop of radio recording did not land in time; terminating.")
    if process.poll() is None:
        try:
            process.terminate()
        except OSError:
            pass


def _assign_kill_on_close_job(process: subprocess.Popen[bytes]) -> object | None:
    """Put *process* in a Windows job object that kills it when the host dies
    (R4/13.5), so a crashed/killed QUILL can no longer strand a bare ffmpeg
    writing to the temp dir.

    Best-effort: returns the job handle (an int) on success, or ``None``
    off-Windows or if anything goes wrong (job creation, assignment, or the
    kill-on-close flag). A ``None`` return degrades to the pre-job behavior --
    the recording still works, it just is not tied to the host's lifetime."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

        class _IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class _BASIC_LIMITS(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class _EXTENDED_LIMITS(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", _BASIC_LIMITS),
                ("IoInfo", _IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
        JobObjectExtendedLimitInformation = 9
        job: object = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = _EXTENDED_LIMITS()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            job,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            kernel32.CloseHandle(job)
            return None
        # subprocess.Popen keeps the process handle on Windows as _handle (int).
        # AssignProcessToJobObject needs that handle; the child must inherit it
        # (CREATE_NO_WINDOW does not block inheritance of the handle Popen keeps).
        proc_handle = getattr(process, "_handle", None)
        if not proc_handle or not kernel32.AssignProcessToJobObject(job, proc_handle):
            kernel32.CloseHandle(job)
            return None
        return job
    except Exception:  # noqa: BLE001 - best-effort; never break a recording
        logger.debug("Could not bind radio recording to a kill-on-close job.", exc_info=True)
        return None


def _close_job_handle(job: object) -> None:
    """Close a job handle returned by :func:`_assign_kill_on_close_job`.

    Safe to call only after the child has exited (the recorder does so from
    ``_monitor`` once ``process.wait()`` returns), so closing the handle
    cannot kill a still-running recording."""
    if not job:
        return
    try:
        import ctypes

        ctypes.windll.kernel32.CloseHandle(cast("int", job))  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - best-effort cleanup
        pass


def _finalize_move(src: Path, dst: Path) -> Path:
    """Move a finished recording from the temp dir *src* to its home *dst* (#5).

    Returns where the file actually ended up. ``os.replace`` handles the same
    volume in one atomic step; a cross-volume move raises ``OSError``, so it
    falls back to copy-then-delete. If even that fails the file is left in the
    temp dir (still playable) and *src* is returned, so a finished recording is
    never lost to a move error.
    """
    if not src.exists():
        return dst
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(src, dst)
        return dst
    except OSError:
        try:
            shutil.copy2(src, dst)
            src.unlink(missing_ok=True)
            return dst
        except OSError as exc:
            logger.warning(
                "Could not move recording to %s (%s); left it in the temp folder.",
                format_args_for_log([str(dst)]),
                exc,
            )
            return src


def _probe_capture_extension(stream_url: str) -> str:
    """Probe *stream_url*'s audio codec and return the raw-capture extension.

    Best-effort: a missing ffprobe, a probe error, or a timeout all fall back
    to Matroska audio (``.mka``), the universal lossless copy container, so
    raw capture always has a valid destination.
    """
    ffprobe = find_ffprobe()
    if ffprobe is None:
        return raw_capture_extension("")
    extra_kwargs: dict = {}
    if os.name == "nt":
        extra_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        completed = subprocess.run(
            build_probe_codec_command(ffprobe, stream_url, user_agent=http_client.user_agent()),
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_SECONDS,
            check=False,
            **extra_kwargs,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("ffprobe failed for raw-capture probe: %s", exc)
        return raw_capture_extension("")
    codec = parse_probe_codec(completed.stdout)
    if not codec:
        # #5 observability: the probe ran but gave us no codec. ffprobe's own
        # stderr (redacted) says why -- previously captured but never logged, so
        # a "why did my recording become .mka?" question had no answer in the log.
        stderr = format_args_for_log((completed.stderr or "").strip().splitlines()[-3:])
        logger.debug("ffprobe returned no codec (falling back to .mka); stderr: %s", stderr)
    return raw_capture_extension(codec)


def _default_dir(home: Path | None = None) -> Path:
    """The default recordings folder -- a user-visible one (quill-radio #4).

    Recordings used to land in ``app_data_dir()/radio_recordings`` (buried in
    AppData with no way to find them). They now default to
    ``~/Music/Quill Radio Recordings``, falling back to the home folder itself
    when a Music folder does not exist. ``home`` is injectable for tests.
    """
    base = home or Path.home()
    music = base / "Music"
    parent = music if music.is_dir() else base
    return parent / "Quill Radio Recordings"


def _store_path(data_dir: Path) -> Path:
    return data_dir / "radio_recording_settings.json"


def load_recording_settings(data_dir: Path) -> RecordingSettings:
    """Read saved recording settings (an absent or broken file reads as
    defaults)."""
    import json

    path = _store_path(data_dir)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return RecordingSettings()
    if not isinstance(raw, dict):
        return RecordingSettings()
    return RecordingSettings.from_dict(raw)


def save_recording_settings(data_dir: Path, settings: RecordingSettings) -> None:
    """Persist recording settings atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(_store_path(data_dir), settings.to_dict())
