"""Finishing a demonstration with the real FFmpeg, on synthetic inputs.

No screen, camera or microphone is opened: FFmpeg's own test sources stand in
for the screen and camera segments and a generated tone for a sound source,
so the filter graphs the builders write (camera overlay, offsets, mixing,
concat, the independent check) are proved to run, not only to look right.
Skipped where FFmpeg is not installed. Also covers PRD 7A.6 test 6: a
crashed session folder is found and finalized.
"""

from __future__ import annotations

import math
import struct
import time
import wave
from pathlib import Path

import pytest

from quill.core.demo_recording import (
    CameraSetup,
    DemoPlan,
    SoundSource,
)
from quill.core.demo_recording_session import (
    SegmentRecord,
    SessionRecord,
    find_unfinished,
    plan_to_dict,
    work_folder,
)
from quill.core.speech.ffmpeg import find_ffmpeg, find_ffprobe
from quill.core.video_colour import colour_tags, to_yuv420p
from quill.stability.safe_subprocess import run_subprocess_safely

FFMPEG = find_ffmpeg()
pytestmark = [
    pytest.mark.skipif(
        FFMPEG is None or find_ffprobe() is None, reason="FFmpeg and ffprobe are needed"
    ),
    # Several real FFmpeg runs per test; the suite's 30-second default is for unit tests.
    pytest.mark.timeout(180),
]


def _video(path: Path, seconds: float, size: str, fps: int = 30) -> None:
    run_subprocess_safely(
        [
            FFMPEG,
            "-hide_banner",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={size}:rate={fps}",
            "-t",
            str(seconds),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            # Converted and tagged as the capture commands do (VIDEO-004).
            "-vf",
            to_yuv420p(),
            "-g",
            str(fps * 2),
            *colour_tags(),
            "-f",
            "matroska",
            str(path),
        ],
        timeout_seconds=120,
    )


def _tone(path: Path, seconds: float, freq: float = 440.0) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(48_000)
        frames = b"".join(
            struct.pack("<hh", value, value)
            for value in (
                int(6000 * math.sin(2 * math.pi * freq * i / 48_000))
                for i in range(int(48_000 * seconds))
            )
        )
        handle.writeframes(frames)


def _session(
    tmp_path: Path,
    *,
    camera: bool,
    segments: int,
    screen: bool = True,
    sound: bool = True,
    sound_format: str = "m4a",
    silent_track: bool = True,
) -> Path:
    plan = DemoPlan(
        screen=screen,
        sound_format=sound_format,
        silent_track=silent_track,
        target_kind="display",
        target_label="Display 1",
        bounds=(0, 0, 640, 360),
        folder=str(tmp_path),
        fps=30,
        sources=(
            SoundSource("application", "Tone sound", "app-tone", enabled=sound, level_db=-3.0),
        ),
        camera=CameraSetup(enabled=camera, device="Test camera", position="bottom left"),
    )
    output = tmp_path / f"Demo - Display 1 - test{plan.extension}"
    work = work_folder(output, "test")
    work.mkdir()
    session = SessionRecord(plan=plan_to_dict(plan), output=str(output), started="test")
    now = time.time()
    for index in range(1, segments + 1):
        folder = work / f"seg-{index:03d}"
        folder.mkdir()
        if screen:
            _video(folder / "video.mkv", 3, "640x360")
        if camera:
            _video(folder / "camera.mkv", 3, "320x240")
        _tone(folder / "app-tone.wav", 3.2)
        session.segments.append(
            SegmentRecord(
                index,
                str(folder),
                video_start=now,
                camera_start=now + 0.2,
                audio_starts={"app-tone": now - 0.2},
                duration=3.0,
                closed=True,
            )
        )
    session.save(work)
    return work


def _caps():
    from quill.platform.windows.demo_media import probe_capabilities

    return probe_capabilities(FFMPEG)


@pytest.mark.parametrize(("camera", "segments"), [(False, 2), (True, 1)])
def test_finalize_joins_mixes_and_verifies(tmp_path, camera, segments):
    from quill.platform.windows.screen_recorder_finish import finalize

    work = _session(tmp_path, camera=camera, segments=segments)
    assert find_unfinished([tmp_path]) == [work]
    verification = finalize(work, ffmpeg=FFMPEG, caps=_caps())
    assert verification.state == "Verified", verification.sentence
    assert f"{3 * segments} seconds" in verification.sentence
    assert "Tone sound present" in verification.sentence
    assert not work.exists()
    assert (tmp_path / "Demo - Display 1 - test.verification.md").is_file()
    assert find_unfinished([tmp_path]) == []


@pytest.mark.parametrize(
    ("label", "options", "expect"),
    [
        ("sound only, M4A", {"screen": False, "camera": False}, "Sound checked."),
        (
            "sound only, FLAC",
            {"screen": False, "camera": False, "sound_format": "flac"},
            "Sound checked.",
        ),
        (
            "camera fills the picture",
            {"screen": False, "camera": True},
            "Picture and sound checked.",
        ),
        (
            "screen, no soundtrack",
            {"camera": False, "sound": False, "silent_track": False},
            "Picture checked.",
        ),
        (
            "screen, silent soundtrack",
            {"camera": False, "sound": False},
            "Picture and sound checked.",
        ),
    ],
)
def test_every_combination_finishes_and_verifies(tmp_path, label, options, expect):
    from quill.platform.windows.screen_recorder_finish import finalize

    work = _session(tmp_path, segments=2, **options)
    verification = finalize(work, ffmpeg=FFMPEG, caps=_caps())
    assert verification.state == "Verified", (label, verification.sentence)
    assert expect in verification.sentence, (label, verification.sentence)
    assert "6 seconds" in verification.sentence


def test_a_drifted_source_is_stretched_and_the_report_says_so(tmp_path):
    """REC-022, mix half: a 30 ms drift over 3 seconds is corrected and reported."""
    import json

    from quill.platform.windows.screen_recorder_finish import finalize

    work = _session(tmp_path, camera=False, segments=1)
    session = SessionRecord.load(work)
    session.segments[0].audio_timing = {
        "app-tone": {"drift_ratio": 1.01, "drift_ms": 30.0, "monotonic_seconds": 3.0}
    }
    session.save(work)
    verification = finalize(work, ffmpeg=FFMPEG, caps=_caps())
    assert verification.state == "Verified", verification.sentence
    assert any("Tone sound, segment 1" in line for line in verification.timing)
    report = json.loads((tmp_path / "Demo - Display 1 - test.verification.json").read_text("utf-8"))
    assert report["timing"]["drift_corrections"][0]["tempo"] == pytest.approx(1.01)
    assert "## Timing" in (tmp_path / "Demo - Display 1 - test.verification.md").read_text("utf-8")


def test_a_lost_picture_keeps_the_sound_and_names_the_stream(tmp_path):
    """REC-024: the screen capture wrote nothing, yet the sound is kept and the check names it."""
    from quill.platform.windows.screen_recorder_finish import finalize

    work = _session(tmp_path, camera=False, segments=1)
    (work / "seg-001" / "video.mkv").unlink()
    session = SessionRecord.load(work)
    session.stream_failures = {"Screen": "Screen capture stopped: exit code 1."}
    session.save(work)
    verification = finalize(work, ffmpeg=FFMPEG, caps=_caps())
    assert verification.state == "Needs review", verification.sentence
    assert "Screen stopped early" in verification.sentence
    assert "Tone sound present" in verification.sentence
    assert "Colour tagged BT.709" not in verification.sentence


@pytest.mark.parametrize("options", [{}, {"zoom": True}, {"wave": True, "shape": "square"}])
def test_picture_and_sound_make_a_checked_youtube_video(tmp_path, options):
    from PIL import Image

    from quill.core.picture_video import Chapter, PictureVideoPlan
    from quill.platform.windows.picture_video_maker import make_picture_video

    picture = tmp_path / "cover.png"
    Image.new("RGB", (800, 600), (40, 90, 160)).save(picture)
    sound = tmp_path / "talk.wav"
    _tone(sound, 4.0)
    plan = PictureVideoPlan(
        picture=picture,
        sound=sound,
        output=tmp_path / "talk - video.mp4",
        title="Talk",
        chapters=(Chapter(0, "Start"), Chapter(1, "Too soon")),
        **options,
    )
    verification = make_picture_video(FFMPEG, plan)
    assert verification.state == "Verified", verification.sentence
    assert "4 seconds" in verification.sentence
    assert (tmp_path / "talk - video.youtube.txt").read_text("utf-8").startswith("Title:\nTalk")


def test_contact_sheet_from_a_real_video(tmp_path):
    from PIL import Image

    from quill.core.video_review import Section, frame_width
    from quill.platform.windows.video_review import contact_sheet

    video = tmp_path / "clip.mkv"
    _video(video, 4, "640x360")
    sheet = tmp_path / "frames.png"
    times = contact_sheet(FFMPEG, video, Section(0, 4), 4, sheet)
    assert len(times) == 4
    with Image.open(sheet) as image:
        assert image.size[0] == 2 * frame_width(4)
