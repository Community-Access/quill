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
        # The actual "&Window" wx.Menu per frame, so EVT_MENU_OPEN can identify
        # it by object identity. Matching by title is wrong: popup context menus
        # report an empty title, so a title check ("Window" or "") rebuilt THEM
        # too -- Shift+F10 on the favorites tree showed the numbered window list
        # instead of the item's actions.
        self._window_menus: dict[str, Any] = {}
        # Stable command ids for the accelerators (created once, reused on every
        # frame's table + menu). Ctrl+Tab / Ctrl+Shift+Tab + Ctrl+1..9.
        self._next_id = wx.NewIdRef()
        self._prev_id = wx.NewIdRef()
        self._num_ids = [wx.NewIdRef() for _ in range(9)]
        #: Per window: the child control focus was last on, remembered as
        #: traversal leaves it, so coming back lands where you were -- not on
        #: the bare frame (which reads as nothing under a screen reader).
        self._last_focus: dict[str, Any] = {}
        #: Per window: the "default control" callable for a first visit.
        self._default_focus: dict[str, Any] = {}

    # -- identity ----------------------------------------------------------------

    @staticmethod
    def key_for(frame: Any) -> str:
        """This frame's stable registry key (its wx window id as a string)."""
        return str(frame.GetId())

    # -- membership --------------------------------------------------------------

    def register(self, frame: Any, title: str, *, focus: Any = None) -> None:
        """Add (or refresh the title of) *frame* in the shared window list.

        *focus*, when given, is a zero-argument callable that puts keyboard
        focus on the window's default control (the favorites tree, say) --
        used the first time the window is reached by traversal, before there
        is a remembered control to return to.
        """
        key = self.key_for(frame)
        self._frames[key] = frame
        if focus is not None:
            self._default_focus[key] = focus
        self._registry.register(key, title)

    def unregister(self, frame: Any) -> None:
        """Drop *frame* from the shared window list (on close)."""
        key = self.key_for(frame)
        self._frames.pop(key, None)
        self._window_menus.pop(key, None)
        self._default_focus.pop(key, None)
        self._last_focus.pop(key, None)
        self._registry.unregister(key)

    def __len__(self) -> int:
        return len(self._registry)

    # -- navigation (pure selection -> thin wx activation) -----------------------

    def activate(self, key: str) -> Any:
        """Raise, show, and focus the window with *key*; returns it (or None).

        Focus goes to a *control*, not the bare frame: the control you left
        the window on last time, else the window's registered default control,
        else its first content control. A frame with the focus reads as
        nothing under a screen reader, and "Ctrl+Tab landed me nowhere" was
        exactly the report (2026-08-23).
        """
        frame = self._frames.get(key)
        if frame is None:
            return None
        self._remember_focus()
        for method in ("Show", "Raise"):
            call = getattr(frame, method, None)
            if callable(call):
                try:
                    call()
                except Exception:  # noqa: BLE001 - a dying window must not crash traversal
                    return None
        self._focus_into(key, frame)
        # And again once the activation has settled. On wxMSW, raising a window
        # that is not already the foreground one hands it the focus *after* this
        # call returns -- so a SetFocus made here is overwritten a moment later
        # by whatever the frame itself decides, which is usually nothing, and
        # the listener lands on a bare frame that reads as silence ("ctrl+tab
        # does not set focus to the first control", 2026-08-23). Deferring a
        # second, identical attempt costs nothing when the first one held.
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after):
            try:
                call_after(self._focus_into, key, frame)
            except Exception:  # noqa: BLE001 - the deferred pass is a nicety
                pass
        return frame

    def _remember_focus(self) -> None:
        """Record which control holds focus, keyed by its registered top-level
        window, so traversal back into that window can land on it again."""
        window_cls = getattr(self._wx, "Window", None)
        find_focus = getattr(window_cls, "FindFocus", None)
        if not callable(find_focus):
            return
        try:
            focused = find_focus()
        except Exception:  # noqa: BLE001 - focus memory is a nicety, never a crash
            return
        if focused is None:
            return
        owners = {id(frame): key for key, frame in self._frames.items()}
        window = focused
        while window is not None:
            key = owners.get(id(window))
            if key is not None:
                self._last_focus[key] = focused
                return
            parent = getattr(window, "GetParent", None)
            window = parent() if callable(parent) else None

    def _focus_into(self, key: str, frame: Any) -> None:
        """Land keyboard focus inside *frame*: remembered control, registered
        default, first content control, bare frame -- in that order.

        Called twice per activation (once now, once deferred); it is
        idempotent, and the second pass is what makes the focus stick on
        wxMSW. A frame that has been destroyed in between is falsy, and
        answering nothing is the right thing to do about it.
        """
        if frame is None:
            return
        try:
            if not bool(frame):  # a destroyed wx window is falsy
                return
        except Exception:  # noqa: BLE001 - a stand-in without __bool__ is fine
            pass
        last = self._last_focus.get(key)
        if last is not None:
            try:
                if bool(last):  # a destroyed wx window is falsy
                    last.SetFocus()
                    return
            except Exception:  # noqa: BLE001 - the control may be half-dead
                pass
            self._last_focus.pop(key, None)
        default = self._default_focus.get(key)
        if callable(default):
            try:
                default()
                return
            except Exception:  # noqa: BLE001 - fall through to the generic pick
                pass
        try:
            from quill.ui.dialog_contract import focus_primary_control

            if focus_primary_control(frame) is not None:
                return
        except Exception:  # noqa: BLE001 - fall through to the frame itself
            pass
        set_focus = getattr(frame, "SetFocus", None)
        if callable(set_focus):
            try:
                set_focus()
            except Exception:  # noqa: BLE001 - a dying window must not crash traversal
                pass

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

    def activate_title(self, title: str) -> Any:
        """Raise the open window registered as *title*, or None if not open.

        Already open means come to the front, not a second copy -- the guard
        every open_* method runs before building a new surface. Title is the
        stable identity a caller has; the wx ids are not knowable in advance.
        """
        for entry in self._registry.items():
            if entry.title == title:
                return self.activate(entry.key)
        return None

    def open_titles(self) -> list[str]:
        """The titles of every open window, in the order they were opened.

        Read-only, and the same identity ``activate_title`` matches on. Added
        for the guided tutorials, which watch for "Browse Stations is open now"
        rather than for a keystroke -- so the lesson notices whichever way you
        opened it.
        """
        return [entry.title for entry in self._registry.items()]

    def hide_all(self) -> None:
        """Hide every registered window (Send to Tray tucks the whole app away).

        The peer frames have no parent, so hiding the main window alone would
        leave them standing on the taskbar while the app claims to be in the
        tray. They come back through the tray icon, the &Window menu, or
        Ctrl+Tab -- :meth:`activate` shows before it raises.
        """
        for frame in list(self._frames.values()):
            try:
                frame.Hide()
            except Exception:  # noqa: BLE001 - a dying window must not block the tray
                continue

    def destroy_all_except(self, keep: Any) -> None:
        """Destroy every registered window except *keep* (app shutdown).

        The peer frames have no parent, so nothing destroys them when the main
        window closes; left alive they keep the process -- and their timers --
        running after Exit. Destroyed directly rather than Closed: this runs
        on the way out, and a close handler that announces or re-activates
        siblings has nothing left to talk to.
        """
        keep_key = self.key_for(keep) if keep is not None else None
        for key, frame in list(self._frames.items()):
            if key == keep_key:
                continue
            self.unregister(frame)
            try:
                frame.Destroy()
            except Exception:  # noqa: BLE001 - shutdown must never block exit
                continue

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
        self._window_menus[self.key_for(frame)] = window_menu
        self._bind_accelerators(frame)
        # Rebuild the Window menu each time it opens (windows come and go).
        frame.Bind(
            wx.EVT_MENU_OPEN,
            lambda event, f=frame: self._on_menu_open(event, f),
        )

    def accelerator_entries(self) -> list[Any]:
        """Fresh AcceleratorEntry rows for the traversal keys (Ctrl+Tab /
        Ctrl+Shift+Tab / Ctrl+1..9), for any table that must *include* them.

        A wx accelerator table cannot be appended to -- setting one replaces
        the last -- so a surface that installs its own table (the transport
        keys) must fold these rows in, or window traversal silently dies on
        that surface the moment its table lands. The command ids are stable and
        the EVT_MENU handlers are bound per-frame in :meth:`install`, so the
        same rows work in any table on any registered frame.
        """
        wx = self._wx
        entries = [
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_TAB, int(self._next_id)),
            wx.AcceleratorEntry(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, wx.WXK_TAB, int(self._prev_id)),
        ]
        for index, num_id in enumerate(self._num_ids):
            entries.append(wx.AcceleratorEntry(wx.ACCEL_CTRL, ord("1") + index, int(num_id)))
        return entries

    def _bind_accelerators(self, frame: Any) -> None:
        wx = self._wx
        frame.SetAcceleratorTable(wx.AcceleratorTable(self.accelerator_entries()))
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
        # Identity, not title: EVT_MENU_OPEN also fires for popup context menus
        # (whose GetTitle() is empty), and rebuilding one of those replaces the
        # item's actions with the window list the instant it opens.
        menu = event.GetMenu() if hasattr(event, "GetMenu") else None
        if menu is None or menu is not self._window_menus.get(self.key_for(frame)):
            event.Skip()
            return
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
