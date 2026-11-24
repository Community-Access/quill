"""The last steps of Quill Radio's menu bar: put it on the window, and what follows.

Moved out of ``radio_menu_bar._build_menu_bar`` (GATE-11) when FUX-09 gave the
rebuild one more thing to do. The menu bar is rebuilt whenever a key is
rebound, so this is also where the window catches up with a new key.
"""

from __future__ import annotations

from typing import Any

__all__ = ["install_menu_bar"]


def install_menu_bar(host: Any, menu_bar: Any, title: str) -> None:
    # Persistent &Window menu + Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+1..9 on the
    # main window; each modeless surface installs the same on its own bar so
    # the numbered traversal reaches every open radio window.
    host._windows.install(host.frame, menu_bar)
    host.frame.SetMenuBar(menu_bar)
    # A rebound key is the key the empty Favorites line says (FUX-09).
    from quill.ui.radio import favorites_first_task

    favorites_first_task.refresh(host)
    # focus= so Ctrl+Tab into the main window lands on the favorites tree
    # (its default control), not on the bare frame.
    host._windows.register(host.frame, title, focus=host._focus_initial_control)
