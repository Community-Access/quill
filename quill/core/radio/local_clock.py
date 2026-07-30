"""OS-live local wall-clock time for recording timestamps (#1223).

Recording filenames were stamped with ``datetime.now()``, whose local timezone
the C runtime resolves once at process start and then caches -- Windows has no
``time.tzset()`` to refresh it. A long-running Quill (or a scheduled recording
firing hours later) kept stamping the *launch-time* zone, so a user who changed
the computer's timezone saw filenames "stuck" in the old zone. ``GetLocalTime``
reads the OS's live local time with no such caching, so a zone change (or a DST
rollover) shows up without a restart.
"""

from __future__ import annotations

import os
from datetime import datetime


def local_now() -> datetime:
    """Current local wall-clock time, re-read from the OS each call.

    On Windows this reads ``GetLocalTime`` (no cached timezone); everywhere
    else -- and on any failure -- it falls back to ``datetime.now()``. The
    result is naive local, as :func:`build_filename`'s ``strftime`` expects.
    """
    if os.name != "nt":
        return datetime.now()
    try:
        import ctypes
        from ctypes import wintypes

        class _SYSTEMTIME(ctypes.Structure):
            _fields_ = [
                ("wYear", wintypes.WORD),
                ("wMonth", wintypes.WORD),
                ("wDayOfWeek", wintypes.WORD),
                ("wDay", wintypes.WORD),
                ("wHour", wintypes.WORD),
                ("wMinute", wintypes.WORD),
                ("wSecond", wintypes.WORD),
                ("wMilliseconds", wintypes.WORD),
            ]

        st = _SYSTEMTIME()
        ctypes.windll.kernel32.GetLocalTime(ctypes.byref(st))  # type: ignore[attr-defined]
        return datetime(st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond)
    except Exception:  # noqa: BLE001 - any failure falls back to the stdlib clock
        return datetime.now()
