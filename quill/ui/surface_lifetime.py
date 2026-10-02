"""One lifetime token per window, invalidated when the window is destroyed (F-02).

``TaskManager.submit(..., ui_lifetime=token)`` suppresses a task's success,
failure and progress delivery once the token is invalidated. The shared guard
existed (84de01d); what was missing was adoption. A dialog that started a search
and was closed before the answer arrived still had the answer delivered --
into controls that were gone (a logged ``RuntimeError``, at best) or as an
announcement about a window the listener had already left.

:func:`lifetime_for` gives a window one token, created on first use and
invalidated by that window's own ``EVT_WINDOW_DESTROY``. Every task a window
starts passes it, and nothing it started can speak or touch a control after the
window is gone. The worker still runs to completion and its result is still
retained by the task manager; only the UI delivery is dropped, which is exactly
the contract ``UiLifetimeToken`` documents.

A window that is hidden rather than destroyed (a peer window reused across
openings) keeps its token alive, deliberately: its controls still exist.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.stability.task_manager import UiLifetimeToken

__all__ = ["SurfaceTasks", "lifetime_for", "surface_tasks"]


class SurfaceTasks:
    """A window's view of the app's task manager: every task it starts is tied
    to the window's lifetime.

    Adoption is one line per surface -- ``self._task_manager =
    SurfaceTasks(task_manager, lambda: self.dialog)`` -- rather than a keyword
    at every call, so a call added later cannot forget it. *window* is a getter
    because a surface usually stores its task manager before it builds its
    window; the token is looked up when a task is submitted, by which time the
    window exists. Everything other than ``submit`` passes straight through.
    """

    def __init__(self, manager: Any, window: Callable[[], Any]) -> None:
        self._manager = manager
        self._window = window

    def submit(self, name: str, func: Callable[..., Any], **kwargs: Any) -> Any:
        window = self._window()
        if window is not None:
            if "ui_lifetime" not in kwargs:
                kwargs["ui_lifetime"] = lifetime_for(window)
            # A top-level window is destroyed at the next idle after Destroy(),
            # and EVT_WINDOW_DESTROY only fires then; a result arriving in that
            # gap would still be delivered. So each callback also checks, at
            # delivery, that the window has not started going.
            for key in ("on_success", "on_failure", "on_progress"):
                callback = kwargs.get(key)
                if callback is not None:
                    kwargs[key] = _while_alive(window, callback)
        return self._manager.submit(name, func, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._manager, name)

    def __bool__(self) -> bool:
        return self._manager is not None


def window_is_going(window: Any) -> bool:
    """True once *window* is destroyed or queued for destruction."""
    try:
        if not window:
            return True
        being_deleted = getattr(window, "IsBeingDeleted", None)
        if callable(being_deleted) and being_deleted():
            return True
        # Destroy() on a top-level window only schedules it: the app knows.
        import wx

        app = wx.GetApp()
        scheduled = getattr(app, "IsScheduledForDestruction", None)
        try:
            return bool(callable(scheduled) and scheduled(window))
        except TypeError:
            return False  # not a wx object (a test's stand-in): nothing to ask
    except RuntimeError:
        return True


def _while_alive(window: Any, callback: Callable[..., Any]) -> Callable[..., Any]:
    def guarded(*args: Any) -> Any:
        if window_is_going(window):
            return None
        return callback(*args)

    return guarded


def surface_tasks(manager: Any, window: Callable[[], Any]) -> Any:
    """*manager* wrapped for a window, or ``None`` when there is no manager.

    ``None`` stays ``None`` so the ``host._task_manager is None`` checks the
    surfaces already make keep meaning "no background work here".
    """
    if manager is None:
        return None
    return SurfaceTasks(manager, window)


_ATTR = "_quill_ui_lifetime"


def lifetime_for(window: Any) -> UiLifetimeToken:
    """The token for *window*, invalidated when *window* is destroyed."""
    token = getattr(window, _ATTR, None)
    if isinstance(token, UiLifetimeToken):
        return token
    token = UiLifetimeToken()
    try:
        setattr(window, _ATTR, token)
    except Exception:  # noqa: BLE001 - a window that refuses attributes still gets a token
        return token
    try:
        import wx

        def on_destroy(event: Any) -> None:
            # Children are destroyed too and send their own events up; only the
            # window's own destruction ends its lifetime.
            if event.GetEventObject() is window:
                token.invalidate()
            event.Skip()

        window.Bind(wx.EVT_WINDOW_DESTROY, on_destroy)
    except Exception:  # noqa: BLE001 - a fake window in a test has no events
        pass
    return token
