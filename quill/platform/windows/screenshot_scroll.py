"""Opt-in scrolling capture through UIA ScrollPattern, never injected keypresses."""

from __future__ import annotations

import time
import uuid
from dataclasses import replace

from quill.core.screenshot_sequences import stitch_vertical
from quill.core.storage import write_json_atomic
from quill.core.studio_capture import save_capture_report
from quill.platform.windows.screenshot_uia import automation, snapshot
from quill.platform.windows.studio_capture import capture_target, physical_pixels, window_target


def _find_scroller(client, module, root, source, token):
    pending = [root]
    deadline = time.monotonic() + 8
    visited = 0
    while pending and visited < 500 and time.monotonic() < deadline:
        token.raise_if_cancelled()
        element = pending.pop()
        visited += 1
        item = snapshot(element, source)
        if item is None:
            continue
        try:
            unknown = element.GetCurrentPattern(10004)
            if unknown:
                pattern = unknown.QueryInterface(module.IUIAutomationScrollPattern)
                if pattern.CurrentVerticallyScrollable:
                    return item, pattern
        except Exception:
            pass  # Not every control implements scrolling.
        child = client.ControlViewWalker.GetFirstChildElement(element)
        siblings = []
        while child:
            siblings.append(child)
            if len(siblings) + len(pending) > 500:
                raise ValueError(
                    "Too many controls. Select a smaller window for scrolling capture."
                )
            child = client.ControlViewWalker.GetNextSiblingElement(child)
        pending.extend(reversed(siblings))
    raise ValueError(
        "This window exposes no supported scrollable area. Use separate screenshots instead."
    )


def capture_scrolling(folder, source, limit, token):
    if source.kind != "window" or not 2 <= limit <= 30:
        raise ValueError("Scrolling capture needs a named window and a 2–30 image limit.")
    captures = []
    folder.mkdir(parents=True, exist_ok=True)
    manifest = folder / ("studio-scrolling-" + uuid.uuid4().hex + ".json")
    result = {"status": "Incomplete", "complete_document": "Not verified", "captures": []}
    with physical_pixels(), automation() as (client, module):
        current = window_target(source.window_handle)
        if (current.process_id, current.bounds) != (source.process_id, source.bounds):
            raise ValueError("Window changed. Select it again before scrolling capture.")
        item, pattern = _find_scroller(
            client, module, client.ElementFromHandle(source.window_handle), source, token
        )
        original = pattern.CurrentVerticalScrollPercent
        viewport = float(pattern.CurrentVerticalViewSize)
        if not 0 < viewport < 100:
            raise ValueError("The application did not provide a usable scroll size.")
        step = max(0.1, 50 * viewport / (100 - viewport))
        percent = 0.0
        try:
            for _index in range(limit):
                token.raise_if_cancelled()
                pattern.SetScrollPercent(-1, percent)
                token.event.wait(0.4)
                token.raise_if_cancelled()
                actual = float(pattern.CurrentVerticalScrollPercent)
                if abs(actual - percent) > 1:
                    raise ValueError("The application did not reach the requested scroll position.")
                target = item.target(source)
                evidence = capture_target(folder, target)
                evidence = replace(
                    evidence, metadata={**evidence.metadata, "scroll_percent": actual}
                )
                save_capture_report(evidence)
                captures.append(evidence)
                result["captures"].append({"path": evidence.path, "sha256": evidence.sha256})
                write_json_atomic(manifest, result)
                if actual >= 99.9:
                    result["reached_scroll_end"] = True
                    break
                percent = min(100.0, percent + step)
            if not result.get("reached_scroll_end"):
                result["warning"] = (
                    "Capture limit reached. Increase the limit or capture smaller sections."
                )
            try:
                combined = stitch_vertical(captures, folder)
                result["combined_path"] = combined.path
                result["status"] = "Joined; content completeness needs review"
            except ValueError as error:
                combined = None
                result["warning"] = str(error)
        except Exception as error:
            result["error"] = str(error)
            raise
        finally:
            try:
                # The existing pattern is tied to the original source, not another window.
                pattern.SetScrollPercent(-1, original)
            except Exception as error:
                result["restore_warning"] = f"Scroll position could not be restored: {error}"
            write_json_atomic(manifest, result)
    if not captures:
        raise ValueError("No scrolling screenshots were captured.")
    return combined or captures[-1], result
