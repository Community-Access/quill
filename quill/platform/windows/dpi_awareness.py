"""Declare the process per-monitor DPI aware before the first ``wx.App`` (#1702).

Every QuillVille app runs inside ``pythonw.exe`` from the shared runtime (the
native launcher only starts it), and that executable's manifest does not
declare DPI awareness. Windows therefore drew every app at 96 DPI and
stretched the bitmap on a display scaled to 150 or 200 percent, which blurs
text and focus rectangles -- hardest on the people who scale their display up
to read it. A manifest is not ours to change (the runtime is shared, and a
stamped copy of ``pythonw.exe`` is what antivirus engines flag), so the
declaration is made at run time instead, and it has to happen before any
window exists: once a window is created the process awareness is fixed.

Awareness and fixed pixel sizes have to change together. With the process
aware, a size written in pixels is too small at 200 percent unless it goes
through ``FromDIP`` -- see :mod:`quill.ui.dpi`, and the gate in
``tests/unit/ui/test_dpi_awareness_gate.py`` that keeps both true.

Windows-only and failure-tolerant: on any other platform, on a Windows too old
for the call, or when something earlier already fixed the awareness, this is a
quiet no-op. ``QUILL_DPI_UNAWARE=1`` skips it, the escape hatch for a window
that turns out to draw badly when the process is aware.
"""

from __future__ import annotations

import os
import sys

#: ``DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2`` (Windows 10 1703 and later).
PER_MONITOR_AWARE_V2 = -4
#: ``PROCESS_PER_MONITOR_DPI_AWARE`` for ``shcore.SetProcessDpiAwareness``
#: (Windows 8.1 and later).
PROCESS_PER_MONITOR_DPI_AWARE = 2

#: What the first call did; later calls return it without touching Windows.
_result: str | None = None


def enable_dpi_awareness() -> str:
    """Make this process per-monitor DPI aware; return which call succeeded.

    Returns ``"per-monitor-v2"``, ``"per-monitor"``, ``"system"``,
    ``"disabled"`` (the environment opt-out), ``"unsupported"`` (not Windows)
    or ``"unavailable"`` (every call failed, including when the awareness was
    already fixed by something else). Never raises.
    """
    global _result
    if _result is not None:
        return _result
    _result = _declare()
    return _result


def _declare() -> str:
    if sys.platform != "win32":
        return "unsupported"
    if os.environ.get("QUILL_DPI_UNAWARE", "").strip() == "1":
        return "disabled"
    try:
        import ctypes
    except ImportError:  # pragma: no cover - ctypes is always present on CPython
        return "unavailable"
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        return "unavailable"
    try:
        set_context = windll.user32.SetProcessDpiAwarenessContext
        set_context.restype = ctypes.c_int
        set_context.argtypes = [ctypes.c_void_p]
        if set_context(ctypes.c_void_p(PER_MONITOR_AWARE_V2)):
            return "per-monitor-v2"
    except (AttributeError, OSError):
        pass
    try:
        # S_OK is 0; E_ACCESSDENIED means it was already set, which is fine
        # but not something this call achieved.
        if windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE) == 0:
            return "per-monitor"
    except (AttributeError, OSError):
        pass
    try:
        if windll.user32.SetProcessDPIAware():
            return "system"
    except (AttributeError, OSError):
        pass
    return "unavailable"


def _reset_for_tests() -> None:
    """Forget the first call's result so a test can run the declaration again."""
    global _result
    _result = None
