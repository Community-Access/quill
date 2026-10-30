"""Record a Demonstration: the plan, the spoken check, file names and markers.

Studio PRD section 7A. Everything here is wx-free and network-free so each
rule is a unit test: what a recording will contain, which problems stop it
(**Stop**) and which only risk spoiling it (**Warn**), where the file goes and
what it is called, and how an interrupted recording is found again.

Privacy is the default: the screen reader's speech, the microphone and the
whole system mix are all *off* until the user turns them on (MX-003, MX-179),
and Studio's own process is never a captured source. Whether the microphone
was on is never written to any saved file -- only which device and level.

The FFmpeg command lines live in :mod:`quill.core.demo_recording_ffmpeg`, the
after-recording check in :mod:`quill.core.demo_recording_verify`, and camera
framing advice in :mod:`quill.core.demo_camera`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from quill.core.error_codes import CodedError

SourceKind = Literal["application", "system", "microphone", "screen_reader"]
TargetKind = Literal["window", "display", "desktop"]
Severity = Literal["Stop", "Warn"]
CameraPosition = Literal["bottom right", "bottom left", "top right", "top left"]
SoundFormat = Literal["m4a", "mp3", "wav", "flac", "opus"]

FRAME_RATES = (15, 24, 30, 60)
SIZE_CEILINGS = (0, 1080, 720)  # 0 = native resolution
CAMERA_POSITIONS: tuple[CameraPosition, ...] = (
    "bottom right",
    "bottom left",
    "top right",
    "top left",
)
#: Sound-only recordings (no picture): format -> (spoken name, extension).
SOUND_FORMATS: dict[SoundFormat, tuple[str, str]] = {
    "m4a": ("M4A (AAC), small and widely playable", ".m4a"),
    "mp3": ("MP3, plays everywhere", ".mp3"),
    "wav": ("WAV, lossless and large", ".wav"),
    "flac": ("FLAC, lossless and compressed", ".flac"),
    "opus": ("Opus, smallest for speech", ".opus"),
}
CAMERA_SIZES = (15, 20, 25, 33, 40)
LEVEL_RANGE_DB = (-60.0, 12.0)
COUNTDOWN_RANGE = (0, 10)
NAME_LIMIT = 60
WORK_PREFIX = ".studio-recording-"
SESSION_FILE = "session.json"
#: Exact zeros for this long from a newly opened input means "probably blocked"
#: (Windows microphone privacy, a muted driver); a quiet room is never zeros.
DIGITAL_SILENCE_SECONDS = 2.5
#: The spoken free-space rule: room for 30 minutes at these settings plus 1 GB.
SPACE_MINUTES = 30
SPACE_MARGIN_BYTES = 1024**3
LOW_SPACE_STOP_BYTES = 200 * 1024**2
#: Microphone lock note: what stops Studio's recording, shown to a refused app.
MICROPHONE_KEY = "Stop and save the demonstration"

_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_SPACES = re.compile(r"\s+")


class DemoRecordingError(CodedError):
    """A recording could not be planned, started or finished."""

    code = "QUILL-STUDIO-RECORD-FAILED"


@dataclass(frozen=True)
class SoundSource:
    """One row of the Sound sources list.

    ``source_id`` is the stable logical identity (MX-114): it names the
    per-source WAV and survives a restart of the process or device, unlike
    ``process_id``.
    """

    kind: SourceKind
    label: str
    source_id: str
    enabled: bool = False
    level_db: float = 0.0
    process_id: int = 0
    process_name: str = ""
    device: str = ""
    #: System sound only: one process tree left out of the system mix (the
    #: screen reader by default), using process-loopback exclude mode.
    exclude_process_id: int = 0
    exclude_name: str = ""

    def spoken(self) -> str:
        level = "" if abs(self.level_db) < 0.05 else f", level {self.level_db:+.0f} dB"
        return f"{self.label}{level}"


@dataclass(frozen=True)
class CameraSetup:
    enabled: bool = False
    device: str = ""
    position: CameraPosition = "bottom right"
    size_percent: int = 25
    #: Say when the presenter's face leaves or returns to the camera's view.
    face_alerts: bool = True
    #: The camera delivers a mirror image, so left and right advice flips.
    mirrored: bool = False


@dataclass(frozen=True)
class DemoPlan:
    target_kind: TargetKind
    target_label: str
    bounds: tuple[int, int, int, int]
    folder: str
    window_handle: int = 0
    process_id: int = 0
    application: str = ""
    #: Physical bounds of the display holding the target (ddagrab offsets are
    #: relative to it) and its index for ``output_idx``.
    display_bounds: tuple[int, int, int, int] = (0, 0, 0, 0)
    display_index: int = 0
    display_device: str = ""
    fps: int = 30
    pointer: bool = True
    size_ceiling: int = 0
    sources: tuple[SoundSource, ...] = ()
    camera: CameraSetup = field(default_factory=CameraSetup)
    keep_stems: bool = False
    countdown: int = 3
    studio_process_id: int = 0
    #: The screen reader the user named (its executable), even if left out.
    screen_reader: str = ""
    #: Record the screen picture. With the camera off too, the recording is
    #: sound only; with the camera on, the camera fills the picture.
    screen: bool = True
    #: The file format when there is no picture at all.
    sound_format: SoundFormat = "m4a"
    #: A picture with no sound source still gets a silent soundtrack, because
    #: some sites refuse a video without one; off writes no audio stream.
    silent_track: bool = True
    #: The picker's full label, used to confirm the window or display is the
    #: same one at check and start time (``target_label`` is the short name).
    target_identity: str = ""

    @property
    def has_picture(self) -> bool:
        return self.screen or self.camera.enabled

    @property
    def camera_fills(self) -> bool:
        """The camera is the whole picture: camera on, screen off."""
        return self.camera.enabled and not self.screen

    @property
    def has_sound_track(self) -> bool:
        return bool(self.enabled_sources()) or (self.has_picture and self.silent_track)

    @property
    def extension(self) -> str:
        return ".mp4" if self.has_picture else SOUND_FORMATS[self.sound_format][1]

    @property
    def name_label(self) -> str:
        """What the file is named after: the screen target, the camera, or the sound."""
        if self.screen:
            return self.target_label
        if self.camera.enabled:
            return self.camera.device or "Camera"
        return "Sound"

    @property
    def width(self) -> int:
        return max(0, self.bounds[2] - self.bounds[0])

    @property
    def height(self) -> int:
        return max(0, self.bounds[3] - self.bounds[1])

    def enabled_sources(self) -> tuple[SoundSource, ...]:
        return tuple(source for source in self.sources if source.enabled)

    def source(self, kind: SourceKind) -> SoundSource | None:
        return next((s for s in self.sources if s.kind == kind and s.enabled), None)


@dataclass(frozen=True)
class Finding:
    severity: Severity
    text: str


@dataclass(frozen=True)
class PreflightFacts:
    """What the platform layer measured; the rules below judge it."""

    target_problem: str = ""
    target_is_studio: bool = False
    display_count: int = 1
    trial_grab_error: str = ""
    trial_grab_uniform: bool = False
    #: source_id -> why it cannot be opened.
    source_errors: dict[str, str] = field(default_factory=dict)
    #: source_ids that delivered only exact digital zeros.
    digital_silence: tuple[str, ...] = ()
    #: source_ids that were open and simply quiet.
    quiet: tuple[str, ...] = ()
    microphone_holder: str = ""
    ffmpeg_found: bool = True
    h264_encoder: str = "libx264"
    video_backend: str = "ddagrab"
    folder_error: str = ""
    free_bytes: int = -1
    hotkeys_assigned: int = 0
    camera_error: str = ""
    camera_guidance: str = ""
    studio_process_in_capture: bool = False


@dataclass
class Marker:
    seconds: float
    label: str
    failure: bool = False


@dataclass
class MarkerLog:
    """Markers in recording time (pauses excluded), written as plain text."""

    markers: list[Marker] = field(default_factory=list)

    def add(self, seconds: float, label: str, *, failure: bool = False) -> Marker:
        marker = Marker(max(0.0, seconds), label.strip() or "Marker", failure)
        self.markers.append(marker)
        self.markers.sort(key=lambda item: item.seconds)
        return marker

    @property
    def failures(self) -> list[Marker]:
        return [marker for marker in self.markers if marker.failure]

    def text(self) -> str:
        lines = []
        for marker in self.markers:
            prefix = "Problem: " if marker.failure else ""
            lines.append(f"{format_timestamp(marker.seconds)}  {prefix}{marker.label}")
        return "\n".join(lines) + ("\n" if lines else "")


def format_timestamp(seconds: float) -> str:
    whole = max(0.0, seconds)
    hours, rest = divmod(int(whole), 3600)
    minutes, secs = divmod(rest, 60)
    tenths = int(round((whole - int(whole)) * 10)) % 10
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{tenths}"


def spoken_duration(seconds: float) -> str:
    total = int(round(max(0.0, seconds)))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if secs or not parts:
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")
    return " ".join(parts)


# -- file naming --------------------------------------------------------------


def short_target_name(label: str) -> str:
    """The picker's spoken label made safe for a Windows file name."""
    name = label.split("; process", 1)[0].split(";", 1)[0]
    name = _FORBIDDEN.sub("", name)
    name = _SPACES.sub(" ", name).strip(" .")
    if len(name) > NAME_LIMIT:
        name = name[:NAME_LIMIT].rstrip(" .")
    return name or "Recording"


def demo_file_name(label: str, when: datetime, extension: str = ".mp4") -> str:
    return f"Demo - {short_target_name(label)} - {when:%Y-%m-%d %H%M%S}{extension}"


def unique_path(path: Path) -> Path:
    """*path*, or ``name (2).ext`` and so on: an existing file is never replaced."""
    if not path.exists():
        return path
    for number in range(2, 10_000):
        candidate = path.with_name(f"{path.stem} ({number}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise DemoRecordingError(f"Could not find a free file name beside {path.name}.")


def sidecar(video: Path, suffix: str) -> Path:
    """``Demo.mp4`` -> ``Demo.verification.json`` and so on."""
    return video.with_name(video.stem + suffix)


def default_folder(videos: Path | None, data_dir: Path, *, portable: bool = False) -> Path:
    if portable or videos is None:
        return data_dir / "studio-recordings"
    return videos / "QUILL Studio"


# -- estimates ------------------------------------------------------------------


def output_size(plan: DemoPlan) -> tuple[int, int]:
    """The encoded picture size: ceiling applied, aspect kept, dimensions even."""
    if not plan.has_picture:
        return 0, 0
    width, height = plan.width, plan.height
    if plan.camera_fills:
        width, height = 1280, 720
    if plan.size_ceiling and height > plan.size_ceiling:
        width = round(width * plan.size_ceiling / height)
        height = plan.size_ceiling
    return width + width % 2, height + height % 2


def bytes_per_minute(plan: DemoPlan) -> int:
    """A deliberately generous estimate: intermediate segments plus the final file."""
    width, height = output_size(plan)
    video_bits = width * height * plan.fps * 0.12 if plan.screen else 0
    audio = 48_000 * 2 * 2 * max(1, len(plan.enabled_sources()))
    camera = 2_500_000 / 8 if plan.camera.enabled else 0
    per_second = video_bits / 8 * 2 + audio + camera * 2 + 192_000 / 8
    return int(per_second * 60)


def space_needed(plan: DemoPlan) -> int:
    return bytes_per_minute(plan) * SPACE_MINUTES + SPACE_MARGIN_BYTES


def minutes_left(free_bytes: int, plan: DemoPlan) -> float:
    rate = bytes_per_minute(plan)
    return max(0.0, (free_bytes - LOW_SPACE_STOP_BYTES) / rate) if rate else 0.0


# -- the spoken check (REC-011) -------------------------------------------------


def preflight(plan: DemoPlan, facts: PreflightFacts) -> list[Finding]:
    """Every Stop and Warn for *plan*, in the order the summary speaks them."""
    findings: list[Finding] = []

    def stop(text: str) -> None:
        findings.append(Finding("Stop", text))

    def warn(text: str) -> None:
        findings.append(Finding("Warn", text))

    if not plan.has_picture and not plan.enabled_sources():
        stop("Nothing to record: turn on the screen, the camera or a sound source.")
    if plan.screen:
        _screen_findings(plan, facts, stop, warn)
    _sound_findings(plan, facts, stop, warn)
    _tool_findings(plan, facts, stop, warn)
    return findings


def _screen_findings(plan: DemoPlan, facts: PreflightFacts, stop: Any, warn: Any) -> None:
    if facts.target_problem:
        stop(facts.target_problem)
    if facts.target_is_studio:
        warn("The target is Studio itself, so the recording will show Studio's controls.")
    if plan.target_kind == "desktop" and facts.display_count > 1:
        warn(
            f"The full desktop spans {facts.display_count} displays; everything on all of them "
            "is recorded, including notifications."
        )
    if plan.target_kind == "window":
        warn(
            "Window recording captures the window's area of the screen: anything that covers "
            "it, such as a notification, is recorded too, and moving the window is not followed."
        )
    if facts.trial_grab_error:
        stop(f"The trial picture could not be taken: {facts.trial_grab_error}")
    elif facts.trial_grab_uniform:
        warn(
            "Every pixel of the trial picture is the same colour. The content may be protected, "
            "blank or black."
        )


def _sound_findings(plan: DemoPlan, facts: PreflightFacts, stop: Any, warn: Any) -> None:
    if plan.has_picture and not plan.enabled_sources():
        warn(
            "No sound source is on: the video will have "
            + ("a silent soundtrack." if plan.silent_track else "no soundtrack at all.")
        )
    for source in plan.enabled_sources():
        error = facts.source_errors.get(source.source_id)
        if error:
            stop(f"{source.label} cannot be opened: {error}")
        elif source.source_id in facts.digital_silence:
            warn(
                f"{source.label} delivers exact digital silence. It is probably blocked; for a "
                "microphone check Windows Settings, Privacy and security, Microphone."
            )
    mic = plan.source("microphone")
    if mic is not None and facts.microphone_holder:
        stop(f"The microphone is in use: {facts.microphone_holder}")
    system = plan.source("system")
    reader = plan.source("screen_reader")
    if system is not None and reader is None and plan.screen_reader:
        if system.exclude_process_id == 0:
            warn(
                "System sound is on while the screen reader is left out. A recording of the "
                "whole system cannot subtract the screen reader; turn on the application's own "
                "sound instead, or leave the screen reader out of system sound."
            )
    if reader is not None:
        warn(
            "Screen reader speech is on: everything your screen reader says while you record "
            "will be in the file. Studio will speak only failures."
        )
    if system is not None and any(s.kind == "application" for s in plan.enabled_sources()):
        warn(
            "System sound and an application's sound are both on, so that application will be "
            "heard twice."
        )
    if system is not None and reader is not None and system.exclude_process_id == 0:
        warn("System sound already contains the screen reader, so it will be heard twice.")
    if facts.studio_process_in_capture:
        stop("Studio's own process is in the capture set; its private sounds would be recorded.")


def _tool_findings(plan: DemoPlan, facts: PreflightFacts, stop: Any, warn: Any) -> None:
    if not facts.ffmpeg_found:
        stop("FFmpeg was not found. Use Voices, Get FFmpeg, then check again.")
    elif plan.has_picture and not facts.h264_encoder:
        stop("This FFmpeg has no H.264 video encoder. Use Voices, Get FFmpeg to replace it.")
    elif plan.screen and plan.target_kind != "window" and facts.video_backend == "gdigrab":
        warn("Only the GDI grabber is available for this display, which uses more processor.")
    if plan.screen and plan.fps == 60 and facts.video_backend != "ddagrab":
        warn("60 frames a second needs desktop duplication; expect dropped frames.")
    if facts.folder_error:
        stop(f"The save folder cannot be written: {facts.folder_error}")
    elif facts.free_bytes >= 0 and facts.free_bytes < space_needed(plan):
        warn(
            f"Free space is low: about {int(minutes_left(facts.free_bytes, plan))} minutes of "
            "recording at these settings."
        )
    if plan.camera.enabled:
        if facts.camera_error:
            stop(f"The camera cannot be opened: {facts.camera_error}")
        elif facts.camera_guidance and not facts.camera_guidance.startswith("Face in view"):
            warn(f"Camera: {facts.camera_guidance}")
    if facts.hotkeys_assigned == 0:
        warn(
            "No system-wide recording keys are assigned. Control the recording from the tray "
            "or the Recording status window, or choose Assign keys."
        )


def can_start(findings: Iterable[Finding]) -> bool:
    return not any(finding.severity == "Stop" for finding in findings)


def summary(plan: DemoPlan, findings: Sequence[Finding]) -> str:
    """The one text the check puts in the read-only field (REC-011 order)."""
    width, height = output_size(plan)
    if plan.screen:
        first = (
            f"Will record: {plan.target_label}, {width} by {height} at {plan.fps} frames a "
            "second"
            + (", with the mouse pointer." if plan.pointer else ", without the mouse pointer.")
        )
    elif plan.camera.enabled:
        first = f"Will record: the camera picture only, at {plan.fps} frames a second."
    else:
        name = SOUND_FORMATS[plan.sound_format][0].split(",", 1)[0]
        first = f"Will record: sound only, saved as {name}."
    lines = [first]
    on = [source.spoken() for source in plan.enabled_sources()]
    off = [source.label for source in plan.sources if not source.enabled]
    if on:
        lines.append("Sound in the recording: " + ", ".join(on) + ".")
    elif plan.has_picture:
        lines.append(
            "Sound in the recording: none, "
            + ("a silent soundtrack." if plan.silent_track else "and no soundtrack.")
        )
    else:
        lines.append("Sound in the recording: none.")
    if off:
        lines.append("Left out: " + ", ".join(off) + ".")
    lines.append(screen_reader_sentence(plan))
    if plan.camera.enabled:
        where = (
            "filling the picture"
            if plan.camera_fills
            else f"camera picture in the {plan.camera.position} corner, "
            f"{plan.camera.size_percent} percent wide"
        )
        lines.append(f"Camera: {plan.camera.device}, {where}.")
    else:
        lines.append("Camera: off.")
    lines.append(f"Saved in: {plan.folder}.")
    if plan.countdown:
        lines.append(f"Recording starts after a {plan.countdown} second countdown.")
    stops = [f for f in findings if f.severity == "Stop"]
    warns = [f for f in findings if f.severity == "Warn"]
    if not findings:
        lines.append("No problems found. Press Start recording.")
    else:
        lines.append(
            f"{len(stops)} stop{'s' if len(stops) != 1 else ''}, "
            f"{len(warns)} warning{'s' if len(warns) != 1 else ''}."
        )
        lines.extend(f"{finding.severity}: {finding.text}" for finding in findings)
        if stops:
            lines.append("Recording cannot start until every Stop is fixed.")
    return "\n".join(lines)


def screen_reader_sentence(plan: DemoPlan) -> str:
    name = plan.screen_reader or "your screen reader"
    reader = plan.source("screen_reader")
    if reader is not None:
        return f"Screen reader: {name} speech IS in the recording."
    system = plan.source("system")
    if system is not None and system.exclude_process_id == 0:
        return f"Screen reader: {name} may be heard, because system sound includes it."
    return f"Screen reader: {name} is left out of the recording."


def capture_process_ids(plan: DemoPlan) -> set[int]:
    """Every process whose sound is captured *including* its tree."""
    return {
        source.process_id
        for source in plan.enabled_sources()
        if source.kind in ("application", "screen_reader") and source.process_id
    }


def validate_plan(plan: DemoPlan) -> None:
    """Shape errors the dialog must fix before a check can even run."""
    if plan.screen:
        if plan.target_kind not in ("window", "display", "desktop"):
            raise DemoRecordingError("Choose a named window, one display or the full desktop.")
        if plan.width <= 0 or plan.height <= 0:
            raise DemoRecordingError("The target has no area to record. Refresh the target list.")
    if plan.sound_format not in SOUND_FORMATS:
        raise DemoRecordingError("Choose a sound file format from the list.")
    if plan.fps not in FRAME_RATES:
        raise DemoRecordingError("Choose 15, 24, 30 or 60 frames a second.")
    if plan.size_ceiling not in SIZE_CEILINGS:
        raise DemoRecordingError("Choose native size, 1080p or 720p.")
    if not COUNTDOWN_RANGE[0] <= plan.countdown <= COUNTDOWN_RANGE[1]:
        raise DemoRecordingError("The countdown is 0 to 10 seconds.")
    if not Path(plan.folder).is_absolute():
        raise DemoRecordingError("Enter an absolute folder for the recording.")
    low, high = LEVEL_RANGE_DB
    for source in plan.sources:
        if not low <= source.level_db <= high:
            raise DemoRecordingError(f"{source.label}: level must be {low:.0f} to +{high:.0f} dB.")
    if plan.studio_process_id and plan.studio_process_id in capture_process_ids(plan):
        raise DemoRecordingError("Studio's own sounds can never be a recorded source.")
    if plan.camera.enabled and not plan.camera.device:
        raise DemoRecordingError("Choose a camera, or turn the camera off.")
    if plan.camera.size_percent not in CAMERA_SIZES:
        raise DemoRecordingError("Choose a camera picture size from the list.")


# -- persisted state --------------------------------------------------------------
