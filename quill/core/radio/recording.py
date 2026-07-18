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
import os
import re
import shutil
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.radio import radio_logging
from quill.core.radio.recording_commands import (
    RECORD_FORMAT_LABELS,
    RECORD_FORMATS,
    build_filename,
    build_probe_codec_command,
    build_record_command,
    parse_probe_codec,
    raw_capture_extension,
)
from quill.core.speech.ffmpeg import INSTALL_HINT, find_ffmpeg, find_ffprobe
from quill.stability.redaction import format_args_for_log, redact_source_tokens

# Re-exported for back-compat: callers still do `from ...recording import
# build_record_command` / `RECORD_FORMATS` etc. The pure builders now live in
# recording_commands (GATE-11 decomposition).
__all__ = [
    "RECORD_FORMATS",
    "RECORD_FORMAT_LABELS",
    "RadioRecorder",
    "RecordingError",
    "RecordingSettings",
    "build_filename",
    "build_probe_codec_command",
    "build_record_command",
    "load_recording_settings",
    "parse_probe_codec",
    "raw_capture_extension",
    "save_recording_settings",
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


class RadioRecorder:
    """Owns at most one active stream recording at a time.

    ``on_state_changed(is_recording, destination)`` fires on a background
    thread when a recording starts or ends (naturally, via :meth:`stop`, or
    by hitting its duration cap) -- callers that touch wx must marshal back
    to the UI thread themselves, the same contract QUILL's other background
    workers use.
    """

    def __init__(
        self,
        *,
        on_state_changed: Callable[[bool, Path | None], None] | None = None,
        on_reconnect: Callable[[int, int], None] | None = None,
    ) -> None:
        self._on_state_changed = on_state_changed or (lambda _recording, _dest: None)
        #: (attempt, max_attempts) -- fired on a background thread each time a
        #: dropped recording is about to be resumed into a continuation file.
        self._on_reconnect = on_reconnect or (lambda _attempt, _maximum: None)
        self._lock = threading.Lock()
        self._process: subprocess.Popen[bytes] | None = None
        #: Where ffmpeg is writing right now (may be the temp dir, #5).
        self._destination: Path | None = None
        #: Where the finished file belongs once this recording ends; differs
        #: from _destination only when settings.temp_dir is set (#5).
        self._final_destination: Path | None = None
        self._station_name: str = ""
        self._user_stopped = False
        self._reconnect_attempt = 0
        #: (station_name, stream_url, settings, duration_minutes, filter_graph,
        #: resolved_extension) of the active recording, kept so a reconnect can
        #: restart with the same shape -- including any Sound Enhancements filter
        #: and, for raw-capture mode, the extension resolved on the first probe
        #: so a continuation file never re-probes or changes container.
        self._active_params: tuple[str, str, RecordingSettings, int, str, str] | None = None

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    @property
    def current_destination(self) -> Path | None:
        with self._lock:
            return self._destination

    @property
    def current_station_name(self) -> str:
        with self._lock:
            return self._station_name

    def start(
        self,
        *,
        station_name: str,
        stream_url: str,
        settings: RecordingSettings,
        duration_minutes: int | None = None,
        filter_graph: str = "",
        _continuation_part: int = 0,
        _forced_extension: str = "",
    ) -> Path:
        """Start recording *stream_url*; raises :class:`RecordingError` if
        ffmpeg is unavailable or a recording is already in progress. A
        non-empty ``filter_graph`` records the Sound-Enhancements-filtered
        audio instead of a raw archival copy (see ``build_record_command``).
        Raw-capture mode (``settings.format == "copy"``) ignores the filter and
        writes a container matching the stream's own codec."""
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                raise RecordingError("A recording is already in progress.")
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
            filename = build_filename(
                settings.filename_pattern, station=station_name, when=datetime.now()
            )
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
            final_destination = dest_root / f"{filename}.{extension}"
            destination = record_root / f"{filename}.{extension}"
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
            self._process = process
            self._destination = destination
            self._final_destination = final_destination
            self._station_name = station_name
            self._user_stopped = False
            if _continuation_part == 0:
                self._reconnect_attempt = 0
            self._active_params = (
                station_name,
                stream_url,
                settings,
                minutes,
                record_filter,
                extension,
            )
        self._on_state_changed(True, destination)
        threading.Thread(
            target=self._monitor, args=(process,), daemon=True, name="quill-radio-record-monitor"
        ).start()
        threading.Thread(
            target=self._drain_stderr,
            args=(process, station_name),
            daemon=True,
            name="quill-radio-record-stderr",
        ).start()
        return destination

    def _drain_stderr(self, process: subprocess.Popen[bytes], station_name: str) -> None:
        """Log ffmpeg's live stderr for *process* (quill-radio #4/#5).

        Always runs so the OS pipe buffer cannot fill and stall ffmpeg. Each
        line is redacted (a stream URL can carry a token) and logged at DEBUG,
        except lines that look like a real error, which log at WARNING so a
        failing recording leaves a trail without debug mode. In debug mode
        ffmpeg runs at ``-loglevel verbose``, so the whole connection/codec
        story lands in ``quill.log``.
        """
        stream = getattr(process, "stderr", None)
        if stream is None:
            return
        try:
            for raw in iter(stream.readline, b""):
                line = raw.decode("utf-8", "replace").rstrip()
                if not line:
                    continue
                safe = redact_source_tokens(line)
                if _STDERR_ERROR_RE.search(line):
                    logger.warning("ffmpeg recording %s: %s", station_name, safe)
                else:
                    logger.debug("ffmpeg recording %s: %s", station_name, safe)
        except (OSError, ValueError):
            pass
        finally:
            try:
                stream.close()
            except OSError:
                pass

    def _monitor(self, process: subprocess.Popen[bytes]) -> None:
        process.wait()
        with self._lock:
            if self._process is process:
                dest = self._destination
                final = self._final_destination
                params = self._active_params
                failed = bool(process.returncode) and not self._user_stopped
                self._process = None
                self._destination = None
                self._final_destination = None
                self._station_name = ""
            else:
                dest, final, params, failed = None, None, None, False
        # Move the finished file from the temp dir to its home (#5). Done for
        # both a clean stop and a failed/partial recording, so a partial is
        # never stranded in temp -- it lands where the user looks for it, then
        # a reconnect (if any) records a fresh continuation.
        landed = dest
        if dest is not None and final is not None and dest != final:
            landed = _finalize_move(dest, final)
        if landed is not None:
            # #5 observability: how a recording ended and where it finalized.
            logger.debug(
                "Recording finished (%s) -> %s",
                "dropped/partial" if failed else "stopped/complete",
                format_args_for_log([str(landed)]),
            )
            self._on_state_changed(False, landed)
        if failed and params is not None:
            self._maybe_reconnect(params)

    def _maybe_reconnect(self, params: tuple[str, str, RecordingSettings, int, str, str]) -> None:
        """A recording died without being asked to stop: wait, then resume
        into a continuation file, up to the configured attempt budget."""
        station_name, stream_url, settings, minutes, filter_graph, extension = params
        if not settings.reconnect_enabled:
            return
        with self._lock:
            self._reconnect_attempt += 1
            attempt = self._reconnect_attempt
        if attempt > max(0, settings.reconnect_max_attempts):
            logger.warning(
                "Radio recording of %s gave up after %d reconnect attempt(s).",
                station_name,
                attempt - 1,
            )
            return
        self._on_reconnect(attempt, settings.reconnect_max_attempts)
        logger.info(
            "Radio recording of %s dropped; reconnect attempt %d/%d in %ds.",
            station_name,
            attempt,
            settings.reconnect_max_attempts,
            settings.reconnect_wait_seconds,
        )
        stop_signal = threading.Event()
        stop_signal.wait(max(1, settings.reconnect_wait_seconds))
        with self._lock:
            if self._user_stopped or (self._process is not None and self._process.poll() is None):
                return
        try:
            self.start(
                station_name=station_name,
                stream_url=stream_url,
                settings=settings,
                duration_minutes=minutes,
                filter_graph=filter_graph,
                _continuation_part=attempt,
                _forced_extension=extension,
            )
        except RecordingError as error:
            logger.warning("Reconnect attempt %d could not start: %s", attempt, error)
            self._maybe_reconnect(params)

    def stop(self) -> None:
        """Ask the current recording to finish cleanly; a no-op if idle."""
        with self._lock:
            process = self._process
            self._user_stopped = True
        if process is None or process.poll() is not None:
            return
        try:
            if process.stdin is not None:
                process.stdin.write(b"q")
                process.stdin.flush()
            process.wait(timeout=_STOP_GRACE_SECONDS)
        except Exception:  # noqa: BLE001 - fall through to a hard stop below
            logger.warning("Graceful stop of radio recording did not land in time; terminating.")
        if process.poll() is None:
            process.terminate()

    def shutdown(self) -> None:
        """Called once, from the frame's close path."""
        self.stop()


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
