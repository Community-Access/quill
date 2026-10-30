"""Make the contact sheet a video question is asked about (roadmap A1).

Frames are taken with FFmpeg at the chosen times, scaled small, and laid out
with Pillow in a labelled grid; the sheet is saved as a verified screenshot so
the Screenshot Inspector can carry the conversation.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from quill.core.demo_recording import DemoRecordingError
from quill.core.video_review import Section, frame_times, frame_width, grid, spoken_time
from quill.stability.safe_subprocess import run_subprocess_safely

_LABEL_SIZE = 26


def contact_sheet(
    ffmpeg: str, video: Path, part: Section, count: int, destination: Path, cancellation: Any = None
) -> list[float]:
    """Write the sheet to *destination*; return the frame times it shows."""
    from PIL import Image, ImageDraw, ImageFont

    times = frame_times(part, count)
    if not times:
        raise DemoRecordingError("That stretch has no length to look at.")
    width = frame_width(len(times))
    frames: list[Any] = []
    with tempfile.TemporaryDirectory(prefix="studio-video-question-") as scratch:
        for index, moment in enumerate(times):
            if cancellation is not None:
                cancellation.raise_if_cancelled()
            target = Path(scratch) / f"frame-{index:02d}.png"
            command = [
                ffmpeg,
                "-hide_banner",
                "-y",
                "-loglevel",
                "error",
                "-ss",
                f"{moment:.2f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                "-vf",
                f"scale={width}:-2",
                "-update",
                "1",
                str(target),
            ]
            try:
                run_subprocess_safely(command, timeout_seconds=60)
            except (OSError, subprocess.TimeoutExpired) as error:
                raise DemoRecordingError(f"A frame could not be taken: {error}") from error
            if target.is_file():
                with Image.open(target) as image:
                    frames.append((moment, image.convert("RGB")))
    if not frames:
        raise DemoRecordingError("No frames could be taken from the video.")
    columns, rows = grid(len(frames))
    height = max(image.height for _moment, image in frames)
    # A time drawn in the default bitmap font is too small to survive a provider
    # shrinking the sheet, and an answer cannot cite a time it cannot read.
    try:
        font: Any = ImageFont.load_default(size=_LABEL_SIZE)
    except TypeError:  # Pillow before 10.1 has one fixed size
        font = ImageFont.load_default()
    label = _LABEL_SIZE + 12
    sheet = Image.new("RGB", (columns * width, rows * (height + label)), "black")
    draw = ImageDraw.Draw(sheet)
    for index, (moment, image) in enumerate(frames):
        column, row = index % columns, index // columns
        left, top = column * width, row * (height + label)
        draw.text((left + 8, top + 5), spoken_time(moment), fill="white", font=font)
        sheet.paste(image, (left, top + label))
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG")
    return [moment for moment, _image in frames]
