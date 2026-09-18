"""Bounded UI Automation selection capture for external text operations.

The reader asks only the currently focused UIA element for its selection. It
never selects all, reads a document range, or stores a clipboard history. Any
provider or identity failure returns ``None`` so callers can refuse mutation.

Windows-only, wx-free.
"""

from __future__ import annotations

from typing import Any

from quill.core.external_text import SelectionSnapshot, TargetSnapshot

__all__ = ["capture_uia_selection"]

_UIA_TEXT_PATTERN = 10014
_MAX_SELECTION_CHARACTERS = 4096


def capture_uia_selection(
    target: TargetSnapshot,
    *,
    max_characters: int = _MAX_SELECTION_CHARACTERS,
) -> SelectionSnapshot | None:
    """Capture bounded selected text from the current UIA-focused element."""
    try:
        import comtypes.client  # noqa: PLC0415 - optional Windows dependency

        uia_module = comtypes.client.GetModule("UIAutomationCore.dll")
        automation = comtypes.client.CreateObject(
            "{ff48dba4-60ef-4201-aa87-54103eef594e}",
            interface=uia_module.IUIAutomation,
        )
        element = automation.GetFocusedElement()
        if element is None or not _belongs_to_target(element, target):
            return None
        pattern = element.GetCurrentPattern(_UIA_TEXT_PATTERN)
        if pattern is None:
            return None
        ranges = pattern.GetSelection()
        if ranges is None or int(ranges.Length) < 1:
            return None
        text_range = ranges.GetElement(0)
        if text_range is None:
            return None
        limit = max(0, int(max_characters))
        selected_text = str(text_range.GetText(limit))
        revision = _runtime_revision(element)
        return SelectionSnapshot(
            source_target=target,
            selected_text=selected_text,
            revision=revision,
        )
    except Exception:  # noqa: BLE001
        return None


def _belongs_to_target(element: Any, target: TargetSnapshot) -> bool:
    native_handle = _as_int(_attribute(element, "CurrentNativeWindowHandle", 0))
    process_id = _as_int(_attribute(element, "CurrentProcessId", 0))
    if target.window_handle and native_handle and target.window_handle != native_handle:
        return False
    if target.process_id and process_id and target.process_id != process_id:
        return False
    automation_id = _as_text(_attribute(element, "CurrentAutomationId", ""))
    if target.control_id.startswith("automation:"):
        return target.control_id == "automation:" + automation_id
    return True


def _runtime_revision(element: Any) -> str:
    try:
        values = element.GetRuntimeId()
        return "uia:" + ".".join(str(int(value)) for value in values or ())
    except Exception:  # noqa: BLE001
        return ""


def _attribute(value: Any, name: str, default: Any) -> Any:
    try:
        return getattr(value, name)
    except Exception:  # noqa: BLE001
        return default


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_text(value: Any) -> str:
    return value if isinstance(value, str) else ""
