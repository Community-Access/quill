"""ffmpeg-based audio preparation for offline speech (#617 follow-up).

whisper.cpp's command-line tool only reliably reads **16 kHz mono PCM WAV**, so
any other input (mp3, m4a, mp4, flac, ogg, or a stereo / 48 kHz WAV) has to be
converted first. This module locates an ``ffmpeg`` executable — preferring a
QUILL-managed copy, then the system ``PATH`` — and transcodes a source file to a
temporary WAV that whisper.cpp can read.

Design notes:

- **Resolution** mirrors ChapterForge's bundled-first ``_find_tool``: look in
  QUILL-managed tool folders, then fall back to ``PATH``; cache the result. The
  basename must be on a narrow allowlist, so QUILL only ever launches a known
  ``ffmpeg`` / ``ffprobe`` binary.
- **Safety**: runs go through :func:`run_subprocess_safely`, which sets
  ``CREATE_NO_WINDOW`` so no console window flashes (important for screen-reader
  users) and bounds every call with a timeout.
- **Licensing**: ffmpeg is GPL/LGPL. QUILL does **not** bundle or redistribute
  it — it uses an ffmpeg already on the system (or a QUILL-managed copy the user
  installs), the same non-redistributor stance ChapterForge takes. This keeps
  QUILL free of ffmpeg's source-distribution obligations.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from quill.core.speech import models

# (fraction 0.0-1.0, human message) — same shape as the speech ProgressCallback.
ProgressCallback = Callable[[float, str], None]

TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1

# whisper.cpp loads these container/codecs natively only as 16 kHz mono WAV.
_ALLOWED_FFMPEG = frozenset({"ffmpeg", "ffmpeg.exe"})
_ALLOWED_FFPROBE = frozenset({"ffprobe", "ffprobe.exe"})

# How to obtain ffmpeg, surfaced in the "not installed" message (no bundling).
INSTALL_HINT = "Install ffmpeg (for example: winget install Gyan.FFmpeg) and try again."


class TranscodeError(Exception):
    """Raised when audio could not be prepared for transcription."""


def ffmpeg_search_dirs() -> list[Path]:
    """QUILL-managed locations to check for ffmpeg/ffprobe before the PATH.

    1. ``{QUILL_APP_ROOT}/tools/ffmpeg`` — a copy shipped beside a portable build
       or dropped in by the user (mirrors the whisper.cpp engine layout).
    2. ``<data>/tools/ffmpeg`` — a copy a future "Download FFmpeg" action installs.
    """
    dirs: list[Path] = []
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        dirs.append(Path(app_root) / "tools" / "ffmpeg")
    dirs.append(models.app_data_dir() / "tools" / "ffmpeg")
    return dirs


def _resolve_tool(name: str, allowed: frozenset[str]) -> str | None:
    exe = name + (".exe" if os.name == "nt" else "")
    for directory in ffmpeg_search_dirs():
        candidate = directory / exe
        if candidate.is_file() and candidate.name.lower() in allowed:
            return str(candidate)
    found = shutil.which(name)
    if found and Path(found).name.lower() in allowed:
        return found
    return None


@lru_cache(maxsize=1)
def find_ffmpeg() -> str | None:
    """Path to an allowed ffmpeg executable, or None if not installed."""
    return _resolve_tool("ffmpeg", _ALLOWED_FFMPEG)


@lru_cache(maxsize=1)
def find_ffprobe() -> str | None:
    """Path to an allowed ffprobe executable, or None if not installed."""
    return _resolve_tool("ffprobe", _ALLOWED_FFPROBE)


def ffmpeg_available() -> bool:
    """True when QUILL can convert arbitrary audio/video for transcription."""
    return find_ffmpeg() is not None


def resolve_export_format(
    typed_suffix: str, filter_index: int, ordered_exts: Sequence[str]
) -> tuple[str, bool]:
    """Pick the output format for the Generate Speech Audio save dialog (#750).

    ``ordered_exts`` is the list of format ids shown as named filters in order
    (e.g. ``["wav", "mp3", ...]``); the trailing "All files" filter occupies
    index ``len(ordered_exts)``. ``typed_suffix`` is the suffix the user typed
    (``output_path.suffix``), ``filter_index`` is the dialog's selected filter.

    Returns ``(format_id, normalize_suffix)``:

    - A recognized typed extension wins, so ``song.mp3`` typed under "All files"
      still makes an MP3 and the user's name is kept (``normalize_suffix`` False).
    - Otherwise the selected named filter decides and the path suffix should be
      normalized to it (``normalize_suffix`` True).
    - An unknown extension under "All files" falls back to WAV.
    """
    typed = typed_suffix.lower().lstrip(".")
    known = set(ordered_exts)
    if typed in known:
        return typed, False
    if 0 <= filter_index < len(ordered_exts):
        return ordered_exts[filter_index], True
    return "wav", typed != "wav"


def build_probe_duration_command(ffprobe: str, path: Path) -> list[str]:
    """ffprobe argv that prints a media file's duration in seconds (plain number)."""
    return [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]


def probe_duration_ms(path: Path, *, timeout_seconds: float = 60.0) -> int:
    """Return *path*'s audio duration in milliseconds via ffprobe (0 if unknown)."""
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffprobe = find_ffprobe()
    if ffprobe is None or not path.is_file():
        return 0
    try:
        completed = run_subprocess_safely(
            build_probe_duration_command(ffprobe, path), timeout_seconds=timeout_seconds
        )
    except OSError:
        return 0
    try:
        return int(round(float((completed.stdout or "").strip()) * 1000))
    except (TypeError, ValueError):
        return 0


def build_transcode_command(ffmpeg: str, source: Path, out_wav: Path) -> list[str]:
    """Build the ffmpeg argv that converts ``source`` to a 16 kHz mono PCM WAV.

    Pure and unit-tested: the audio path is a controlled, on-disk file (never
    untrusted document content), so this is safe to hand to a subprocess.
    """
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-vn",  # drop any video stream
        "-ac",
        str(TARGET_CHANNELS),
        "-ar",
        str(TARGET_SAMPLE_RATE),
        "-acodec",
        "pcm_s16le",
        "-y",  # overwrite the temp file
        str(out_wav),
    ]


# Listening-quality MP3 defaults (distinct from the 16 kHz mono transcription
# profile above): keep speech intelligible at a small size. libmp3lame VBR
# quality 4 is ~128-165 kbps; the source channels/rate are preserved so a stereo
# voice stays stereo. Used by the batch document-to-speech MP3 path (§4.1).
MP3_VBR_QUALITY = "4"

# Compressed listening formats QUILL can write from a speech WAV. Each maps a
# format id to (ffmpeg codec, default extra encode args, container `-f` muxer or
# ""). m4b is the audiobook container (ipod muxer, AAC) and the natural home for
# chapter markers + metadata; opus/flac/ogg round out the offline options.
ENCODE_FORMATS: dict[str, tuple[str, list[str], str]] = {
    "mp3": ("libmp3lame", [], ""),  # bitrate flag added from vbr_quality below
    "ogg": ("libvorbis", ["-q:a", "4"], ""),
    "opus": ("libopus", ["-b:a", "96k"], ""),
    "flac": ("flac", [], ""),
    "m4a": ("aac", ["-b:a", "160k"], "ipod"),
    "m4b": ("aac", ["-b:a", "96k"], "ipod"),
}


@dataclass(slots=True)
class AudioMetadata:
    """Container/ID3 tags stamped on a compressed output (album, author, …).

    Empty fields are omitted, so a default instance adds no ``-metadata`` flags
    and the encode is byte-identical to an untagged one. Used by the batch
    document-to-speech pipeline to make a folder of audio a real audiobook.
    """

    title: str = ""
    artist: str = ""  # author / narrator
    album: str = ""
    album_artist: str = ""
    genre: str = ""
    year: str = ""
    track: str = ""
    comment: str = ""

    def ffmpeg_args(self) -> list[str]:
        """The ``-metadata key=value`` argv pairs for the non-empty fields."""
        mapping = {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "album_artist": self.album_artist,
            "genre": self.genre,
            "date": self.year,
            "track": self.track,
            "comment": self.comment,
        }
        args: list[str] = []
        for key, value in mapping.items():
            text = str(value).strip()
            if text:
                args.extend(["-metadata", f"{key}={text}"])
        return args


def build_encode_command(
    ffmpeg: str,
    source_wav: Path,
    out_path: Path,
    fmt: str,
    *,
    mp3_vbr_quality: str = MP3_VBR_QUALITY,
    metadata: AudioMetadata | None = None,
) -> list[str]:
    """Build the ffmpeg argv that encodes ``source_wav`` to ``out_path`` as ``fmt``.

    Pure and unit-tested: ``source_wav`` is a controlled, on-disk file produced by
    a synthesis engine (never untrusted document content), so this is safe to hand
    to a subprocess. Channels/rate are preserved (no downmix/resample) — only the
    codec changes. ``fmt`` must be a key of :data:`ENCODE_FORMATS`.
    """
    key = fmt.strip().lower()
    profile = ENCODE_FORMATS.get(key)
    if profile is None:
        raise TranscodeError(f"Unsupported output format: {fmt!r}")
    codec, extra, muxer = profile
    args = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source_wav),
        "-vn",
        "-c:a",
        codec,
    ]
    if key == "mp3":
        args.extend(["-q:a", str(mp3_vbr_quality)])
    args.extend(extra)
    if muxer:
        args.extend(["-f", muxer])
    if metadata is not None:
        args.extend(metadata.ffmpeg_args())
    args.extend(["-y", str(out_path)])
    return args


def build_mp3_command(
    ffmpeg: str,
    source_wav: Path,
    out_mp3: Path,
    *,
    vbr_quality: str = MP3_VBR_QUALITY,
    metadata: AudioMetadata | None = None,
) -> list[str]:
    """Build the ffmpeg argv that encodes ``source_wav`` to a listening-grade MP3.

    Thin wrapper over :func:`build_encode_command` kept for the MP3 call sites and
    their tests. Preserves the speech WAV's channels/rate; only re-encodes to MP3.
    """
    return build_encode_command(
        ffmpeg, source_wav, out_mp3, "mp3", mp3_vbr_quality=vbr_quality, metadata=metadata
    )


def transcode_audio(
    source_wav: Path,
    out_path: Path,
    fmt: str,
    *,
    mp3_vbr_quality: str = MP3_VBR_QUALITY,
    metadata: AudioMetadata | None = None,
    timeout_seconds: float = 600.0,
) -> Path:
    """Encode a speech ``source_wav`` to ``out_path`` in ``fmt`` (mp3/m4b/opus/…).

    Returns ``out_path``. Raises :class:`TranscodeError` if ffmpeg is missing or
    fails — callers in the batch pipeline catch this and fall back to WAV with a
    per-file note, never hard-failing the whole batch (§4.1, Risks table).
    """
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        raise TranscodeError(f"ffmpeg is not installed. {INSTALL_HINT}")
    if not source_wav.is_file():
        raise TranscodeError(f"The audio file was not found: {source_wav}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    args = build_encode_command(
        ffmpeg, source_wav, out_path, fmt, mp3_vbr_quality=mp3_vbr_quality, metadata=metadata
    )
    try:
        completed = run_subprocess_safely(args, timeout_seconds=timeout_seconds)
    except OSError as exc:
        raise TranscodeError(f"Could not run ffmpeg: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip()[:300]
        out_path.unlink(missing_ok=True)
        raise TranscodeError(f"ffmpeg could not encode the audio. {detail}".strip())
    if not out_path.is_file():
        raise TranscodeError("ffmpeg produced no output.")
    return out_path


def _escape_ffmetadata(value: str) -> str:
    """Escape the FFMETADATA special characters (``= ; # \\``) and fold newlines."""
    out = value.replace("\\", "\\\\")
    for char in ("=", ";", "#"):
        out = out.replace(char, "\\" + char)
    return out.replace("\r", " ").replace("\n", " ")


def build_ffmetadata(
    chapters: list[tuple[str, int, int]], metadata: AudioMetadata | None = None
) -> str:
    """Build an ffmpeg FFMETADATA document for native chapter atoms (M4B/MP4).

    Each chapter is ``(title, start_ms, end_ms)``. Fed to ffmpeg as a metadata
    input (``-i meta -map_metadata 1 -map_chapters 1``), this gives an M4B chapters
    an audiobook player navigates natively — the MP4 equivalent of the MP3 ID3
    CHAP/CTOC frames in ``chapters.py``. Global tags (album/author/…) ride along in
    the header so one document carries both. Pure and unit-tested.
    """
    lines = [";FFMETADATA1"]
    if metadata is not None:
        header = {
            "title": metadata.album or metadata.title,
            "album": metadata.album,
            "artist": metadata.artist,
            "album_artist": metadata.album_artist,
            "genre": metadata.genre,
            "date": metadata.year,
            "comment": metadata.comment,
        }
        for key, value in header.items():
            text = str(value).strip()
            if text:
                lines.append(f"{key}={_escape_ffmetadata(text)}")
    for title, start_ms, end_ms in chapters:
        lines.append("[CHAPTER]")
        lines.append("TIMEBASE=1/1000")
        lines.append(f"START={max(0, int(start_ms))}")
        lines.append(f"END={max(0, int(end_ms))}")
        lines.append(f"title={_escape_ffmetadata(str(title))}")
    return "\n".join(lines) + "\n"


def build_m4b_command(ffmpeg: str, source: Path, ffmetadata: Path, out_m4b: Path) -> list[str]:
    """Build the ffmpeg argv that encodes ``source`` to an M4B with native chapters.

    ``ffmetadata`` is the chapter+tag document from :func:`build_ffmetadata`,
    supplied as a second input and mapped in (``-map_metadata 1 -map_chapters 1``).
    Pure and unit-tested.
    """
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-i",
        str(ffmetadata),
        "-map_metadata",
        "1",
        "-map_chapters",
        "1",
        "-vn",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-f",
        "ipod",
        "-y",
        str(out_m4b),
    ]


def encode_m4b_with_chapters(
    source: Path,
    out_m4b: Path,
    chapters: list[tuple[str, int, int]],
    *,
    metadata: AudioMetadata | None = None,
    timeout_seconds: float = 600.0,
) -> Path:
    """Encode ``source`` audio to an M4B audiobook with native chapter atoms.

    Writes the FFMETADATA document to a temp file and runs ffmpeg. Raises
    :class:`TranscodeError` if ffmpeg is missing or fails.
    """
    import tempfile

    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        raise TranscodeError(f"ffmpeg is not installed. {INSTALL_HINT}")
    if not source.is_file():
        raise TranscodeError(f"The audio file was not found: {source}")
    out_m4b.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="quill_m4b_") as tmp:
        meta_path = Path(tmp) / "chapters.ffmeta"
        meta_path.write_text(build_ffmetadata(chapters, metadata), encoding="utf-8")
        args = build_m4b_command(ffmpeg, source, meta_path, out_m4b)
        try:
            completed = run_subprocess_safely(args, timeout_seconds=timeout_seconds)
        except OSError as exc:
            raise TranscodeError(f"Could not run ffmpeg: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip()[:300]
        out_m4b.unlink(missing_ok=True)
        raise TranscodeError(f"ffmpeg could not encode the M4B. {detail}".strip())
    if not out_m4b.is_file():
        raise TranscodeError("ffmpeg produced no output.")
    return out_m4b


def transcode_to_mp3(
    source_wav: Path,
    out_mp3: Path,
    *,
    vbr_quality: str = MP3_VBR_QUALITY,
    metadata: AudioMetadata | None = None,
    timeout_seconds: float = 600.0,
) -> Path:
    """Encode a speech ``source_wav`` to ``out_mp3`` (listening-grade MP3)."""
    return transcode_audio(
        source_wav,
        out_mp3,
        "mp3",
        mp3_vbr_quality=vbr_quality,
        metadata=metadata,
        timeout_seconds=timeout_seconds,
    )


def build_wav_conform_command(
    ffmpeg: str,
    source: Path,
    out_wav: Path,
    *,
    sample_rate: int | None = None,
    channels: int | None = None,
) -> list[str]:
    """Build the ffmpeg argv that re-samples/down-mixes ``source`` to PCM WAV.

    Only the requested attributes are forced; ``None`` leaves that attribute as
    the engine produced it. Used to give a batch a uniform WAV sample rate /
    channel count when the user asks for one.
    """
    args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(source), "-vn"]
    if channels is not None:
        args.extend(["-ac", str(int(channels))])
    if sample_rate is not None:
        args.extend(["-ar", str(int(sample_rate))])
    args.extend(["-c:a", "pcm_s16le", "-y", str(out_wav)])
    return args


def conform_wav(
    source: Path,
    out_wav: Path,
    *,
    sample_rate: int | None = None,
    channels: int | None = None,
    timeout_seconds: float = 600.0,
) -> Path:
    """Re-sample/down-mix ``source`` to ``out_wav`` (PCM s16le). Returns ``out_wav``."""
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        raise TranscodeError(f"ffmpeg is not installed. {INSTALL_HINT}")
    if not source.is_file():
        raise TranscodeError(f"The audio file was not found: {source}")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    args = build_wav_conform_command(
        ffmpeg, source, out_wav, sample_rate=sample_rate, channels=channels
    )
    try:
        completed = run_subprocess_safely(args, timeout_seconds=timeout_seconds)
    except OSError as exc:
        raise TranscodeError(f"Could not run ffmpeg: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip()[:300]
        out_wav.unlink(missing_ok=True)
        raise TranscodeError(f"ffmpeg could not conform the audio. {detail}".strip())
    if not out_wav.is_file():
        raise TranscodeError("ffmpeg produced no output.")
    return out_wav


def transcode_to_wav(
    source: Path,
    *,
    out_dir: Path | None = None,
    progress: ProgressCallback | None = None,
    timeout_seconds: float = 600.0,
) -> Path:
    """Convert ``source`` to a 16 kHz mono WAV whisper.cpp can read.

    Returns the path to the new WAV. When ``out_dir`` is given the file is written
    there (so the caller's temp dir handles cleanup); otherwise a temp file is
    created. Raises :class:`TranscodeError` if ffmpeg is missing or fails.
    """
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        raise TranscodeError(f"ffmpeg is not installed. {INSTALL_HINT}")
    if not source.is_file():
        raise TranscodeError(f"The audio file was not found: {source}")

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_wav = out_dir / f"{source.stem}.transcode.wav"
    else:
        import tempfile

        fd, raw = tempfile.mkstemp(prefix="quill_transcode_", suffix=".wav")
        os.close(fd)
        out_wav = Path(raw)

    if progress is not None:
        progress(0.0, "Preparing audio...")
    args = build_transcode_command(ffmpeg, source, out_wav)
    try:
        completed = run_subprocess_safely(args, timeout_seconds=timeout_seconds)
    except OSError as exc:
        raise TranscodeError(f"Could not run ffmpeg: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip()[:300]
        out_wav.unlink(missing_ok=True)
        raise TranscodeError(f"ffmpeg could not convert the audio. {detail}".strip())
    if not out_wav.is_file():
        raise TranscodeError("ffmpeg produced no output.")
    if progress is not None:
        progress(0.05, "Audio ready.")
    return out_wav
