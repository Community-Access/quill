"""A 30-second test recording with the settings being chosen (FUX-11).

"I don't want to record an hour before finding the settings were wrong."
Recording Settings can make a short test recording of the playing station
with the format, quality and Sound Enhancements chosen in the window -- through
the same ffmpeg command a real recording uses (:func:`build_record_command`)
-- into a temporary folder. What it measured is said in the window: how large
those seconds came out, and so how large an hour of this station will be at
these settings, which for a raw capture or a lossless format no formula can
say.

The test never writes into the recordings folder, never appears in the
recordings list or the history, never counts against the simultaneous
recordings limit, and never changes a setting. The exact OptiLab pass that
runs after a real recording is not part of it.

wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.audio.media_probe import format_size
from quill.core.radio.recording_commands import (
    RECORD_FORMAT_LABELS,
    build_record_command,
    format_uses_bitrate,
    probe_capture_extension,
)
from quill.core.rehearsal import fingerprint, limits_sentence

__all__ = [
    "TEST_SECONDS",
    "TestPlan",
    "hour_size_sentence",
    "plan_test",
    "settings_print",
    "test_sentence",
]

#: How long a test recording runs.
TEST_SECONDS = 30


@dataclass(frozen=True, slots=True)
class TestPlan:
    """The ffmpeg command for one test recording and where it writes."""

    args: list[str]
    out_path: Path


def settings_print(fmt: str, bitrate_kbps: int, filter_graph: str, station_url: str) -> str:
    """What a test proves: the station, the format, the quality and the sound."""
    return fingerprint({
        "url": station_url,
        "format": fmt,
        "kbps": bitrate_kbps if format_uses_bitrate(fmt) else 0,
        "filter": filter_graph if fmt != "copy" else "",
    })


def plan_test(
    ffmpeg: str,
    capture_url: str,
    folder: Path,
    *,
    fmt: str,
    bitrate_kbps: int,
    filter_graph: str = "",
    user_agent: str = "",
) -> TestPlan:
    """The real recording command, capped at :data:`TEST_SECONDS`, into *folder*.

    A raw capture keeps the stream's own codec and drops the filter, exactly
    as :meth:`RadioRecorder.start` does.
    """
    if fmt == "copy":
        extension = probe_capture_extension(capture_url)
        record_filter = ""
    else:
        extension = fmt
        record_filter = filter_graph
    out = folder / f"test-recording.{extension}"
    args = build_record_command(
        ffmpeg,
        capture_url,
        out,
        format=fmt,
        bitrate_kbps=bitrate_kbps,
        duration_seconds=TEST_SECONDS,
        filter_graph=record_filter,
        user_agent=user_agent,
    )
    return TestPlan(args=args, out_path=out)


def hour_size_sentence(fmt: str, bitrate_kbps: int) -> str:
    """What an hour weighs at these settings, where the format fixes it."""
    if format_uses_bitrate(fmt):
        size = format_size(int(bitrate_kbps * 1000 / 8 * 3600))
        return f"An hour at {bitrate_kbps} kbps is about {size}."
    return "The size of an hour depends on the station. Test These Settings measures it."


def test_sentence(
    *, station: str, fmt: str, bitrate_kbps: int, seconds: float, size_bytes: int
) -> str:
    """What the test recording made and what an hour will weigh at that rate."""
    label = RECORD_FORMAT_LABELS.get(fmt, fmt)
    if format_uses_bitrate(fmt):
        label = f"{label}, {bitrate_kbps} kbps"
    if seconds <= 0 or size_bytes <= 0:
        return (
            f"The test recording of {station} made no sound. Check that the station "
            "is playing, then try again."
        )
    per_hour = int(size_bytes * 3600 / seconds)
    return (
        f"Test recording of {station} as {label}: {round(seconds)} seconds made "
        f"{format_size(size_bytes)}, so an hour should be about {format_size(per_hour)}. "
        f"{limits_sentence(f'{round(seconds)} seconds of {station}')}"
    )
