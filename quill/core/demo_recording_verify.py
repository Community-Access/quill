"""The independent check after a demonstration is saved (REC-014).

Studio never trusts its own counters: the finished MP4 is reopened with
``ffprobe`` and FFmpeg and judged here, wx-free. The states are VERIFY-002's:
**Verified** (every objective check passed), **Needs review** (it will play but
something may be spoiled) and **Failed** (a stream is missing or the file does
not decode). The spoken result is one sentence; the report has every check.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from quill.core.demo_recording import (
    DemoPlan,
    MarkerLog,
    screen_reader_sentence,
    sidecar,
    spoken_duration,
)
from quill.core.storage import write_json_atomic, write_text_atomic
from quill.core.video_colour import EXPECTED_PROBE, colour_problems

State = Literal["Verified", "Needs review", "Failed"]
DURATION_TOLERANCE = 1.0
FRAME_TOLERANCE = 0.02
DROPPED_WARN = 0.01


@dataclass(frozen=True)
class ProbeResult:
    video_streams: int = 0
    audio_streams: int = 0
    width: int = 0
    height: int = 0
    frame_rate: float = 0.0
    video_packets: int = 0
    duration: float = 0.0
    video_codec: str = ""
    audio_codec: str = ""
    error: str = ""
    #: VIDEO-004: the picture's colour tags as ffprobe reads them back.
    colour: dict[str, str] = field(default_factory=dict)


def build_probe_command(ffprobe: str, path: Path) -> list[str]:
    return [
        ffprobe,
        "-v",
        "error",
        "-count_packets",
        "-show_entries",
        "stream=index,codec_type,codec_name,width,height,avg_frame_rate,nb_read_packets,"
        "color_space,color_primaries,color_transfer,color_range"
        ":format=duration",
        "-of",
        "json",
        str(path),
    ]


def _rate(text: str) -> float:
    try:
        if "/" in text:
            top, bottom = text.split("/", 1)
            return float(top) / float(bottom) if float(bottom) else 0.0
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def parse_probe(text: str) -> ProbeResult:
    try:
        data = json.loads(text or "{}")
    except ValueError as error:
        return ProbeResult(error=f"ffprobe output was not readable: {error}")
    streams = data.get("streams", []) if isinstance(data, dict) else []
    video = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"]
    audio = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"]
    first = video[0] if video else {}
    try:
        duration = float((data.get("format") or {}).get("duration", 0) or 0)
    except (TypeError, ValueError):
        duration = 0.0
    try:
        packets = int(first.get("nb_read_packets", 0) or 0)
    except (TypeError, ValueError):
        packets = 0
    return ProbeResult(
        video_streams=len(video),
        audio_streams=len(audio),
        width=int(first.get("width", 0) or 0),
        height=int(first.get("height", 0) or 0),
        frame_rate=_rate(str(first.get("avg_frame_rate", "0"))),
        video_packets=packets,
        duration=duration,
        video_codec=str(first.get("codec_name", "")),
        audio_codec=str(audio[0].get("codec_name", "")) if audio else "",
        colour={key: str(first.get(key, "") or "") for key in EXPECTED_PROBE},
    )


def decode_check_command(ffmpeg: str, path: Path, start: float, length: float = 2.0) -> list[str]:
    return [
        ffmpeg,
        "-hide_banner",
        "-v",
        "error",
        "-ss",
        f"{max(0.0, start):.3f}",
        "-t",
        f"{length:.3f}",
        "-i",
        str(path),
        "-f",
        "null",
        "-",
    ]


def decode_positions(duration: float) -> list[float]:
    """The first, middle and last two seconds (REC-014)."""
    if duration <= 2.0:
        return [0.0]
    return [0.0, max(0.0, duration / 2 - 1.0), max(0.0, duration - 2.0)]


def black_check_command(ffmpeg: str, path: Path) -> list[str]:
    """Black intervals on key frames only, so a long file is checked quickly."""
    return [
        ffmpeg,
        "-hide_banner",
        "-skip_frame",
        "nokey",
        "-i",
        str(path),
        "-vf",
        "blackdetect=d=2:pix_th=0.10",
        "-an",
        "-f",
        "null",
        "-",
    ]


_BLACK = re.compile(r"black_start:\s*([\d.]+)\s+black_end:\s*([\d.]+)")


def parse_black(text: str) -> list[tuple[float, float]]:
    return [(float(a), float(b)) for a, b in _BLACK.findall(text)]


@dataclass(frozen=True)
class SourceLevel:
    """One source's measured level from its own WAV."""

    label: str
    peak_dbfs: float
    rms_dbfs: float
    digital_silence: bool
    seconds: float = 0.0

    @property
    def present(self) -> bool:
        return not self.digital_silence and self.peak_dbfs > -70.0


@dataclass
class Check:
    name: str
    passed: bool
    detail: str
    severity: Literal["fail", "review"] = "review"


@dataclass
class Verification:
    state: State
    sentence: str
    checks: list[Check] = field(default_factory=list)
    sha256: str = ""
    path: str = ""
    duration: float = 0.0
    #: What was done to the timing, one sentence each: REC-022's drift
    #: corrections, and VERIFY-009's measured sync when it was measured.
    timing: list[str] = field(default_factory=list)
    #: The same, as data for the JSON report.
    timing_data: dict[str, Any] = field(default_factory=dict)
    #: Per source: samples measured, drift against the monotonic span and
    #: glitch counts (REC-022, REC-023), from ``source_timing_summary``.
    source_timing: list[dict[str, Any]] = field(default_factory=list)

    def report_markdown(self, plan: DemoPlan, markers: MarkerLog) -> str:
        lines = [
            f"# Demonstration check: {Path(self.path).name}",
            "",
            f"Result: {self.state}",
            "",
            self.sentence,
            "",
            "## Checks",
            "",
        ]
        for check in self.checks:
            lines.append(
                f"- {'Passed' if check.passed else 'Problem'}: {check.name}. {check.detail}"
            )
        if self.timing:
            lines += ["", "## Timing", ""] + [f"- {line}" for line in self.timing]
        lines += ["", "## Recording", "", f"- Target: {plan.target_label}"]
        lines.append(f"- Requested frame rate: {plan.fps}")
        lines.append(f"- {screen_reader_sentence(plan)}")
        for source in plan.enabled_sources():
            lines.append(f"- Sound: {source.spoken()}")
        if plan.camera.enabled:
            lines.append(f"- Camera: {plan.camera.device}, {plan.camera.position}")
        lines.append(f"- SHA-256: {self.sha256}")
        if self.source_timing:
            lines += ["", "## Sound timing", ""]
            lines += [f"- {timing_sentence(row)}" for row in self.source_timing]
        if markers.markers:
            lines += ["", "## Markers", "", markers.text().rstrip()]
        return "\n".join(lines) + "\n"


def timing_sentence(row: dict[str, Any]) -> str:
    """One source's timing and glitch counts, as the report says them."""
    return (
        f"{row.get('label', row.get('source_id', 'Source'))}: "
        f"{int(row.get('measured_frames', 0))} samples over "
        f"{float(row.get('monotonic_seconds', 0.0)):.1f} seconds, drift "
        f"{float(row.get('drift_ms', 0.0)):+.1f} ms "
        f"(ratio {float(row.get('drift_ratio', 1.0)):.6f}); "
        f"{int(row.get('discontinuity_count', 0))} gaps reported by Windows, "
        f"{int(row.get('overflow_count', 0))} input overflows, "
        f"{int(row.get('stall_count', 0))} stalls."
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classify(
    plan: DemoPlan,
    probe: ProbeResult,
    *,
    expected_duration: float,
    decode_errors: Sequence[str],
    black: Sequence[tuple[float, float]],
    levels: Sequence[SourceLevel],
    markers: MarkerLog,
    dropped_frames: int = 0,
    folder_label: str = "",
    stream_failures: Mapping[str, str] | None = None,
) -> Verification:
    """Every REC-014 check, and the one sentence that is spoken.

    *stream_failures* (REC-024) names each stream that stopped while the
    others went on recording; each is its own Needs review check, so the
    result says which one rather than only that something went wrong.
    """
    checks: list[Check] = []

    def add(name: str, passed: bool, detail: str, severity: Literal["fail", "review"]) -> None:
        checks.append(Check(name, passed, detail, severity))

    if probe.error:
        add("File opens", False, probe.error, "fail")
    want_video = 1 if plan.has_picture else 0
    want_audio = 1 if plan.has_sound_track else 0
    add(
        "One video stream" if want_video else "No video stream",
        probe.video_streams == want_video,
        f"{probe.video_streams} found ({probe.video_codec or 'none'})",
        "fail",
    )
    add(
        "One audio stream" if want_audio else "No audio stream, as chosen",
        probe.audio_streams == want_audio,
        f"{probe.audio_streams} found ({probe.audio_codec or 'none'})",
        "fail",
    )
    add(
        "Length",
        abs(probe.duration - expected_duration) <= DURATION_TOLERANCE,
        f"{probe.duration:.1f} seconds in the file, {expected_duration:.1f} recorded",
        "review",
    )
    if plan.has_picture:
        _picture_checks(plan, probe, dropped_frames, black, add)
    add(
        "Decodes cleanly",
        not decode_errors,
        "; ".join(decode_errors[:3]) if decode_errors else "start, middle and end decode",
        "fail",
    )
    for level in levels:
        detail = (
            "exact digital silence"
            if level.digital_silence
            else f"peak {level.peak_dbfs:.1f} dBFS, average {level.rms_dbfs:.1f} dBFS"
        )
        add(f"{level.label} present", level.present, detail, "review")
    for name, reason in (stream_failures or {}).items():
        add(f"{name} stopped early", False, f"{reason} The rest kept recording.", "review")
    if markers.failures:
        add(
            "No problems during recording",
            False,
            f"{len(markers.failures)} marked; see the markers",
            "review",
        )
    failed = any(not c.passed and c.severity == "fail" for c in checks)
    review = any(not c.passed for c in checks)
    state: State = "Failed" if failed else "Needs review" if review else "Verified"
    sentence = result_sentence(plan, probe, state, levels, checks, folder_label)
    return Verification(state, sentence, checks, duration=probe.duration)


def _picture_checks(
    plan: DemoPlan,
    probe: ProbeResult,
    dropped_frames: int,
    black: Sequence[tuple[float, float]],
    add: Any,
) -> None:
    expected_frames = probe.duration * plan.fps
    if expected_frames > 0:
        ratio = abs(probe.video_packets - expected_frames) / expected_frames
        add(
            "Frame count",
            ratio <= FRAME_TOLERANCE,
            f"{probe.video_packets} frames, {expected_frames:.0f} expected",
            "review",
        )
    total_frames = max(1, probe.video_packets)
    add(
        "Dropped frames",
        dropped_frames / total_frames <= DROPPED_WARN,
        f"{dropped_frames} dropped while recording",
        "review",
    )
    black_total = sum(end - start for start, end in black)
    add(
        "No black stretches",
        not black,
        f"{len(black)} black stretch{'es' if len(black) != 1 else ''}, "
        f"{black_total:.0f} seconds in all"
        if black
        else "none found",
        "review",
    )
    if probe.video_codec == "h264":
        problems = colour_problems(probe.colour)
        add(
            "Colour tagged BT.709",
            not problems,
            "; ".join(problems) if problems else "BT.709, limited range",
            "review",
        )


def result_sentence(
    plan: DemoPlan,
    probe: ProbeResult,
    state: State,
    levels: Sequence[SourceLevel],
    checks: Sequence[Check],
    folder_label: str,
) -> str:
    what = "Demonstration" if plan.has_picture else "Recording"
    if state == "Failed":
        problems = "; ".join(f"{c.name}: {c.detail}" for c in checks if not c.passed)
        return f"{what} failed its check. {problems}. The recorded pieces were kept."
    if plan.has_picture:
        parts = [
            f"{what} saved, {spoken_duration(probe.duration)}, "
            f"{probe.width} by {probe.height} at {probe.frame_rate:.0f} frames a second."
        ]
    else:
        parts = [f"{what} saved, {spoken_duration(probe.duration)}, sound only."]
    if state == "Verified":
        if plan.has_picture and plan.has_sound_track:
            parts.append("Picture and sound checked.")
        elif plan.has_picture:
            parts.append("Picture checked.")
        else:
            parts.append("Sound checked.")
    else:
        names = [c.name for c in checks if not c.passed]
        parts.append("Needs review: " + ", ".join(names) + ".")
    present = [level.label for level in levels if level.present]
    if present:
        parts.append(" and ".join(present) + " present;")
    elif not plan.enabled_sources():
        parts.append(
            "No sound sources were chosen, so the soundtrack is silent;"
            if plan.silent_track
            else "No sound sources were chosen, so there is no soundtrack;"
        )
    reader = plan.source("screen_reader")
    parts.append("screen reader included." if reader is not None else "screen reader left out.")
    if folder_label:
        parts.append(f"Saved in {folder_label}.")
    return " ".join(parts)


def save_reports(
    video: Path, verification: Verification, plan: DemoPlan, markers: MarkerLog
) -> tuple[Path, Path]:
    data: dict[str, Any] = {
        "file": str(video),
        "state": verification.state,
        "sentence": verification.sentence,
        "sha256": verification.sha256,
        "duration_seconds": verification.duration,
        "checks": [asdict(check) for check in verification.checks],
        "target": plan.target_label,
        "requested_fps": plan.fps,
        "sources": [source.label for source in plan.enabled_sources()],
        "screen_reader": screen_reader_sentence(plan),
        "camera": plan.camera.device if plan.camera.enabled else "",
        "markers": [asdict(marker) for marker in markers.markers],
        "timing": verification.timing_data,
        "source_timing": verification.source_timing,
    }
    json_path = sidecar(video, ".verification.json")
    md_path = sidecar(video, ".verification.md")
    write_json_atomic(json_path, data)
    write_text_atomic(md_path, verification.report_markdown(plan, markers))
    if markers.markers:
        write_text_atomic(sidecar(video, ".markers.txt"), markers.text())
    return json_path, md_path
