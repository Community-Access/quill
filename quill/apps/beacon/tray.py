"""System tray icon for QuillBeacon (PRD 13.4, 44.3).

A ``wx.TaskBarIcon`` with a keyboard-reachable menu: show/hide the window,
quick capture, sync now, open the status center, and exit. Minimizing to the
tray keeps long-running capture/sync available without a visible window.

The icon owns no business logic; it calls handlers supplied by the shell, so
it stays a thin view. If the platform does not provide a system tray, the
shell simply does not create the icon -- nothing else changes.
"""

from __future__ import annotations

import wx

try:
    import wx.adv  # noqa: F401 -- TaskBarIcon lives here on some builds

    _Base = wx.adv.TaskBarIcon if hasattr(wx.adv, "TaskBarIcon") else wx.TaskBarIcon
except Exception:
    _Base = wx.TaskBarIcon if hasattr(wx, "TaskBarIcon") else object


class TrayIcon(_Base):
    """Tray icon with a menu of the most-used actions."""

    def __init__(self, frame, *, on_capture=None, on_sync_now=None, on_status=None):
        super().__init__()
        self.frame = frame
        self._on_capture = on_capture
        self._on_sync_now = on_sync_now
        self._on_status = on_status
        try:
            bmp = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, wx.ART_MENU, (16, 16))
            self.SetIcon(wx.Icon(bmp), "QuillBeacon")
        except Exception:
            pass  # a missing icon must not prevent the tray menu from working
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self._on_left_click)

    def _on_left_click(self, _e) -> None:
        # Left-click toggles the window, the common expectation.
        if self.frame.IsShown():
            self.frame.Hide()
        else:
            self.frame.Show()
            self.frame.Raise()

    def CreatePopupMenu(self):  # noqa: N802 (wx override)
        menu = wx.Menu()
        show = menu.Append(wx.ID_ANY, "Show/Hide")
        menu.AppendSeparator()
        cap = menu.Append(wx.ID_ANY, "Quick Capture...")
        sync = menu.Append(wx.ID_ANY, "Sync Now")
        status = menu.Append(wx.ID_ANY, "Status Center...")
        menu.AppendSeparator()
        exit_item = menu.Append(wx.ID_ANY, "Exit")
        self.Bind(wx.EVT_MENU, self._on_show_hide, show)
        self.Bind(wx.EVT_MENU, self._on(cap, self._on_capture), cap)
        self.Bind(wx.EVT_MENU, self._on(sync, self._on_sync_now), sync)
        self.Bind(wx.EVT_MENU, self._on(status, self._on_status), status)
        self.Bind(wx.EVT_MENU, lambda _e: self.frame.Close(True), exit_item)
        return menu

    def _on(self, item, handler):
        def _h(_e):
            if handler:
                handler()

        return _h

    def _on_show_hide(self, _e) -> None:
        if self.frame.IsShown():
            self.frame.Hide()
        else:
            self.frame.Show()
            self.frame.Raise()
