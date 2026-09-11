"""Apply and remember a main window's size, for every app in the family.

The wx half of :mod:`quill.core.window_geometry`: two calls an app makes once,
and after that its window opens maximized on a fresh machine and opens the way
the user left it on a machine they have used.

    apply_window_geometry(self.frame, "radio", default_size=(460, 360))

is the whole integration. It sizes the frame, maximizes it when the store says
so, and binds the size and close events that keep the store current -- so no app
has to remember to save anything, and no app can half-implement this by applying
geometry it never records.

Two details that are easy to get wrong and both were, once:

**Only record a restored size while the window is not maximized.** A maximized
window's ``GetSize`` is the whole screen. Recording that as the restored size
means un-maximizing gives you a full-screen "restored" window, and the size you
actually chose is gone for good.

**Size events fire during construction and teardown.** Before the frame is shown
its size is whatever wx last set, and while it is closing it may be mid-destroy;
recording either would overwrite a real preference with a transient. So the
handler ignores everything until the frame has been shown once, and stops at the
first close.
"""

from __future__ import annotations

from typing import Any

from quill.core.window_geometry import WindowGeometry, load_geometry, save_geometry

__all__ = [
    "apply_window_geometry",
    "remember_window_geometry",
]

#: Stashed on the frame so the handlers can find their own app id and state
#: without every caller having to keep a reference. One attribute, prefixed,
#: because a wx.Frame is a shared namespace with the app's own mixins.
_STATE_ATTR = "_quill_window_state"


def _data_dir() -> Any:
    from quill.core.paths import app_data_dir

    return app_data_dir()


def apply_window_geometry(
    frame: Any, app_id: str, *, default_size: tuple[int, int] | None = None
) -> WindowGeometry:
    """Open *frame* the way *app_id* was left, maximized by default.

    Returns the geometry applied, which is what a test asserts on. A failure to
    read or apply is swallowed and the frame is left exactly as its own code
    sized it: a window that will not open is a far worse outcome than one that
    opens at the wrong size.
    """
    try:
        geometry = load_geometry(_data_dir(), app_id)
    except Exception:  # noqa: BLE001 - a broken store must not stop the app opening
        geometry = WindowGeometry()
    try:
        fallback = tuple(default_size) if default_size else tuple(frame.GetSize())
        frame.SetSize(geometry.restored_size(fallback))  # type: ignore[arg-type]
        if geometry.maximized:
            frame.Maximize(True)
        _bind_memory(frame, app_id)
    except Exception:  # noqa: BLE001
        pass
    return geometry


def remember_window_geometry(frame: Any, app_id: str) -> None:
    """Write *frame*'s current geometry to the store. Safe to call at any time.

    A failed write is swallowed and *not* reported: this runs on the close path,
    and a read-only profile costs the user the next session's window size, which
    is not worth an error dialog between them and quitting.
    """
    try:
        maximized = bool(frame.IsMaximized())
        geometry = WindowGeometry(maximized=maximized)
        state = getattr(frame, _STATE_ATTR, None)
        if maximized and isinstance(state, dict):
            # Keep the last non-maximized size rather than recording the screen.
            geometry.width, geometry.height = state.get("restored", (0, 0))
        elif not maximized:
            width, height = frame.GetSize()
            geometry.width, geometry.height = int(width), int(height)
        save_geometry(_data_dir(), app_id, geometry)
    except Exception:  # noqa: BLE001 - see the docstring
        pass


def _bind_memory(frame: Any, app_id: str) -> None:
    """Keep the restored size current, and write the store as the frame closes."""
    import wx

    state: dict[str, Any] = {"app_id": app_id, "restored": (0, 0), "live": False}
    setattr(frame, _STATE_ATTR, state)

    def on_show(event: Any) -> None:
        # Nothing before the first Show is a size the user chose.
        state["live"] = True
        event.Skip()

    def on_size(event: Any) -> None:
        try:
            if state["live"] and not frame.IsMaximized():
                width, height = frame.GetSize()
                state["restored"] = (int(width), int(height))
        except RuntimeError:
            pass  # a frame mid-teardown
        event.Skip()

    def on_close(event: Any) -> None:
        if state["live"]:
            state["live"] = False
            remember_window_geometry(frame, app_id)
        event.Skip()

    frame.Bind(wx.EVT_SHOW, on_show)
    frame.Bind(wx.EVT_SIZE, on_size)
    frame.Bind(wx.EVT_CLOSE, on_close)
