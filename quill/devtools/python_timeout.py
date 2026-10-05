"""Stop a Python console command that runs too long (question 38).

``console_python_timeout`` -- "Maximum seconds a Python console command may run
before QUILL interrupts it" -- was drawn in Settings and read by nothing, so
``while True: pass`` typed into the console froze QUILL until it was killed.

The console runs on QUILL's UI thread, on purpose: its commands drive the
editor, and wx may only be touched from that thread. So the command cannot be
moved to a worker and abandoned. Instead a timer raises :class:`ConsoleTimedOut`
*inside* the running command (``PyThreadState_SetAsyncExc``), which is the same
mechanism Ctrl+C uses in an ordinary interpreter.

What that can and cannot stop, said plainly because the label promises it:

* Python code -- a loop, a long calculation -- stops within moments of the limit.
* A command that is waiting inside one long call into the system (a long
  ``time.sleep``, a network read with no timeout) stops when that call returns,
  not before; Python only checks for the interruption between instructions.

``ConsoleTimedOut`` derives from ``BaseException`` so a script's own
``except Exception:`` cannot swallow it and keep running.
"""

from __future__ import annotations

import ctypes
import threading
from collections.abc import Callable


class ConsoleTimedOut(BaseException):  # noqa: N818 - reads as the event it reports
    """Raised inside a console command that ran past the limit."""


def _set_async_exc(thread_id: int, exc: type[BaseException] | None) -> int:
    """Raise *exc* in thread *thread_id* at its next instruction; None clears it."""
    target = ctypes.c_ulong(thread_id)
    if exc is None:
        return int(ctypes.pythonapi.PyThreadState_SetAsyncExc(target, None))
    return int(ctypes.pythonapi.PyThreadState_SetAsyncExc(target, ctypes.py_object(exc)))


def run_with_timeout[T](func: Callable[[], T], seconds: float) -> T:
    """Run *func* on this thread; raise :class:`ConsoleTimedOut` past *seconds*.

    ``seconds <= 0`` means no limit. The timer can only interrupt while *func*
    is still running: completion and the interruption are decided under one
    lock, and any interruption already queued when *func* finishes is cleared,
    so it can never land in whatever the UI thread does next.
    """
    if seconds <= 0:
        return func()
    thread_id = threading.get_ident()
    lock = threading.Lock()
    state = {"done": False, "fired": False}

    def _fire() -> None:
        with lock:
            if state["done"]:
                return
            state["fired"] = True
            _set_async_exc(thread_id, ConsoleTimedOut)

    timer = threading.Timer(seconds, _fire)
    timer.daemon = True
    timer.start()
    try:
        return func()
    finally:
        timer.cancel()
        with lock:
            state["done"] = True
            if state["fired"]:
                # Undelivered (func returned in the same instant): clear it.
                _set_async_exc(thread_id, None)


__all__ = ["ConsoleTimedOut", "run_with_timeout"]
