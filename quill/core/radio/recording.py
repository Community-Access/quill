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

from quill.core import http_client
from quill.core.audio.exact_optilab import ExactOptilab
from quill.core.error_codes import CodedError
from quill.core.radio import radio_logging, recording_outcome
from quill.core.radio.local_clock import local_now
from quill.core.radio.recording_commands import (
    RECORD_FORMAT_LABELS,
    RECORD_FORMATS,
    build_filename,
    build_probe_codec_command,
    build_record_command,
    encode_args_for_format,
    format_uses_bitrate,
    parse_probe_codec,
    probe_capture_extension,
    raw_capture_extension,
    uniquify,
)
from quill.core.radio.recording_join import describe_join, join_recording_parts
from quill.core.radio.recording_liveness import wait_for_exit
from quill.core.radio.recording_winjob import assign_kill_on_close_job, close_job_handle
from quill.core.speech.ffmpeg import INSTALL_HINT, find_ffmpeg
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
    #: Off by default. When true *and* the optional OptiLab component is present
    #: in this build, a finished recording gets one more pass through the **real**
    #: OptiLab Core engine (quill/native/optilab), instead of the ffmpeg chain's
    #: adaptation of it. Saved files only -- live listening is untouched, and is
    #: meant to be: see quill/core/audio/exact_optilab.py. The caller supplies the
    #: mode/input/adapt (RadioRecorder.start's ``exact_optilab``) and is
    #: responsible for leaving the OptiLab *filters* out of the recording's own
    #: graph so the audio is never processed twice.
    exact_optilab: bool = False
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
            "exact_optilab": self.exact_optilab,
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
            exact_optilab=bool(data.get("exact_optilab", False)),
            # 0 (unlimited) is the floor -- a negative saved value coerces to it.
            max_concurrent_recordings=max(0, _coerce_int(data.get("max_concurrent_recordings"), 0)),
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
    #: The exact-OptiLab pass to run over the finished file, or None (the
    #: default) for "leave it as recorded". Carried on the job, not read from
    #: settings at the end, so a recording is post-processed the way it was
    #: started even if the listener changes their settings while it runs.
    exact: ExactOptilab | None = None
    #: Recent ffmpeg stderr (R4/13.3), inspected on a drop to decide fatal vs
    #: transient. Per-job so a second recording's stderr never poisons this
    #: job's verdict.
    stderr_tail: deque[str] = field(default_factory=lambda: deque(maxlen=32))
    #: Guards ``stderr_tail`` -- the drain thread appends/clears it while
    #: _monitor snapshots it, so both sides take this to avoid a "deque mutated
    #: during iteration" RuntimeError. (self._lock does not cover it: the drain
    #: thread never holds self._lock.)
    stderr_lock: threading.Lock = field(default_factory=threading.Lock)
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
        on_parts_joined: Callable[[str], None] | None = None,
        on_exact_processed: Callable[[str], None] | None = None,
        on_capture_failed: Callable[[str, str], None] | None = None,
    ) -> None:
        self._on_state_changed = on_state_changed or (lambda _recording, _dest, _job_id: None)
        #: (attempt, max_attempts) -- fired on a background thread each time a
        #: dropped recording is about to be resumed into a continuation file.
        self._on_reconnect = on_reconnect or (lambda _attempt, _maximum: None)
        #: One ready-to-speak sentence, fired on a background thread once a
        #: recording that dropped and resumed has finished and its parts have
        #: been joined -- or honestly reported as still separate.
        self._on_parts_joined = on_parts_joined or (lambda _note: None)
        #: One ready-to-speak sentence, fired on a background thread when a
        #: finished recording has been through the real OptiLab engine -- or when
        #: that pass was asked for and could not be done. Never silent either
        #: way: a listener who turned exact processing on is entitled to know
        #: whether the file they kept actually got it.
        self._on_exact_processed = on_exact_processed or (lambda _note: None)
        #: ``(station name, reason)`` -- fired on a background thread when a
        #: recording ended having captured nothing. Separate from
        #: ``on_state_changed`` because the two say opposite things: one reports
        #: a file that exists, and this reports that there is no file.
        self._on_capture_failed = on_capture_failed or (lambda _station, _reason: None)
        #: Guards membership of the jobs dict; per-job fields are only mutated
        #: under it (or, for a job's own stderr tail, by that job's single drain
        #: thread, read back under the lock in _monitor).
        self._lock = threading.Lock()
        #: Every recording currently running, keyed by job id.
        self._jobs: dict[str, RecordingJob] = {}
        #: Jobs whose ffmpeg has exited and that are waiting out the reconnect
        #: delay before a continuation starts, keyed by job id. They are no
        #: longer in ``_jobs`` (their process is dead) but stop()/stop_all()/
        #: shutdown() must still be able to cancel them -- otherwise a Stop during
        #: the reconnect wait is a no-op and a continuation starts anyway.
        self._reconnect_pending: dict[str, RecordingJob] = {}
        #: Output paths reserved by jobs that are still starting (before ffmpeg
        #: has created the file on disk). uniquify() consults this so two
        #: concurrent same-name recordings never resolve to the same path in the
        #: window before either file exists.
        self._reserved: set[Path] = set()
        #: Every file one recording has produced, keyed by job id: the base
        #: recording plus any continuation parts a reconnect wrote. Appended as
        #: each part finishes and consumed once, at finalize, to join them back
        #: into a single recording (recording_join).
        self._parts: dict[str, list[Path]] = {}

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
        exact_optilab: ExactOptilab | None = None,
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
        marker). ``exact_optilab`` asks for one pass of the **real** OptiLab
        engine over the finished file (see :mod:`quill.core.audio.exact_optilab`);
        it is ignored for raw capture, and the caller must have left the OptiLab
        filters out of ``filter_graph`` so the audio is not processed twice. The
        ``_``-prefixed parameters are internal to the reconnect
        path: a continuation reuses the dropped recording's ``_job_id`` and its
        original ``_started_at``/``_scheduled_end`` so identity and the
        remaining-time math survive a drop.
        """
        is_continuation = _continuation_part > 0
        # Concurrency cap (0 = unlimited). A continuation replaces a recording
        # that just dropped -- it reuses an existing job_id and so is never
        # counted against the cap.
        cap = max(0, getattr(settings, "max_concurrent_recordings", 0) or 0)
        cap_message = (
            f"The maximum of {cap} simultaneous "
            f"recording{'s' if cap != 1 else ''} is already running. "
            "Stop one to start another, or raise the limit in Recording Settings."
        )

        def _at_cap() -> bool:
            # Caller holds self._lock.
            return sum(1 for j in self._jobs.values() if j.process.poll() is None) >= cap

        # Cheap pre-check so we don't do ~10s of ffprobe/spawn work only to refuse
        # (the authoritative re-check happens under the lock at insert time). The
        # heavy work below runs WITHOUT self._lock so the read API (and thus the
        # UI, which polls it) never blocks on a slow probe or a spawning ffmpeg.
        if not is_continuation and cap:
            with self._lock:
                over_cap = _at_cap()
            if over_cap:
                raise RecordingLimitError(cap_message)
        ffmpeg = find_ffmpeg()
        if ffmpeg is None:
            raise RecordingError(f"ffmpeg is not installed. {INSTALL_HINT}")
        # #1268: a YouTube link is a web page, and its playable media URL expires
        # within hours -- so it is resolved here, at the moment of capture, rather
        # than stored. That is what lets a scheduled recording of a YouTube
        # broadcast still work days after it was scheduled. The job keeps the
        # durable page URL (identity, reconnects, the resume marker); only ffmpeg
        # sees the short-lived one. A non-YouTube URL passes straight through.
        capture_url = _resolve_capture_url(stream_url)
        dest_root = Path(settings.destination_root) if settings.destination_root else _default_dir()
        try:
            dest_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            # Keep the documented RecordingError contract: a raw OSError here
            # (e.g. permission denied on the recordings folder) would abort the
            # scheduler's due-entry loop instead of being handled as a failed fire.
            raise RecordingError(
                f"Could not create the recordings folder {dest_root}: {exc}"
            ) from exc
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
        # #1223: OS-live local time so the filename reflects the computer's
        # *current* timezone, not the one cached when Quill launched.
        now = local_now()
        when = _started_at if (is_continuation and _started_at is not None) else now
        filename = build_filename(settings.filename_pattern, station=station_name, when=when)
        if _continuation_part > 0:
            filename = f"{filename} (part {_continuation_part + 1})"
        # Raw capture: the file extension follows the server's own codec
        # (probed once, reused across continuations); a filter is impossible
        # without decoding, so it is dropped. Re-encode formats keep their
        # format name as the extension and honor the filter.
        if settings.format == "copy":
            extension = _forced_extension or probe_capture_extension(capture_url)
            record_filter = ""
        else:
            extension = settings.format
            record_filter = filter_graph
        # Reserve the output name(s) under the lock, consulting both the disk and
        # other still-starting jobs, so two same-name recordings never collide in
        # the window before either file exists. Reservations are released in
        # _monitor when the job ends (or below if this start fails).
        reserved_here: list[Path] = []
        with self._lock:
            final_destination = uniquify(dest_root / f"{filename}.{extension}", self._reserved)
            self._reserved.add(final_destination)
            reserved_here.append(final_destination)
            if record_root != dest_root:
                # The temp file shares a unique name so the post-stop move lands
                # on the same final path; reserve against the temp dir too.
                destination = uniquify(record_root / f"{filename}.{extension}", self._reserved)
                self._reserved.add(destination)
                reserved_here.append(destination)
            else:
                destination = final_destination
        minutes = (
            duration_minutes if duration_minutes is not None else settings.max_duration_minutes
        )
        args = build_record_command(
            ffmpeg,
            capture_url,
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
            self._release_reserved(reserved_here)
            raise RecordingError(f"Could not start ffmpeg: {exc}") from exc
        # R4/13.5: on Windows, put the ffmpeg child in a job object that dies
        # with the host (a crash/kill of QUILL closes the handle and the OS
        # kills the child), so a crashed host can no longer strand a bare
        # ffmpeg writing to the temp dir. Best-effort: a failure degrades to
        # the pre-job behavior, never blocks the recording.
        win_job = assign_kill_on_close_job(process)
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
            # Raw capture is never decoded, so it can never be post-processed
            # without ceasing to be a raw capture. Dropped here rather than in
            # the caller so every entry point gets the same answer.
            exact=exact_optilab if settings.format != "copy" else None,
        )
        # Authoritative cap re-check + registration under the lock. If another
        # start won the last slot while we were spawning, kill the process we just
        # started and refuse, so the cap is never exceeded.
        with self._lock:
            if not is_continuation and cap and _at_cap():
                lost_race = True
            else:
                self._jobs[job_id] = job
                lost_race = False
        if lost_race:
            try:
                process.terminate()
            except OSError:
                pass
            if win_job is not None:
                close_job_handle(win_job)
            self._release_reserved(reserved_here)
            raise RecordingLimitError(cap_message)
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

    def _release_reserved(self, paths: list[Path]) -> None:
        """Drop reserved output names (a start that failed, or a finished job)."""
        with self._lock:
            for path in paths:
                self._reserved.discard(path)

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
                with job.stderr_lock:
                    if recording_outcome.is_recovery(line):
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
        # Second liveness signal, alongside ffmpeg's -rw_timeout and the
        # process-exit watch this call replaces: if the output file stops
        # growing for a sustained run of checks, the stream has stalled even
        # though ffmpeg is still alive. wait_for_exit then stops it, so the
        # ordinary drop handling below (reconnect, or finalize the partial)
        # runs exactly as it does for a stream that dropped outright.
        wait_for_exit(
            job.process,
            job.destination,
            is_stopped=lambda: job.user_stopped,
            label=job.station_name,
        )
        with self._lock:
            # Drop this job from the active set (only if it is still the one
            # registered under its id -- a reconnect that already replaced it
            # inserts a distinct object under the same id).
            if self._jobs.get(job.job_id) is job:
                del self._jobs[job.job_id]
            # Release this job's reserved output names; the file now exists on
            # disk (or the recording failed), so the reservation is no longer
            # needed to keep a concurrent start from picking the same name.
            self._reserved.discard(job.destination)
            self._reserved.discard(job.final_destination)
            failed = bool(job.process.returncode) and not job.user_stopped
            # R4/13.3: classify a drop as fatal (disk full / HTTP 4xx) so it is
            # not retried -- reconnecting a stream the server took down with a 404
            # would only waste the attempt budget and spam continuation files. The
            # tail is snapshotted under the job's own stderr_lock because the drain
            # thread may still be appending to it (the child's stderr can outlive
            # process.wait()); iterating it directly races into a RuntimeError.
            with job.stderr_lock:
                tail_snapshot = list(job.stderr_tail)
            fatal = failed and recording_outcome.is_fatal(tail_snapshot)
            # R4/13.5: close this job's kill-on-close handle now the child has
            # exited (wait() returned), so a long session does not leak a handle
            # per recording.
            win_job = job.win_job
            job.win_job = None
        if win_job is not None:
            close_job_handle(win_job)
        # Move the finished file from the temp dir to its home (#5). Done for
        # both a clean stop and a failed/partial recording, so a partial is
        # never stranded in temp -- it lands where the user looks for it, then
        # a reconnect (if any) records a fresh continuation.
        landed = job.destination
        if job.destination != job.final_destination:
            landed = _finalize_move(job.destination, job.final_destination)
        # _finalize_move always returns a Path (dst or the temp src on a move
        # failure), so `landed` is never None here.
        # #5 observability: how a recording ended and where it finalized.
        logger.debug(
            "Recording finished (%s) -> %s",
            "dropped/partial" if failed else "stopped/complete",
            format_args_for_log([str(landed)]),
        )
        # A recording that captured nothing is a failure, and must be reported
        # as one. Announcing "Recording saved" over a zero-byte file -- or one
        # that was never created -- is worse than silence, because it sends
        # somebody looking in a folder for audio that does not exist.
        if not job.user_stopped and recording_outcome.captured_nothing(landed):
            reason = recording_outcome.empty_capture_reason(tail_snapshot)
            recording_outcome.discard_empty_capture(landed)
            logger.info(
                "Recording captured nothing (%s): %s",
                job.station_name,
                reason,
            )
            self._on_state_changed(False, None, job.job_id)
            self._on_capture_failed(job.station_name, reason)
            with self._lock:
                self._parts.pop(job.job_id, None)
            return
        self._on_state_changed(False, landed, job.job_id)
        with self._lock:
            self._parts.setdefault(job.job_id, []).append(landed)
        # Finalize is "no further continuation will start" -- so it is decided
        # by the reconnect attempt, not guessed at beforehand. Only then are the
        # parts of a dropped-and-resumed recording stitched back together.
        resumed = self._maybe_reconnect(job) if (failed and not fatal) else False
        if not resumed:
            final = self._join_parts(job)
            if final is not None:
                self._apply_exact_optilab(job, final)

    def _apply_exact_optilab(self, job: RecordingJob, path: Path) -> None:
        """Run the real OptiLab engine over the finished recording, if asked.

        Runs *after* the recording is over and after any parts are joined, never
        during the capture: an adapter fault mid-recording must not be able to
        cost somebody the recording they were making. The pass writes a temp file
        and replaces the original only on success, so the worst case here is a
        file that is exactly what was recorded, plus a spoken explanation.
        """
        spec = job.exact
        if spec is None or not spec.active:
            return
        from quill.core.audio import exact_optilab

        if not exact_optilab.available():
            self._on_exact_processed(
                f"{path.name} was saved without exact OptiLab processing. "
                f"{exact_optilab.unavailable_reason()}"
            )
            return
        encode_args = encode_args_for_format(job.settings.format, job.settings.bitrate_kbps)
        if not encode_args:
            return  # raw capture; nothing to re-encode into
        try:
            exact_optilab.process_in_place(path, spec, encode_args=encode_args)
        except Exception as exc:  # noqa: BLE001 - the recording itself is safe either way
            logger.warning("Exact OptiLab processing of %s failed: %s", path.name, exc)
            self._on_exact_processed(
                f"{path.name} was saved, but exact OptiLab processing could not be applied: {exc}"
            )
            return
        logger.info("Exact OptiLab processing applied to %s", format_args_for_log([str(path)]))
        self._on_exact_processed(f"{path.name} was processed with the OptiLab engine.")

    def _join_parts(self, job: RecordingJob) -> Path | None:
        """Stitch a dropped-and-resumed recording's parts into one file.

        Runs once per recording, from the monitor thread of its final part. A
        recording that never dropped has a single part and is a no-op. A join
        that cannot be done, or fails, leaves every part exactly where it is --
        a failed join must never cost the user their recording -- and either
        outcome is announced honestly.

        Returns where the recording now is (the joined file, or the first
        surviving part), or ``None`` when there was nothing to join -- so the
        exact-OptiLab pass that follows always processes the whole show rather
        than part one of it.
        """
        with self._lock:
            parts = self._parts.pop(job.job_id, [])
        if len(parts) < 2:
            return parts[0] if parts else None
        outcome = join_recording_parts(parts)
        note = describe_join(outcome)
        if note:
            self._on_parts_joined(note)
        # A join that did not happen leaves several files. Returning None then is
        # deliberate: processing part one of a show that is still in pieces would
        # produce a set of files where some had the exact engine applied and some
        # did not, which is worse than applying it to none of them.
        return outcome.path if outcome.joined else None

    def _maybe_reconnect(self, job: RecordingJob) -> bool:
        """*job* died without being asked to stop: wait, then resume into a
        continuation file (reusing the same job id), up to the attempt budget.

        R4/13.1: a continuation records only the *remaining* time to the
        original scheduled end (``job.scheduled_end``), never a fresh full
        duration -- a 60-minute show that drops at minute 50 records a ~10
        minute continuation, not another 60.

        Returns whether a continuation actually started. ``False`` means this
        recording is over, which is the recorder's cue to finalize -- and so to
        join whatever parts it produced."""
        settings = job.settings
        if not settings.reconnect_enabled:
            return False
        attempt = job.reconnect_attempt + 1
        scheduled_end = job.scheduled_end
        # R4/13.1: remaining minutes to the absolute end, floored at 1 so a
        # reconnect that fires just before the end still records something; a
        # drop discovered after the scheduled end gives up (the show is over).
        if scheduled_end is None:
            remaining = settings.max_duration_minutes
        else:
            # Same clock basis as started_at/scheduled_end (local_now),
            # so the remaining-minutes math stays consistent across a zone change.
            remaining = math.ceil((scheduled_end - local_now()).total_seconds() / 60)
        if remaining <= 0:
            logger.info(
                "Radio recording of %s dropped past its scheduled end; not reconnecting.",
                job.station_name,
            )
            return False
        if attempt > max(0, settings.reconnect_max_attempts):
            logger.warning(
                "Radio recording of %s gave up after %d reconnect attempt(s).",
                job.station_name,
                attempt - 1,
            )
            return False
        self._on_reconnect(attempt, settings.reconnect_max_attempts)
        logger.info(
            "Radio recording of %s dropped; reconnect attempt %d/%d in %ds (remaining %d min).",
            job.station_name,
            attempt,
            settings.reconnect_max_attempts,
            settings.reconnect_wait_seconds,
            remaining,
        )
        # Register as reconnect-pending *before* the wait so a Stop/Stop All/
        # shutdown during the delay can cancel it: the job is no longer in
        # self._jobs (its process died), so without this stop() could not set
        # user_stopped and a continuation would start anyway.
        with self._lock:
            if job.user_stopped:
                return False
            self._reconnect_pending[job.job_id] = job
        stop_signal = threading.Event()
        stop_signal.wait(max(1, settings.reconnect_wait_seconds))
        with self._lock:
            self._reconnect_pending.pop(job.job_id, None)
            existing = self._jobs.get(job.job_id)
            if job.user_stopped:
                return False
            if existing is not None and existing.process.poll() is None:
                # Another path already resumed this recording; that continuation
                # owns the finalize (and so the join), not this one.
                return True
        # Recompute the remaining time *after* the wait: the value computed
        # before the sleep is stale by up to reconnect_wait_seconds, so using it
        # would overshoot the scheduled end. Give up if the show ended meanwhile.
        if scheduled_end is not None:
            remaining = math.ceil((scheduled_end - local_now()).total_seconds() / 60)
            if remaining <= 0:
                logger.info(
                    "Radio recording of %s dropped past its scheduled end during the "
                    "reconnect wait; not reconnecting.",
                    job.station_name,
                )
                return False
        try:
            self.start(
                station_name=job.station_name,
                stream_url=job.stream_url,
                settings=settings,
                duration_minutes=remaining,
                filter_graph=job.filter_graph,
                entry_id=job.entry_id,
                exact_optilab=job.exact,
                _job_id=job.job_id,
                _continuation_part=attempt,
                _forced_extension=job.extension,
                _started_at=job.started_at,
                _scheduled_end=job.scheduled_end,
            )
        except RecordingError as error:
            logger.warning("Reconnect attempt %d could not start: %s", attempt, error)
            job.reconnect_attempt = attempt
            return self._maybe_reconnect(job)
        return True

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
                pending = list(self._reconnect_pending.values())
            else:
                one = self._jobs.get(job_id)
                targets = [one] if one is not None else []
                waiting = self._reconnect_pending.get(job_id)
                pending = [waiting] if waiting is not None else []
            # Mark both the live recordings and any job waiting out a reconnect
            # delay: the latter has no live process to signal, but user_stopped
            # makes _maybe_reconnect abandon its continuation after the wait.
            for target in (*targets, *pending):
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


def _resolve_capture_url(stream_url: str) -> str:
    """The URL ffmpeg should capture: a YouTube page resolved to its stream (#1268).

    Every other station URL is already playable and passes through untouched, so
    this costs nothing for ordinary radio. A YouTube link is resolved through
    yt-dlp here rather than at schedule time because its media URL expires within
    hours -- a recording scheduled on Monday for Friday would otherwise capture
    nothing. A resolve failure raises :class:`RecordingError` with the reason
    (Safe Mode, yt-dlp missing, private/removed/not-live video) instead of
    handing ffmpeg an HTML page to record.
    """
    from quill.core.radio.youtube import YouTubeError, is_youtube_url, resolve_youtube_stream

    if not is_youtube_url(stream_url):
        return stream_url
    try:
        return resolve_youtube_stream(stream_url).stream_url
    except YouTubeError as exc:
        raise RecordingError(str(exc)) from exc


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
