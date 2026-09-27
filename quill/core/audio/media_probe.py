"""What is inside a media file, read by ffprobe and said in plain words.

Quill Converter's File Properties (Alt+Enter), the chapter list that Split by
Chapters works from, and the durations Join uses for its chapter marks all
come from one ffprobe call parsed here. The parse is pure -- it takes the JSON
text -- so it is tested without ffprobe; only :func:`probe` runs anything.

Wording follows the family's rule for spoken summaries: the thing a person
asks first comes first (how long, what kind), numbers carry their units, and
nothing is abbreviated that a speech synthesizer would spell out.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Chapter:
    """One chapter mark: a title and where it starts and stops, in seconds."""

    title: str
    start_s: float
    end_s: float


@dataclass(frozen=True, slots=True)
class StreamInfo:
    """One track in the file."""

    kind: str  # "audio" | "video" | "subtitle" | "cover"
    codec: str
    language: str = ""
    title: str = ""
    sample_rate: int = 0
    channels: int = 0
    channel_layout: str = ""
    width: int = 0
    height: int = 0
    frame_rate: float = 0.0
    bit_rate: int = 0


@dataclass(frozen=True, slots=True)
class MediaInfo:
    """Everything File Properties says about one file."""

    path: Path
    container: str = ""
    duration_s: float = 0.0
    size_bytes: int = 0
    bit_rate: int = 0
    tags: dict[str, str] = field(default_factory=dict)
    streams: tuple[StreamInfo, ...] = ()
    chapters: tuple[Chapter, ...] = ()

    @property
    def audio(self) -> tuple[StreamInfo, ...]:
        return tuple(s for s in self.streams if s.kind == "audio")

    @property
    def video(self) -> tuple[StreamInfo, ...]:
        return tuple(s for s in self.streams if s.kind == "video")


def build_probe_command(ffprobe: str, path: Path) -> list[str]:
    """The ffprobe argv that describes *path* as JSON (pure)."""
    return [
        ffprobe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        "-show_chapters",
        str(path),
    ]


def _f(value: object) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def _i(value: object) -> int:
    return int(_f(value))


def _rate(text: object) -> float:
    """``"30000/1001"`` -> 29.97."""
    raw = str(text or "")
    if "/" in raw:
        top, _, bottom = raw.partition("/")
        try:
            den = float(bottom)
            return float(top) / den if den else 0.0
        except ValueError:
            return 0.0
    return _f(raw)


def parse_probe_json(path: Path, text: str) -> MediaInfo:
    """Parse ffprobe's JSON for *path* into a :class:`MediaInfo` (pure)."""
    try:
        data = json.loads(text or "{}")
    except json.JSONDecodeError:
        data = {}
    fmt = data.get("format") or {}
    streams: list[StreamInfo] = []
    for raw in data.get("streams") or []:
        codec_type = str(raw.get("codec_type", ""))
        disposition = raw.get("disposition") or {}
        kind = codec_type
        if codec_type == "video" and disposition.get("attached_pic"):
            kind = "cover"
        if kind not in ("audio", "video", "subtitle", "cover"):
            continue
        tags = raw.get("tags") or {}
        streams.append(
            StreamInfo(
                kind=kind,
                codec=str(raw.get("codec_long_name") or raw.get("codec_name") or "unknown"),
                language=str(tags.get("language", "")),
                title=str(tags.get("title", "")),
                sample_rate=_i(raw.get("sample_rate")),
                channels=_i(raw.get("channels")),
                channel_layout=str(raw.get("channel_layout", "")),
                width=_i(raw.get("width")),
                height=_i(raw.get("height")),
                frame_rate=_rate(raw.get("avg_frame_rate")),
                bit_rate=_i(raw.get("bit_rate")),
            )
        )
    chapters = []
    for index, raw in enumerate(data.get("chapters") or [], start=1):
        tags = raw.get("tags") or {}
        chapters.append(
            Chapter(
                title=str(tags.get("title") or f"Chapter {index}"),
                start_s=_f(raw.get("start_time")),
                end_s=_f(raw.get("end_time")),
            )
        )
    tags = {str(k).lower(): str(v) for k, v in (fmt.get("tags") or {}).items()}
    # Ogg, Opus and Speex keep their tags on the audio stream, not the file.
    for raw in data.get("streams") or []:
        if raw.get("codec_type") == "audio":
            for key, value in (raw.get("tags") or {}).items():
                tags.setdefault(str(key).lower(), str(value))
            break
    return MediaInfo(
        path=path,
        container=str(fmt.get("format_long_name") or fmt.get("format_name") or ""),
        duration_s=_f(fmt.get("duration")),
        size_bytes=_i(fmt.get("size")),
        bit_rate=_i(fmt.get("bit_rate")),
        tags=tags,
        streams=tuple(streams),
        chapters=tuple(chapters),
    )


def probe(path: Path, *, ffprobe: str | None = None, timeout_seconds: float = 60.0) -> MediaInfo:
    """Run ffprobe on *path*. A file ffprobe cannot read yields an empty MediaInfo."""
    from quill.core.speech.ffmpeg import find_ffprobe
    from quill.stability.safe_subprocess import run_subprocess_safely

    tool = ffprobe or find_ffprobe()
    if not tool:
        return MediaInfo(path=path)
    try:
        completed = run_subprocess_safely(
            build_probe_command(tool, path), timeout_seconds=timeout_seconds
        )
    except Exception:  # noqa: BLE001 - an unreadable file is described as empty
        return MediaInfo(path=path)
    return parse_probe_json(path, str(getattr(completed, "stdout", "") or ""))


def format_duration(seconds: float) -> str:
    """``3725.4`` -> ``"1 hour 2 minutes 5 seconds"`` (spoken, never "1:02:05")."""
    total = int(round(max(0.0, seconds)))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    parts = []
    for value, unit in ((hours, "hour"), (minutes, "minute"), (secs, "second")):
        if value:
            parts.append(f"{value} {unit}{'' if value == 1 else 's'}")
    return " ".join(parts) or "0 seconds"


def format_size(size_bytes: int) -> str:
    """Bytes in the largest unit that keeps the number readable."""
    size = float(max(0, size_bytes))
    for unit in ("bytes", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "bytes" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _channels_words(stream: StreamInfo) -> str:
    named = {1: "mono", 2: "stereo", 6: "5.1 surround", 8: "7.1 surround"}
    return named.get(stream.channels, f"{stream.channels} channels")


def describe(info: MediaInfo) -> list[str]:
    """File Properties, one fact per line, most-asked first."""
    lines = [f"File: {info.path.name}"]
    if not info.streams and not info.duration_s:
        lines.append("This file could not be read. It may be damaged, or not a media file.")
        return lines
    lines.append(f"Length: {format_duration(info.duration_s)}")
    lines.append(f"Size: {format_size(info.size_bytes)}")
    if info.container:
        lines.append(f"Container: {info.container}")
    if info.bit_rate:
        lines.append(f"Overall bit rate: {info.bit_rate // 1000} kilobits per second")
    for key in ("title", "artist", "album", "album_artist", "date", "genre", "track"):
        if info.tags.get(key):
            lines.append(f"{key.replace('_', ' ').capitalize()}: {info.tags[key]}")
    for number, stream in enumerate(info.video, start=1):
        fps = f", {stream.frame_rate:.3g} frames per second" if stream.frame_rate else ""
        lines.append(f"Video {number}: {stream.codec}, {stream.width} by {stream.height}{fps}")
    for number, stream in enumerate(info.audio, start=1):
        rate = f", {stream.sample_rate / 1000:g} kHz" if stream.sample_rate else ""
        bits = f", {stream.bit_rate // 1000} kbps" if stream.bit_rate else ""
        extra = "".join(f", {x}" for x in (stream.language, stream.title) if x)
        lines.append(
            f"Audio {number}: {stream.codec}, {_channels_words(stream)}{rate}{bits}{extra}"
        )
    subs = [s for s in info.streams if s.kind == "subtitle"]
    if subs:
        langs = ", ".join(s.language for s in subs if s.language)
        lines.append(f"Subtitle tracks: {len(subs)}" + (f" ({langs})" if langs else ""))
    if any(s.kind == "cover" for s in info.streams):
        lines.append("Cover art: yes")
    if info.chapters:
        lines.append(f"Chapters: {len(info.chapters)}")
        for chapter in info.chapters:
            lines.append(f"  {chapter.title}, at {format_duration(chapter.start_s)}")
    return lines
