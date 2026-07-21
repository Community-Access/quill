"""Family window registry -- numbered traversal across open windows.

The QuillVille apps open several top-level windows (the main window plus Browse,
Manager, Weather, ...). This is the ONE place that tracks the open windows,
numbers them 1-9 in open order, and computes navigation for the "&Window" menu
and the Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+1..9 shortcuts. Pure and testable; the
thin wx layer (window_menu_mixin) registers a frame on show, drops it on close,
and reads this for the menu labels and for which window a shortcut targets.
Written once, reused by every surface.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WindowItem:
    """One open window's menu number, stable key, and current title."""

    number: int  # 1-based position, for the Window menu and Ctrl+<n>
    key: str  # stable identity (e.g. the wx window id as a string, or a slug)
    title: str


class WindowRegistry:
    """Ordered set of open windows with numbered, cyclic navigation."""

    def __init__(self) -> None:
        self._order: list[str] = []
        self._titles: dict[str, str] = {}

    def register(self, key: str, title: str) -> None:
        """Add a window, or refresh its title. Open order is preserved so the
        numbers stay stable while a window is open."""
        if key not in self._titles:
            self._order.append(key)
        self._titles[key] = title

    def unregister(self, key: str) -> None:
        """Drop a closed window; the rest renumber to close the gap."""
        if key in self._titles:
            self._order.remove(key)
            del self._titles[key]

    def __contains__(self, key: object) -> bool:
        return key in self._titles

    def __len__(self) -> int:
        return len(self._order)

    def title(self, key: str) -> str:
        """The current title for *key*, or an empty string if unknown."""
        return self._titles.get(key, "")

    def items(self) -> list[WindowItem]:
        """Every open window, numbered 1..N in open order (for the Window menu)."""
        return [WindowItem(i + 1, key, self._titles[key]) for i, key in enumerate(self._order)]

    def by_number(self, number: int) -> str | None:
        """The key of the *number*-th window (1-based), or None if out of range."""
        if 1 <= number <= len(self._order):
            return self._order[number - 1]
        return None

    def next(self, current: str) -> str | None:
        """The window after *current* (cyclic). None only when there are none."""
        return self._step(current, 1)

    def previous(self, current: str) -> str | None:
        """The window before *current* (cyclic). None only when there are none."""
        return self._step(current, -1)

    def _step(self, current: str, delta: int) -> str | None:
        if not self._order:
            return None
        try:
            index = self._order.index(current)
        except ValueError:
            return self._order[0]  # current unknown: land on the first window
        return self._order[(index + delta) % len(self._order)]
