"""A picture and a sound as a YouTube-ready video (roadmap V3, V4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.demo_recording import DemoRecordingError
from quill.core.picture_video import (
    Chapter,
    PictureVideoPlan,
    ffmetadata,
    read_markers,
    size_for,
    upload_text,
    validate,
    video_command,
    video_name,
    youtube_chapters,
)


def _plan(tmp_path: Path, **changes) -> PictureVideoPlan:
    picture = tmp_path / "cover.png"
    sound = tmp_path / "show.m4a"
    picture.write_bytes(b"x")
    sound.write_bytes(b"x")
    values = dict(picture=picture, sound=sound, output=tmp_path / "show - video.mp4")
    values.update(changes)
    return PictureVideoPlan(**values)


def _value(command, flag):
    return command[command.index(flag) + 1]


def test_validate_accepts_pictures_and_sounds_and_refuses_others(tmp_path):
    validate(_plan(tmp_path))
    with pytest.raises(DemoRecordingError, match="picture"):
        validate(_plan(tmp_path, picture=tmp_path / "cover.gifx"))
    with pytest.raises(DemoRecordingError, match="MP4"):
        validate(_plan(tmp_path, output=tmp_path / "x.mov"))


def test_still_picture_command_fits_never_stretches(tmp_path):
    plan = _plan(tmp_path)
    command = video_command("ffmpeg", plan, picture_size=(3000, 3000), metadata=None)
    graph = _value(command, "-filter_complex")
    assert "force_original_aspect_ratio=decrease" in graph and "pad=1920:1080" in graph
    assert "stillimage" in command and _value(command, "-r") == "1"
    assert _value(command, "-c:a") == "aac" and "-shortest" in command and "+faststart" in command


def test_zoom_and_wave_move_at_25_frames(tmp_path):
    plan = _plan(tmp_path, zoom=True, wave=True, shape="vertical")
    command = video_command("ffmpeg", plan, picture_size=(800, 600), metadata=tmp_path / "m.txt")
    graph = _value(command, "-filter_complex")
    assert "zoompan" in graph and "showwaves=s=1080x320" in graph and "overlay=0:H-h" in graph
    assert _value(command, "-r") == "25" and "stillimage" not in command
    assert _value(command, "-map_chapters") == "2"


def test_picture_shape_keeps_its_own_even_size(tmp_path):
    assert size_for(_plan(tmp_path, shape="picture"), (1001, 701)) == (1002, 702)


def test_markers_become_youtube_chapters(tmp_path):
    markers = tmp_path / "show.markers.txt"
    markers.write_text(
        "00:00:15.0  Welcome\n00:00:20.0  Too close\n00:01:00.0  Problem: Mic unplugged\n"
        "00:02:00.0  Wrap up\n",
        encoding="utf-8",
    )
    chapters = read_markers(markers)
    assert [c.title for c in chapters] == ["Welcome", "Too close", "Mic unplugged", "Wrap up"]
    kept = youtube_chapters(chapters, 180)
    assert [(c.seconds, c.title) for c in kept] == [
        (0.0, "Start"),
        (15, "Welcome"),
        (60, "Mic unplugged"),
        (120, "Wrap up"),
    ]
    assert youtube_chapters(chapters[:1], 180) == []  # fewer than three: YouTube ignores them


def test_upload_text_and_metadata(tmp_path):
    chapters = (Chapter(0, "Start"), Chapter(30, "Part two"), Chapter(90, "End"))
    plan = _plan(tmp_path, title="Episode 4", description="Our show.", chapters=chapters)
    text = upload_text(plan, 200)
    assert text.startswith("Title:\nEpisode 4")
    assert "Chapters:\n0:00 Start\n0:30 Part two\n1:30 End" in text
    meta = ffmetadata(chapters, 200, "Episode 4")
    assert meta.startswith(";FFMETADATA1\ntitle=Episode 4") and meta.count("[CHAPTER]") == 3
    assert "END=200000" in meta
    assert video_name(Path("C:/x/show.m4a")).name == "show - video.mp4"
