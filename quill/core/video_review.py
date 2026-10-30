"""Ask AI about a video: the whole of it, or a stretch you choose (roadmap A1).

Most vision models take pictures, not video, so Studio sends one picture that
stands for the stretch: frames taken at even times across it, laid out as a
labelled contact sheet ("0:12", "0:24" ...), with the transcript of the same
stretch when one exists beside the video. The conversation then runs in the
Screenshot Inspector, with its consent, provider and Safe Mode rules.

wx-free and network-free: choosing the stretch, the frame times, the sheet's
layout and the transcript excerpt are all unit-tested here.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from quill.core.demo_recording import DemoRecordingError

FRAME_CHOICES = (4, 6, 9, 12, 16)
_TIME = re.compile(r"^\s*(?:(\d+):)?(\d{1,2}):(\d{2})(?:\.(\d))?\s*$")
_SRT_TIME = re.compile(r"(\d+):(\d\d):(\d\d)[,.](\d{3})\s*-->\s*(\d+):(\d\d):(\d\d)[,.](\d{3})")


@dataclass(frozen=True)
class Section:
    start: float
    end: float

    @property
    def length(self) -> float:
        return max(0.0, self.end - self.start)


def parse_time(text: str) -> float:
    """``"1:05"``, ``"01:02:03"`` or ``"75"`` seconds, as seconds."""
    text = text.strip()
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return float(text)
    match = _TIME.match(text)
    if not match:
        raise DemoRecordingError(f'"{text}" is not a time. Write minutes and seconds, like 1:05.')
    hours, minutes, seconds, tenths = match.groups()
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds) + int(tenths or 0) / 10


def spoken_time(seconds: float) -> str:
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def section(duration: float, start: str = "", end: str = "") -> Section:
    """The stretch to ask about; empty fields mean the start or the end of the video."""
    first = parse_time(start) if start.strip() else 0.0
    last = parse_time(end) if end.strip() else duration
    last = min(last, duration)
    if first >= last:
        raise DemoRecordingError("The start of the stretch must come before its end.")
    return Section(first, last)


def frame_times(part: Section, count: int) -> list[float]:
    """*count* times spread evenly across *part*, each in the middle of its slice."""
    if count <= 0 or part.length <= 0:
        return []
    step = part.length / count
    return [round(part.start + step * (index + 0.5), 2) for index in range(count)]


def grid(count: int) -> tuple[int, int]:
    """Columns and rows for a contact sheet of *count* frames."""
    columns = math.ceil(math.sqrt(count))
    rows = math.ceil(count / columns)
    return columns, rows


def transcript_excerpt(srt_text: str, part: Section, limit: int = 6000) -> str:
    """The captions that fall inside *part*, each with its time, from SRT or VTT text."""
    lines: list[str] = []
    blocks = re.split(r"\n\s*\n", srt_text.replace("\r\n", "\n"))
    for block in blocks:
        match = _SRT_TIME.search(block)
        if not match:
            continue
        values = [int(v) for v in match.groups()]
        start = values[0] * 3600 + values[1] * 60 + values[2] + values[3] / 1000
        end = values[4] * 3600 + values[5] * 60 + values[6] + values[7] / 1000
        if end < part.start or start > part.end:
            continue
        text_lines = block[match.end() :].strip().splitlines()
        text = " ".join(line.strip() for line in text_lines if line.strip())
        if text:
            lines.append(f"[{spoken_time(start)}] {text}")
    excerpt = "\n".join(lines)
    return excerpt if len(excerpt) <= limit else excerpt[: limit - 3].rstrip() + "..."


def captions_beside(video: Path) -> Path | None:
    for suffix in (".srt", ".vtt"):
        candidate = video.with_suffix(suffix)
        if candidate.is_file():
            return candidate
    return None


def question_prompt(video: Path, part: Section, times: list[float], transcript: str) -> str:
    """What the AI is told the picture is, so its answers cite times."""
    where = (
        "the whole video"
        if part.start == 0
        else f"the stretch from {spoken_time(part.start)} to {spoken_time(part.end)}"
    )
    lines = [
        f"This picture is a contact sheet of {len(times)} frames from {where} of the video "
        f'"{video.name}", read left to right and top to bottom. Each frame is labelled '
        "with its time. Answer from what is visible, and cite the frame times you rely on.",
    ]
    if transcript:
        lines += ["", "Transcript of the same stretch, with times:", transcript]
    return "\n".join(lines)
