"""Read-only bounded UIA discovery for screenshot selection; no control invocation.

Uses the same comtypes/UIAutomationCore boundary as external_target and
selection_capture. Password and offscreen controls are excluded before naming.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, replace

from quill.core.studio_capture import CaptureTarget, validate_region
from quill.platform.windows.screen_capture import ScreenCaptureError


@dataclass(frozen=True)
class ScreenshotControl:
    name: str
    role: str
    bounds: tuple[int, int, int, int]
    runtime_id: tuple[int, ...]
    window_handle: int
    process_id: int

    @property
    def label(self):
        return f"{self.role}: {self.name or 'Unnamed control'}"

    def target(self, window: CaptureTarget) -> CaptureTarget:
        return replace(
            window,
            kind="element",
            label=self.label,
            bounds=self.bounds,
            reference_bounds=window.bounds,
            element_id=self.runtime_id,
        )


@contextmanager
def automation():
    import comtypes
    import comtypes.client

    comtypes.CoInitialize()
    try:
        module = comtypes.client.GetModule("UIAutomationCore.dll")
        client = comtypes.client.CreateObject(
            "{ff48dba4-60ef-4201-aa87-54103eef594e}", interface=module.IUIAutomation
        )
        yield client, module
    finally:
        comtypes.CoUninitialize()


def snapshot(element, window: CaptureTarget) -> ScreenshotControl | None:
    try:
        # Fail closed: unreadable privacy/visibility properties do not grant capture.
        if element.CurrentIsPassword or element.CurrentIsOffscreen:
            return None
        if int(element.CurrentProcessId) != window.process_id:
            return None
        rect = element.CurrentBoundingRectangle
        bounds = (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))
        validate_region(bounds, window.bounds)
        runtime_id = tuple(int(v) for v in element.GetRuntimeId())
        if not runtime_id:
            return None
        return ScreenshotControl(
            str(element.CurrentName)[:1000],
            str(element.CurrentLocalizedControlType)[:100],
            bounds,
            runtime_id,
            window.window_handle,
            window.process_id,
        )
    except Exception:
        return None


def controls_for_window(window: CaptureTarget, cancellation_token=None) -> list[ScreenshotControl]:
    from quill.platform.windows.studio_capture import physical_pixels, window_target

    if window.kind != "window":
        raise ValueError("Choose a named window before listing its controls.")
    with physical_pixels(), automation() as (client, _module):
        current = window_target(window.window_handle)
        if (current.process_id, current.bounds) != (window.process_id, window.bounds):
            raise ScreenCaptureError("Window changed. Refresh and select it again.")
        root = client.ElementFromHandle(window.window_handle)
        walker = client.ControlViewWalker
        pending = [root]
        result = []
        deadline = time.monotonic() + 8
        visited = 0
        while pending:
            if cancellation_token is not None:
                cancellation_token.raise_if_cancelled()
            if visited >= 1000 or time.monotonic() >= deadline:
                raise ScreenCaptureError(
                    "Control discovery exceeded its limit. Choose a smaller window."
                )
            element = pending.pop()
            visited += 1
            item = snapshot(element, window)
            if item is not None:
                result.append(item)
            # Do not enumerate password descendants either.
            try:
                if element.CurrentIsPassword:
                    continue
                child = walker.GetFirstChildElement(element)
                children = []
                while child:
                    children.append(child)
                    if len(children) + len(pending) > 1000:
                        raise ScreenCaptureError("Too many controls. Select a smaller window.")
                    child = walker.GetNextSiblingElement(child)
                pending.extend(reversed(children))
            except ScreenCaptureError:
                raise
            except Exception as error:
                raise ScreenCaptureError(
                    "The application stopped exposing its controls."
                ) from error
        return result


def resolve_control(requested: CaptureTarget) -> CaptureTarget:
    from quill.platform.windows.studio_capture import window_target

    current = window_target(requested.window_handle)
    if current.process_id != requested.process_id or current.bounds != requested.reference_bounds:
        raise ScreenCaptureError("The control's window changed. Select the control again.")
    for control in controls_for_window(current):
        if control.runtime_id == requested.element_id:
            if control.bounds != requested.bounds or control.label != requested.label:
                raise ScreenCaptureError("Selected control moved or changed. Select it again.")
            return requested
    raise ScreenCaptureError("Selected control disappeared or is protected/offscreen. No capture.")
