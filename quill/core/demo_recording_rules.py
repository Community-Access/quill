"""The Stop and Warn rules of Record a Demonstration's spoken check (REC-011).

Split from :mod:`quill.core.demo_recording` (GATE-11), which calls these from
:func:`~quill.core.demo_recording.preflight`. Grouped by what they judge:
the screen target, the sound sources, and the tools and storage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from quill.core.demo_recording import DemoPlan, PreflightFacts


def screen_findings(plan: DemoPlan, facts: PreflightFacts, stop: Any, warn: Any) -> None:
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


def sound_findings(plan: DemoPlan, facts: PreflightFacts, stop: Any, warn: Any) -> None:
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
    devices = [s for s in plan.enabled_sources() if s.kind == "device"]
    if devices and reader is None and plan.screen_reader:
        warn(
            "A whole sound card is in the recording. If your screen reader speaks on that "
            "card, its speech will be recorded too; record the program's own sound instead."
        )
    if devices and (system is not None or len(devices) > 1):
        warn(
            "More than one whole-system or whole-card source is on, so some sounds may be "
            "heard twice."
        )
    if facts.studio_process_in_capture:
        stop("Studio's own process is in the capture set; its private sounds would be recorded.")


def tool_findings(plan: DemoPlan, facts: PreflightFacts, stop: Any, warn: Any) -> None:
    from quill.core.demo_recording import minutes_left, space_needed

    share = facts.trial_dropped_share
    if plan.screen and share is not None and share > 0.05:
        warn(
            f"In a 3-second trial at these settings, {round(share * 100)} percent of frames "
            "were dropped because the computer fell behind. Choose a lower frame rate or the "
            "1080p or 720p size."
        )
    if facts.on_battery:
        left = f", about {facts.battery_minutes} minutes left" if facts.battery_minutes >= 0 else ""
        charge = f" at {facts.battery_percent} percent" if facts.battery_percent >= 0 else ""
        warn(f"The computer is on battery{charge}{left}. Plug it in for a long recording.")
    if facts.restart_pending:
        warn(
            "Windows Update is waiting to restart this computer, which could end a long "
            "recording. Restart first if you can."
        )

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
    if plan.do_not_disturb and not facts.dnd_available:
        warn(
            "Windows did not let Studio control Do Not Disturb. Turn it on yourself, or "
            "notifications may appear in the recording."
        )
    if plan.show_status_window and plan.screen:
        warn(
            "The Recording status window is left visible to magnifiers and screen sharing, "
            "so it is recorded too if it is inside what you record."
        )
    if not plan.do_not_disturb and plan.screen:
        warn("Do Not Disturb is off, so a notification could appear in the picture.")
    if facts.hotkeys_assigned == 0:
        warn(
            "No system-wide recording keys are assigned. Control the recording from the tray "
            "or the Recording status window, or choose Assign keys."
        )
