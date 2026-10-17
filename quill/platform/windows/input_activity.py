"""When Windows last saw a key or the mouse, from any program: a tick count.

Used by dictation in other programs (D-10,
:mod:`quill.core.windows_dictation.external_edits`) to tell whether the person
has typed or clicked since dictation typed its own words, without reading the
other program's text: ``GetLastInputInfo`` says *when*, never *what*.

Read-only; it sends nothing. ``None`` off Windows or when the call fails, which
the caller treats as "cannot tell".
"""

from __future__ import annotations

import ctypes
import sys

__all__ = ["last_input_tick"]


class _LastInputInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def last_input_tick() -> int | None:
    """Milliseconds since Windows started, at the last keyboard or mouse input."""
    if sys.platform != "win32":
        return None
    try:
        info = _LastInputInfo()
        info.cbSize = ctypes.sizeof(_LastInputInfo)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):  # type: ignore[attr-defined]
            return None
        return int(info.dwTime)
    except Exception:  # noqa: BLE001 - "cannot tell" is the answer
        return None
