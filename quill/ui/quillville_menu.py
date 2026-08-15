"""The shared **QuillVille** menu -- one consistent cross-app switcher.

Every QuillVille app (QUILL, Quill Radio, Quill Weather, Quill Cast, Audio
Studio) carries the same top-level QuillVille menu: a list of "Open <sibling
app>" items that launch a family member in its own window. Same name, same
place, same job everywhere -- so moving around the suite is muscle memory.

This is deliberately *not* a functional menu (it is not "Weather" or "Radio"):
it is the family-navigation menu, which is exactly what a brand name should
label. Functional menus keep their descriptive names.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.app_launcher import APP_NAMES, RELEASED_APPS, is_app_released

#: The order siblings are listed in the QuillVille menu (the current app is
#: skipped via ``exclude``).
QUILLVILLE_APP_ORDER: tuple[str, ...] = (
    "quill",
    "radio",
    "weather",
    "cast",
    "studio",
    "converter",
    "inkwell",
)

#: ``RELEASED_APPS`` is re-exported from ``quill.core.app_launcher`` (the single
#: source of truth). Gating uses :func:`is_app_released`, which also honors a
#: developer build (``QUILL_DEV_BUILD=1``).
__all__ = ["QUILLVILLE_APP_ORDER", "RELEASED_APPS", "build_quillville_menu"]


def build_quillville_menu(
    wx: Any,
    frame: Any,
    on_launch: Callable[[str], None],
    *,
    exclude: str,
    retain: Callable[[Any], None],
    also_exclude: tuple[str, ...] = (),
) -> Any:
    """Build the QuillVille menu for one app.

    ``on_launch(key)`` opens sibling ``key`` (the app's own launch handler);
    ``exclude`` is this app's key (left off the list); ``retain`` pins each
    menu-item id for the frame's lifetime (a bare ``NewIdRef`` would otherwise
    hand its id to whatever allocates one next). Bindings go on ``frame`` so the
    menu-bar events are caught.

    ``also_exclude`` lets one app leave a sibling off its own menu without
    changing whether that sibling is released for everybody else. A menu item
    that opens an app somebody is not expecting to be shipped alongside this
    release is a promise this release did not mean to make.
    """
    menu = wx.Menu()
    skip = {exclude, *also_exclude}
    for key in QUILLVILLE_APP_ORDER:
        if key in skip or not is_app_released(key):
            continue
        item_id = wx.NewIdRef()
        menu.Append(item_id, f"Open {APP_NAMES[key]}")
        frame.Bind(wx.EVT_MENU, lambda _e, k=key: on_launch(k), id=item_id)
        retain(item_id)
    return menu
