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
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.speech.ffmpeg import INSTALL_HINT, find_ffmpeg, find_ffprobe
from quill.stability.redaction import format_args_for_log

logger = logging.getLogger(__name__)

#: Formats a live stream can be recorded to. The first four re-encode the
#: decoded audio to a chosen codec. ``"copy"`` is the raw-capture mode
#: (feature request): ffmpeg stream-copies the server's audio packets with no
#: re-encoding, so the saved file is bit-for-bit the original stream -- the
#: most lossless capture possible, for a listener who wants to edit/convert it
#: themselves. All are streamable containers (no trailing index atom like
#: MP4/M4A), so even an unclean stop leaves a playable file up to the last
#: flushed frame.
RECORD_FORMATS = ("mp3", "ogg", "flac", "wav", "copy")
#: Human labels for the Recording Settings format dropdown.
RECORD_FORMAT_LABELS: dict[str, str] = {
    "mp3": "MP3",
    "ogg": "OGG Vorbis",
    "flac": "FLAC (lossless, re-encoded)",
    "wav": "WAV (lossless, re-encoded)",
    "copy": "Raw stream -- exactly as sent, no re-encoding (lossless)",
}
_CODECS = {"mp3": "libmp3lame", "ogg": "libvorbis", "flac": "flac", "wav": "pcm_s16le"}

#: The raw-capture container extension for a probed source codec. Common codecs
#: get their natural elementary-stream extension so the file opens anywhere;
#: anything else falls back to Matroska audio (``.mka``), which stream-copies
#: any codec losslessly into one file the user can extract from later.
_RAW_EXT_BY_CODEC: dict[str, str] = {
    "mp3": "mp3",
    "aac": "aac",
    "aac_latm": "aac",
    "vorbis": "ogg",
    "opus": "opus",
    "flac": "flac",
    "alac": "m4a",
    "ac3": "ac3",
    "wav": "wav",
    "pcm_s16le": "wav",
}
#: Universal lossless fallback container for stream-copy of an unknown codec.
_RAW_FALLBACK_EXT = "mka"
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
    destination_root: str = ""  # "" = default (<data_dir>/radio_recordings)
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


def _sanitize_filename_component(text: str) -> str:
    """Strip characters that are invalid in a filename on any of QUILL's
    supported platforms, collapsing whitespace runs to one space."""
    cleaned = re.sub(r'[\\/:*?"<>|]+', "", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def build_filename(pattern: str, *, station: str, when: datetime) -> str:
    """Fill in ``{station}``/``{date}``/``{time}`` tokens, then sanitize the
    result for use as a filename (without extension)."""
    filled = (
        pattern
        .replace("{station}", station)
        .replace("{date}", when.strftime("%Y-%m-%d"))
        .replace("{time}", when.strftime("%H-%M-%S"))
    )
    sanitized = _sanitize_filename_component(filled)
    return sanitized or "recording"


def build_record_command(
    ffmpeg: str,
    stream_url: str,
    out_path: Path,
    *,
    format: str,
    bitrate_kbps: int,
    duration_seconds: int,
    reconnect_delay_max: int = 0,
    filter_graph: str = "",
    user_agent: str = "",
) -> list[str]:
    """Build the ffmpeg argv that records *stream_url* to *out_path*.

    Pure and unit-tested. ``-t`` caps every recording at ``duration_seconds``
    even if :meth:`RadioRecorder.stop` is never called, so a forgotten
    recording cannot grow unbounded. A positive ``reconnect_delay_max`` turns
    on ffmpeg's own HTTP reconnect handling (first line of defense against a
    dropped connection; the recorder's process-level retry is the second),
    valid only for http(s) inputs. A non-empty ``filter_graph`` (built by
    ``core.audio_enhance.build_filter_graph``, this module stays decoupled
    from that one) records the *filtered* audio -- Sound Enhancements applied
    to the archival copy, not just live playback.

    ``format="copy"`` is the raw-capture mode: ffmpeg stream-copies the
    server's audio packets (``-c:a copy``) with no decode/re-encode, so the
    file is bit-for-bit the original. A bitrate and a filter graph are
    meaningless with no re-encode and are ignored (Sound Enhancements cannot
    apply to a raw copy). The output container is chosen by ``out_path``'s
    extension, which the caller resolves from the stream's own codec.
    """
    args = [ffmpeg, "-hide_banner", "-loglevel", "error"]
    is_http = stream_url.lower().startswith(("http://", "https://"))
    if user_agent and is_http:
        # Identify as Quill Radio in the station's listener logs instead of the
        # default "Lavf" (quill-radio #6). Input option, so it goes before -i.
        args.extend(["-user_agent", user_agent])
    if reconnect_delay_max > 0 and stream_url.lower().startswith(("http://", "https://")):
        args.extend([
            "-reconnect",
            "1",
            "-reconnect_streamed",
            "1",
            "-reconnect_delay_max",
            str(reconnect_delay_max),
        ])
    args.extend(["-i", stream_url, "-vn"])
    if format == "copy":
        # Raw capture: copy packets verbatim -- no filter (nothing is decoded),
        # no bitrate (no re-encode).
        args.extend(["-c:a", "copy"])
    else:
        if filter_graph:
            args.extend(["-af", filter_graph])
        args.extend(["-c:a", _CODECS.get(format, "libmp3lame")])
        if format in ("mp3", "ogg"):
            args.extend(["-b:a", f"{max(32, bitrate_kbps)}k"])
    args.extend(["-t", str(max(1, duration_seconds)), "-y", str(out_path)])
    return args


def build_probe_codec_command(ffprobe: str, stream_url: str, *, user_agent: str = "") -> list[str]:
    """ffprobe argv that prints the first audio stream's codec name (pure).

    Raw-capture mode uses this to pick a natural output extension for the
    server's actual codec; a probe failure just falls back to Matroska. A
    non-empty ``user_agent`` identifies the probe as Quill Radio on http(s)
    inputs (quill-radio #6).
    """
    args = [ffprobe]
    if user_agent and stream_url.lower().startswith(("http://", "https://")):
        args.extend(["-user_agent", user_agent])
    args.extend([
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name",
        "-of",
        "default=nokey=1:noprint_wrappers=1",
        stream_url,
    ])
    return args


def parse_probe_codec(output: str) -> str:
    """The codec name from ``build_probe_codec_command`` output (pure)."""
    for line in output.splitlines():
        name = line.strip()
        if name:
            return name.lower()
    return ""


def raw_capture_extension(codec: str) -> str:
    """The lossless container extension for a raw stream-copy of *codec* (pure).

    Common codecs get their natural extension; anything else falls back to
    Matroska audio (``.mka``), which stream-copies any codec losslessly.
    """
    return _RAW_EXT_BY_CODEC.get(codec.strip().lower(), _RAW_FALLBACK_EXT)


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
        self._destination: Path | None = None
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
            destination = dest_root / f"{filename}.{extension}"
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
            )
            extra_kwargs: dict = {}
            if os.name == "nt":
                extra_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            logger.info("Starting radio recording: %s", format_args_for_log(args))
            try:
                process = subprocess.Popen(
                    args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    **extra_kwargs,
                )
            except OSError as exc:
                raise RecordingError(f"Could not start ffmpeg: {exc}") from exc
            self._process = process
            self._destination = destination
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
        return destination

    def _monitor(self, process: subprocess.Popen[bytes]) -> None:
        process.wait()
        with self._lock:
            if self._process is process:
                dest = self._destination
                params = self._active_params
                failed = bool(process.returncode) and not self._user_stopped
                self._process = None
                self._destination = None
                self._station_name = ""
            else:
                dest, params, failed = None, None, False
        if dest is not None:
            self._on_state_changed(False, dest)
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


def _probe_capture_extension(stream_url: str) -> str:
    """Probe *stream_url*'s audio codec and return the raw-capture extension.

    Best-effort: a missing ffprobe, a probe error, or a timeout all fall back
    to Matroska audio (``.mka``), the universal lossless copy container, so
    raw capture always has a valid destination.
    """
    ffprobe = find_ffprobe()
    if ffprobe is None:
        return _RAW_FALLBACK_EXT
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
    except (OSError, subprocess.SubprocessError):
        return _RAW_FALLBACK_EXT
    return raw_capture_extension(parse_probe_codec(completed.stdout))


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
