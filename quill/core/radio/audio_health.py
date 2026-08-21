"""Whether the audio side of this installation is actually fit to play and record.

WHY THIS EXISTS
---------------
:mod:`quill.core.radio.media_health` answers "is a tool missing?" and
``ui.radio.media_preflight`` speaks that answer once, at launch, deliberately
never modally -- a launch is not the moment to take focus a screen reader has
not settled yet.

That covers the case where the app has something to *tell* you. It leaves the
opposite case unanswered: when **you** want to know. Somebody whose station
will not play, who is about to trust a two-hour scheduled recording to a
machine they are leaving alone, or who has just moved their recordings folder,
has no way to ask "is this going to work?" -- and the launch notice, correctly,
said nothing, because at launch nothing was wrong.

So this is the on-demand half. Same facts, same words, asked rather than told.

WHAT IT REFUSES TO DO
---------------------
It does not test anything. Every row is a fact the app already holds -- which
engine was selected, whether a binary resolved, what the recording folder is
set to and whether it can be written -- and the report is a pure function of
those. It never plays a test tone, opens a device, or writes a probe file,
because a diagnostic that changes what it measures is worse than no diagnostic,
and because somebody opening this window mid-recording must not have their
recording disturbed by the act of checking on it.

It also does not grade. There is no health score and no traffic light: each row
states a fact and, where the fact is bad news, what that costs. A green tick on
five rows and a number at the top would be an invitation to trust a summary
over the sentences underneath it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.radio.media_health import (
    FFMPEG_CAPABILITIES,
    MPV_CAPABILITIES,
    MediaHealth,
)

#: Row severities. Only two, and neither is a score: a row either reports a
#: working state or names something the listener has lost. "Degraded" exists
#: because a missing tool is not a broken app -- stations still play through
#: Windows Media -- and calling that an error would be crying wolf.
OK = "ok"
DEGRADED = "degraded"


@dataclass(frozen=True, slots=True)
class HealthRow:
    """One line of the report: what was checked, and what the answer means."""

    label: str
    detail: str
    severity: str = OK

    def spoken(self) -> str:
        """The whole row as one sentence, the way the house ListBox pattern reads.

        Label first because somebody arrowing the list is looking for a
        subject -- "Recording folder" -- and the verdict is what they stay to
        hear.
        """
        return f"{self.label}: {self.detail}"


@dataclass(frozen=True, slots=True)
class AudioHealthFacts:
    """Everything the report is built from, gathered by the caller.

    A plain record of already-known facts rather than anything that can probe,
    so the report is a pure function and every row below is a table test. The
    UI layer fills this in from the live app (see
    ``ui.radio.audio_health_dialog``), using the *same* predicates the engine
    selection itself uses -- a report that asked a different question from the
    code it describes would eventually describe a machine nobody has.
    """

    #: Which backend is actually in use right now: "mpv", "wx", "spotify", "".
    active_engine: str = ""
    #: The configured preference: "auto", "mpv", "wx".
    engine_preference: str = "auto"
    ffmpeg_present: bool = True
    mpv_present: bool = True
    #: The output device the listener chose, "" for the system default.
    output_device: str = ""
    #: False when a device was chosen and is no longer offered by the system.
    output_device_available: bool = True
    #: Whether Sound Enhancements are doing anything at all right now.
    enhancements_active: bool = False
    #: A short description of what they are set to, e.g. "Voice Clarity".
    enhancements_summary: str = ""
    #: True when this station has its own remembered settings.
    enhancements_per_station: bool = False
    #: Whether the OptiLab Core adapter shipped in this build.
    optilab_available: bool = False
    #: Where finished recordings land, as configured.
    recording_folder: str = ""
    recording_folder_exists: bool = True
    recording_folder_writable: bool = True
    #: Running captures, so somebody checking mid-recording sees it named.
    active_recordings: int = 0
    #: Extra rows the caller wants appended (kept for callers that know
    #: something this module deliberately does not, e.g. an engine-specific
    #: warning). Empty in the ordinary case.
    extra: tuple[HealthRow, ...] = field(default=())


_ENGINE_NAMES = {
    "mpv": "the mpv engine",
    "wx": "the classic Windows Media engine",
    "spotify": "Spotify's own player",
}


def _join(items: tuple[str, ...]) -> str:
    """An Oxford-comma list, matching media_health's own phrasing."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _engine_row(facts: AudioHealthFacts) -> HealthRow:
    """Which engine is playing, and -- when it is the lesser one -- why.

    The case worth catching is "auto" silently falling through to Windows Media
    because libmpv is absent. That is the exact bug ``media_health`` was written
    for, and it is invisible from anywhere else in the app: the setting still
    reads "automatic", which is true and tells you nothing.
    """
    name = _ENGINE_NAMES.get(facts.active_engine, "")
    if facts.active_engine == "spotify":
        return HealthRow("Playback engine", "Spotify's own player, for this station.")
    if facts.active_engine == "mpv":
        return HealthRow("Playback engine", "the mpv engine, with everything it provides.")
    if not name:
        return HealthRow("Playback engine", "nothing is playing, so no engine is in use.")
    if not facts.mpv_present:
        return HealthRow(
            "Playback engine",
            "the classic Windows Media engine, because mpv is missing from this "
            "installation. This is the setting working as designed, not a fault "
            "you caused -- but it is why some stations will not play.",
            DEGRADED,
        )
    if facts.engine_preference == "wx":
        return HealthRow(
            "Playback engine",
            "the classic Windows Media engine, because you chose it in Preferences.",
        )
    return HealthRow("Playback engine", f"{name}.")


def _mpv_row(present: bool) -> HealthRow:
    if present:
        return HealthRow("mpv playback engine", "present.")
    return HealthRow(
        "mpv playback engine",
        "missing. Without it you lose " + _join(MPV_CAPABILITIES) + ". "
        "Help, then Get mpv Playback Engine, downloads it; the full installer "
        "also carries it.",
        DEGRADED,
    )


def _ffmpeg_row(present: bool) -> HealthRow:
    if present:
        return HealthRow("FFmpeg", "present, so recording and converting work.")
    return HealthRow(
        "FFmpeg",
        "missing. Without it you lose " + _join(FFMPEG_CAPABILITIES) + ". "
        "Help > Get FFmpeg fetches it on its own.",
        DEGRADED,
    )


def _output_device_row(facts: AudioHealthFacts) -> HealthRow:
    if not facts.output_device:
        return HealthRow("Output device", "the system default.")
    if not facts.output_device_available:
        return HealthRow(
            "Output device",
            f"{facts.output_device} -- chosen, but the system is not offering it "
            "now. Audio is going to the default device instead. Unplugging a "
            "USB headset does exactly this.",
            DEGRADED,
        )
    if not facts.mpv_present:
        return HealthRow(
            "Output device",
            f"{facts.output_device} is chosen, but routing needs mpv, which is "
            "missing -- so audio is going to the default device.",
            DEGRADED,
        )
    return HealthRow("Output device", f"{facts.output_device}.")


def _enhancements_row(facts: AudioHealthFacts) -> HealthRow:
    if not facts.enhancements_active:
        return HealthRow("Sound Enhancements", "off; audio plays exactly as broadcast.")
    detail = facts.enhancements_summary or "on"
    scope = "for this station only" if facts.enhancements_per_station else "for every station"
    return HealthRow("Sound Enhancements", f"{detail}, {scope}.")


def _optilab_row(available: bool) -> HealthRow:
    """Present-or-absent, and never an error.

    The built-in chain is the default and works everywhere; the adapter is an
    extra. A build without it is a complete build, so this row is informational
    at both ends -- flagging it as degraded would report a missing optional
    component as damage.
    """
    if available:
        return HealthRow("Exact OptiLab processing", "available in this build.")
    return HealthRow(
        "Exact OptiLab processing",
        "not included in this build. The built-in broadcast polish is unaffected.",
    )


def _recording_folder_row(facts: AudioHealthFacts) -> HealthRow:
    folder = facts.recording_folder or "the default recordings folder"
    if not facts.recording_folder_exists:
        return HealthRow(
            "Recording folder",
            f"{folder} -- this folder does not exist. A recording started now "
            "would fail at the moment it tried to write.",
            DEGRADED,
        )
    if not facts.recording_folder_writable:
        return HealthRow(
            "Recording folder",
            f"{folder} -- this folder cannot be written to. A recording started "
            "now would fail at the moment it tried to write.",
            DEGRADED,
        )
    return HealthRow("Recording folder", f"{folder}.")


def _recording_row(count: int) -> HealthRow:
    if count <= 0:
        return HealthRow("Recording now", "nothing is being recorded.")
    if count == 1:
        return HealthRow("Recording now", "one recording is running.")
    return HealthRow("Recording now", f"{count} recordings are running.")


def build_report(facts: AudioHealthFacts) -> list[HealthRow]:
    """Every row, in the order somebody troubleshooting would want them.

    Playback first, because a station that will not play is what brings people
    here; then the two tools underneath it; then output; then the recording
    side. The rows are always all present, including the good ones -- unlike
    the launch notice, which is silent when healthy. This window was *asked* a
    question, and answering "nothing to report" by showing an empty list is not
    an answer.
    """
    return [
        _engine_row(facts),
        _mpv_row(facts.mpv_present),
        _ffmpeg_row(facts.ffmpeg_present),
        _output_device_row(facts),
        _enhancements_row(facts),
        _optilab_row(facts.optilab_available),
        _recording_folder_row(facts),
        _recording_row(facts.active_recordings),
        *facts.extra,
    ]


def headline(rows: list[HealthRow]) -> str:
    """One sentence for the top of the window, and for speaking on open.

    Counts problems rather than scoring health, and names the number so
    somebody who opened the window to check can leave again without arrowing
    the list.
    """
    problems = [row for row in rows if row.severity == DEGRADED]
    if not problems:
        return "Everything the radio needs to play and record is here."
    if len(problems) == 1:
        return f"One thing needs attention: {problems[0].label.lower()}."
    labels = _join(tuple(row.label.lower() for row in problems))
    return f"{len(problems)} things need attention: {labels}."


def media_health_of(facts: AudioHealthFacts) -> MediaHealth:
    """The two-tool view of the same facts, for callers that already speak it."""
    return MediaHealth(ffmpeg=facts.ffmpeg_present, mpv=facts.mpv_present)
