"""Which window "Browse Stations" opens, answered once for every door onto it.

Quill Radio has two station windows. **Browse Stations** is the tree of every
source (Station > Browse Stations, Ctrl+B); **Search Stations** is the field
search whose window is titled "Internet Radio". Inside QUILL there is only the
second, and QUILL's own "Browse Stations..." menu item opens it.

Four doors in the standalone app said "Browse Stations" and opened Search
Stations instead -- the Command Palette's ``radio.browse``, the tray menu, the
status bar's Play cell and the first-run screen's button -- because each called
``open_internet_radio`` directly, the QUILL spelling (found 2026-09-25). They
all come through here now.

The test is the WindowManager: only the standalone app has one (``_windows``),
and it is the app whose Ctrl+B opens the tree.
"""

from __future__ import annotations

from typing import Any

__all__ = ["open_browse"]


def open_browse(host: Any) -> None:
    """Open whatever "Browse Stations" means on *host*."""
    tree = getattr(host, "open_browse_stations", None)
    search = getattr(host, "open_internet_radio", None)
    standalone = getattr(host, "_windows", None) is not None
    if callable(tree) and (standalone or not callable(search)):
        tree()
    elif callable(search):
        search()
