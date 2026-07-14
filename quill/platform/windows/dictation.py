from __future__ import annotations

try:  # pragma: no cover - Windows-only runtime hook
    import ctypes
    from ctypes import wintypes
except ImportError:  # pragma: no cover - non-Windows fallback
    ctypes = None  # type: ignore[assignment]
    wintypes = None  # type: ignore[assignment]

VK_LWIN = 0x5B
VK_H = 0x48
KEYEVENTF_KEYUP = 0x0002


def launch_windows_dictation() -> None:
    if ctypes is None or wintypes is None or not hasattr(ctypes, "windll"):
        raise OSError("Windows dictation is only available on Windows")

    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    for key_code, keyup in (
        (VK_LWIN, False),
        (VK_H, False),
        (VK_H, True),
        (VK_LWIN, True),
    ):
        ok = user32.keybd_event(key_code, 0, KEYEVENTF_KEYUP if keyup else 0, 0)
        if ok != 0:
            raise OSError(ctypes.GetLastError(), "Failed to send Windows dictation hotkey")
