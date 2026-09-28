"""The graphics card's video encoder, and the ways back to the processor.

Before this, every H.264 and H.265 encode ran on the processor, at about real
time for H.264 and half that for H.265, so a film could take longer to convert
than to watch. These pin the choice of encoder, the switches each family
needs, and that a card which fails is never tried twice.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.audio import assemble, convert, convert_runner, ffmpeg_live, video_accel
from quill.core.audio.formats import VIDEO_OUTPUT_FORMATS, VideoQuality, video_quality_args

cv = convert


@pytest.fixture(autouse=True)
def _fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(video_accel, "_found", {})
    monkeypatch.setattr(video_accel, "_broken", set())
    monkeypatch.delenv("QUILL_NO_HARDWARE_VIDEO", raising=False)


def test_the_processor_path_is_unchanged() -> None:
    mp4 = VIDEO_OUTPUT_FORMATS["mp4"]
    assert video_accel.video_codec_args(mp4, VideoQuality.HIGH, "libx264") == [
        "-c:v",
        "libx264",
        *video_quality_args("libx264", VideoQuality.HIGH),
        *mp4.video_args,
    ]


@pytest.mark.parametrize(
    ("encoder", "expected"),
    [
        ("h264_nvenc", ["-rc", "vbr", "-cq", "20", "-b:v", "0", "-preset", "p5"]),
        ("h264_qsv", ["-global_quality", "20", "-preset", "medium"]),
        ("h264_amf", ["-rc", "cqp", "-qp_i", "24", "-qp_p", "24", "-qp_b", "24"]),
    ],
)
def test_each_card_gets_its_own_quality_switches(encoder: str, expected: list[str]) -> None:
    args = video_accel.video_codec_args(VIDEO_OUTPUT_FORMATS["mp4"], VideoQuality.HIGH, encoder)
    assert args[:2] == ["-c:v", encoder]
    assert args[2 : 2 + len(expected)] == expected
    assert "-movflags" in args  # the container's own switches survive


def test_quick_sync_is_given_nv12() -> None:
    args = video_accel.video_codec_args(
        VIDEO_OUTPUT_FORMATS["mp4_hevc"], VideoQuality.SMALL, "hevc_qsv"
    )
    assert args[args.index("-pix_fmt") + 1] == "nv12"
    assert "yuv420p" not in args


def test_the_first_encoder_that_works_is_used_and_remembered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tried: list[str] = []

    def works(ffmpeg: str, encoder: str) -> bool:
        tried.append(encoder)
        return encoder == "h264_qsv"

    monkeypatch.setattr(video_accel, "_works", works)
    assert video_accel.hardware_encoder("ffmpeg", "libx264") == "h264_qsv"
    assert video_accel.hardware_encoder("ffmpeg", "libx264") == "h264_qsv"
    assert tried == ["h264_nvenc", "h264_qsv"]  # probed once per session


def test_a_card_that_failed_is_not_tried_again(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(video_accel, "_works", lambda _f, _e: True)
    assert video_accel.hardware_encoder("ffmpeg", "libx265") == "hevc_nvenc"
    video_accel.mark_broken("hevc_nvenc")
    assert video_accel.hardware_encoder("ffmpeg", "libx265") is None


def test_no_card_for_formats_without_one_or_when_switched_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(video_accel, "_works", lambda _f, _e: True)
    assert video_accel.hardware_encoder("ffmpeg", "libvpx-vp9") is None
    monkeypatch.setenv("QUILL_NO_HARDWARE_VIDEO", "1")
    assert video_accel.hardware_encoder("ffmpeg", "libx264") is None


def test_the_runner_picks_the_card_and_falls_back_to_the_processor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(video_accel, "_works", lambda _f, e: e == "h264_amf")
    job = cv.ConversionJob(Path("a.mkv"), Path("a.mp4"), cv.ConversionSpec(fmt="mp4"))
    on_card = convert_runner._with_graphics_card("ffmpeg", job)
    assert on_card.spec.video_encoder == "h264_amf"
    assert "h264_amf" in cv.build_convert_command("ffmpeg", on_card)
    retry = convert_runner._retry_spec(on_card, "Error initializing output stream")
    assert retry is not None
    assert retry[0].spec.video_encoder == ""
    assert "libx264" in cv.build_convert_command("ffmpeg", retry[0])
    assert video_accel.hardware_encoder("ffmpeg", "libx264") is None  # marked broken


def test_sound_and_stream_copies_never_touch_the_card(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(video_accel, "_works", lambda _f, _e: True)
    sound = cv.ConversionJob(Path("a.wav"), Path("a.mp3"), cv.ConversionSpec(fmt="mp3"))
    copy = cv.ConversionJob(
        Path("a.mkv"), Path("a.mp4"), cv.ConversionSpec(fmt="mp4", copy_video=True)
    )
    assert convert_runner._with_graphics_card("ffmpeg", sound) is sound
    assert convert_runner._with_graphics_card("ffmpeg", copy) is copy


# -- Join stops inside a file, and leaves nothing -----------------------------


def test_a_stopped_join_leaves_nothing_at_the_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.audio import media_probe

    monkeypatch.setattr(
        assemble, "probe", lambda p: media_probe.MediaInfo(path=Path(p), duration_s=60.0)
    )
    heard: list[tuple[int, int]] = []

    def live(command, *, duration_s, hooks, timeout_seconds):
        assert duration_s == 60.0
        hooks.on_fraction(0.5)  # half way through the first file...
        return ffmpeg_live.LiveResult(returncode=1, stderr="", cancelled=True)  # ...Stop

    monkeypatch.setattr(assemble, "run_ffmpeg_live", live)
    out = tmp_path / "book.mp3"
    with pytest.raises(RuntimeError, match="Join was stopped"):
        assemble.run_join(
            "ffmpeg",
            [tmp_path / "a.wav", tmp_path / "b.wav"],
            cv.ConversionSpec(fmt="mp3"),
            out,
            progress=lambda _t, cur, total: heard.append((cur, total)),
            cancelled=lambda: False,
        )
    assert not out.exists()
    assert (500, 3000) in heard  # progress inside the first of three steps
