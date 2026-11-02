"""Measured sync from the decoded file, not from its headers (VERIFY-009).

Container timestamps are not evidence of sync: an encoder setting can fix
the headers and move the real sync the wrong way. So the check decodes the
picture and the sound and finds a fixture in each -- a white flash and a
tone that start together -- then measures how far apart they land at the
start, the middle and the end of the file, and how fast that gap moves
(drift per minute).

Pure functions over decoded bytes, plus :func:`measure_sync`, which takes the
runner as an argument so the platform layer (or a test) decides how FFmpeg is
run. Positive offsets mean the sound is late.

The lesson -- "read the pixels, not the boxes" -- is from Tony Gebhard's
TG Drop Deck (https://github.com/tonygeb23/tg-drop-deck), whose own checker
measures sync from frames that carry their capture time. No code was copied.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Seconds decoded at each of the three places.
SYNC_WINDOW_SECONDS = 4.0
#: Each frame is shrunk to this many pixels a side; its mean is the brightness.
LUMA_EDGE = 8
#: The sound is decoded to mono at this rate; 1 ms blocks are 16 samples.
TONE_RATE = 16_000
_BLOCK = TONE_RATE // 1000
#: A flash must lift the mean brightness by at least this much (0-255).
_FLASH_CONTRAST = 64.0
#: Below this mean absolute sample the sound has no tone in it at all.
_TONE_FLOOR = 300.0
#: A flash and a tone further apart than this are not one fixture pulse.
PAIR_LIMIT_SECONDS = 0.5


def sync_starts(duration: float, fps: float, window: float = SYNC_WINDOW_SECONDS) -> list[float]:
    """Where the start, middle and end windows begin, each on a frame boundary."""
    if duration <= window:
        return [0.0]
    raw = [0.0, duration / 2 - window / 2, duration - window]
    if fps <= 0:
        return raw
    return [math.floor(max(0.0, start) * fps) / fps for start in raw]


def luma_command(ffmpeg: str, path: Path, start: float, length: float) -> list[str]:
    """The decoded picture as one small grey frame after another, on stdout."""
    return [
        ffmpeg,
        "-hide_banner",
        "-v",
        "error",
        "-ss",
        f"{start:.6f}",
        "-t",
        f"{length:.3f}",
        "-i",
        str(path),
        "-map",
        "0:v:0",
        "-vf",
        f"scale={LUMA_EDGE}:{LUMA_EDGE}:flags=area,format=gray",
        "-f",
        "rawvideo",
        "pipe:1",
    ]


def tone_command(ffmpeg: str, path: Path, start: float, length: float) -> list[str]:
    """The decoded sound as mono 16-bit samples at :data:`TONE_RATE`, on stdout.

    Raw samples carry no timestamps, so the first one must be the window's
    start: ``first_pts=0`` pads with silence when the sound begins later
    (an AAC file's first decoded sample is about 21 ms in, after the encoder's
    priming), which would otherwise read as the sound being 21 ms early.
    """
    return [
        ffmpeg,
        "-hide_banner",
        "-v",
        "error",
        "-ss",
        f"{start:.6f}",
        "-t",
        f"{length:.3f}",
        "-i",
        str(path),
        "-map",
        "0:a:0",
        "-af",
        f"aresample={TONE_RATE}:async=1:first_pts=0",
        "-ac",
        "1",
        "-ar",
        str(TONE_RATE),
        "-f",
        "s16le",
        "pipe:1",
    ]


def frame_lumas(raw: bytes, edge: int = LUMA_EDGE) -> list[float]:
    size = edge * edge
    return [sum(raw[i : i + size]) / size for i in range(0, len(raw) - size + 1, size)]


def _rising(levels: Sequence[float], threshold: float, holdoff: int) -> list[int]:
    found: list[int] = []
    previous = levels[0] if levels else 0.0
    for index in range(1, len(levels)):
        level = levels[index]
        if previous < threshold <= level and (not found or index - found[-1] >= holdoff):
            found.append(index)
        previous = level
    return found


def flash_onsets(lumas: Sequence[float], *, fps: float, start: float) -> list[float]:
    """The times the picture turns bright, from decoded frame brightness."""
    if len(lumas) < 2 or fps <= 0 or max(lumas) - min(lumas) < _FLASH_CONTRAST:
        return []
    threshold = (max(lumas) + min(lumas)) / 2
    holdoff = max(1, int(fps * 0.2))
    return [start + index / fps for index in _rising(lumas, threshold, holdoff)]


def tone_onsets(pcm: bytes, *, start: float, rate: int = TONE_RATE) -> list[float]:
    """The times the tone starts, from 1 ms blocks of decoded sound."""
    block = max(1, rate // 1000)
    count = len(pcm) // 2
    if count < block * 2:
        return []
    samples = memoryview(pcm[: count * 2]).cast("h")
    levels = [
        sum(abs(value) for value in samples[i : i + block]) / block
        for i in range(0, count - block + 1, block)
    ]
    loudest = max(levels)
    if loudest < _TONE_FLOOR:
        return []
    onsets = _rising(levels, loudest * 0.3, holdoff=200)
    return [start + index * block / rate for index in onsets]


def pair_offsets(
    flashes: Sequence[float], tones: Sequence[float], limit: float = PAIR_LIMIT_SECONDS
) -> list[float]:
    """Tone minus flash, in seconds, for each flash with a tone close enough."""
    offsets = []
    for flash in flashes:
        nearest = min(tones, key=lambda tone: abs(tone - flash), default=None)
        if nearest is not None and abs(nearest - flash) <= limit:
            offsets.append(nearest - flash)
    return offsets


@dataclass(frozen=True)
class SyncReading:
    """The offset at one place in the file; ``None`` when no pulse was found."""

    position: float
    offset_ms: float | None
    pulses: int = 0


@dataclass
class SyncReport:
    readings: list[SyncReading] = field(default_factory=list)

    @property
    def measured(self) -> list[SyncReading]:
        return [r for r in self.readings if r.offset_ms is not None]

    @property
    def drift_ms_per_minute(self) -> float | None:
        return drift_per_minute(self.readings)

    def lines(self) -> list[str]:
        out = []
        names = ("start", "middle", "end")
        for index, reading in enumerate(self.readings):
            name = names[index] if len(self.readings) == 3 else f"{reading.position:.0f} seconds"
            if reading.offset_ms is None:
                out.append(f"Sync at the {name}: no flash and tone found.")
            else:
                way = "late" if reading.offset_ms > 0 else "early"
                out.append(
                    f"Sync at the {name}: sound {abs(reading.offset_ms):.1f} ms {way} "
                    f"({reading.pulses} pulses)."
                )
        drift = self.drift_ms_per_minute
        if drift is not None:
            out.append(f"Drift: {drift:+.2f} ms a minute.")
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "readings": [
                {"position": r.position, "offset_ms": r.offset_ms, "pulses": r.pulses}
                for r in self.readings
            ],
            "drift_ms_per_minute": self.drift_ms_per_minute,
        }


def drift_per_minute(readings: Sequence[SyncReading]) -> float | None:
    """The least-squares slope of offset against position, in ms a minute."""
    points = [(r.position, r.offset_ms) for r in readings if r.offset_ms is not None]
    if len(points) < 2:
        return None
    mean_x = sum(x for x, _ in points) / len(points)
    mean_y = sum(y for _, y in points) / len(points)
    spread = sum((x - mean_x) ** 2 for x, _ in points)
    if spread <= 0:
        return None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in points) / spread
    return slope * 60.0


def reading_at(start: float, lumas: Sequence[float], pcm: bytes, *, fps: float) -> SyncReading:
    offsets = pair_offsets(flash_onsets(lumas, fps=fps, start=start), tone_onsets(pcm, start=start))
    if not offsets:
        return SyncReading(start, None, 0)
    ordered = sorted(offsets)
    median = ordered[len(ordered) // 2]
    return SyncReading(start, median * 1000.0, len(offsets))


def measure_sync(
    ffmpeg: str,
    path: Path,
    *,
    duration: float,
    fps: float,
    run: Callable[[list[str]], bytes],
    window: float = SYNC_WINDOW_SECONDS,
) -> SyncReport:
    """Decode three windows of *path* and read the flash-and-tone offset in each.

    *run* executes one FFmpeg command and returns its standard output.
    """
    report = SyncReport()
    for start in sync_starts(duration, fps, window):
        length = min(window, max(0.0, duration - start)) or window
        lumas = frame_lumas(run(luma_command(ffmpeg, path, start, length)))
        pcm = run(tone_command(ffmpeg, path, start, length))
        report.readings.append(reading_at(start, lumas, pcm, fps=fps))
    return report
