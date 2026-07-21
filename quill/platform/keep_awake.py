"""Keep the machine awake while audio is playing or recording.

Internet radio and scheduled recordings are long-running background audio: if
Windows drops into system standby the stream stops and a recording is cut off.
This asks the OS to keep the *system* awake (the display is still allowed to
sleep) for as long as playback or a recording is active, and to release that
request the moment nothing is going on.

Windows only -- via ``SetThreadExecutionState``. On macOS/Linux this is a no-op
that reports ``False`` (upstream QUILL covers those platforms, where the tray
long-run pattern does not apply); a caller treats a ``False`` return as "the OS
was not asked" and simply carries on.
"""

from __future__ import annotations

import sys

# SetThreadExecutionState flags (winbase.h). ES_CONTINUOUS makes the request
# persist until the next call on this thread; ES_SYSTEM_REQUIRED forbids system
# standby. We deliberately omit ES_DISPLAY_REQUIRED so the screen may still
# blank -- only audio needs the machine awake.
_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001


def set_keep_awake(active: bool) -> bool:
    """Inhibit system standby while *active* is True; release it when False.

    Returns True when the request was applied (Windows), False on other
    platforms or if the call failed. The state is thread-persistent, so call
    this from the UI thread that lives for the app's lifetime.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        flags = _ES_CONTINUOUS | (_ES_SYSTEM_REQUIRED if active else 0)
        # A zero return means the call failed (e.g. an unexpected flag).
        state = ctypes.windll.kernel32.SetThreadExecutionState(flags)  # type: ignore[attr-defined]
        return bool(state != 0)
    except Exception:  # noqa: BLE001 - keep-awake is best-effort, never fatal
        return False
