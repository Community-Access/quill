"""The after-recording check: ffprobe parsing and state rules (PRD 7A.6 test 5)."""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.demo_recording import DemoPlan, MarkerLog, SoundSource
from quill.core.demo_recording_verify import (
    ProbeResult,
    SourceLevel,
    black_check_command,
    build_probe_command,
    classify,
    decode_positions,
    parse_black,
    parse_probe,
    save_reports,
    sha256_file,
)


def _plan(**kw) -> DemoPlan:
    return DemoPlan(
        target_kind="window",
        target_label="Edge",
        bounds=(0, 0, 1920, 1080),
        folder="C:\\x",
        sources=(SoundSource("microphone", "Microphone", "microphone", enabled=True),),
        **kw,
    )


def _probe_json(*, audio=True, duration="10.0", packets=300):
    streams = [
        {
            "index": 0,
            "codec_type": "video",
            "codec_name": "h264",
            "width": 1920,
            "height": 1080,
            "avg_frame_rate": "30/1",
            "nb_read_packets": str(packets),
        },
    ]
    if audio:
        streams.append({"index": 1, "codec_type": "audio", "codec_name": "aac"})
    return json.dumps({"streams": streams, "format": {"duration": duration}})


GOOD = [SourceLevel("Microphone", -6.0, -20.0, False)]


def _classify(probe, **kw):
    defaults = dict(
        expected_duration=10.0, decode_errors=[], black=[], levels=GOOD, markers=MarkerLog()
    )
    defaults.update(kw)
    return classify(_plan(), probe, **defaults)


def test_clean_file_is_verified_and_sentence_reads_well():
    result = _classify(parse_probe(_probe_json()))
    assert result.state == "Verified"
    assert result.sentence.startswith("Demonstration saved, 10 seconds, 1920 by 1080 at 30 frames")
    assert "Picture and sound checked." in result.sentence
    assert "Microphone present" in result.sentence
    assert "screen reader left out" in result.sentence


def test_missing_audio_stream_is_failed():
    result = _classify(parse_probe(_probe_json(audio=False)))
    assert result.state == "Failed"
    assert "One audio stream" in result.sentence


def test_duration_mismatch_is_needs_review():
    result = _classify(parse_probe(_probe_json(duration="14.0", packets=420)))
    assert result.state == "Needs review"
    assert "Length" in result.sentence


def test_decode_errors_fail_and_black_or_silence_or_markers_review():
    assert _classify(parse_probe(_probe_json()), decode_errors=["corrupt"]).state == "Failed"
    assert _classify(parse_probe(_probe_json()), black=[(1.0, 4.0)]).state == "Needs review"
    silent = [SourceLevel("Microphone", -120.0, -120.0, True)]
    assert _classify(parse_probe(_probe_json()), levels=silent).state == "Needs review"
    markers = MarkerLog()
    markers.add(3, "Microphone unplugged", failure=True)
    assert _classify(parse_probe(_probe_json()), markers=markers).state == "Needs review"


def test_dropped_frames_over_one_percent_review():
    assert _classify(parse_probe(_probe_json()), dropped_frames=10).state == "Needs review"
    assert _classify(parse_probe(_probe_json()), dropped_frames=2).state == "Verified"


def test_unreadable_probe():
    probe = parse_probe("not json")
    assert probe.error
    assert _classify(probe).state == "Failed"


def test_commands_and_helpers(tmp_path):
    assert "-count_packets" in build_probe_command("ffprobe", Path("a.mp4"))
    assert "blackdetect=d=2:pix_th=0.10" in black_check_command("ffmpeg", Path("a.mp4"))
    assert decode_positions(1.5) == [0.0]
    assert decode_positions(60) == [0.0, 29.0, 58.0]
    log = "[blackdetect @ 0] black_start:0 black_end:2.5 black_duration:2.5\n"
    assert parse_black(log) == [(0.0, 2.5)]


def test_reports_are_written_beside_the_video(tmp_path):
    video = tmp_path / "Demo.mp4"
    video.write_bytes(b"data")
    result = _classify(parse_probe(_probe_json()))
    result.sha256 = sha256_file(video)
    result.path = str(video)
    markers = MarkerLog()
    markers.add(1.0, "Intro done")
    json_path, md_path = save_reports(video, result, _plan(), markers)
    data = json.loads(json_path.read_text("utf-8"))
    assert data["state"] == "Verified" and data["sha256"] == result.sha256
    assert "Intro done" in md_path.read_text("utf-8")
    assert (tmp_path / "Demo.markers.txt").read_text("utf-8").startswith("00:00:01.0")


def test_probe_result_defaults():
    assert ProbeResult().video_streams == 0


def test_sound_only_file_is_verified_without_picture_checks():
    from dataclasses import replace

    plan = replace(_plan(), screen=False)
    probe = parse_probe(
        json.dumps({
            "streams": [{"index": 0, "codec_type": "audio", "codec_name": "aac"}],
            "format": {"duration": "10.0"},
        })
    )
    result = classify(
        plan,
        probe,
        expected_duration=10.0,
        decode_errors=[],
        black=[],
        levels=GOOD,
        markers=MarkerLog(),
    )
    assert result.state == "Verified", result.sentence
    assert result.sentence.startswith("Recording saved, 10 seconds, sound only. Sound checked.")
    assert not any(c.name == "Frame count" for c in result.checks)


def test_picture_with_no_soundtrack_expects_no_audio_stream():
    from dataclasses import replace

    plan = replace(_plan(), sources=(), silent_track=False)
    result = classify(
        plan,
        parse_probe(_probe_json(audio=False)),
        expected_duration=10.0,
        decode_errors=[],
        black=[],
        levels=[],
        markers=MarkerLog(),
    )
    assert result.state == "Verified", result.sentence
    assert "Picture checked." in result.sentence and "no soundtrack" in result.sentence
