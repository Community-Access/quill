"""Make and check a picture-and-sound video (roadmap V3, V4).

The plan and command are :mod:`quill.core.picture_video`; this runs FFmpeg,
writes the chapters and the YouTube upload text beside the video, and checks
the result with the same independent check a recording gets.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from quill.core.demo_recording import DemoPlan, DemoRecordingError, MarkerLog, SoundSource, sidecar
from quill.core.demo_recording_verify import Verification, save_reports
from quill.core.picture_video import (
    PictureVideoPlan,
    ffmetadata,
    upload_text,
    validate,
    video_command,
    youtube_chapters,
)
from quill.core.speech.ffmpeg import find_ffprobe, probe_duration_ms
from quill.stability.safe_subprocess import run_subprocess_safely


def make_picture_video(
    ffmpeg: str, plan: PictureVideoPlan, cancellation: Any = None
) -> Verification:
    validate(plan)
    from PIL import Image

    with Image.open(plan.picture) as image:
        picture_size = image.size
    try:
        duration = probe_duration_ms(plan.sound) / 1000
    except Exception as error:  # noqa: BLE001 - one clear sentence for the user
        raise DemoRecordingError(f"The sound file could not be read: {error}") from error
    if duration <= 0:
        raise DemoRecordingError("The sound file has no length.")
    chapters = youtube_chapters(plan.chapters, duration)
    with tempfile.TemporaryDirectory(prefix="studio-picture-video-") as scratch:
        metadata = None
        if chapters or plan.title:
            metadata = Path(scratch) / "chapters.txt"
            metadata.write_text(ffmetadata(chapters, duration, plan.title), encoding="utf-8")
        if cancellation is not None:
            cancellation.raise_if_cancelled()
        result = run_subprocess_safely(
            video_command(ffmpeg, plan, picture_size=picture_size, metadata=metadata),
            timeout_seconds=max(300.0, duration * 3 + 120),
        )
    if result.returncode != 0 or not plan.output.is_file():
        lines = (result.stderr or "").strip().splitlines()
        raise DemoRecordingError(
            "The video could not be made: "
            + (lines[-1] if lines else f"exit code {result.returncode}")
        )
    stand_in = DemoPlan(
        target_kind="display",
        target_label=plan.output.stem,
        bounds=(0, 0, 2, 2),
        folder=str(plan.output.parent),
        fps=plan.fps,
        sources=(SoundSource("application", "Sound", "sound", enabled=True),),
    )
    from quill.platform.windows.screen_recorder_finish import verify

    verification = verify(
        plan.output,
        stand_in,
        duration,
        [],
        MarkerLog(),
        ffmpeg=ffmpeg,
        ffprobe=find_ffprobe(),
    )
    save_reports(plan.output, verification, stand_in, MarkerLog())
    sidecar(plan.output, ".youtube.txt").write_text(upload_text(plan, duration), encoding="utf-8")
    return verification
