"""The facts Record a Demonstration's spoken check judges, measured on Windows.

Split from :mod:`quill.platform.windows.screen_recorder` (GATE-11): which
capture backend reaches the chosen display, a trial picture, a brief open of
each sound source, the camera and the folder. The rules that judge these are
in :func:`quill.core.demo_recording.preflight`.
"""

from __future__ import annotations

import ctypes
import subprocess
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path

from quill.core.demo_recording import DemoPlan, PreflightFacts
from quill.core.demo_recording_ffmpeg import Capabilities, trial_grab_command
from quill.platform.windows.demo_audio import probe_source
from quill.platform.windows.demo_media import folder_problem, free_bytes, list_cameras
from quill.stability.safe_subprocess import run_subprocess_safely

_WDA_NONE = 0


class _NoScreen(Exception):  # noqa: N818 - a private control-flow signal, never raised out
    """The screen is not being recorded, so there is no target to check."""


_WDA_EXCLUDEFROMCAPTURE = 0x11


def dxgi_output_index(device_name: str) -> int | None:
    """The ``ddagrab`` ``output_idx`` of display *device_name* on the first adapter.

    FFmpeg's desktop duplication opens the default adapter's outputs in DXGI
    order, which need not be Windows' display numbering, so the two are
    matched by device name (``\\\\.\\DISPLAY2``). ``None`` when the display is
    on another adapter -- the GDI grabber records it instead.
    """
    from quill.platform.windows.face_detect import _GUID, _method, _release

    class _Rect(ctypes.Structure):
        _fields_ = [
            ("l", ctypes.c_long),
            ("t", ctypes.c_long),
            ("r", ctypes.c_long),
            ("b", ctypes.c_long),
        ]

    class _OutputDesc(ctypes.Structure):
        _fields_ = [
            ("DeviceName", ctypes.c_wchar * 32),
            ("Desktop", _Rect),
            ("Attached", ctypes.c_int),
            ("Rotation", ctypes.c_int),
            ("Monitor", ctypes.c_void_p),
        ]

    try:
        create = ctypes.windll.dxgi.CreateDXGIFactory1
    except (AttributeError, OSError):
        return None
    create.argtypes = [ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p)]
    factory = ctypes.c_void_p()
    if create(
        ctypes.byref(_GUID.parse("770aae78-f26f-4dba-a829-253c83d1b387")), ctypes.byref(factory)
    ):
        return None
    adapter = ctypes.c_void_p()
    try:
        if _method(factory, 7, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p))(
            0, ctypes.byref(adapter)
        ):
            return None
    except OSError:
        return None
    finally:
        _release(factory)
    try:
        for index in range(16):
            output = ctypes.c_void_p()
            try:
                _method(adapter, 7, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p))(
                    index, ctypes.byref(output)
                )
            except OSError:
                return None  # DXGI_ERROR_NOT_FOUND: no more outputs
            try:
                desc = _OutputDesc()
                _method(output, 7, ctypes.POINTER(_OutputDesc))(ctypes.byref(desc))
                if desc.DeviceName.casefold() == device_name.casefold():
                    return index
            finally:
                _release(output)
    finally:
        _release(adapter)
    return None


def choose_backend(plan: DemoPlan, caps: Capabilities) -> tuple[DemoPlan, str]:
    """Desktop duplication when it can reach the display, else the GDI grabber."""
    if "ddagrab" in caps.filters and plan.target_kind != "desktop" and plan.display_device:
        index = dxgi_output_index(plan.display_device)
        if index is not None:
            return replace(plan, display_index=index), "ddagrab"
    if "gdigrab" in caps.devices:
        return plan, "gdigrab"
    return plan, ""


def display_for(bounds: tuple[int, int, int, int]) -> tuple[str, tuple[int, int, int, int]]:
    """The display that holds the centre of *bounds*, in physical pixels."""
    from quill.platform.windows.studio_capture import display_targets, physical_pixels

    with physical_pixels():
        displays = display_targets()
    centre_x = (bounds[0] + bounds[2]) // 2
    centre_y = (bounds[1] + bounds[3]) // 2
    for display in displays:
        left, top, right, bottom = display.bounds
        if left <= centre_x < right and top <= centre_y < bottom:
            return display.device, display.bounds
    first = displays[0]
    return first.device, first.bounds


def exclude_from_capture(handles: list[int], exclude: bool) -> None:
    """Keep Studio's own windows out of a display recording (S4)."""
    user32 = ctypes.windll.user32
    for handle in handles:
        try:
            user32.SetWindowDisplayAffinity(
                ctypes.c_void_p(handle), _WDA_EXCLUDEFROMCAPTURE if exclude else _WDA_NONE
            )
        except OSError:
            continue


@dataclass
class CheckContext:
    ffmpeg: str | None
    caps: Capabilities
    hotkeys_assigned: int
    studio_window_handles: list[int] = field(default_factory=list)
    microphone_holder: str = ""
    camera_guidance: str = ""


def gather_facts(plan: DemoPlan, context: CheckContext, scratch: Path) -> PreflightFacts:
    """Measure everything :func:`quill.core.demo_recording.preflight` judges."""
    from quill.core.studio_capture import CaptureTarget
    from quill.platform.windows.studio_capture import (
        desktop_target,
        display_targets,
        physical_pixels,
        resolve_target,
    )

    target_problem = ""
    display_count = 1
    is_studio = False
    try:
        if not plan.screen:
            raise _NoScreen
        with physical_pixels():
            displays = display_targets()
            display_count = len(displays)
            requested = CaptureTarget(
                plan.target_kind,
                plan.target_identity or plan.target_label,
                plan.bounds,
                plan.window_handle,
                plan.process_id,
                device=plan.display_device
                if plan.target_kind == "display"
                else desktop_target(displays).device
                if plan.target_kind == "desktop"
                else "",
                application=plan.application,
            )
            resolve_target(requested)
            if plan.target_kind == "window" and _hung(plan.window_handle):
                target_problem = "The window is not responding."
    except _NoScreen:
        pass
    except Exception as error:  # noqa: BLE001 - every target failure is a spoken Stop
        target_problem = str(error)
    if (
        plan.screen
        and plan.target_kind == "window"
        and plan.window_handle in context.studio_window_handles
    ):
        is_studio = True
    trial_error = ""
    uniform = False
    backend = ""
    if plan.screen and context.ffmpeg and not target_problem:
        plan, backend = choose_backend(plan, context.caps)
        if backend:
            trial_error, uniform = trial_grab(context.ffmpeg, plan, backend, scratch)
    source_errors: dict[str, str] = {}
    silence: list[str] = []
    quiet: list[str] = []
    for source in plan.enabled_sources():
        if source.kind == "microphone" and context.microphone_holder:
            continue  # Opening it would fail; the lock is its own Stop.
        result = probe_source(source, studio_pid=plan.studio_process_id, folder=scratch)
        if result.error:
            source_errors[source.source_id] = result.error
        elif result.digital_silence:
            silence.append(source.source_id)
        elif result.quiet:
            quiet.append(source.source_id)
    camera_error = ""
    if plan.camera.enabled and context.ffmpeg:
        if plan.camera.device not in list_cameras(context.ffmpeg):
            camera_error = f"{plan.camera.device} is not connected"
    folder = Path(plan.folder)
    problem = folder_problem(folder)
    from quill.platform.windows.focus_guard import dnd_state

    return PreflightFacts(
        dnd_available=dnd_state() is not None,
        target_problem=target_problem,
        target_is_studio=is_studio,
        display_count=display_count,
        trial_grab_error=trial_error,
        trial_grab_uniform=uniform,
        source_errors=source_errors,
        digital_silence=tuple(silence),
        quiet=tuple(quiet),
        microphone_holder=context.microphone_holder,
        ffmpeg_found=bool(context.ffmpeg),
        h264_encoder=context.caps.h264_encoder if context.ffmpeg else "",
        video_backend=backend or context.caps.video_backend,
        folder_error=problem,
        free_bytes=-1 if problem else free_bytes(folder),
        hotkeys_assigned=context.hotkeys_assigned,
        camera_error=camera_error,
        camera_guidance=context.camera_guidance,
        studio_process_in_capture=plan.studio_process_id
        in {s.process_id for s in plan.enabled_sources() if s.kind != "system" and s.process_id},
    )


def _hung(handle: int) -> bool:
    try:
        return bool(ctypes.windll.user32.IsHungAppWindow(ctypes.c_void_p(handle)))
    except OSError:
        return False


def trial_grab(ffmpeg: str, plan: DemoPlan, backend: str, scratch: Path) -> tuple[str, bool]:
    """One frame through the real backend: ``(error, every pixel the same colour)``."""
    path = scratch / f"trial-{uuid.uuid4().hex}.png"
    try:
        result = run_subprocess_safely(
            trial_grab_command(ffmpeg, plan, path, backend=backend), timeout_seconds=20
        )
        if result.returncode != 0 or not path.is_file():
            lines = (result.stderr or "").strip().splitlines()
            return (lines[-1] if lines else f"FFmpeg exit code {result.returncode}"), False
        from PIL import Image

        with Image.open(path) as image:
            extrema = image.convert("RGB").getextrema()
        return "", all(low == high for low, high in extrema)
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        return str(error), False
    finally:
        try:
            path.unlink()
        except OSError:
            pass
