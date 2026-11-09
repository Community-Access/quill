"""Make a Video: a failed encode leaves no broken file and keeps the last good one.

FFmpeg, the duration probe and the independent check are doubles; nothing runs.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

PIL = pytest.importorskip("PIL")

from PIL import Image  # noqa: E402

from quill.core.demo_recording import DemoRecordingError  # noqa: E402
from quill.core.picture_video import PictureVideoPlan  # noqa: E402
from quill.platform.windows import picture_video_maker as maker  # noqa: E402


def _plan(tmp_path: Path) -> PictureVideoPlan:
    picture = tmp_path / "cover.png"
    Image.new("RGB", (4, 4)).save(picture)
    sound = tmp_path / "show.m4a"
    sound.write_bytes(b"x")
    return PictureVideoPlan(picture=picture, sound=sound, output=tmp_path / "show - video.mp4")


def _ffmpeg(monkeypatch, returncode: int):
    commands: list[list[str]] = []

    def run(command, **_kwargs):
        commands.append(command)
        Path(command[-1]).write_bytes(b"new" if returncode == 0 else b"half")
        return SimpleNamespace(returncode=returncode, stderr="Conversion failed!")

    monkeypatch.setattr(maker, "probe_duration_ms", lambda _p: 60_000)
    monkeypatch.setattr(maker, "run_subprocess_safely", run)
    return commands


def test_a_failed_encode_leaves_no_partial_file_and_the_old_video_survives(tmp_path, monkeypatch):
    plan = _plan(tmp_path)
    plan.output.write_bytes(b"old")
    commands = _ffmpeg(monkeypatch, returncode=1)
    with pytest.raises(DemoRecordingError, match="Conversion failed"):
        maker.make_picture_video("ffmpeg", plan)
    assert commands[0][-1] != str(plan.output)  # FFmpeg never wrote the real name
    assert plan.output.read_bytes() == b"old"
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "cover.png",
        "show - video.mp4",
        "show.m4a",
    ]


def test_a_good_encode_is_moved_into_place(tmp_path, monkeypatch):
    from quill.platform.windows import screen_recorder_finish

    plan = _plan(tmp_path)
    _ffmpeg(monkeypatch, returncode=0)
    monkeypatch.setattr(screen_recorder_finish, "verify", lambda *a, **k: "checked")
    monkeypatch.setattr(maker, "save_reports", lambda *a, **k: None)
    monkeypatch.setattr(maker, "find_ffprobe", lambda: "")
    assert maker.make_picture_video("ffmpeg", plan) == "checked"
    assert plan.output.read_bytes() == b"new"
    assert not any(".partial" in p.name for p in tmp_path.iterdir())
