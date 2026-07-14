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

from quill.core.error_codes import CodedError
from quill.core.speech.ffmpeg import INSTALL_HINT, find_ffmpeg
from quill.stability.redaction import format_args_for_log

logger = logging.getLogger(__name__)

#: Formats a live stream can be recorded to. All are streamable containers
#: (no trailing index atom like MP4/M4A), so even an unclean stop leaves a
#: playable file up to the last flushed frame.
RECORD_FORMATS = ("mp3", "ogg", "flac", "wav")
_CODECS = {"mp3": "libmp3lame", "ogg": "libvorbis", "flac": "flac", "wav": "pcm_s16le"}
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

    def to_dict(self) -> dict[str, object]:
        return {
            "format": self.format,
            "bitrate_kbps": self.bitrate_kbps,
            "destination_root": self.destination_root,
            "filename_pattern": self.filename_pattern,
            "max_duration_minutes": self.max_duration_minutes,
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
) -> list[str]:
    """Build the ffmpeg argv that records *stream_url* to *out_path*.

    Pure and unit-tested. ``-t`` caps every recording at ``duration_seconds``
    even if :meth:`RadioRecorder.stop` is never called, so a forgotten
    recording cannot grow unbounded.
    """
    codec = _CODECS.get(format, "libmp3lame")
    args = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        stream_url,
        "-vn",
        "-c:a",
        codec,
    ]
    if format in ("mp3", "ogg"):
        args.extend(["-b:a", f"{max(32, bitrate_kbps)}k"])
    args.extend(["-t", str(max(1, duration_seconds)), "-y", str(out_path)])
    return args


class RadioRecorder:
    """Owns at most one active stream recording at a time.

    ``on_state_changed(is_recording, destination)`` fires on a background
    thread when a recording starts or ends (naturally, via :meth:`stop`, or
    by hitting its duration cap) -- callers that touch wx must marshal back
    to the UI thread themselves, the same contract QUILL's other background
    workers use.
    """

    def __init__(
        self, *, on_state_changed: Callable[[bool, Path | None], None] | None = None
    ) -> None:
        self._on_state_changed = on_state_changed or (lambda _recording, _dest: None)
        self._lock = threading.Lock()
        self._process: subprocess.Popen[bytes] | None = None
        self._destination: Path | None = None
        self._station_name: str = ""

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
    ) -> Path:
        """Start recording *stream_url*; raises :class:`RecordingError` if
        ffmpeg is unavailable or a recording is already in progress."""
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
            destination = dest_root / f"{filename}.{settings.format}"
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
                self._process = None
                self._destination = None
                self._station_name = ""
            else:
                dest = None
        if dest is not None:
            self._on_state_changed(False, dest)

    def stop(self) -> None:
        """Ask the current recording to finish cleanly; a no-op if idle."""
        with self._lock:
            process = self._process
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


def _default_dir() -> Path:
    from quill.core.paths import app_data_dir

    return app_data_dir() / "radio_recordings"


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
