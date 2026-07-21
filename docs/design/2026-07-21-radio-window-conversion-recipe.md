# Radio surface conversion recipe: modal dialog -> modeless frame

Branch: `radio-window-model`. This is the step-by-step for converting each heavy
radio surface (Browse, Station Browser, Favorites Manager, Schedule Recording,
Weather) from a `wx.Dialog` shown modally to a modeless `wx.Frame` that carries
the persistent menu bar + numbered `&Window` menu. Do these on the branch and
validate each with a screen reader before merging (this is the part that cannot
be verified headlessly).

## What already exists (tested, on the branch)

- `quill/ui/window_manager.py` -> `WindowRegistry` (pure numbered/cyclic order).
- `quill/ui/window_menu.py` -> `WindowManager` (wx: key->frame, `&Window` menu,
  Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+1..9 accelerators, raise/show/focus).
- `quill/ui/dialog_contract.py::show_modeless_surface` -> entry onboarding
  (accessible names + region/announce + Show + focus first control).

## One-time app wiring (radio.py)

1. Create one manager: `self._windows = WindowManager(wx)` in the app frame's
   init (the main window and every surface share it).
2. In `_build_menu_bar`, after appending the app menus, add the shared menu:
   `self._windows.install(self.frame, menu_bar)` (appends `&Window` + installs
   the accelerators on the main frame).
3. Register the main window: `self._windows.register(self.frame, "Quill Radio")`
   right after it is created, and refresh its title (station name) where the
   title bar is updated so the `&Window` entry tracks it.

## Per-surface conversion (worked example: browse_tree_dialog.py)

1. **Dialog -> Frame.** Replace
   `self.dialog = wx.Dialog(parent, title=..., style=DEFAULT_DIALOG_STYLE|RESIZE_BORDER)`
   with
   `self.frame = wx.Frame(parent, title=..., style=wx.DEFAULT_FRAME_STYLE)`.
   Rename `self.dialog` -> `self.frame` throughout the class (it is the wx object).

2. **Menu bar.** Build a small `wx.MenuBar` for the surface and set it on the
   frame: a `&Window` menu via `windows.install(self.frame, menu_bar)`, plus a
   `&Close\tCtrl+W` item bound to `self.frame.Close`. (The surface keeps its
   action buttons; the menu bar exists so Alt always lands on a real menu and
   the &Window traversal is reachable.) Pass the shared `WindowManager` into the
   surface's `__init__` (new keyword arg `windows`).

3. **Escape closes.** A frame has no automatic Escape->Cancel. Bind a char hook:
   `self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)` and in it, on
   `WXK_ESCAPE`, call `self.frame.Close()`; else `event.Skip()`.

4. **Show (replace the modal `show()`).** Replace the body of `show()`:
   - remove `apply_modal_ids(...)` and the `show_modal_dialog(...); finally: Destroy()`;
   - `self._windows.register(self.frame, "Browse Stations")`;
   - `show_modeless_surface(self.frame, "Browse Stations", announce=self._announce,
     enter_region=<region.enter>)`;
   - do NOT Destroy here -- teardown is in EVT_CLOSE.
   `show()` now returns immediately (modeless).

5. **Close lifecycle.** Bind `self.frame.Bind(wx.EVT_CLOSE, self._on_close)`:
   - `previous = self._windows.previous_key(self.frame)` (capture before unregister);
   - `self._windows.unregister(self.frame)`;
   - region exit + `announce("Exited Browse Stations")`;
   - `self._on_favorites_changed()` if the surface mutated favorites;
   - `event.Skip()` then `self.frame.Destroy()` (or `Destroy` in the handler);
   - `if previous: self._windows.activate(previous)` so focus returns to the
     window the listener came from.

6. **Caller (radio.py `open_browse_stations`).** It currently constructs the
   surface and calls `.show()` expecting a blocking modal. Now `.show()` is
   non-blocking; drop any post-show code that assumed the dialog had closed
   (move it into the surface's EVT_CLOSE via the existing `on_favorites_changed`
   callback). Guard against opening a second copy: if a Browse frame is already
   registered, `activate` it instead of building a new one.

## Gates to re-run after each surface

- `python -m quill.tools.dialog_inventory --write` (the surface leaves the modal
  registry; its child controls still need accessible names -> `accessible_name`
  audit).
- ruff, mypy(core/io unaffected), module-size budget (frames + menu bars add
  lines -> rebaseline with a dated note), banned-patterns.

## Order + validation

Convert Browse first (this example), validate with NVDA/JAWS: menu bar present,
Alt reaches it, Ctrl+Tab / Ctrl+1..9 move between the main window and Browse,
Escape closes and returns focus. Only then replicate to Station Browser,
Favorites Manager, Schedule Recording, and Weather (same six steps).
