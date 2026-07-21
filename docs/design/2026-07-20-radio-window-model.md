# Radio window model: modeless frames + persistent menu bar + numbered Window menu

Status: planned (deferred behind runtime completion). Decided 2026-07-20.

## Why

Rick Lewis reported the menu bar disappears in certain radio surfaces. Root
cause is architectural, not a redraw bug: the main window (`RadioAppFrame`) is a
`wx.Frame` that carries the menu bar (Station / Playback / Record / Weather via
`_build_menu_bar`, radio.py:743), but the heavy surfaces are `wx.Dialog`s, which
**cannot** carry a menu bar:

- `browse_tree_dialog.py` (`wx.Dialog`)
- `station_browser_dialog.py` (`wx.Dialog`)
- `favorites_manager_dialog.py` (`wx.Dialog`, `ShowModal`)
- `schedule_recording_dialog.py` (`wx.Dialog`)

Entering any of these "loses" the menu bar, and the modal ones also make the
main window (and its menu bar) unreachable.

## Decision (user-confirmed)

Full conversion:

1. The heavy surfaces become **modeless `wx.Frame`s**, each carrying the **same
   shared menu bar** (so the bar is always visible on every surface).
2. Add a **"&Window" menu** listing every open window, numbered 1-9 in open
   order, for discovery.
3. **Rich, industry-standard keyboarding** (user: "follow industry standards"):
   - Ctrl+Tab = next window, Ctrl+Shift+Tab = previous (cyclic, open order).
   - Ctrl+1..9 (and/or Alt+1..9) = jump directly to the Nth window.
4. **Modeless, open on demand** ("keep everything closed unless you want them");
   the Window menu lists only what's open; closing one returns focus to the
   previous.

## DRY foundation (write once, reuse)

One shared, pure registry tracks open windows + numbering + navigation; a thin
wx mixin wires the menu, accelerators, and frame register/unregister. Proposed
module `quill/ui/window_manager.py`:

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class WindowItem:
    number: int  # 1-based, for the Window menu and Ctrl+<n>
    key: str     # stable identity (wx window id as str, or a slug)
    title: str

class WindowRegistry:
    """Ordered set of open windows with numbered, cyclic navigation."""
    def __init__(self) -> None:
        self._order: list[str] = []
        self._titles: dict[str, str] = {}

    def register(self, key: str, title: str) -> None:
        if key not in self._titles:
            self._order.append(key)
        self._titles[key] = title

    def unregister(self, key: str) -> None:
        if key in self._titles:
            self._order.remove(key)
            del self._titles[key]

    def items(self) -> list[WindowItem]:
        return [WindowItem(i + 1, k, self._titles[k]) for i, k in enumerate(self._order)]

    def by_number(self, number: int) -> str | None:
        return self._order[number - 1] if 1 <= number <= len(self._order) else None

    def next(self, current: str) -> str | None:
        return self._step(current, 1)

    def previous(self, current: str) -> str | None:
        return self._step(current, -1)

    def _step(self, current: str, delta: int) -> str | None:
        if not self._order:
            return None
        try:
            index = self._order.index(current)
        except ValueError:
            return self._order[0]
        return self._order[(index + delta) % len(self._order)]
```

Tests (pure, no wx): register preserves open order and numbers 1..N; unregister
renumbers and closes the gap; by_number bounds; next/previous cycle; unknown
current lands on the first window; empty registry returns None.

## Implementation order (when resumed)

1. Land `window_manager.py` + unit tests (pure, gate-safe).
2. wx mixin: builds the shared menu bar incl. a dynamic "&Window" menu from
   `registry.items()`; installs an accelerator table (Ctrl+Tab / Ctrl+Shift+Tab
   / Ctrl+1..9); on Show, `register`; on Close, `unregister` + raise the
   previous window.
3. Convert surfaces Dialog -> modeless Frame one at a time, re-checking every
   `ShowModal` call site, focus return, and the z-order / dialog-contract rules.
   Start with Browse, then Station Browser, Favorites Manager, Schedule
   Recording, Weather Center.
4. Reuse the same mixin in Cast/Studio/Beacon surfaces where the same
   menu-bar-loss applies.

## Risks

- Dialog -> Frame changes modality, parenting, default-button/Enter/Escape
  handling, and sizing; each surface needs its Enter/Escape behavior preserved
  explicitly (frames do not get the dialog's automatic OK/Cancel).
- The dialog-contract and accessible-name GATE audits target dialogs; converting
  to frames may shift what those audits see -- re-run and rebaseline as needed.
- Modeless surfaces can now co-exist; guard against opening duplicates (focus the
  existing window instead of opening a second).
