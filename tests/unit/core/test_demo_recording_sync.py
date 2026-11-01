"""Measured sync from the decoded file (VERIFY-009).

The pure parts are checked on hand-made bytes; the acceptance -- a clip
whose tone lands 40 ms after its flash is read back within 5 ms -- runs on a
generated flash-and-tone clip, and is skipped when FFmpeg is not installed.
"""

from __future__ import annotations

import struct
import subprocess
from pathlib import Path

import pytest

from quill.core.demo_recording_sync import (
    LUMA_EDGE,
    TONE_RATE,
    SyncReading,
    SyncReport,
    drift_per_minute,
    flash_onsets,
    frame_lumas,
    measure_sync,
    pair_offsets,
    sync_starts,
    tone_onsets,
)


def test_windows_sit_at_start_middle_and_end_on_frame_boundaries():
    assert sync_starts(3.0, 30) == [0.0]
    starts = sync_starts(60.0, 30, window=4.0)
    assert starts == [0.0, 28.0, 56.0]
    assert all(abs(s * 30 - round(s * 30)) < 1e-9 for s in sync_starts(61.01, 30))


def test_flashes_are_found_from_frame_brightness():
    dark, bright = bytes(LUMA_EDGE * LUMA_EDGE), bytes([255]) * (LUMA_EDGE * LUMA_EDGE)
    frames = ([bright] * 3 + [dark] * 27) * 2
    lumas = frame_lumas(b"".join(frames))
    assert lumas[0] == 255.0 and lumas[3] == 0.0
    # The first frame is already bright, so only the second rise counts.
    assert flash_onsets(lumas, fps=30, start=10.0) == [pytest.approx(11.0)]
    assert flash_onsets([0.0] * 30, fps=30, start=0.0) == []


def test_tone_onsets_from_one_millisecond_blocks():
    silence = [0] * (TONE_RATE // 10)
    tone = [8000 if i % 2 else -8000 for i in range(TONE_RATE // 10)]
    pcm = struct.pack(f"<{len(silence) * 3}h", *(silence + tone + silence))
    assert tone_onsets(pcm, start=2.0) == [pytest.approx(2.1, abs=0.001)]
    assert tone_onsets(bytes(TONE_RATE), start=0.0) == []


def test_pairs_ignore_a_tone_too_far_from_its_flash():
    assert pair_offsets([1.0, 2.0], [1.04, 2.9]) == [pytest.approx(0.04)]
    assert pair_offsets([1.0], []) == []


def test_drift_per_minute_is_the_slope_of_the_offsets():
    readings = [SyncReading(0.0, 40.0, 4), SyncReading(30.0, 45.0, 4), SyncReading(60.0, 50.0, 4)]
    assert drift_per_minute(readings) == pytest.approx(10.0)
    assert drift_per_minute([SyncReading(0.0, 40.0, 4), SyncReading(30.0, None)]) is None
    lines = SyncReport(readings).lines()
    assert lines[0] == "Sync at the start: sound 40.0 ms late (4 pulses)."
    assert lines[-1] == "Drift: +10.00 ms a minute."


def _flash_and_tone_clip(ffmpeg: str, path: Path, *, seconds: int, offset: float) -> None:
    """A white flash at every whole second and a 1 kHz tone *offset* seconds after it."""
    late = f"{offset:.3f}"
    video = (
        "color=black:s=64x64:r=30,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='lt(mod(t\\,1)\\,0.1)'"
    )
    # Timeline gating is decided once per generated frame, so the frames are
    # 1 ms long; at the default 1024 samples the tone would start up to 21 ms late.
    audio = (
        "sine=frequency=1000:sample_rate=48000:samples_per_frame=48,"
        f"volume=volume=0:enable='not(between(mod(t\\,1)\\,{late}\\,{late}+0.1))'"
    )
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            video,
            "-f",
            "lavfi",
            "-i",
            audio,
            "-t",
            str(seconds),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )


def test_a_clip_offset_by_40_ms_is_measured_within_5_ms(tmp_path):
    """VERIFY-009 acceptance, on the decoded file rather than its headers."""
    from quill.core.speech.ffmpeg import find_ffmpeg

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        pytest.skip("ffmpeg is not installed")
    clip = tmp_path / "fixture.mp4"
    _flash_and_tone_clip(ffmpeg, clip, seconds=14, offset=0.040)

    def run(command: list[str]) -> bytes:
        return subprocess.run(command, check=True, capture_output=True, timeout=60).stdout

    report = measure_sync(ffmpeg, clip, duration=14.0, fps=30, run=run)
    assert len(report.readings) == 3
    for reading in report.readings:
        assert reading.offset_ms is not None, report.lines()
        assert reading.offset_ms == pytest.approx(40.0, abs=5.0), report.lines()
        assert reading.pulses >= 3
    drift = report.drift_ms_per_minute
    # Onsets resolve to 1 ms; over this 10-second span that is 6 ms a minute.
    assert drift is not None and abs(drift) <= 7.0, report.lines()
    assert report.to_dict()["readings"][1]["position"] == pytest.approx(5.0)
