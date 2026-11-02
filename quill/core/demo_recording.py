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
from typing import Literal

from quill.core.error_codes import CodedError

SourceKind = Literal["application", "system", "microphone", "screen_reader", "device"]
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


#: The microphone channel choice (MX-185), as shown -> as saved. Both mixed
#: comes first because it is the default for a device with two inputs.
MIC_CHANNEL_LABELS = {"Both inputs mixed": "mix", "Input 1 only": "1", "Input 2 only": "2"}


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
    #: Microphone only: the Windows capture endpoint ID saved with ``device``,
    #: so the same device is found first by identity, then by name (MX-114).
    endpoint_id: str = ""
    #: Microphone only: ``"mix"`` (both inputs mixed, the default), ``"1"`` or
    #: ``"2"`` -- which input of a two-input interface is recorded (MX-185).
    channel_mode: str = "mix"

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
    #: Hold off sleep, display-off and the screen saver while recording.
    keep_awake: bool = True
    #: Turn on Windows Do Not Disturb while recording, and put it back after.
    do_not_disturb: bool = True
    #: Leave the Recording status window visible to magnifiers and screen
    #: sharing. Keeping a window out of a recording hides it from them too, so
    #: Kelly Ford's Quick Describe keeps a window out only for the moment of a
    #: capture; a recording lasts longer, so here it is the presenter's choice.
    show_status_window: bool = False

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
    #: source_id -> a sentence when one channel is over 30 dB below the other (REC-021).
    one_ear: dict[str, str] = field(default_factory=dict)
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
    #: Whether Windows lets Studio read and set Do Not Disturb.
    dnd_available: bool = True
    #: Share of frames dropped in a 3-second trial at these settings (P3).
    trial_dropped_share: float | None = None
    on_battery: bool = False
    battery_percent: int = -1
    battery_minutes: int = -1
    restart_pending: bool = False


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
    from quill.core.demo_recording_rules import screen_findings, sound_findings, tool_findings

    findings: list[Finding] = []

    def stop(text: str) -> None:
        findings.append(Finding("Stop", text))

    def warn(text: str) -> None:
        findings.append(Finding("Warn", text))

    if not plan.has_picture and not plan.enabled_sources():
        stop("Nothing to record: turn on the screen, the camera or a sound source.")
    if plan.screen:
        screen_findings(plan, facts, stop, warn)
    sound_findings(plan, facts, stop, warn)
    tool_findings(plan, facts, stop, warn)
    return findings


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
    quiet = []
    if plan.keep_awake:
        quiet.append("the computer is kept awake")
    if plan.do_not_disturb:
        quiet.append("Do Not Disturb is turned on")
    if quiet:
        lines.append("While recording, " + " and ".join(quiet) + "; both are put back after.")
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
    if plan.source("device") is not None:
        return f"Screen reader: {name} may be heard if it speaks on the recorded sound card."
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
