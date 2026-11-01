"""Recording Pre-flight Check: QUILL Studio's agent task (codex.md 6.1, Phase 4c).

The person presses Ctrl+3 (AI > Recording Pre-flight Check...) and Enter, and
an agent engine -- My GitHub Copilot or Codex -- checks the set-up with
Studio's own tools and answers with a short checklist in plain words: "The
microphone is the webcam mic, not the USB headset. The captured window is
Settings, not the browser you named."

* ``studio.read_preflight`` -- a read: Record a Demonstration's own check
  (``demo_recording.preflight`` over ``PreflightFacts``, with the screen, sound
  and tool rules of ``demo_recording_rules``), made now on the set-up last
  checked -- or, before any, on the saved settings and the main display -- plus
  the mixer's devices and levels. All text.
* ``studio.preview_still`` -- one picture of what would be recorded, only when
  the connection in use can see. It asks first, naming what is captured; the
  first picture on a connection also asks where pictures go (10B.4); Studio's
  own windows are kept out of a display picture (``exclude_from_capture``),
  and the picture is fitted on this computer before it goes.
* ``studio.open_mixer`` -- the Studio Mixer, Studio's own command, after a yes.

**Never sent:** sound or video. Handlers run on a worker thread, so every
touch of Studio goes through ``ctx.on_ui``; nothing here announces (GATE-13).
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.ai.app_task import AppTaskHost, AppTaskSpec
from quill.core.ai.family_tools import FamilyTool, ToolImage
from quill.core.ai.permissions import PermissionCategory, RiskLevel
from quill.core.ai.tool_gateway import ToolError

__all__ = [
    "INSTRUCTION_HELP",
    "PREFLIGHT",
    "STARTER",
    "mixer_text",
    "studio_preflight_facts",
    "studio_preflight_tools",
]

APP = "studio"

PREFLIGHT = AppTaskSpec(
    app=APP,
    agent_id="studio-preflight",
    title="Recording Pre-flight Check",
    instructions=(
        "You help someone who uses a screen reader get ready to record in QUILL "
        "Studio. Read the set-up with studio_read_preflight first. Compare what "
        "will be recorded with what the person said they want: the window or "
        "display, the microphone and other sound sources, their levels, the "
        "camera and the save folder. If you can, and it would settle a question, "
        "look at one picture with studio_preview_still. Offer studio_open_mixer "
        "only when a device or level needs changing. Answer with a short "
        "checklist in plain words, most important first; say what is fine in one "
        "line at the end."
    ),
    done_words={f"{APP}.open_mixer": "Opened the Studio Mixer"},
    noun="step",
)

STARTER = "Check my set-up before I record, and tell me anything that is wrong."

INSTRUCTION_HELP = (
    "Say what you are about to record, or just press Enter to check your set-up. "
    "The check reads what Record a Demonstration would record, your sound devices "
    "and levels. A picture of the screen is only taken if your AI can see and you "
    "say yes; sound and video never leave this computer. While a task runs, what "
    "you type here goes to it as a follow-up."
)


# --------------------------------------------------------------------------- #
# Reads, as text
# --------------------------------------------------------------------------- #


def mixer_text() -> str:
    """The Studio Mixer's devices and levels, and the programs playing, as text."""
    from quill.platform.windows import audio_routing, audio_sessions

    lines: list[str] = []
    try:
        inputs = audio_routing.list_devices(audio_routing.CAPTURE)
        outputs = audio_routing.list_devices(audio_routing.RENDER)
    except audio_routing.AudioRoutingError as error:
        return f"The sound devices could not be read: {error}"

    def roles(device: Any) -> str:
        found = []
        if device.is_default:
            found.append("the default")
        if device.is_communications:
            found.append("the default for calls")
        return f", {' and '.join(found)}" if found else ""

    lines.append("Recording devices:" if inputs else "Recording devices: none.")
    for device in inputs:
        try:
            level, muted = audio_routing.input_level(device.device_id)
            state = "muted" if muted else f"level {round(level * 100)} percent"
        except audio_routing.AudioRoutingError:
            state = "level unknown"
        lines.append(f"- {device.name}{roles(device)}, {state}.")
    lines.append("Playback devices:" if outputs else "Playback devices: none.")
    lines.extend(f"- {device.name}{roles(device)}." for device in outputs)
    try:
        sessions = audio_sessions.list_sessions()
    except audio_sessions.AudioSessionError:
        sessions = []
    playing = [s for s in sessions if s.process_id != os.getpid()]
    if playing:
        lines.append("Programs with sound:")
        for session in playing:
            heard = "muted" if session.muted else f"{round(session.volume * 100)} percent"
            now = "playing now" if session.peak > 0.001 else "quiet"
            lines.append(f"- {session.name}, {heard}, {now}.")
    return "\n".join(lines)


def _measured_lines(facts: Any) -> list[str]:
    from quill.ui.audio_studio.studio_ai_features import _measured

    return [f"{name}: {value}." for name, value in _measured(facts).items()]


def _saved_plan(host: Any) -> Any:
    """The saved Record a Demonstration settings, on the main display (no check yet)."""
    from quill.core.demo_recording_session import plan_from_dict
    from quill.platform.windows.studio_capture import display_targets, physical_pixels

    with physical_pixels():
        displays = display_targets()
    main = next((d for d in displays if "; primary" in d.label), displays[0])
    saved = dict(host._demo_preferences())
    data = {
        **saved,
        "target_kind": "display",
        "target_label": main.friendly_label,
        "target_identity": main.label,
        "bounds": main.bounds,
        "display_bounds": main.bounds,
        "display_device": main.device,
        "folder": str(saved.get("folder") or host._demo_default_folder()),
        "studio_process_id": os.getpid(),
    }
    return plan_from_dict(data)


def _check_inputs(host: Any) -> tuple[Any, Any, str] | str:
    """On the UI thread: the plan, the check's context and what it is; or why not."""
    ffmpeg = host._demo_ffmpeg()
    if not ffmpeg:
        return (
            "FFmpeg was not found, so Studio cannot record or check a recording until "
            "it is. The fix is Voices, Get FFmpeg."
        )
    caps = host._demo_caps(ffmpeg)
    plan = getattr(host, "_studio_last_plan", None)
    where = "the set-up you last checked in Record a Demonstration"
    if plan is None:
        try:
            plan = _saved_plan(host)
        except Exception as error:  # noqa: BLE001 - said, never raised
            return (
                f"No set-up has been checked yet, and the saved settings could not be read: {error}"
            )
        where = (
            "your saved Record a Demonstration settings on the main display, because no "
            "set-up has been checked yet; the person may mean another window or display"
        )
    return plan, host._demo_check_context(plan, ffmpeg, caps), where


def run_check(host: Any, ctx: AppTaskHost) -> str:
    """Record a Demonstration's own pre-flight check, made now, as text."""
    from quill.core.demo_recording import preflight, summary

    prepared = ctx.on_ui(lambda: _check_inputs(host), "The task was stopped.")
    if isinstance(prepared, str):
        return prepared
    plan, context, where = prepared
    from quill.platform.windows.screen_recorder_check import gather_facts

    scratch = Path(tempfile.mkdtemp(prefix="studio-ai-check-"))
    try:
        facts = gather_facts(plan, context, scratch)
    except Exception as error:  # noqa: BLE001 - said, never raised
        return f"The check could not run: {error}"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    findings = preflight(plan, facts)
    lines = [f"Checked now, on {where}:", summary(plan, findings)]
    measured = _measured_lines(facts)
    if measured:
        lines += ["What was measured:", *measured]
    return "\n".join(lines)


def _capture_target(host: Any) -> Any:
    """What a recording would capture now: the plan's target, or the main display."""
    from quill.core.studio_capture import CaptureTarget

    plan = getattr(host, "_studio_last_plan", None)
    if plan is not None and plan.screen:
        return CaptureTarget(
            plan.target_kind,
            plan.target_identity or plan.target_label,
            plan.bounds,
            plan.window_handle,
            plan.process_id,
            device=plan.display_device,
            application=plan.application,
        )
    from quill.platform.windows.studio_capture import display_targets, physical_pixels

    with physical_pixels():
        displays = display_targets()
    return next((d for d in displays if "; primary" in d.label), displays[0])


def _grab(host: Any, ctx: AppTaskHost, target: Any) -> bytes:
    """One picture of *target*, with Studio's windows kept out of a display picture."""
    from quill.platform.windows.studio_capture import capture_target

    whole_screen = target.kind in ("display", "desktop", "region")
    if whole_screen:
        ctx.on_ui(lambda: host._exclude_studio_windows(True), None)
    scratch = Path(tempfile.mkdtemp(prefix="studio-ai-still-"))
    try:
        evidence = capture_target(scratch, target)
        return Path(evidence.path).read_bytes()
    finally:
        if whole_screen:
            ctx.on_ui(lambda: host._exclude_studio_windows(False), None)
        shutil.rmtree(scratch, ignore_errors=True)


def studio_preflight_facts(host: Any) -> str:
    """What is on hand, as text, sent with the first instruction."""
    lines: list[str] = []
    last = getattr(host, "_studio_last_check", None)
    if last:
        first = str(last[0]).splitlines()[0] if str(last[0]).strip() else ""
        lines.append(f"Last check this session: {first}" if first else "A check was made.")
    else:
        lines.append("No pre-flight check has been made this session.")
    recorder = getattr(host, "_demo", None)
    if recorder is not None:
        lines.append("A recording is running now.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# The tools
# --------------------------------------------------------------------------- #


def _connection(host: Any) -> tuple[str, bool]:
    """The connection in use and whether it can see (UI thread)."""
    from quill.core.ai.connection_caps import PICTURES

    service = host._ai_service()
    can_do = getattr(service, "can_do", None)
    return str(getattr(service, "connection_in_use", "") or ""), bool(
        callable(can_do) and can_do(PICTURES)
    )


def studio_preflight_tools(
    host: Any,
    ctx: AppTaskHost,
    *,
    check: Callable[[], str] | None = None,
    mixer: Callable[[], str] | None = None,
    grab: Callable[[Any], bytes] | None = None,
) -> list[FamilyTool]:
    """Studio's pre-flight tools for one task. The keywords replace the machine (tests)."""
    from quill.core.ai.connection_caps import CONNECTION_NAMES

    check_now = check or (lambda: run_check(host, ctx))
    read_mixer = mixer or (lambda: str(ctx.on_ui(mixer_text, "") or ""))
    take = grab or (lambda target: _grab(host, ctx, target))
    connection, can_see = ctx.on_ui(lambda: _connection(host), ("", False)) or ("", False)
    company = CONNECTION_NAMES.get(connection, "your AI")

    def read_preflight(_args: dict[str, Any]) -> str:
        parts = [check_now().strip()]
        devices = read_mixer().strip()
        if devices:
            parts += ["", "The Studio Mixer now:", devices]
        return "\n".join(p for p in parts if p is not None)

    def target_label() -> str:
        try:
            target = ctx.on_ui(lambda: _capture_target(host), None)
        except Exception:  # noqa: BLE001 - the question still asks
            target = None
        return str(getattr(target, "friendly_label", "") or "the main display")

    def preview_still(_args: dict[str, Any]) -> ToolImage:
        from quill.core.ai.picture_prep import PicturePrepError, fit_image, longest_side_for
        from quill.ui.hosted_ai_picture_consent import ask_picture_consent

        if not ctx.on_ui(lambda: ask_picture_consent(host, connection), False):
            raise ToolError("The person has not agreed to send pictures on this connection.")
        target = ctx.on_ui(lambda: _capture_target(host), None)
        if target is None:
            raise ToolError("There is nothing to take a picture of.")
        try:
            data = take(target)
            prepared = fit_image(data, longest_side_for(connection))
        except (OSError, PicturePrepError) as error:
            raise ToolError(f"The picture could not be taken: {error}") from error
        except ToolError:
            raise
        except Exception as error:  # noqa: BLE001 - a capture failure is a sentence
            raise ToolError(f"The picture could not be taken: {error}") from error
        return ToolImage(
            prepared.data,
            prepared.mime,
            description=f"One picture of {target.friendly_label}, as a recording shows it now.",
        )

    def open_mixer(_args: dict[str, Any]) -> str:
        done = ctx.on_ui(lambda: host.open_mixer() or True, False)
        if not done:
            raise ToolError("The Studio Mixer could not be opened.")
        devices = read_mixer().strip()
        said = "The person opened the Studio Mixer and has closed it."
        return f"{said}\nThe Studio Mixer now:\n{devices}" if devices else said

    tools = [
        FamilyTool(
            name=f"{APP}.read_preflight",
            description=(
                "Run Record a Demonstration's pre-flight check now and read it as text: "
                "what will be recorded, every Stop and Warn, what was measured, and the "
                "Studio Mixer's devices and levels."
            ),
            handler=read_preflight,
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
    ]
    if can_see:
        tools.append(
            FamilyTool(
                name=f"{APP}.preview_still",
                description=(
                    "Look at one picture of what a recording would capture now. Asks "
                    "the person first, because the picture leaves this computer."
                ),
                handler=preview_still,
                category=PermissionCategory.CAPTURE_SCREEN,
                risk=RiskLevel.MEDIUM,
                app=APP,
                summarize=lambda _a: (
                    f"Take one picture of {target_label()} and send it to {company}."
                ),
            )
        )
    tools.append(
        FamilyTool(
            name=f"{APP}.open_mixer",
            description=(
                "Open the Studio Mixer so the person can change a device or a level "
                "themselves. Asks first."
            ),
            handler=open_mixer,
            category=PermissionCategory.MODIFY_SELECTION,
            risk=RiskLevel.MEDIUM,
            app=APP,
            mutating=True,
            summarize=lambda _a: (
                "Open the Studio Mixer, where you can change sound devices and levels yourself."
            ),
        )
    )
    return tools
