"""Picture preparation: frames, OCR first, fitting, the cap, the sentence, the cache."""

from __future__ import annotations

import io
import subprocess
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from quill.core.ai import picture_prep as pp
from quill.core.ai.connection_caps import (
    CHATGPT,
    FREE,
    OWN_KEY,
    CapabilityMissing,
    record_for,
)
from quill.core.video_review import Section


def _png(width: int, height: int, colour: str = "red", mode: str = "RGB") -> bytes:
    out = io.BytesIO()
    Image.new(mode, (width, height), colour).save(out, format="PNG")
    return out.getvalue()


def _jpeg(width: int, height: int) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), "blue").save(out, format="JPEG")
    return out.getvalue()


# -- times ------------------------------------------------------------------ #


def test_clock_time_pads_minutes_and_shows_hours() -> None:
    assert pp.clock_time(0) == "00:00"
    assert pp.clock_time(330) == "05:30"
    assert pp.clock_time(3723) == "1:02:03"


def test_named_times_sorted_deduped_clamped() -> None:
    assert pp.named_times([130, 10, 10.001, 999], duration=200) == [10.0, 130.0, 199.95]


def test_named_times_refuses_more_than_four() -> None:
    with pytest.raises(pp.PicturePrepError, match="At most 4"):
        pp.named_times([1, 2, 3, 4, 5])


def test_sheet_frames_never_more_than_sixteen() -> None:
    assert len(pp.sheet_frames(Section(0, 600), 40)) == pp.MAX_SHEET_FRAMES == 16
    assert len(pp.sheet_frames(Section(0, 600), 4)) == 4


# -- FFmpeg commands, without FFmpeg ---------------------------------------- #


def test_scene_command_uses_the_scene_filter_and_cap(tmp_path: Path) -> None:
    command = pp.scene_command("ffmpeg", tmp_path / "v.mp4", tmp_path / "s-%03d.png", cap=99)
    joined = " ".join(command)
    assert "select='gt(scene,0.3)'" in joined
    assert "showinfo" in joined
    assert command[command.index("-frames:v") + 1] == "16"


def test_parse_scene_times_reads_pts_time() -> None:
    stderr = (
        "[Parsed_showinfo_2 @ 0x1] n:   0 pts:  12800 pts_time:1.5     duration:512\n"
        "[Parsed_showinfo_2 @ 0x1] n:   1 pts:  99999 pts_time:42.04   duration:512\n"
    )
    assert pp.parse_scene_times(stderr) == [1.5, 42.04]


def test_extract_frames_with_a_fake_runner(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], timeout_seconds: float) -> Any:
        calls.append(command)
        Path(command[-1]).write_bytes(_png(32, 18))
        return subprocess.CompletedProcess(command, 0, "", "")

    frames = pp.extract_frames("ffmpeg", tmp_path / "v.mp4", [1.0, 2.5], tmp_path, runner=runner)
    assert [f.time for f in frames] == [1.0, 2.5]
    assert all(f.path.is_file() for f in frames)
    assert calls[0][calls[0].index("-ss") + 1] == "1.00"


def test_extract_frames_says_when_nothing_came(tmp_path: Path) -> None:
    def runner(command: list[str], timeout_seconds: float) -> Any:
        return subprocess.CompletedProcess(command, 1, "", "boom")

    with pytest.raises(pp.PicturePrepError, match="No frames"):
        pp.extract_frames("ffmpeg", tmp_path / "v.mp4", [1.0], tmp_path, runner=runner)


def test_runner_failure_is_a_sentence(tmp_path: Path) -> None:
    def runner(command: list[str], timeout_seconds: float) -> Any:
        raise OSError("not found")

    with pytest.raises(pp.PicturePrepError, match="FFmpeg could not"):
        pp.extract_frames("ffmpeg", tmp_path / "v.mp4", [1.0], tmp_path, runner=runner)


def test_scene_change_frames_pairs_files_with_times(tmp_path: Path) -> None:
    def runner(command: list[str], timeout_seconds: float) -> Any:
        for index in range(1, 4):
            (tmp_path / f"scene-{index:03d}.png").write_bytes(_png(16, 9))
        return subprocess.CompletedProcess(command, 0, "", "pts_time:3 x pts_time:9.5 pts_time:20")

    frames = pp.scene_change_frames("ffmpeg", tmp_path / "v.mp4", tmp_path, runner=runner)
    assert [f.time for f in frames] == [3.0, 9.5, 20.0]


# -- the sheet -------------------------------------------------------------- #


def _frames(tmp_path: Path, count: int) -> list[pp.Frame]:
    frames = []
    for index in range(count):
        path = tmp_path / f"f{index}.png"
        path.write_bytes(_png(320, 180, "green"))
        frames.append(pp.Frame(float(index * 10), path))
    return frames


def test_build_sheet_lays_out_a_grid(tmp_path: Path) -> None:
    sheet = pp.build_sheet(_frames(tmp_path, 4))
    with Image.open(io.BytesIO(sheet)) as image:
        assert image.format == "PNG"
        assert image.width == 2 * 960  # two columns at the widest frame width


def test_build_sheet_refuses_seventeen(tmp_path: Path) -> None:
    with pytest.raises(pp.PicturePrepError, match="at most 16"):
        pp.build_sheet(_frames(tmp_path, 17))


# -- fitting ---------------------------------------------------------------- #


def test_fit_image_downscales_to_longest_side_and_keeps_png() -> None:
    fitted = pp.fit_image(_png(4000, 1000), 2048)
    assert (fitted.width, fitted.height) == (2048, 512)
    assert fitted.mime == "image/png"


def test_fit_image_reencodes_photographs_as_jpeg() -> None:
    fitted = pp.fit_image(_jpeg(300, 200), 2048)
    assert fitted.mime == "image/jpeg"
    assert (fitted.width, fitted.height) == (300, 200)


def test_fit_image_rejects_non_pictures_and_blind_connections() -> None:
    with pytest.raises(pp.PicturePrepError, match="not a picture"):
        pp.fit_image(b"not an image", 2048)
    with pytest.raises(pp.PicturePrepError, match="cannot see"):
        pp.fit_image(_png(10, 10), pp.longest_side_for(FREE))


def test_longest_side_per_connection() -> None:
    assert pp.longest_side_for(FREE) == 0
    assert pp.longest_side_for(CHATGPT) == 2048
    assert pp.longest_side_for(OWN_KEY) == 3072


def test_prepare_request_refuses_a_connection_that_cannot_see() -> None:
    with pytest.raises(CapabilityMissing):
        pp.prepare_request([_png(10, 10)], record_for(FREE))


def test_prepare_request_enforces_the_cap() -> None:
    record = record_for(CHATGPT)
    with pytest.raises(pp.PicturePrepError, match="At most 4"):
        pp.prepare_request([_png(10, 10)] * 5, record)
    with pytest.raises(pp.PicturePrepError, match="one picture"):
        pp.prepare_request([_png(10, 10)] * 2, record, sheet_frame_count=8)
    with pytest.raises(pp.PicturePrepError, match="at most 16"):
        pp.prepare_request([_png(10, 10)], record, sheet_frame_count=17)


def test_prepare_request_carries_times_and_the_sentence() -> None:
    request = pp.prepare_request(
        [_png(3000, 3000)],
        record_for(CHATGPT),
        times=[0, 330],
        sheet_frame_count=12,
        captions=True,
    )
    assert request.times == (0, 330)
    assert request.images[0].width == 2048
    assert request.inspected == (
        "Looked at 12 frames from 00:00 to 05:30, and the captions beside them."
    )


def test_inspected_sentence_forms() -> None:
    assert pp.inspected_sentence(1) == "Looked at 1 picture."
    assert pp.inspected_sentence(1, [130]) == "Looked at 1 frame at 02:10."


# -- OCR first -------------------------------------------------------------- #


def test_read_locally_answers_a_question_about_words() -> None:
    reading = pp.read_locally(_png(10, 10), "What does the title say?", ocr=lambda p: "Chapter 1")
    assert reading.answered
    assert reading.text == "Chapter 1"
    assert reading.sentence == "Read on this computer."


def test_read_locally_needs_the_model_for_other_questions() -> None:
    reading = pp.read_locally(_png(10, 10), "Is the person smiling?", ocr=lambda p: "Chapter 1")
    assert not reading.answered


def test_read_locally_needs_the_model_when_ocr_finds_nothing() -> None:
    assert not pp.read_locally(_png(10, 10), "What does it say?", ocr=lambda p: "").answered


def test_described_by_sentence_names_the_connection() -> None:
    assert pp.described_by_sentence(CHATGPT) == "Described by My ChatGPT plan."


# -- cache ------------------------------------------------------------------ #


def test_cache_by_content_hash_and_question() -> None:
    cache = pp.PictureCache(limit=2)
    digest = pp.content_hash(b"abc")
    cache.put(digest, "What is  this?", "A cat.", connection=CHATGPT)
    assert cache.get(digest, "what is this?", CHATGPT) == "A cat."
    assert cache.get(digest, "Something else?", CHATGPT) is None
    cache.put("b", "q", "x")
    cache.put("c", "q", "y")
    assert len(cache) == 2
    assert cache.get(digest, "what is this?", CHATGPT) is None  # oldest dropped


# -- with the real FFmpeg, when there is one ---------------------------------- #


def test_real_ffmpeg_frames_and_scene_changes(tmp_path: Path) -> None:
    ffmpeg = pp.find_ffmpeg()
    if not ffmpeg:
        pytest.skip("FFmpeg is not installed here")
    video = tmp_path / "v.mp4"
    made = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=160x90:d=1",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=160x90:d=1",
            "-filter_complex",
            "[0][1]concat=n=2:v=1",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        capture_output=True,
        timeout=60,
        check=False,
    )
    if made.returncode != 0 or not video.is_file():
        pytest.skip("this FFmpeg cannot make a test video")
    frames = pp.extract_frames(ffmpeg, video, [0.5, 1.5], tmp_path, width=80)
    assert len(frames) == 2
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    scenes = pp.scene_change_frames(ffmpeg, video, scenes_dir)
    assert 1 <= len(scenes) <= 16
    assert any(abs(f.time - 1.0) < 0.2 for f in scenes)
