"""Fail-closed Windows target snapshots for external text operations.

The legacy expansion hook has an advisory editable heuristic in
:mod:`text_target`. This module is the stricter path for explicit global text
operations: a target receives mutation capabilities only from positive UIA or
known native-control evidence. Unknown UIA ``Pane`` and ``Custom`` elements
remain unknown.

Windows-only, wx-free.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.expansion.targets import is_denied_target
from quill.core.external_text import (
    CapabilityConfidence,
    CapabilityEvidence,
    TargetFamily,
    TargetSnapshot,
    TargetState,
    TextCapability,
)
from quill.platform.windows.foreground import ForegroundWindow, foreground_window_info
from quill.platform.windows.text_target import (
    focused_class_name,
    is_elevated_window,
    self_is_elevated,
)

__all__ = [
    "UIAElementSnapshot",
    "capture_uia_focus",
    "probe_focused_target",
    "snapshot_from_foreground",
]

_UIA_EDIT_CONTROL_TYPE = 50004
_UIA_DOCUMENT_CONTROL_TYPE = 50030
_UIA_COMBO_BOX_CONTROL_TYPE = 50005
_UIA_PANE_CONTROL_TYPE = 50008
_UIA_CUSTOM_CONTROL_TYPE = 50033

_UIA_VALUE_PATTERN = 10002
_UIA_SELECTION_PATTERN = 10010
_UIA_TEXT_PATTERN = 10014

_EDITABLE_NATIVE_CLASSES = frozenset({
    "edit",
    "richedit",
    "richedit20w",
    "richedit50w",
    "richedit60w",
    "scintilla",
    "consolewindowclass",
    "pseudoconsolewindow",
    "cascadia_hosting_window_class",
})

_KNOWN_UIA_EDIT_TYPES = frozenset({
    _UIA_EDIT_CONTROL_TYPE,
    _UIA_DOCUMENT_CONTROL_TYPE,
    _UIA_COMBO_BOX_CONTROL_TYPE,
})


@dataclass(frozen=True, slots=True)
class UIAElementSnapshot:
    """The bounded UIA facts needed to build a target snapshot."""

    native_window_handle: int = 0
    process_id: int = 0
    automation_id: str = ""
    class_name: str = ""
    control_type: int = 0
    localized_control_type: str = ""
    is_enabled: bool = True
    is_keyboard_focusable: bool = False
    is_password: bool = False
    has_value_pattern: bool = False
    value_is_read_only: bool = False
    has_text_pattern: bool = False
    has_selection_pattern: bool = False
    runtime_id: tuple[int, ...] = ()


def _read_attribute(value: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(value, name)
    except Exception:  # noqa: BLE001
        return default


def _as_text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def _supports_pattern(element: Any, pattern_id: int) -> tuple[bool, Any | None]:
    try:
        pattern = element.GetCurrentPattern(pattern_id)
    except Exception:  # noqa: BLE001
        return False, None
    return pattern is not None, pattern


def _runtime_id(element: Any) -> tuple[int, ...]:
    try:
        values = element.GetRuntimeId()
    except Exception:  # noqa: BLE001
        return ()
    try:
        return tuple(int(value) for value in values or ())
    except (TypeError, ValueError):
        return ()


def capture_uia_focus() -> UIAElementSnapshot | None:
    """Capture bounded metadata for the current UIA-focused element.

    UIA is optional at runtime. Any COM, provider, or property failure becomes
    an absent element and therefore cannot grant mutation capabilities.
    """
    try:
        import comtypes.client  # noqa: PLC0415 - optional Windows dependency

        uia_module = comtypes.client.GetModule("UIAutomationCore.dll")
        automation = comtypes.client.CreateObject(
            "{ff48dba4-60ef-4201-aa87-54103eef594e}",
            interface=uia_module.IUIAutomation,
        )
        element = automation.GetFocusedElement()
        if element is None:
            return None

        has_value, value_pattern = _supports_pattern(element, _UIA_VALUE_PATTERN)
        has_text, _ = _supports_pattern(element, _UIA_TEXT_PATTERN)
        has_selection, _ = _supports_pattern(element, _UIA_SELECTION_PATTERN)
        value_is_read_only = False
        if has_value and value_pattern is not None:
            value_is_read_only = _as_bool(
                _read_attribute(value_pattern, "CurrentIsReadOnly", False)
            )

        return UIAElementSnapshot(
            native_window_handle=_as_int(_read_attribute(element, "CurrentNativeWindowHandle", 0)),
            process_id=_as_int(_read_attribute(element, "CurrentProcessId", 0)),
            automation_id=_as_text(_read_attribute(element, "CurrentAutomationId", "")),
            class_name=_as_text(_read_attribute(element, "CurrentClassName", "")),
            control_type=_as_int(_read_attribute(element, "CurrentControlType", 0)),
            localized_control_type=_as_text(
                _read_attribute(element, "CurrentLocalizedControlType", "")
            ),
            is_enabled=_as_bool(_read_attribute(element, "CurrentIsEnabled", True), True),
            is_keyboard_focusable=_as_bool(
                _read_attribute(element, "CurrentIsKeyboardFocusable", False)
            ),
            is_password=_as_bool(_read_attribute(element, "CurrentIsPassword", False)),
            has_value_pattern=has_value,
            value_is_read_only=value_is_read_only,
            has_text_pattern=has_text,
            has_selection_pattern=has_selection,
            runtime_id=_runtime_id(element),
        )
    except Exception:  # noqa: BLE001
        return None


def _control_identity(element: UIAElementSnapshot | None, control_class: str) -> str:
    if element is not None and element.automation_id:
        return f"automation:{element.automation_id}"
    if element is not None and element.native_window_handle:
        return f"hwnd:{element.native_window_handle}"
    if element is not None and element.runtime_id:
        values = ".".join(str(value) for value in element.runtime_id)
        return f"runtime:{values}"
    if control_class:
        return f"class:{control_class.lower()}"
    return ""


def _target_identity(
    foreground: ForegroundWindow,
    element: UIAElementSnapshot | None,
    control_id: str,
) -> str:
    if not foreground.hwnd and not foreground.process_id:
        return ""
    parts = [str(foreground.hwnd), str(foreground.process_id)]
    if element is not None and element.runtime_id:
        parts.append("runtime:" + ".".join(str(value) for value in element.runtime_id))
    elif control_id:
        parts.append(control_id)
    else:
        parts.append("unknown")
    return "windows:" + ":".join(parts)


def _capability_facts(
    element: UIAElementSnapshot | None,
    control_class: str,
) -> tuple[set[TextCapability], list[CapabilityEvidence], set[str]]:
    capabilities: set[TextCapability] = set()
    evidence: list[CapabilityEvidence] = []
    patterns: set[str] = set()
    native_class = control_class.strip().lower()
    native_editable = native_class in _EDITABLE_NATIVE_CLASSES

    if native_editable:
        capabilities.update({
            TextCapability.INSERT_TEXT,
            TextCapability.EXPAND_TRIGGER,
            TextCapability.PLAIN_TEXT,
        })
        evidence.append(CapabilityEvidence.NATIVE_CLASS)

    if element is None:
        return capabilities, evidence, patterns

    if element.has_value_pattern:
        patterns.add("value")
        evidence.append(CapabilityEvidence.UIA_PATTERN)
        capabilities.add(TextCapability.PLAIN_TEXT)
        if not element.value_is_read_only:
            capabilities.update({
                TextCapability.INSERT_TEXT,
                TextCapability.EXPAND_TRIGGER,
                TextCapability.REPLACE_SELECTION,
            })

    if element.has_text_pattern:
        patterns.add("text")
        evidence.append(CapabilityEvidence.UIA_PATTERN)
        capabilities.update({
            TextCapability.READ_SELECTION,
            TextCapability.READ_CONTEXT,
            TextCapability.PLAIN_TEXT,
        })
        if not element.value_is_read_only:
            capabilities.add(TextCapability.REPLACE_SELECTION)

    if element.has_selection_pattern:
        patterns.add("selection")
        evidence.append(CapabilityEvidence.UIA_PATTERN)
        capabilities.add(TextCapability.READ_SELECTION)

    if (
        element.control_type in _KNOWN_UIA_EDIT_TYPES
        and element.is_keyboard_focusable
        and not element.value_is_read_only
        and element.is_enabled
    ):
        evidence.append(CapabilityEvidence.UIA_CONTROL_TYPE)
        capabilities.update({
            TextCapability.INSERT_TEXT,
            TextCapability.EXPAND_TRIGGER,
            TextCapability.PLAIN_TEXT,
        })

    return capabilities, list(dict.fromkeys(evidence)), patterns


def snapshot_from_foreground(
    foreground: ForegroundWindow,
    *,
    element: UIAElementSnapshot | None = None,
    focused_control_class: str = "",
    target_elevated: bool = False,
    own_process_elevated: bool = False,
    captured_at: float = 0.0,
) -> TargetSnapshot:
    """Build a target snapshot from bounded foreground and UIA facts."""
    control_class = (
        (element.class_name if element is not None else "").strip()
        or focused_control_class.strip()
        or foreground.window_class.strip()
    )
    control_id = _control_identity(element, control_class)
    target_id = _target_identity(foreground, element, control_id)
    process_id = foreground.process_id or (element.process_id if element is not None else 0)
    privilege_match = not target_elevated or own_process_elevated
    capabilities, evidence, patterns = _capability_facts(element, control_class)
    read_only: bool | None = None
    if element is not None and element.value_is_read_only:
        read_only = True
    elif capabilities:
        read_only = False

    base = dict(
        target_id=target_id,
        window_handle=foreground.hwnd,
        process_id=process_id,
        process_name=foreground.process_name,
        window_title=foreground.title,
        control_id=control_id,
        control_class=control_class,
        control_role=(element.localized_control_type if element is not None else ""),
        family=TargetFamily.NATIVE_CONTROL if capabilities else TargetFamily.UNKNOWN,
        read_only=read_only,
        protected=False,
        privilege_match=privilege_match,
        capabilities=frozenset(capabilities),
        evidence=tuple(evidence),
        confidence=(
            CapabilityConfidence.CONFIRMED
            if CapabilityEvidence.UIA_PATTERN in evidence
            else (CapabilityConfidence.ADVISORY if evidence else CapabilityConfidence.UNKNOWN)
        ),
        patterns=frozenset(patterns),
        captured_at=captured_at,
        revision=(
            "uia:" + ".".join(str(value) for value in element.runtime_id)
            if element is not None and element.runtime_id
            else ""
        ),
        adapter_name="windows.external_target",
    )

    if not foreground.hwnd and not foreground.process_id:
        return TargetSnapshot(**base, state=TargetState.UNKNOWN)

    denied = is_denied_target(
        foreground.process_name,
        foreground.title,
        foreground.window_class or control_class,
    )
    if denied:
        return TargetSnapshot(
            **(
                base
                | {
                    "state": TargetState.DENIED,
                    "protected": True,
                    "capabilities": frozenset(),
                }
            )
        )

    if target_elevated and not own_process_elevated:
        return TargetSnapshot(
            **(base | {"state": TargetState.ELEVATED, "capabilities": frozenset()})
        )

    if element is not None and element.is_password:
        return TargetSnapshot(
            **(
                base
                | {
                    "state": TargetState.PROTECTED,
                    "protected": True,
                    "capabilities": frozenset(),
                }
            )
        )

    if element is not None and not element.is_enabled:
        return TargetSnapshot(
            **(base | {"state": TargetState.UNSUPPORTED, "capabilities": frozenset()})
        )

    if read_only:
        return TargetSnapshot(**base, state=TargetState.READ_ONLY)

    if capabilities:
        return TargetSnapshot(**base, state=TargetState.SUPPORTED)

    if element is not None and element.control_type not in {
        0,
        _UIA_PANE_CONTROL_TYPE,
        _UIA_CUSTOM_CONTROL_TYPE,
    }:
        return TargetSnapshot(**base, state=TargetState.UNSUPPORTED)

    return TargetSnapshot(**base, state=TargetState.UNKNOWN)


def probe_focused_target(
    *,
    clock: Callable[[], float] = time.monotonic,
) -> TargetSnapshot:
    """Capture and classify the current foreground text target."""
    foreground = foreground_window_info()
    captured_at = clock()
    if not foreground.hwnd and not foreground.process_id:
        return snapshot_from_foreground(foreground, captured_at=captured_at)

    denied = is_denied_target(
        foreground.process_name,
        foreground.title,
        foreground.window_class,
    )
    target_elevated = is_elevated_window(foreground.hwnd)
    own_process_elevated = self_is_elevated() if target_elevated else False
    if denied or (target_elevated and not own_process_elevated):
        return snapshot_from_foreground(
            foreground,
            target_elevated=target_elevated,
            own_process_elevated=own_process_elevated,
            captured_at=captured_at,
        )

    element = capture_uia_focus()
    return snapshot_from_foreground(
        foreground,
        element=element,
        focused_control_class=focused_class_name(),
        target_elevated=target_elevated,
        own_process_elevated=own_process_elevated,
        captured_at=captured_at,
    )
