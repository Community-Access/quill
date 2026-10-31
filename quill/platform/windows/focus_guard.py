"""Keep the computer awake and notifications quiet while Studio records or streams.

Both are must-haves for a long take (Studio roadmap P7): a computer that
sleeps or a toast that slides into the picture can spoil an hour's work.

**Keep awake** uses ``SetThreadExecutionState`` with ``ES_CONTINUOUS``, which
Windows ties to the calling thread, so one small daemon thread holds the
request for exactly as long as the recording and clears it on release. With
the display flag, the screen saver and display-off timers are held off too.

**Do Not Disturb** is Windows' own quiet-hours profile (Focus Assist on
Windows 10, Do not disturb on Windows 11), read and set through the shell's
published notification state (WNF). Microsoft does not document that state,
so every change is read back and reported honestly when it did not take, and
the previous value is written to disk first so a crash cannot leave the
user's notifications switched off: :func:`restore_after_crash` puts it back on
the next launch. Windows-only; on any failure these do nothing and say so.
"""

from __future__ import annotations

import ctypes
import logging
import threading
from ctypes import byref, c_int32, c_uint64, c_ulong
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic

logger = logging.getLogger(__name__)

__all__ = [
    "DoNotDisturb",
    "KeepAwake",
    "dnd_state",
    "restore_after_crash",
]

_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001
_ES_DISPLAY_REQUIRED = 0x00000002
#: WNF_SHEL_QUIETHOURS_ACTIVE_PROFILE_CHANGED: 0 off, 1 priority only, 2 alarms only.
_QUIET_HOURS = 0x0D83063EA3BF1C75
QUIET_OFF, QUIET_PRIORITY, QUIET_ALARMS = 0, 1, 2
_RESTORE_FILE = "studio-dnd-restore.json"


class KeepAwake:
    """Hold off sleep, display-off and the screen saver until :meth:`release`."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._started = threading.Event()
        self.ok = False
        self._thread: threading.Thread | None = None

    def acquire(self) -> bool:
        if self._thread is not None:
            return self.ok
        self._thread = threading.Thread(target=self._hold, daemon=True, name="studio-keep-awake")
        self._thread.start()
        self._started.wait(2.0)
        return self.ok

    def _hold(self) -> None:
        api = ctypes.windll.kernel32.SetThreadExecutionState
        api.restype = ctypes.c_uint32
        flags = _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED | _ES_DISPLAY_REQUIRED
        try:
            self.ok = bool(api(flags))
        except (AttributeError, OSError):
            self.ok = False
        self._started.set()
        self._stop.wait()
        try:
            api(_ES_CONTINUOUS)
        except (AttributeError, OSError):
            pass

    def release(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(2.0)
        self._thread = None


def dnd_state() -> int | None:
    """The quiet-hours profile now (0 off, 1 priority only, 2 alarms only), or None."""
    try:
        state = c_uint64(_QUIET_HOURS)
        stamp = c_ulong(0)
        value = c_int32(-1)
        size = c_ulong(4)
        status = ctypes.windll.ntdll.NtQueryWnfStateData(
            byref(state), None, None, byref(stamp), byref(value), byref(size)
        )
    except (AttributeError, OSError):
        return None
    if status != 0 or size.value != 4 or value.value not in (0, 1, 2):
        return None
    return int(value.value)


def _set_dnd(profile: int) -> bool:
    try:
        state = c_uint64(_QUIET_HOURS)
        value = c_int32(profile)
        status = ctypes.windll.ntdll.NtUpdateWnfStateData(
            byref(state), byref(value), 4, None, None, 0, 0
        )
    except (AttributeError, OSError):
        return False
    return status == 0 and dnd_state() == profile


class DoNotDisturb:
    """Turn quiet hours on for a recording and put back what was there before."""

    def __init__(self, data_dir: Path, *, profile: int = QUIET_PRIORITY) -> None:
        self.data_dir = data_dir
        self.profile = profile
        self.before: int | None = None
        self.active = False

    def start(self) -> str:
        """``""`` when quiet hours are on, else a plain sentence saying why not."""
        before = dnd_state()
        if before is None:
            return "Windows did not let Studio read Do Not Disturb, so it was left as it is."
        self.before = before
        if before != QUIET_OFF:
            return ""  # Already quiet: nothing to change, nothing to restore.
        write_json_atomic(self.data_dir / _RESTORE_FILE, {"before": before})
        if not _set_dnd(self.profile):
            self._forget()
            return "Windows did not turn on Do Not Disturb; notifications may appear."
        self.active = True
        return ""

    def stop(self) -> None:
        if self.active and self.before is not None:
            if not _set_dnd(self.before):
                logger.warning("Could not restore Do Not Disturb to %s", self.before)
        self.active = False
        self._forget()

    def _forget(self) -> None:
        try:
            (self.data_dir / _RESTORE_FILE).unlink()
        except OSError:
            pass


def restore_after_crash(data_dir: Path) -> bool:
    """Put Do Not Disturb back if a recording ended without doing so. True if restored."""
    path = data_dir / _RESTORE_FILE
    if not path.is_file():
        return False
    saved = read_json(path, {})
    before = saved.get("before") if isinstance(saved, dict) else None
    restored = isinstance(before, int) and _set_dnd(before)
    try:
        path.unlink()
    except OSError:
        pass
    return bool(restored)
