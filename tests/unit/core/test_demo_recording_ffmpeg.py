"""FFmpeg argument builders for Record a Demonstration (PRD 7A.6 test 2)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from quill.core.demo_recording import CameraSetup, DemoPlan
from quill.core.demo_recording_ffmpeg import (
    AudioInput,
    Capabilities,
    StartEstimator,
    camera_capture_command,
    camera_preview_command,
    concat_command,
    concat_list,
    finish_segment_command,
    finish_sound_segment_command,
    parse_dshow_devices,
    parse_listing,
    parse_stats,
    screen_capture_command,
    sound_file_command,
    trial_grab_command,
)

FF = "ffmpeg.exe"


def _plan(**changes) -> DemoPlan:
    base = DemoPlan(
        target_kind="display",
        target_label="Display 2",
        bounds=(1920, 0, 3840, 1080),
        folder="C:\\out",
        display_bounds=(1920, 0, 3840, 1080),
        display_index=1,
    )
    return replace(base, **changes)


def _value(command, flag):
    return command[command.index(flag) + 1]


def test_ddagrab_display_rate_pointer_and_output():
    command = screen_capture_command(
        FF, _plan(fps=60), Path("seg.mkv"), backend="ddagrab", encoder="libx264"
    )
    source = _value(command, "-i")
    assert source.startswith("ddagrab=output_idx=1:framerate=60:draw_mouse=1")
    assert "offset_x" not in source
    assert "hwdownload,format=bgra" in _value(command, "-vf")
    assert _value(command, "-r") == "60" and _value(command, "-fps_mode") == "cfr"
    assert command[-1] == "seg.mkv" and _value(command, "-f") == "lavfi"
    assert "matroska" in command


def test_ddagrab_window_is_offset_within_its_display():
    plan = _plan(target_kind="window", bounds=(2020, 50, 2821, 651), pointer=False)
    source = _value(
        screen_capture_command(FF, plan, Path("s.mkv"), backend="ddagrab", encoder="libx264"), "-i"
    )
    assert "offset_x=100:offset_y=50:video_size=801x601" in source
    assert "draw_mouse=0" in source


def test_gdigrab_desktop_rectangle_and_odd_padding():
    plan = _plan(target_kind="desktop", bounds=(-1280, 0, 1921, 1080))
    command = screen_capture_command(FF, plan, Path("s.mkv"), backend="gdigrab", encoder="h264_mf")
    assert _value(command, "-offset_x") == "-1280"
    assert _value(command, "-video_size") == "3201x1080"
    assert "pad=ceil(iw/2)*2:ceil(ih/2)*2" in _value(command, "-vf")
    assert _value(command, "-c:v") == "h264_mf"


def test_size_ceiling_scales():
    plan = _plan(bounds=(0, 0, 3840, 2160), display_bounds=(0, 0, 3840, 2160), size_ceiling=1080)
    filters = _value(
        screen_capture_command(FF, plan, Path("s.mkv"), backend="gdigrab", encoder="libx264"), "-vf"
    )
    assert "scale=1920:1080" in filters


def test_unknown_backend_is_refused():
    with pytest.raises(ValueError):
        screen_capture_command(FF, _plan(), Path("s"), backend="wgc", encoder="libx264")


def test_trial_grab_writes_one_rgb_frame():
    command = trial_grab_command(FF, _plan(), Path("t.png"), backend="ddagrab")
    assert _value(command, "-frames:v") == "1"
    assert "format=rgb24" in _value(command, "-vf")
    assert command[-1] == "t.png"


def test_camera_capture_tees_small_grey_frames_to_stdout():
    command = camera_capture_command(
        FF, "Surface Camera Front", Path("c.mkv"), fps=30, encoder="libx264", face_frames=True
    )
    assert "video=Surface Camera Front" in command
    assert command[-1] == "pipe:1"
    assert "format=gray" in " ".join(command)
    plain = camera_capture_command(
        FF, "Cam", Path("c.mkv"), fps=30, encoder="libx264", face_frames=False
    )
    assert plain[-1] == "c.mkv"
    preview = camera_preview_command(FF, "Cam")
    assert preview[-1] == "pipe:1" and "matroska" not in preview


def test_finish_mixes_levels_and_offsets_with_a_limiter():
    sources = [
        AudioInput(Path("mic.wav"), -3.0, 0.120),
        AudioInput(Path("app.wav"), 6.0, -0.250),
    ]
    command = finish_segment_command(
        FF,
        _plan(),
        Path("v.mkv"),
        Path("p.mp4"),
        sources=sources,
        camera=None,
        camera_offset=0.0,
        duration=12.5,
        encoder="libx264",
    )
    graph = _value(command, "-filter_complex")
    assert "[1:a]adelay=120:all=1" in graph and "volume=-3.0dB" in graph
    assert "[2:a]atrim=start=0.250,asetpts=PTS-STARTPTS" in graph and "volume=6.0dB" in graph
    assert "amix=inputs=2:normalize=0" in graph and "alimiter" in graph
    assert _value(command, "-c:v") == "copy"
    assert _value(command, "-c:a") == "aac" and _value(command, "-b:a") == "192k"
    assert _value(command, "-t") == "12.500"
    assert "+faststart" in command


def test_finish_without_sources_adds_silence_so_there_is_one_audio_stream():
    command = finish_segment_command(
        FF,
        _plan(),
        Path("v.mkv"),
        Path("p.mp4"),
        sources=[],
        camera=None,
        camera_offset=0.0,
        duration=3,
        encoder="libx264",
    )
    assert any(arg.startswith("anullsrc") for arg in command)
    assert "-filter_complex" not in command


def test_finish_overlays_camera_in_the_chosen_corner():
    plan = _plan(
        camera=CameraSetup(enabled=True, device="Cam", position="top left", size_percent=25)
    )
    command = finish_segment_command(
        FF,
        plan,
        Path("v.mkv"),
        Path("p.mp4"),
        sources=[AudioInput(Path("a.wav"), 0, 0)],
        camera=Path("c.mkv"),
        camera_offset=0.4,
        duration=5,
        encoder="libx264",
    )
    graph = _value(command, "-filter_complex")
    assert "tpad=start_duration=0.400" in graph
    assert "scale=480:-2[cam]" in graph
    assert "overlay=x=16:y=16" in graph
    assert _value(command, "-c:v") == "libx264"
    assert "[v]" in command


def test_camera_filling_the_picture_is_the_video_input_without_overlay():
    plan = _plan(screen=False, camera=CameraSetup(enabled=True, device="Cam"))
    command = finish_segment_command(
        FF,
        plan,
        Path("camera.mkv"),
        Path("p.mp4"),
        sources=[],
        camera=None,
        camera_offset=0.0,
        duration=5,
        encoder="libx264",
    )
    assert _value(command, "-i") == "camera.mkv"
    assert "overlay" not in " ".join(command)
    assert _value(command, "-c:v") == "copy"


def test_no_sound_and_no_silent_track_writes_no_audio_stream():
    plan = _plan(silent_track=False)
    command = finish_segment_command(
        FF,
        plan,
        Path("v.mkv"),
        Path("p.mp4"),
        sources=[],
        camera=None,
        camera_offset=0.0,
        duration=5,
        encoder="libx264",
    )
    assert not any(arg.startswith("anullsrc") for arg in command)
    assert "-c:a" not in command
    assert command.count("-map") == 1


def test_sound_only_segment_and_file_formats():
    command = finish_sound_segment_command(
        FF,
        Path("part.wav"),
        sources=[AudioInput(Path("mic.wav"), -2.0, 0.05), AudioInput(Path("app.wav"), 0, 0)],
        duration=7.5,
    )
    assert _value(command, "-c:a") == "pcm_s16le"
    assert "amix=inputs=2" in _value(command, "-filter_complex")
    assert command[-1] == "part.wav"
    for fmt, codec in (
        ("m4a", "aac"),
        ("mp3", "libmp3lame"),
        ("wav", "pcm_s16le"),
        ("flac", "flac"),
        ("opus", "libopus"),
    ):
        encode = sound_file_command(FF, Path("parts.txt"), Path(f"out.{fmt}"), fmt)
        assert _value(encode, "-c:a") == codec and _value(encode, "-f") == "concat"


def test_concat_list_escapes_quotes_and_backslashes(tmp_path):
    text = concat_list([Path("C:\\a b\\it's.mp4")])
    assert text == "file 'C:/a b/it'\\''s.mp4'\n"
    command = concat_command(FF, Path("list.txt"), Path("out.mp4"))
    assert _value(command, "-f") == "concat" and _value(command, "-c") == "copy"


def test_parse_listings_and_capabilities():
    encoders = parse_listing(" V....D libx264              libx264 H.264\n A....D aac   AAC\n")
    filters = parse_listing(" .. ddagrab           |->V       Grab\n")
    devices = parse_listing(" D  gdigrab         GDI API\n D  dshow  DirectShow\n")
    caps = Capabilities(encoders, filters, devices)
    assert caps.h264_encoder == "libx264" and caps.video_backend == "ddagrab" and caps.can_record
    assert not Capabilities(frozenset({"aac"}), frozenset(), devices).h264_encoder


def test_parse_dshow_devices():
    text = (
        '[in#0 @ 0] "Surface Camera Front" (video)\n'
        '[in#0 @ 0]   Alternative name "@device_pnp_x"\n'
        '[in#0 @ 0] "Microphone (Logi)" (audio)\n'
    )
    assert parse_dshow_devices(text) == [
        ("Surface Camera Front", "video"),
        ("Microphone (Logi)", "audio"),
    ]


def test_parse_stats_and_start_estimator():
    stats = parse_stats(
        "frame=  152 fps= 30 q=-1.0 size=1kB time=00:00:05.06 bitrate=1 dup=3 drop=1 speed=1x"
    )
    assert stats is not None
    assert (stats.frames, stats.duplicated, stats.dropped) == (152, 3, 1)
    assert stats.seconds == pytest.approx(5.06)
    assert parse_stats("time=N/A") is None
    assert parse_stats("time=-00:00:00.03") is None
    estimator = StartEstimator()
    estimator.report(105.3, 5.0)
    estimator.report(110.1, 10.0)
    estimator.report(100.0, 0.0)
    assert estimator.start == pytest.approx(100.1)
