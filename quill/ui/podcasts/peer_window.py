"""Cast's peer windows: one contract for every surface that is not a question.

qc.md section 6 and Phase 4 (P9). A *peer* is a modeless ``wx.Frame`` beside
the library rather than a modal dialog in front of it, and every peer behaves
the same way:

* **Made once.** Opening it again raises the one that exists and calls its
  ``refresh()`` -- never a second copy, and its number in the Window menu does
  not move. Closing it hides it.
* **A menu bar** with the window's own menu (Close, Ctrl+W) and, when the host
  keeps one, the shared Window menu, so Ctrl+number and Ctrl+Tab reach it.
* **Escape or Ctrl+W closes it**, says the shared exit announcement, and puts
  focus back on the control that opened it -- the button, the list row, the
  editor -- rather than on the top of the main window.

A window handed to :func:`open_peer` needs only this much:

``frame``
    its ``wx.Frame``, parented to ``host.frame``;
``TITLE`` / ``MENU_TITLE``
    the title the exit announcement says and the label of its own menu
    (``"&Statistics"``);
``focus_target()``
    the control the window is for, focused every time it is shown;
``refresh()`` (optional)
    called when an existing window is raised again;
``menu_rows()`` (optional)
    ``[(label, handler), ...]`` put in its own menu above Close -- Save with
    Ctrl+S, say, since a frame has no default button for Enter to press.

Works for both hosts: QUILL Cast, which has a ``_windows`` manager, and QUILL,
which does not -- there the peer simply has the Close menu and no Window menu.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

__all__ = ["open_peer", "close_peer"]


def _alive(window: Any) -> bool:
    try:
        return window is not None and bool(window)
    except Exception:  # noqa: BLE001 - a destroyed wx object can raise on bool()
        return False


def _inside(control: Any, frame: Any) -> bool:
    """Whether *control* is *frame* or one of its descendants."""
    node = control
    while _alive(node):
        if node is frame:
            return True
        parent = getattr(node, "GetParent", None)
        node = parent() if callable(parent) else None
    return False


def open_peer(
    host: Any,
    key: str,
    factory: Callable[[Any], Any],
    *,
    focus: bool = True,
    opener: Any = None,
) -> Any:
    """Open, or raise and refresh, the peer kept at ``host.<key>``.

    *factory(host)* builds the window the first time. *opener* is the control
    focus returns to on close; by default whatever had focus just now.
    """
    if opener is None:
        try:
            opener = wx.Window.FindFocus()
        except Exception:  # noqa: BLE001 - focus memory is a nicety
            opener = None
    window = getattr(host, key, None)
    if window is None or not _alive(window.frame):
        window = factory(host)
        setattr(host, key, window)
        _install(host, window)
    else:
        refresh = getattr(window, "refresh", None)
        if callable(refresh):
            refresh()
    if _alive(opener) and not _inside(opener, window.frame):
        window._peer_opener = opener
    windows = getattr(host, "_windows", None)
    if windows is not None:
        windows.register(
            window.frame, window.frame.GetTitle() or window.TITLE, focus=window.focus_target
        )
    from quill.ui.dialog_contract import show_modeless_surface

    if window.frame.IsIconized():
        window.frame.Iconize(False)
    show_modeless_surface(window.frame, window.TITLE, announce=getattr(host, "_announce", None))
    window.frame.Raise()
    if focus:
        target = window.focus_target()
        if _alive(target):
            target.SetFocus()
    return window


def close_peer(host: Any, window: Any) -> None:
    """Hide *window*, say so, and give focus back to whoever opened it."""
    window.frame.Hide()
    from quill.ui.dialog_contract import announce_surface_exit

    announce_surface_exit(window.TITLE, getattr(host, "_announce", None))
    opener = getattr(window, "_peer_opener", None)
    if _alive(opener) and opener.IsShownOnScreen():
        top = opener.GetTopLevelParent()
        if _alive(top) and top is not window.frame:
            top.Raise()
        opener.SetFocus()
        wx.CallAfter(_refocus, opener)
        return
    fallback = getattr(host, "_focus_cast_initial_control", None)
    if callable(fallback):
        fallback()
        return
    frame = getattr(host, "frame", None)
    if _alive(frame):
        frame.Raise()
        from quill.ui.dialog_contract import focus_primary_control

        focus_primary_control(frame)


def _refocus(control: Any) -> None:
    # wxMSW hands focus to the newly active window after the hide settles, so
    # the first SetFocus can be overwritten; a second, identical one sticks.
    if _alive(control) and control.IsShownOnScreen():
        control.SetFocus()


def _install(host: Any, window: Any) -> None:
    """The peer's menu bar, Window menu, close and Escape -- once per window."""
    frame = window.frame
    menu_bar = wx.MenuBar()
    own = wx.Menu()
    kept: list[Any] = []
    rows = getattr(window, "menu_rows", None)
    for label, handler in rows() if callable(rows) else ():
        row_id = wx.NewIdRef()
        own.Append(row_id, label)
        frame.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=row_id)
        kept.append(row_id)
    if kept:
        own.AppendSeparator()
    close_id = wx.NewIdRef()
    own.Append(close_id, "&Close\tCtrl+W")
    frame.Bind(wx.EVT_MENU, lambda _e: frame.Close(), id=close_id)
    menu_bar.Append(own, window.MENU_TITLE)
    windows = getattr(host, "_windows", None)
    if windows is not None:
        windows.install(frame, menu_bar)
    frame.SetMenuBar(menu_bar)
    # Held for the window's life: a released NewIdRef hands its id to the next
    # menu built, and both would then answer the same key.
    window._peer_menu_ids = [close_id, *kept]
    keep = getattr(host, "_keep_menu_ids", None)
    if callable(keep):
        keep(close_id, *kept)

    def _on_close(event: Any) -> None:
        if event.CanVeto():
            event.Veto()
            close_peer(host, window)
            return
        if windows is not None:
            windows.unregister(frame)
        event.Skip()

    def _on_char_hook(event: Any) -> None:
        if event.GetKeyCode() == wx.WXK_ESCAPE and not event.HasAnyModifiers():
            frame.Close()
            return
        event.Skip()

    frame.Bind(wx.EVT_CLOSE, _on_close)
    frame.Bind(wx.EVT_CHAR_HOOK, _on_char_hook)
