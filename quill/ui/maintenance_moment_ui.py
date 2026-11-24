"""The wx side of :mod:`quill.core.maintenance_moment` (FUX-15).

:func:`offer_when_quiet` is what an app calls instead of opening an automatic
maintenance window itself. A quiet moment opens it at once; otherwise it is
held, *note* is given the one sentence saying what waits (the app writes it to
its status bar and to the record it already keeps), and a light poll opens it
when the moment is quiet. Nothing is spoken while it waits: the person is
recording, listening or dictating, and speech would land on top of that.

The poll runs every two seconds while something is held, so a short burst of
work between two polls is still seen and still earns its settle. Besides each
app's own probes it asks Windows two things: how long since the last key
press or mouse movement (an offer must never take a keystroke meant for the
document), and whether a menu is open (a timer fires inside the menu loop,
and the window still counts as active there).

One moment per app key. :func:`note_launch` starts the first minute as the
app's window appears; without it the minute counts from the first offer.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable
from typing import Any

from quill.core.maintenance_moment import MaintenanceMoment, Probe

__all__ = [
    "POLL_MS",
    "input_idle_seconds",
    "moment_for",
    "note_launch",
    "offer_when_quiet",
    "reset_for_tests",
    "take_held",
    "window_in_front",
]

#: How often a held offer looks for a quiet moment.
POLL_MS = 2_000

_MOMENTS: dict[str, MaintenanceMoment] = {}
_POLLING: set[str] = set()

Later = Callable[[int, Callable[[], None]], Any]


def moment_for(key: str) -> MaintenanceMoment:
    moment = _MOMENTS.get(key)
    if moment is None:
        moment = _MOMENTS[key] = MaintenanceMoment()
    return moment


def note_launch(key: str) -> None:
    """Start *key*'s first minute now (call it as the app's window appears)."""
    if key not in _MOMENTS:
        _MOMENTS[key] = MaintenanceMoment()


def reset_for_tests() -> None:
    _MOMENTS.clear()
    _POLLING.clear()


def take_held(key: str, kind: str) -> Callable[[], object] | None:
    """The held offer of *kind*, removed, for an explicit command to run now."""
    moment = _MOMENTS.get(key)
    return moment.take(kind) if moment is not None else None


def input_idle_seconds() -> float | None:
    """Seconds since the last keyboard or mouse input, or ``None`` if unknown."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class _LastInput(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        info = _LastInput()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):  # type: ignore[attr-defined]
            return None
        now = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF  # type: ignore[attr-defined]
        return ((now - info.dwTime) & 0xFFFFFFFF) / 1000.0
    except Exception:  # noqa: BLE001 - unknown is not "busy"
        return None


def _menu_open() -> bool:
    """Whether this thread is in a menu (a menu bar or a context menu)."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class _GuiThreadInfo(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("hwndActive", wintypes.HWND),
                ("hwndFocus", wintypes.HWND),
                ("hwndCapture", wintypes.HWND),
                ("hwndMenuOwner", wintypes.HWND),
                ("hwndMoveSize", wintypes.HWND),
                ("hwndCaret", wintypes.HWND),
                ("rcCaret", wintypes.RECT),
            ]

        info = _GuiThreadInfo()
        info.cbSize = ctypes.sizeof(info)
        thread = ctypes.windll.kernel32.GetCurrentThreadId()  # type: ignore[attr-defined]
        if not ctypes.windll.user32.GetGUIThreadInfo(thread, ctypes.byref(info)):  # type: ignore[attr-defined]
            return False
        gui_inmenumode, gui_popupmenumode = 0x4, 0x10
        return bool(info.flags & (gui_inmenumode | gui_popupmenumode))
    except Exception:  # noqa: BLE001
        return False


def window_in_front(window: Any) -> bool:
    """Whether *window*'s top-level window is shown and active, with no menu open.

    An active frame with one of our own modals on it is not active; neither is
    one hidden in the tray. A dead window answers False.
    """
    try:
        top = window.GetTopLevelParent() if hasattr(window, "GetTopLevelParent") else window
        return bool(top.IsShown() and top.IsActive()) and not _menu_open()
    except Exception:  # noqa: BLE001 - destroyed or not a window
        return False


def _alive(window: Any) -> bool:
    try:
        return bool(window) and not getattr(window, "IsBeingDeleted", lambda: False)()
    except Exception:  # noqa: BLE001 - wx raises on a destroyed C++ object
        return False


def _wx_later(delay_ms: int, run: Callable[[], None]) -> Any:
    import wx

    return wx.CallLater(delay_ms, run)


def offer_when_quiet(
    key: str,
    *,
    kind: str,
    label: str,
    run: Callable[[], object],
    route: str,
    window: Any,
    note: Callable[[str], object],
    probes: Iterable[Probe] = (),
    in_front: Callable[[], bool] | None = None,
    idle: Callable[[], float | None] | None = None,
    clear: Callable[[], object] | None = None,
    later: Later | None = None,
) -> bool:
    """Open an automatic maintenance offer now, or hold it until quiet.

    ``True`` when *run* ran now. *window* is the app's top-level window: while
    it is not in front the offer waits, and once it is gone the poll stops.
    *clear* runs as a held offer opens, so the "waits" line is not left in the
    status bar to be read after it has stopped being true.
    """
    probes = tuple(probes)
    front = in_front or (lambda: window_in_front(window))
    quiet_for = idle or input_idle_seconds
    moment = moment_for(key)
    decision = moment.offer(
        kind,
        label,
        run,
        route=route,
        probes=probes,
        in_front=front(),
        input_idle=quiet_for(),
    )
    if decision.run_now:
        run()
        return True
    if decision.line:
        try:
            note(decision.line)
        except Exception:  # noqa: BLE001 - the record is best-effort; the hold is not
            pass
    if key not in _POLLING:
        _POLLING.add(key)
        schedule = later or _wx_later

        def _poll() -> None:
            current = _MOMENTS.get(key)
            if current is None or not current.holding or not _alive(window):
                _POLLING.discard(key)
                return
            due = current.due(probes, in_front=front(), input_idle=quiet_for())
            if due is not None:
                try:
                    if clear is not None:
                        clear()
                    due()
                except Exception:  # noqa: BLE001 - one failed offer must not stop the rest
                    pass
            if current.holding:
                schedule(POLL_MS, _poll)
            else:
                _POLLING.discard(key)

        schedule(POLL_MS, _poll)
    return False
