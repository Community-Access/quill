"""FUX-11: Radio's test recording uses the real command, capped at 30 seconds."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.radio import test_recording as tr


def test_the_plan_is_the_recording_command_capped_into_the_test_folder(tmp_path: Path) -> None:
    plan = tr.plan_test(
        "ffmpeg", "http://example.test/s", tmp_path, fmt="mp3", bitrate_kbps=128, filter_graph="x"
    )
    assert plan.out_path == tmp_path / "test-recording.mp3"
    assert plan.args[-1] == str(plan.out_path)
    assert "-t" in plan.args and plan.args[plan.args.index("-t") + 1] == str(tr.TEST_SECONDS)
    assert "128k" in " ".join(plan.args)


def test_raw_capture_keeps_the_stream_codec_and_drops_the_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tr, "probe_capture_extension", lambda _url: "aac")
    plan = tr.plan_test(
        "ffmpeg", "http://example.test/s", tmp_path, fmt="copy", bitrate_kbps=128, filter_graph="eq"
    )
    assert plan.out_path.suffix == ".aac"
    assert "eq" not in plan.args


def test_what_an_hour_weighs() -> None:
    assert tr.hour_size_sentence("mp3", 192) == "An hour at 192 kbps is about 82.4 MB."
    assert "depends on the station" in tr.hour_size_sentence("flac", 192)
    text = tr.test_sentence(
        station="WXYZ", fmt="flac", bitrate_kbps=192, seconds=30, size_bytes=3_000_000
    )
    assert "30 seconds made 2.9 MB, so an hour should be about 343.3 MB" in text
    assert "does not prove the rest" in text
    assert "made no sound" in tr.test_sentence(
        station="WXYZ", fmt="mp3", bitrate_kbps=192, seconds=0, size_bytes=0
    )


def test_the_print_ignores_what_a_format_does_not_use() -> None:
    assert tr.settings_print("flac", 128, "", "u") == tr.settings_print("flac", 320, "", "u")
    assert tr.settings_print("mp3", 128, "", "u") != tr.settings_print("mp3", 320, "", "u")
    assert tr.settings_print("copy", 128, "eq", "u") == tr.settings_print("copy", 128, "", "u")
