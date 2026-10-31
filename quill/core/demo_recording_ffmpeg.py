"""FFmpeg command lines for Record a Demonstration (REC-003 to REC-009).

Pure argument builders, so every flag is unit-tested without a screen, a
camera or FFmpeg. The platform layer runs them through the safe-subprocess
wrapper with an argument list, never a shell.

Capture writes Matroska segments (a crash leaves a playable file up to the
last cluster) with a constant frame rate and a keyframe every two seconds.
Finishing a segment mixes the enabled sound sources at their levels and
measured offsets, overlays the camera picture when there is one, and writes
an MP4 part; the parts are then joined without re-encoding.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from quill.core.demo_recording import DemoPlan, output_size

CAPTURE_PRESET = "superfast"
FINAL_PRESET = "veryfast"
CRF = "23"
AUDIO_BITRATE = "192k"
SAMPLE_RATE = 48_000
#: Frames the camera check and face alerts look at: small and grey is plenty.
FACE_FRAME_SIZE = (320, 240)
FACE_FPS = 2


@dataclass(frozen=True)
class Capabilities:
    encoders: frozenset[str] = frozenset()
    filters: frozenset[str] = frozenset()
    devices: frozenset[str] = frozenset()

    @property
    def h264_encoder(self) -> str:
        for name in ("libx264", "h264_mf"):
            if name in self.encoders:
                return name
        return ""

    @property
    def video_backend(self) -> str:
        if "ddagrab" in self.filters:
            return "ddagrab"
        return "gdigrab" if "gdigrab" in self.devices else ""

    @property
    def can_record(self) -> bool:
        return bool(self.h264_encoder and self.video_backend and "aac" in self.encoders)


_LISTING = re.compile(r"^\s*[A-Z.|]{2,7}\s+(\S+)\s", re.MULTILINE)


def parse_listing(text: str) -> frozenset[str]:
    """Names from ``ffmpeg -encoders``, ``-filters`` or ``-devices`` output."""
    names = set()
    for line in text.splitlines():
        if "=" in line or line.strip().startswith("--"):
            continue
        match = _LISTING.match(line)
        if match:
            names.add(match.group(1))
    return frozenset(names)


_DSHOW_DEVICE = re.compile(r'"([^"]+)"\s+\((video|audio|none)\)')


def parse_dshow_devices(text: str) -> list[tuple[str, str]]:
    """``(name, kind)`` from ``ffmpeg -list_devices true -f dshow -i dummy``."""
    found: list[tuple[str, str]] = []
    for match in _DSHOW_DEVICE.finditer(text):
        entry = (match.group(1), match.group(2))
        if entry not in found:
            found.append(entry)
    return found


def _video_filters(plan: DemoPlan, *, hw_download: bool) -> str:
    width, height = output_size(plan)
    chain = []
    if hw_download:
        chain += ["hwdownload", "format=bgra"]
    if plan.size_ceiling and plan.height > plan.size_ceiling:
        chain.append(f"scale={width}:{height}:flags=bicubic")
    # H.264 4:2:0 needs even dimensions: pad an odd edge by one pixel.
    chain.append("pad=ceil(iw/2)*2:ceil(ih/2)*2")
    chain.append("format=yuv420p")
    return ",".join(chain)


def _encode_args(plan: DemoPlan, encoder: str, *, preset: str) -> list[str]:
    if encoder == "libx264":
        codec = ["-c:v", "libx264", "-preset", preset, "-tune", "zerolatency", "-crf", CRF]
    else:
        codec = ["-c:v", encoder, "-b:v", "8M"]
    return [*codec, "-g", str(plan.fps * 2), "-fps_mode", "cfr", "-r", str(plan.fps)]


def _screen_input(plan: DemoPlan, backend: str) -> tuple[list[str], str]:
    """Input arguments for *backend* and the picture filter chain after it."""
    left, top, right, bottom = plan.bounds
    width, height = right - left, bottom - top
    command: list[str] = []
    if backend == "ddagrab":
        d_left, d_top = plan.display_bounds[0], plan.display_bounds[1]
        options = [
            f"output_idx={plan.display_index}",
            f"framerate={plan.fps}",
            f"draw_mouse={1 if plan.pointer else 0}",
        ]
        if plan.target_kind == "window":
            options += [
                f"offset_x={left - d_left}",
                f"offset_y={top - d_top}",
                f"video_size={width}x{height}",
            ]
        command += ["-f", "lavfi", "-i", "ddagrab=" + ":".join(options)]
        filters = _video_filters(plan, hw_download=True)
    elif backend == "gdigrab":
        command += [
            "-f",
            "gdigrab",
            "-framerate",
            str(plan.fps),
            "-draw_mouse",
            "1" if plan.pointer else "0",
            "-offset_x",
            str(left),
            "-offset_y",
            str(top),
            "-video_size",
            f"{width}x{height}",
            "-i",
            "desktop",
        ]
        filters = _video_filters(plan, hw_download=False)
    else:
        raise ValueError(f"Unknown video backend: {backend!r}")
    return command, filters


def screen_capture_command(
    ffmpeg: str, plan: DemoPlan, output: Path, *, backend: str, encoder: str
) -> list[str]:
    """One segment of screen video, stopped by sending ``q`` on standard input."""
    inputs, filters = _screen_input(plan, backend)
    return [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-loglevel",
        "info",
        "-stats_period",
        "0.5",
        *inputs,
        "-vf",
        filters,
        *_encode_args(plan, encoder, preset=CAPTURE_PRESET),
        "-an",
        "-f",
        "matroska",
        str(output),
    ]


def trial_grab_command(ffmpeg: str, plan: DemoPlan, output: Path, *, backend: str) -> list[str]:
    """One PNG frame through the same backend, for the spoken check."""
    inputs, filters = _screen_input(plan, backend)
    filters = filters.replace(",format=yuv420p", ",format=rgb24")
    return [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-loglevel",
        "error",
        *inputs,
        "-frames:v",
        "1",
        "-vf",
        filters,
        "-update",
        "1",
        str(output),
    ]


def camera_capture_command(
    ffmpeg: str,
    device: str,
    output: Path,
    *,
    fps: int,
    encoder: str,
    face_frames: bool,
) -> list[str]:
    """The camera to its own segment file; optionally small grey frames to stdout.

    One process owns the camera, so face alerts during a recording read the
    same frames FFmpeg is recording instead of opening the device twice.
    """
    command = [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-loglevel",
        "info",
        "-stats_period",
        "0.5",
        "-f",
        "dshow",
        "-rtbufsize",
        "256M",
        "-i",
        f"video={device}",
        "-map",
        "0:v",
        "-vf",
        "pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p",
    ]
    if encoder == "libx264":
        command += ["-c:v", "libx264", "-preset", CAPTURE_PRESET, "-tune", "zerolatency"]
        command += ["-crf", CRF]
    else:
        command += ["-c:v", encoder, "-b:v", "4M"]
    command += ["-fps_mode", "cfr", "-r", str(fps), "-an", "-f", "matroska", str(output)]
    if face_frames:
        command += face_frame_output()
    return command


def face_frame_output() -> list[str]:
    width, height = FACE_FRAME_SIZE
    return [
        "-map",
        "0:v",
        "-vf",
        f"fps={FACE_FPS},scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=gray",
        "-f",
        "rawvideo",
        "pipe:1",
    ]


def camera_preview_command(ffmpeg: str, device: str) -> list[str]:
    """The camera check: only the small grey frames, nothing written to disk."""
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "dshow",
        "-i",
        f"video={device}",
        *face_frame_output(),
    ]


def list_cameras_command(ffmpeg: str) -> list[str]:
    return [ffmpeg, "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]


@dataclass(frozen=True)
class AudioInput:
    path: Path
    level_db: float
    #: Seconds after the video's first frame this source's first sample was
    #: captured. Positive: the sound started late; negative: early.
    offset: float


def _audio_chain(index: int, source: AudioInput) -> str:
    steps = []
    if source.offset > 0.0005:
        steps.append(f"adelay={int(round(source.offset * 1000))}:all=1")
    elif source.offset < -0.0005:
        steps.append(f"atrim=start={-source.offset:.3f}")
        steps.append("asetpts=PTS-STARTPTS")
    steps.append(f"aresample={SAMPLE_RATE}")
    steps.append("aformat=channel_layouts=stereo")
    steps.append(f"volume={source.level_db:.1f}dB")
    return f"[{index}:a]" + ",".join(steps) + f"[a{index}]"


def _overlay_xy(position: str) -> str:
    margin = 16
    return {
        "bottom right": f"x=W-w-{margin}:y=H-h-{margin}",
        "bottom left": f"x={margin}:y=H-h-{margin}",
        "top right": f"x=W-w-{margin}:y={margin}",
        "top left": f"x={margin}:y={margin}",
    }.get(position, f"x=W-w-{margin}:y=H-h-{margin}")


def finish_segment_command(
    ffmpeg: str,
    plan: DemoPlan,
    video: Path,
    output: Path,
    *,
    sources: Sequence[AudioInput],
    camera: Path | None,
    camera_offset: float,
    duration: float,
    encoder: str,
) -> list[str]:
    """One segment's picture, camera and mixed sound as an MP4 part.

    *video* is the screen segment, or the camera segment when the camera
    fills the picture (then *camera* is ``None``). The sum of the sources
    goes through a limiter so it cannot clip; with no source the soundtrack
    is generated silence, unless the plan asks for no soundtrack at all.
    """
    command = [ffmpeg, "-hide_banner", "-y", "-loglevel", "error", "-i", str(video)]
    filters: list[str] = []
    next_index = 1
    video_label = "0:v"
    if camera is not None:
        command += ["-i", str(camera)]
        cam = next_index
        next_index += 1
        delay = ""
        if camera_offset > 0.0005:
            delay = f"tpad=start_duration={camera_offset:.3f}:start_mode=clone,"
        elif camera_offset < -0.0005:
            delay = f"trim=start={-camera_offset:.3f},setpts=PTS-STARTPTS,"
        width, _height = output_size(plan)
        cam_width = max(2, int(width * plan.camera.size_percent / 100) // 2 * 2)
        filters.append(f"[{cam}:v]{delay}scale={cam_width}:-2[cam]")
        filters.append(
            f"[0:v][cam]overlay={_overlay_xy(plan.camera.position)}:eof_action=pass,"
            "format=yuv420p[v]"
        )
        video_label = "[v]"
    audio_labels = []
    for source in sources:
        command += ["-i", str(source.path)]
        filters.append(_audio_chain(next_index, source))
        audio_labels.append(f"[a{next_index}]")
        next_index += 1
    if audio_labels:
        if len(audio_labels) == 1:
            filters.append(f"{audio_labels[0]}alimiter=limit=0.97[aout]")
        else:
            filters.append(
                "".join(audio_labels)
                + f"amix=inputs={len(audio_labels)}:normalize=0:duration=longest,"
                "alimiter=limit=0.97[aout]"
            )
        audio_map = "[aout]"
    elif not plan.silent_track:
        audio_map = ""
    else:
        command += [
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=channel_layout=stereo:sample_rate={SAMPLE_RATE}",
        ]
        audio_map = f"{next_index}:a"
    if filters:
        command += ["-filter_complex", ";".join(filters)]
    command += ["-map", video_label] + (["-map", audio_map] if audio_map else [])
    if camera is None:
        command += ["-c:v", "copy"]
    elif encoder == "libx264":
        command += ["-c:v", "libx264", "-preset", FINAL_PRESET, "-crf", CRF, "-pix_fmt", "yuv420p"]
        command += ["-g", str(plan.fps * 2), "-fps_mode", "cfr", "-r", str(plan.fps)]
    else:
        command += ["-c:v", encoder, "-b:v", "8M", "-fps_mode", "cfr", "-r", str(plan.fps)]
    if audio_map:
        command += ["-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", str(SAMPLE_RATE), "-ac", "2"]
    command += ["-t", f"{max(duration, 0.1):.3f}", "-movflags", "+faststart", str(output)]
    return command


def _mix_graph(sources: Sequence[AudioInput], first_index: int) -> tuple[list[str], str]:
    filters = []
    labels = []
    for offset, source in enumerate(sources):
        index = first_index + offset
        filters.append(_audio_chain(index, source))
        labels.append(f"[a{index}]")
    if len(labels) == 1:
        filters.append(f"{labels[0]}alimiter=limit=0.97[aout]")
    else:
        filters.append(
            "".join(labels)
            + f"amix=inputs={len(labels)}:normalize=0:duration=longest,alimiter=limit=0.97[aout]"
        )
    return filters, "[aout]"


def finish_sound_segment_command(
    ffmpeg: str, output: Path, *, sources: Sequence[AudioInput], duration: float
) -> list[str]:
    """A sound-only segment: the sources mixed to one lossless 48 kHz stereo WAV.

    The first source's own timeline is the segment's clock, so offsets are
    measured against the segment's start rather than a video frame.
    """
    command = [ffmpeg, "-hide_banner", "-y", "-loglevel", "error"]
    for source in sources:
        command += ["-i", str(source.path)]
    filters, label = _mix_graph(sources, 0)
    command += ["-filter_complex", ";".join(filters), "-map", label]
    command += ["-c:a", "pcm_s16le", "-ar", str(SAMPLE_RATE), "-ac", "2"]
    command += ["-t", f"{max(duration, 0.1):.3f}", str(output)]
    return command


#: Sound-only formats -> FFmpeg encoder arguments.
SOUND_CODECS: dict[str, list[str]] = {
    "m4a": ["-c:a", "aac", "-b:a", AUDIO_BITRATE, "-movflags", "+faststart"],
    "mp3": ["-c:a", "libmp3lame", "-b:a", "192k"],
    "wav": ["-c:a", "pcm_s16le"],
    "flac": ["-c:a", "flac"],
    "opus": ["-c:a", "libopus", "-b:a", "96k"],
}


def sound_file_command(ffmpeg: str, list_file: Path, output: Path, sound_format: str) -> list[str]:
    """Join the WAV parts and encode them once to the chosen sound format."""
    return [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        *SOUND_CODECS[sound_format],
        "-ar",
        str(SAMPLE_RATE),
        str(output),
    ]


def concat_list(parts: Sequence[Path]) -> str:
    """The concat demuxer's list file; single quotes escaped its own way."""
    lines = []
    for part in parts:
        escaped = str(part).replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    return "\n".join(lines) + "\n"


def concat_command(ffmpeg: str, list_file: Path, output: Path) -> list[str]:
    return [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(output),
    ]


_STATS_TIME = re.compile(r"time=\s*(-?\d+):(\d+):(\d+(?:\.\d+)?)")
_STATS_FRAMES = re.compile(r"frame=\s*(\d+)")
_STATS_DUP = re.compile(r"dup=\s*(\d+)")
_STATS_DROP = re.compile(r"drop=\s*(\d+)")


@dataclass(frozen=True)
class Stats:
    seconds: float
    frames: int = 0
    duplicated: int = 0
    dropped: int = 0


def parse_stats(line: str) -> Stats | None:
    """FFmpeg's ``frame= ... time= ... dup= drop=`` progress line."""
    match = _STATS_TIME.search(line)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    if hours.startswith("-"):
        return None
    total = int(hours) * 3600 + int(minutes) * 60 + float(seconds)

    def number(pattern: re.Pattern[str]) -> int:
        found = pattern.search(line)
        return int(found.group(1)) if found else 0

    return Stats(total, number(_STATS_FRAMES), number(_STATS_DUP), number(_STATS_DROP))


class StartEstimator:
    """The wall time a stream's first frame was captured, measured from progress.

    Each progress report at wall time ``W`` says ``T`` seconds were written, so
    the stream began no later than ``W - T``; the earliest such bound is the
    best estimate, since a report is only ever late, never early.
    """

    def __init__(self) -> None:
        self.start: float | None = None

    def report(self, wall_time: float, written_seconds: float) -> None:
        if written_seconds <= 0:
            return
        candidate = wall_time - written_seconds
        if self.start is None or candidate < self.start:
            self.start = candidate
