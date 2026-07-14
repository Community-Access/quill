"""Speak announcements through Narrator via UI Automation notifications (#966).

Narrator has no scripting bridge the way JAWS and NVDA do (Prism /
accessible_output2 cannot drive it), but since Windows 10 1709 it *listens*:
``UiaRaiseNotificationEvent`` asks the running UIA-based screen reader to
speak a string in its own voice. This module raises that event against one of
QUILL's own top-level windows, wrapped into a UIA provider with
``UiaProviderFromIAccessible`` — no hand-written provider, no new process,
no window.

The chain, all ctypes/comtypes and fully guarded:

1. Find a visible top-level window belonging to this process (the event must
   be raised on an element we own).
2. ``AccessibleObjectFromWindow(OBJID_CLIENT)`` -> the window's ``IAccessible``.
3. ``UiaProviderFromIAccessible`` -> an ``IRawElementProviderSimple`` over it.
4. ``UiaRaiseNotificationEvent(provider, kind, processing, text, activity_id)``.

Used by :mod:`quill.platform.windows.prism_bridge` when the detected reader is
Narrator and no other bridge exists: Narrator then reads QUILL's announcements
in its own One Core voice instead of QUILL either self-voicing over it (the
original #966 double speech) or dropping to the status bar. Every step
degrades to ``False`` so callers fall back safely.

**Needs on-device Narrator verification** (the calls are exercised by unit
tests with fakes; whether Narrator actually voices the notification can only
be judged with Narrator running). wx-free.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes
from typing import Any

logger = logging.getLogger(__name__)

# UiaRaiseNotificationEvent enums (uiautomationcoreapi.h).
_NOTIFICATION_KIND_ACTION_COMPLETED = 2
_NOTIFICATION_KIND_OTHER = 4
_PROCESSING_IMPORTANT_MOST_RECENT = 1
_PROCESSING_MOST_RECENT = 3
# AccessibleObjectFromWindow object id for the client area (winuser.h).
_OBJID_CLIENT = 0xFFFFFFFC

_provider_cache: Any | None = None
_provider_hwnd: int = 0
_unavailable = False  # latched after a hard setup failure; retried per session


def available() -> bool:
    """True when the UIA notification chain can be attempted on this platform."""
    return sys.platform == "win32" and not _unavailable


def reset_for_tests() -> None:
    global _provider_cache, _provider_hwnd, _unavailable
    _provider_cache = None
    _provider_hwnd = 0
    _unavailable = False


def announce(message: str, *, important: bool = False) -> bool:
    """Ask the running UIA screen reader (Narrator) to speak *message*.

    Returns True when the notification was raised (S_OK); False on any
    failure, so the caller can fall back (status bar). ``important``
    interrupts the reader's current utterance (internal-state narration);
    routine announcements queue behind it.
    """
    global _unavailable
    if not message or sys.platform != "win32" or _unavailable:
        return False
    try:
        provider = _own_window_provider()
        if provider is None:
            return False
        uia = ctypes.WinDLL("uiautomationcore", use_last_error=True)
        processing = _PROCESSING_IMPORTANT_MOST_RECENT if important else _PROCESSING_MOST_RECENT
        result = uia.UiaRaiseNotificationEvent(
            provider,
            _NOTIFICATION_KIND_ACTION_COMPLETED if important else _NOTIFICATION_KIND_OTHER,
            processing,
            ctypes.c_wchar_p(message),
            ctypes.c_wchar_p("quill.announce"),
        )
        return int(result) == 0  # S_OK
    except Exception as exc:  # noqa: BLE001 - the channel is best-effort
        logger.debug("Narrator UIA notification failed: %s", exc)
        _unavailable = True
        return False


def _own_window_provider() -> Any | None:
    """A cached ``IRawElementProviderSimple`` over one of our own windows."""
    global _provider_cache, _provider_hwnd
    hwnd = _own_top_level_hwnd()
    if not hwnd:
        return None
    if _provider_cache is not None and hwnd == _provider_hwnd:
        return _provider_cache
    accessible = _accessible_for_hwnd(hwnd)
    if accessible is None:
        return None
    uia = ctypes.WinDLL("uiautomationcore", use_last_error=True)
    provider = ctypes.c_void_p()
    # UIA_PFIA_DEFAULT (0): wrap the IAccessible as-is.
    result = uia.UiaProviderFromIAccessible(accessible, 0, 0, ctypes.byref(provider))
    if int(result) != 0 or not provider.value:
        return None
    # Keep the IAccessible alive alongside the provider it backs.
    _provider_cache = provider
    _provider_hwnd = hwnd
    _accessible_keepalive[hwnd] = accessible
    return provider


_accessible_keepalive: dict[int, Any] = {}


def _accessible_for_hwnd(hwnd: int) -> Any | None:
    """The window's client ``IAccessible`` via oleacc (comtypes-typed)."""
    try:
        import comtypes
        import comtypes.client

        from quill.platform.windows.comtypes_setup import ensure_comtypes_gen_dir_redirected

        ensure_comtypes_gen_dir_redirected()
        oleacc_module = comtypes.client.GetModule("oleacc.dll")
        oleacc = ctypes.WinDLL("oleacc", use_last_error=True)
        pointer = ctypes.POINTER(oleacc_module.IAccessible)()
        result = oleacc.AccessibleObjectFromWindow(
            wintypes.HWND(hwnd),
            wintypes.DWORD(_OBJID_CLIENT),
            ctypes.byref(oleacc_module.IAccessible._iid_),
            ctypes.byref(pointer),
        )
        if int(result) != 0 or not pointer:
            return None
        return pointer
    except Exception as exc:  # noqa: BLE001
        logger.debug("AccessibleObjectFromWindow failed: %s", exc)
        return None


def _own_top_level_hwnd() -> int:
    """A visible top-level window handle owned by this process, or 0."""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        current_pid = kernel32.GetCurrentProcessId()
        found = wintypes.HWND(0)

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def _on_window(hwnd: int, _lparam: int) -> bool:
            pid = wintypes.DWORD(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == current_pid and user32.IsWindowVisible(hwnd):
                found.value = hwnd
                return False  # stop enumerating
            return True

        user32.EnumWindows(_on_window, 0)
        return int(found.value or 0)
    except Exception:  # noqa: BLE001
        return 0


__all__ = ["announce", "available", "reset_for_tests"]
