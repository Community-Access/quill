"""Named capture targets using existing pywin32/Pillow dependencies.

This module selects exact windows by handle and PID, never silently falling
back to a full desktop. Coordinates are physical desktop pixels. Video will
use a separate capture-session backend; this is the still-image path.
"""

from __future__ import annotations

import ctypes
import os
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

from quill.core.studio_capture import (
    CaptureEvidence,
    CaptureTarget,
    validate_region,
    verify_capture,
)
from quill.platform.windows.screen_capture import ScreenCaptureError, _new_capture_path


@contextmanager
def physical_pixels():
    """Use per-monitor DPI awareness only on this thread; restore it afterward."""
    if os.name != "nt":
        raise ScreenCaptureError("Screen capture is available on Windows only.")
    api = ctypes.windll.user32.SetThreadDpiAwarenessContext
    api.argtypes = [ctypes.c_void_p]
    api.restype = ctypes.c_void_p
    previous = api(ctypes.c_void_p(-4))
    if not previous:
        raise ScreenCaptureError("Could not establish physical-pixel capture coordinates.")
    try:
        yield
    finally:
        api(previous)


def display_targets() -> list[CaptureTarget]:
    import win32api

    targets = []
    for index, (handle, _dc, bounds) in enumerate(win32api.EnumDisplayMonitors(), 1):
        info = win32api.GetMonitorInfo(handle)
        primary = "; primary" if info["Flags"] & 1 else ""
        left, top, right, bottom = bounds
        targets.append(
            CaptureTarget(
                "display",
                f"Display {index}: {info['Device']}; {right - left} by {bottom - top}; "
                f"origin {left}, {top}{primary}",
                tuple(bounds),
                device=info["Device"],
            )
        )
    if not targets:
        raise ScreenCaptureError("No displays are available to capture.")
    return targets


def desktop_target(displays: list[CaptureTarget]) -> CaptureTarget:
    bounds = (
        min(d.bounds[0] for d in displays),
        min(d.bounds[1] for d in displays),
        max(d.bounds[2] for d in displays),
        max(d.bounds[3] for d in displays),
    )
    topology = repr(sorted((d.device, d.bounds) for d in displays))
    return CaptureTarget("desktop", "Full desktop (all displays)", bounds, device=topology)


def window_target(handle: int) -> CaptureTarget:
    import win32gui
    import win32process

    if not win32gui.IsWindow(handle) or not win32gui.IsWindowVisible(handle):
        raise ScreenCaptureError(
            "The selected window is closed or hidden. Refresh the target list."
        )
    if win32gui.IsIconic(handle):
        raise ScreenCaptureError("Restore the selected window before capturing it.")
    title = win32gui.GetWindowText(handle).strip()
    _thread, pid = win32process.GetWindowThreadProcessId(handle)
    application = ""
    try:
        import psutil
    except ImportError:
        pass
    else:
        try:
            application = psutil.Process(pid).name()
        except psutil.Error:
            pass
    bounds = tuple(win32gui.GetWindowRect(handle))
    if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
        raise ScreenCaptureError("The selected window has no capture area.")
    return CaptureTarget(
        "window",
        f"Window: {title or 'Untitled'} ({application or 'application unknown'}); "
        f"process {pid}; id {handle}",
        bounds,
        handle,
        pid,
        application=application,
    )


def list_capture_targets() -> list[CaptureTarget]:
    """Snapshot selectable displays and named, visible, non-minimized windows."""
    with physical_pixels():
        import win32gui

        displays = display_targets()
        windows = []

        def collect(handle, _context):
            if win32gui.IsWindowVisible(handle) and win32gui.GetWindowText(handle).strip():
                try:
                    windows.append(window_target(handle))
                except ScreenCaptureError:
                    pass  # Closed/minimized between EnumWindows and GetWindowRect.

        win32gui.EnumWindows(collect, None)
        return [
            desktop_target(displays),
            *displays,
            *sorted(windows, key=lambda target: target.label.casefold()),
            CaptureTarget("active_window", "Active window after the delay"),
            CaptureTarget(
                "region",
                "Guided region (choose a window or display, then a portion)",
                device=desktop_target(displays).device,
            ),
        ]


def resolve_target(requested: CaptureTarget) -> CaptureTarget:
    import win32gui

    displays = display_targets()
    desktop = desktop_target(displays)
    if requested.kind == "element":
        from quill.platform.windows.screenshot_uia import resolve_control

        return resolve_control(requested)
    if requested.kind == "desktop":
        # Never silently include a newly attached display after user review.
        if requested.bounds != desktop.bounds or requested.device != desktop.device:
            raise ScreenCaptureError(
                "Display layout changed. Refresh and review the capture target."
            )
        return desktop
    if requested.kind == "display":
        current = next((d for d in displays if d.device == requested.device), None)
        if current is None or current.bounds != requested.bounds:
            raise ScreenCaptureError(
                "Selected display changed or disconnected. Refresh the target list."
            )
        return current
    if requested.kind in ("window", "active_window"):
        handle = requested.window_handle
        if requested.kind == "active_window":
            handle = win32gui.GetForegroundWindow()
        current = window_target(handle)
        if requested.kind == "window" and current.process_id != requested.process_id:
            raise ScreenCaptureError("Selected window identity changed. Select it again.")
        if requested.kind == "window" and current.label != requested.label:
            raise ScreenCaptureError(
                "Selected window title or application changed. Select it again."
            )
        return current
    if requested.kind == "region":
        if requested.device != desktop.device:
            raise ScreenCaptureError("Display layout changed. Review the rectangle again.")
        if requested.window_handle:
            reference = window_target(requested.window_handle)
            if (
                reference.process_id != requested.process_id
                or reference.bounds != requested.reference_bounds
            ):
                raise ScreenCaptureError(
                    "The region's source window moved, resized or changed. "
                    "Refresh and review the guided region before capturing again."
                )
        validate_region(requested.bounds, desktop.bounds)
        return requested
    raise ScreenCaptureError("Unsupported capture target. No image was captured.")


def capture_target(folder: Path, requested: CaptureTarget) -> CaptureEvidence:
    from PIL import ImageGrab

    from quill.platform.windows.screenshot_window import render_window

    with physical_pixels():
        target = resolve_target(requested)
        started = datetime.now(UTC).isoformat()
        try:
            if target.kind in {"window", "element"} or (
                target.kind == "region" and target.window_handle
            ):
                image = render_window(target.window_handle)
                backend = "Windows selected-window rendering"
                if target.kind != "window":
                    left, top, right, bottom = target.reference_bounds
                    expected = (right - left, bottom - top)
                    if image.size != expected:
                        raise ScreenCaptureError("Window scale changed. Select the source again.")
                    crop = tuple(
                        value - offset
                        for value, offset in zip(target.bounds, (left, top, left, top), strict=True)
                    )
                    image = image.crop(crop)
                    resolve_target(requested)
                # Reject a handle reassigned to another process during capture.
                if window_target(target.window_handle).process_id != target.process_id:
                    raise ScreenCaptureError("Window changed during capture. Capture again.")
            else:
                image = ImageGrab.grab(
                    bbox=target.bounds, all_screens=True, include_layered_windows=True
                )
                if requested.kind in {"region", "element"} and requested.window_handle:
                    resolve_target(requested)  # Reject source movement during the grab too.
                backend = "Pillow desktop rectangle"
                expected = (
                    target.bounds[2] - target.bounds[0],
                    target.bounds[3] - target.bounds[1],
                )
                if image.size != expected:
                    raise ScreenCaptureError(
                        "Capture dimensions do not match the selected rectangle."
                    )
            destination = _new_capture_path(folder, "studio-capture")
            image.convert("RGB").save(destination, format="PNG")
        except OSError as error:
            raise ScreenCaptureError(f"Could not capture the selected target: {error}") from error
        evidence = verify_capture(destination, target.label)
        metadata = asdict(target)
        metadata.update({
            "backend": backend,
            "coordinate_units": "physical desktop pixels",
            "capture_started_utc": started,
            "scale": "Mixed desktop DPI; window DPI not independently verified",
            "limitations": "Protected/GPU content may be blank; inspect before sharing",
            "uniform_pixels": all(low == high for low, high in image.convert("RGB").getextrema()),
        })
        if target.window_handle:
            dpi = ctypes.windll.user32.GetDpiForWindow(target.window_handle)
            if dpi:
                metadata["window_dpi"] = dpi
                metadata["scale_factor"] = dpi / 96
        return replace(evidence, captured_at=started, metadata=metadata)
