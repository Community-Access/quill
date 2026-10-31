"""A picture and a sound made into one video YouTube accepts (roadmap V3, V4).

A podcast episode, a talk or a song with a cover picture becomes an MP4:
H.264 at a low frame rate suited to a still picture, AAC sound at 48 kHz,
``+faststart`` for streaming. The sound goes in exactly as it is; nothing is
edited. Options, all off by default: a slow zoom on the picture, a sound
wave along the bottom so viewers can see that sound is playing, and chapters
from a recording's markers, written into the file and into the description
as YouTube timestamps.

wx-free and network-free: the plan, the FFmpeg command and the upload text
are all unit-tested. Running FFmpeg and checking the file is the platform
layer's job.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from quill.core.demo_recording import DemoRecordingError

Shape = Literal["youtube", "square", "vertical", "picture"]

#: Plain-word sizes. "picture" keeps the picture's own size (made even).
SHAPES: dict[Shape, tuple[str, int, int]] = {
    "youtube": ("YouTube video, 1920 by 1080", 1920, 1080),
    "square": ("Square, 1080 by 1080, for social posts", 1080, 1080),
    "vertical": ("Vertical, 1080 by 1920, for Shorts", 1080, 1920),
    "picture": ("The picture's own size", 0, 0),
}
PICTURE_TYPES = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
SOUND_TYPES = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma")
#: YouTube's description limit, and the shortest chapter it accepts.
DESCRIPTION_LIMIT = 5000
MIN_CHAPTER_SECONDS = 10

_MARKER = re.compile(r"^(\d+):(\d\d):(\d\d)(?:\.\d)?\s+(?:Problem:\s*)?(.+?)\s*$")


@dataclass(frozen=True)
class Chapter:
    seconds: float
    title: str


@dataclass(frozen=True)
class PictureVideoPlan:
    picture: Path
    sound: Path
    output: Path
    shape: Shape = "youtube"
    zoom: bool = False
    wave: bool = False
    title: str = ""
    description: str = ""
    chapters: tuple[Chapter, ...] = ()

    @property
    def fps(self) -> int:
        """One frame a second is enough for a still picture; motion needs more."""
        return 25 if (self.zoom or self.wave) else 1


def validate(plan: PictureVideoPlan) -> None:
    if plan.picture.suffix.lower() not in PICTURE_TYPES or not plan.picture.is_file():
        raise DemoRecordingError("Choose a picture: PNG, JPEG, WebP or BMP.")
    if plan.sound.suffix.lower() not in SOUND_TYPES or not plan.sound.is_file():
        raise DemoRecordingError("Choose a sound file: WAV, MP3, M4A, FLAC, Ogg or Opus.")
    if plan.output.suffix.lower() != ".mp4":
        raise DemoRecordingError("The video is saved as an MP4 file.")
    if plan.shape not in SHAPES:
        raise DemoRecordingError("Choose a video shape from the list.")


def video_name(sound: Path) -> Path:
    return sound.with_name(f"{sound.stem} - video.mp4")


def read_markers(path: Path) -> tuple[Chapter, ...]:
    """Chapters from a recording's ``.markers.txt`` (``00:01:02.5  Label``)."""
    chapters = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    for line in lines:
        match = _MARKER.match(line.strip())
        if match:
            hours, minutes, seconds, label = match.groups()
            chapters.append(Chapter(int(hours) * 3600 + int(minutes) * 60 + int(seconds), label))
    return tuple(chapters)


def youtube_chapters(chapters: Sequence[Chapter], duration: float) -> list[Chapter]:
    """Chapters YouTube will accept: the first at 0:00, each at least 10 seconds long.

    YouTube needs at least three chapters, starting at 0:00, each ten seconds
    or longer; anything else is ignored by YouTube, so it is dropped here
    rather than published to no effect.
    """
    kept: list[Chapter] = []
    for chapter in sorted(chapters, key=lambda c: c.seconds):
        if chapter.seconds >= duration:
            continue
        if kept and chapter.seconds - kept[-1].seconds < MIN_CHAPTER_SECONDS:
            continue
        kept.append(chapter)
    if kept and kept[0].seconds > 0:
        kept.insert(0, Chapter(0.0, "Start"))
    if kept and duration - kept[-1].seconds < MIN_CHAPTER_SECONDS:
        kept.pop()
    return kept if len(kept) >= 3 else []


def _stamp(seconds: float) -> str:
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def upload_text(plan: PictureVideoPlan, duration: float) -> str:
    """Title and description, ready to paste into YouTube's upload form."""
    chapters = youtube_chapters(plan.chapters, duration)
    description = plan.description.strip()
    if chapters:
        lines = [f"{_stamp(c.seconds)} {c.title}" for c in chapters]
        description = (
            (description + "\n\n" if description else "") + "Chapters:\n" + "\n".join(lines)
        )
    if len(description) > DESCRIPTION_LIMIT:
        description = description[: DESCRIPTION_LIMIT - 1].rstrip() + "..."
    title = plan.title.strip() or plan.sound.stem
    return f"Title:\n{title[:100]}\n\nDescription:\n{description}\n"


def ffmetadata(chapters: Sequence[Chapter], duration: float, title: str) -> str:
    """FFmpeg's metadata file: the title and chapters players show."""

    def escape(text: str) -> str:
        return re.sub(r"([=;#\\\n])", r"\\\1", text)

    lines = [";FFMETADATA1"]
    if title:
        lines.append(f"title={escape(title)}")
    ordered = sorted(chapters, key=lambda c: c.seconds)
    for index, chapter in enumerate(ordered):
        end = ordered[index + 1].seconds if index + 1 < len(ordered) else duration
        lines += [
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={int(chapter.seconds * 1000)}",
            f"END={int(max(end, chapter.seconds + 0.001) * 1000)}",
            f"title={escape(chapter.title)}",
        ]
    return "\n".join(lines) + "\n"


def size_for(plan: PictureVideoPlan, picture_size: tuple[int, int]) -> tuple[int, int]:
    _label, width, height = SHAPES[plan.shape]
    if not width:
        width, height = picture_size
    return width + width % 2, height + height % 2


def video_command(
    ffmpeg: str,
    plan: PictureVideoPlan,
    *,
    picture_size: tuple[int, int],
    metadata: Path | None,
) -> list[str]:
    """The one FFmpeg run that makes the video. The picture is fitted, never stretched."""
    width, height = size_for(plan, picture_size)
    fps = plan.fps
    fit = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
    )
    chain = f"[0:v]{fit}"
    if plan.zoom:
        # Scale up first so the zoom has pixels to spare, then ease in to 112 percent.
        chain = (
            f"[0:v]{fit},scale={width * 2}:{height * 2},"
            f"zoompan=z='min(zoom+0.0004,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d=1:s={width}x{height}:fps={fps}"
        )
    filters = [chain + ",format=yuv420p[pic]"]
    video_label = "[pic]"
    if plan.wave:
        wave_height = max(2, height // 6 // 2 * 2)
        filters.append(
            f"[1:a]showwaves=s={width}x{wave_height}:mode=cline:rate={fps}:colors=white,"
            "format=yuva420p[wave]"
        )
        filters.append("[pic][wave]overlay=0:H-h:shortest=1,format=yuv420p[v]")
        video_label = "[v]"
    command = [ffmpeg, "-hide_banner", "-y", "-loglevel", "error"]
    command += ["-loop", "1", "-framerate", str(fps), "-i", str(plan.picture)]
    command += ["-i", str(plan.sound)]
    if metadata is not None:
        command += ["-f", "ffmetadata", "-i", str(metadata)]
    command += ["-filter_complex", ";".join(filters), "-map", video_label, "-map", "1:a"]
    if metadata is not None:
        command += ["-map_metadata", "2", "-map_chapters", "2"]
    command += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
    if not (plan.zoom or plan.wave):
        command += ["-tune", "stillimage"]
    command += ["-r", str(fps), "-g", str(fps * 2)]
    command += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
    command += ["-shortest", "-movflags", "+faststart", str(plan.output)]
    return command
