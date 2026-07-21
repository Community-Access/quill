"""wx window manager: the shared "&Window" menu + numbered window traversal.

Wraps the pure :class:`quill.ui.window_manager.WindowRegistry` with the wx side
-- a key->frame map, the dynamic "&Window" menu, the industry-standard
Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+1..9 accelerators, and raise/focus -- so every
family window (the main window and each modeless surface) shares one numbered
list of open windows.

One :class:`WindowManager` per app. A frame:
  1. ``register(frame, title)`` when it opens, ``unregister(frame)`` when it closes;
  2. ``install(frame, menu_bar)`` while building its menu bar (appends "&Window"
     and installs the accelerator table).

The selection logic (which window a shortcut targets) lives in the pure registry
and is unit-tested; the wx calls (Raise/Show/SetFocus, menu/accelerator objects)
are thin and validated in the running app.
"""

from __future__ import annotations

from typing import Any

from quill.ui.window_manager import WindowRegistry


class WindowManager:
    """Shared, per-app registry of open windows with numbered wx traversal."""

    def __init__(self, wx: Any) -> None:
        self._wx = wx
        self._registry = WindowRegistry()
        self._frames: dict[str, Any] = {}
        # Stable command ids for the accelerators (created once, reused on every
        # frame's table + menu). Ctrl+Tab / Ctrl+Shift+Tab + Ctrl+1..9.
        self._next_id = wx.NewIdRef()
        self._prev_id = wx.NewIdRef()
        self._num_ids = [wx.NewIdRef() for _ in range(9)]

    # -- identity ----------------------------------------------------------------

    @staticmethod
    def key_for(frame: Any) -> str:
        """This frame's stable registry key (its wx window id as a string)."""
        return str(frame.GetId())

    # -- membership --------------------------------------------------------------

    def register(self, frame: Any, title: str) -> None:
        """Add (or refresh the title of) *frame* in the shared window list."""
        key = self.key_for(frame)
        self._frames[key] = frame
        self._registry.register(key, title)

    def unregister(self, frame: Any) -> None:
        """Drop *frame* from the shared window list (on close)."""
        key = self.key_for(frame)
        self._frames.pop(key, None)
        self._registry.unregister(key)

    def __len__(self) -> int:
        return len(self._registry)

    # -- navigation (pure selection -> thin wx activation) -----------------------

    def activate(self, key: str) -> Any:
        """Raise, show, and focus the window with *key*; returns it (or None)."""
        frame = self._frames.get(key)
        if frame is None:
            return None
        for method in ("Show", "Raise", "SetFocus"):
            call = getattr(frame, method, None)
            if callable(call):
                try:
                    call()
                except Exception:  # noqa: BLE001 - a dying window must not crash traversal
                    return None
        return frame

    def activate_next(self, frame: Any) -> Any:
        """Cycle to the window after *frame* (Ctrl+Tab)."""
        target = self._registry.next(self.key_for(frame))
        return self.activate(target) if target else None

    def activate_previous(self, frame: Any) -> Any:
        """Cycle to the window before *frame* (Ctrl+Shift+Tab)."""
        target = self._registry.previous(self.key_for(frame))
        return self.activate(target) if target else None

    def activate_number(self, number: int) -> Any:
        """Jump to the *number*-th window (Ctrl+<number>)."""
        target = self._registry.by_number(number)
        return self.activate(target) if target else None

    def previous_key(self, frame: Any) -> str | None:
        """The window to fall back to when *frame* closes (or None)."""
        return self._registry.previous(self.key_for(frame))

    # -- wx wiring ---------------------------------------------------------------

    def install(self, frame: Any, menu_bar: Any) -> None:
        """Append the "&Window" menu to *menu_bar* and install the accelerators
        on *frame*. Rebinds the Window menu just-in-time on open so it always
        reflects the currently-open windows."""
        wx = self._wx
        window_menu = wx.Menu()
        menu_bar.Append(window_menu, "&Window")
        self._bind_accelerators(frame)
        # Rebuild the Window menu each time it opens (windows come and go).
        frame.Bind(
            wx.EVT_MENU_OPEN,
            lambda event, f=frame: self._on_menu_open(event, f),
        )

    def _bind_accelerators(self, frame: Any) -> None:
        wx = self._wx
        entries = [
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_TAB, int(self._next_id)),
            wx.AcceleratorEntry(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, wx.WXK_TAB, int(self._prev_id)),
        ]
        for index, num_id in enumerate(self._num_ids):
            entries.append(wx.AcceleratorEntry(wx.ACCEL_CTRL, ord("1") + index, int(num_id)))
        frame.SetAcceleratorTable(wx.AcceleratorTable(entries))
        nxt, prv = int(self._next_id), int(self._prev_id)
        frame.Bind(wx.EVT_MENU, lambda _e, f=frame: self.activate_next(f), id=nxt)
        frame.Bind(wx.EVT_MENU, lambda _e, f=frame: self.activate_previous(f), id=prv)
        for index, num_id in enumerate(self._num_ids):
            frame.Bind(
                wx.EVT_MENU,
                lambda _e, n=index + 1: self.activate_number(n),
                id=int(num_id),
            )

    def _on_menu_open(self, event: Any, frame: Any) -> None:
        menu = event.GetMenu() if hasattr(event, "GetMenu") else None
        if menu is None or menu.GetTitle().replace("&", "") not in ("Window", ""):
            event.Skip()
            return
        # Only rebuild our Window menu (identified by its numbered entries).
        self._rebuild_window_menu(menu, frame)
        event.Skip()

    def _rebuild_window_menu(self, menu: Any, frame: Any) -> None:
        wx = self._wx
        for item in list(menu.GetMenuItems()):
            menu.Delete(item)
        current = self.key_for(frame)
        for entry in self._registry.items():
            accel = f"\tCtrl+{entry.number}" if entry.number <= 9 else ""
            label = f"&{entry.number} {entry.title}{accel}"
            menu_item = menu.Append(wx.ID_ANY, label, "", wx.ITEM_CHECK)
            if entry.key == current:
                menu_item.Check(True)
            frame.Bind(
                wx.EVT_MENU,
                lambda _e, k=entry.key: self.activate(k),
                id=menu_item.GetId(),
            )
