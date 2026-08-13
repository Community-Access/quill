"""Is there somewhere to type, and can we reach it?

Two questions system-wide expansion has to answer before it replaces anything:

- **Is the focused thing editable?** Backspaces sent into a list that is doing
  type-ahead, or a page that treats Backspace as "go back", are worse than a
  missed expansion. This asks UI Automation what has focus and whether it takes
  text.
- **Can we see this window's keys at all?** A normal-privilege process receives
  no keystrokes from an elevated one, so expansion in an administrator window
  silently does nothing. Better to say so once than to look broken.

Both answers are *advisory*. When they cannot be determined -- UI Automation
unavailable, a control that reports nothing useful -- the answer is "probably
yes", because refusing to expand wherever we are unsure would make the feature
unreliable in exactly the places people use it most. The rule that must never
fail open is the credential deny-list, and that one lives in
:mod:`quill.core.expansion.targets`.

Windows-only, wx-free.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging

logger = logging.getLogger(__name__)

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

_TOKEN_QUERY = 0x0008
_TOKEN_ELEVATION = 20  # TokenElevation
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

#: UI Automation control types that take typed text.
_EDITABLE_CONTROL_TYPES: frozenset[int] = frozenset({
    50004,  # UIA_EditControlTypeId
    50030,  # UIA_DocumentControlTypeId
    50005,  # UIA_ComboBoxControlTypeId (editable combos)
    50008,  # UIA_PaneControlTypeId -- browsers report content this way
    50033,  # UIA_CustomControlTypeId -- Electron/Qt often report this
})

#: Window classes that are text surfaces even when automation says nothing.
_EDITABLE_WINDOW_CLASSES: frozenset[str] = frozenset({
    "Edit",
    "RichEdit",
    "RichEdit20W",
    "RichEdit50W",
    "RICHEDIT60W",
    "Scintilla",
    "ConsoleWindowClass",
    "PSEUDOCONSOLEWINDOW",
    "CASCADIA_HOSTING_WINDOW_CLASS",  # Windows Terminal
})


class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("hwndActive", ctypes.wintypes.HWND),
        ("hwndFocus", ctypes.wintypes.HWND),
        ("hwndCapture", ctypes.wintypes.HWND),
        ("hwndMenuOwner", ctypes.wintypes.HWND),
        ("hwndMoveSize", ctypes.wintypes.HWND),
        ("hwndCaret", ctypes.wintypes.HWND),
        ("rcCaret", ctypes.wintypes.RECT),
    ]


def has_text_caret() -> bool:
    """Whether the foreground thread reports a caret -- a classic text cursor.

    Cheap (one API call, no COM) and completely reliable when it says *yes*.
    It says no for most browser and Electron surfaces, which draw their own
    caret, so a negative answer means "ask something else", not "not editable".
    """
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return False
        thread_id = _user32.GetWindowThreadProcessId(hwnd, None)
        info = _GUITHREADINFO()
        info.cbSize = ctypes.sizeof(_GUITHREADINFO)
        if not _user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
            return False
        return bool(info.hwndCaret)
    except Exception:  # noqa: BLE001
        return False


def focused_class_name() -> str:
    """The window class of the focused control, or "" when unknown."""
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return ""
        thread_id = _user32.GetWindowThreadProcessId(hwnd, None)
        info = _GUITHREADINFO()
        info.cbSize = ctypes.sizeof(_GUITHREADINFO)
        if not _user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
            return ""
        target = info.hwndFocus or hwnd
        buf = ctypes.create_unicode_buffer(256)
        _user32.GetClassNameW(target, buf, 256)
        return buf.value
    except Exception:  # noqa: BLE001
        return ""


def uia_focus_is_editable() -> bool | None:
    """Ask UI Automation whether the focused element takes text.

    Returns True, False, or None when UI Automation cannot answer (not
    installed, COM unavailable, or an element that exposes nothing useful).
    None means "no opinion" and the caller should not treat it as a refusal.
    """
    try:
        import comtypes.client  # noqa: PLC0415 - optional, and slow to import
    except Exception:  # noqa: BLE001
        return None
    try:
        automation = comtypes.client.CreateObject(
            "{ff48dba4-60ef-4201-aa87-54103eef594e}",  # CUIAutomation
            interface=comtypes.client.GetModule("UIAutomationCore.dll").IUIAutomation,
        )
        element = automation.GetFocusedElement()
        if element is None:
            return None
        # A read-only value pattern is the clearest possible "no".
        try:
            value_pattern = element.GetCurrentPattern(10002)  # UIA_ValuePatternId
            if value_pattern is not None:
                is_read_only = value_pattern.QueryInterface(
                    comtypes.client.GetModule("UIAutomationCore.dll").IUIAutomationValuePattern
                ).CurrentIsReadOnly
                return not bool(is_read_only)
        except Exception:  # noqa: BLE001
            pass
        control_type = int(element.CurrentControlType)
        if control_type in _EDITABLE_CONTROL_TYPES:
            return True
        return False
    except Exception:  # noqa: BLE001
        return None


def is_editable_target() -> bool:
    """Whether it is safe to erase and retype where the caret is.

    Ordered cheapest-first, and biased towards allowing expansion: a real caret
    or a known text window class is an immediate yes; otherwise UI Automation
    decides; and if it has no opinion, the answer is yes. Someone whose editor
    reports nothing to automation should still get their abbreviations.
    """
    if has_text_caret():
        return True
    if focused_class_name() in _EDITABLE_WINDOW_CLASSES:
        return True
    verdict = uia_focus_is_editable()
    return True if verdict is None else verdict


def is_elevated_window(hwnd: int) -> bool:
    """Whether *hwnd* belongs to an elevated process.

    Used only to explain why expansion is not working there. False whenever the
    answer cannot be read -- an unreadable process is much more likely to be an
    ordinary permissions quirk than a genuine administrator window, and telling
    someone their app is elevated when it is not would send them chasing the
    wrong problem.
    """
    if not hwnd:
        return False
    try:
        pid = ctypes.wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return False
        handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid.value))
        if not handle:
            # Access denied on the process handle itself is the usual symptom
            # of an elevated target for a normal-privilege caller.
            return ctypes.get_last_error() == 5
        try:
            token = ctypes.wintypes.HANDLE()
            if not _kernel32.OpenProcessToken(handle, _TOKEN_QUERY, ctypes.byref(token)):
                return False
            try:
                elevation = ctypes.wintypes.DWORD()
                size = ctypes.wintypes.DWORD()
                ok = ctypes.windll.advapi32.GetTokenInformation(
                    token,
                    _TOKEN_ELEVATION,
                    ctypes.byref(elevation),
                    ctypes.sizeof(elevation),
                    ctypes.byref(size),
                )
                return bool(ok and elevation.value)
            finally:
                _kernel32.CloseHandle(token)
        finally:
            _kernel32.CloseHandle(handle)
    except Exception:  # noqa: BLE001
        return False


def self_is_elevated() -> bool:
    """Whether *this* process is elevated."""
    try:
        token = ctypes.wintypes.HANDLE()
        if not _kernel32.OpenProcessToken(
            _kernel32.GetCurrentProcess(), _TOKEN_QUERY, ctypes.byref(token)
        ):
            return False
        try:
            elevation = ctypes.wintypes.DWORD()
            size = ctypes.wintypes.DWORD()
            ok = ctypes.windll.advapi32.GetTokenInformation(
                token,
                _TOKEN_ELEVATION,
                ctypes.byref(elevation),
                ctypes.sizeof(elevation),
                ctypes.byref(size),
            )
            return bool(ok and elevation.value)
        finally:
            _kernel32.CloseHandle(token)
    except Exception:  # noqa: BLE001
        return False


def unreachable_because_elevated(hwnd: int) -> bool:
    """True when *hwnd* is elevated and we are not -- so its keys never reach us."""
    return is_elevated_window(hwnd) and not self_is_elevated()


#: A window property an application sets on its own top-level window to say
#: "I expand abbreviations myself; do not expand into me." QUILL's editor sets
#: it, because its in-document expansion is strictly better than synthesised
#: keystrokes -- it edits the document directly, keeps undo, fires Quillin
#: events, and needs no keyboard hook at all. Without this marker both paths
#: fire on the same keystroke and the text is mangled.
EXPANSION_OWNER_PROPERTY = "QuillHandlesOwnExpansion"


def claim_own_expansion(hwnd: int) -> None:
    """Mark *hwnd* as handling its own abbreviation expansion.

    A window property rather than a list of executable names: it identifies the
    actual window, so it works for a development run (``python -m quill``), a
    portable build, and a renamed executable alike. Best effort -- failing to
    set it costs a double expansion, not a crash.
    """
    if not hwnd:
        return
    try:
        _user32.SetPropW(int(hwnd), EXPANSION_OWNER_PROPERTY, 1)
    except Exception:  # noqa: BLE001
        pass


def release_own_expansion(hwnd: int) -> None:
    """Remove the marker (on shutdown, so the property does not outlive us)."""
    if not hwnd:
        return
    try:
        _user32.RemovePropW(int(hwnd), EXPANSION_OWNER_PROPERTY)
    except Exception:  # noqa: BLE001
        pass


def window_handles_own_expansion(hwnd: int) -> bool:
    """Whether *hwnd* has claimed its own expansion (see :func:`claim_own_expansion`)."""
    if not hwnd:
        return False
    try:
        return bool(_user32.GetPropW(int(hwnd), EXPANSION_OWNER_PROPERTY))
    except Exception:  # noqa: BLE001
        return False
