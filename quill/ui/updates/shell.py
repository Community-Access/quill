"""Release-channel menu and version wiring for every QuillVille app.

One menu row and one Preferences action, each a line in the app's own module,
so the apps' menu builders -- already at their size budgets -- grow by the
least possible.
"""

from __future__ import annotations

import re
from typing import Any

import wx

from quill.core.release_catalog import installed_version, product

__all__ = [
    "append_release_channel_item",
    "installed_app_version",
    "open_for_shell",
]


def installed_app_version(app_key: str, *, current: bool = True) -> str:
    """The version the installer recorded, falling back to the app's constant."""
    return installed_version(app_key, current=current)


def _frame(shell: Any) -> Any:
    return getattr(shell, "frame", shell)


def open_for_shell(
    shell: Any, app_key: str, *, check_menu_id: Any = None, parent: Any = None
) -> None:
    """The shared Release Channel window, run through *shell*'s own modal runner.

    *check_menu_id* is the app's Check for Updates menu id: after joining Beta
    or Dev, that command runs once on the new channel (plan 7.5, step 4).
    """
    from quill.ui.updates.flow import open_release_channel

    frame = _frame(shell)

    def _check_now() -> None:
        wx.PostEvent(frame, wx.CommandEvent(wx.wxEVT_MENU, int(check_menu_id)))

    # Over whatever is in front -- a Preferences window opens this too.
    owner = parent if parent is not None else (wx.GetActiveWindow() or frame)
    open_release_channel(
        owner,
        app_key=app_key,
        installed_version=installed_app_version(app_key),
        show_modal=shell._show_modal_dialog,
        announce=shell._announce,
        check_now=_check_now if check_menu_id is not None else None,
        install_release=shell._download_app_update,
    )


def append_release_channel_item(shell: Any, help_menu: Any, app_key: str, check_id: Any) -> Any:
    """Append Help > Release Channel... (no chord; its Alt path) and bind it."""
    product(app_key)
    labels = " ".join(str(item.GetItemLabel()) for item in help_menu.GetMenuItems()).lower()
    used = set(re.findall(r"&([^&])", labels))
    candidates = "nlreachbdgfijkmopqsuvwxyz"
    letter = next(candidate for candidate in candidates if candidate not in used)
    title = "Release Channel"
    index = title.lower().find(letter)
    label = (
        f"{title[:index]}&{title[index:]}... (Alt+H, {letter.upper()})"
        if index >= 0
        else f"&Release Channel... (Alt+H, {letter.upper()})"
    )
    item_id = wx.NewIdRef()
    help_menu.Append(item_id, label)
    _frame(shell).Bind(
        wx.EVT_MENU,
        lambda _e: open_for_shell(shell, app_key, check_menu_id=check_id),
        id=item_id,
    )
    return item_id
