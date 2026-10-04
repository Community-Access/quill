"""Release channels for the apps built on the shared app shell (Radio, Cast).

One menu row and one Preferences action, each a line in the app's own module,
so the apps' menu builders -- already at their size budgets -- grow by the
least possible.
"""

from __future__ import annotations

from typing import Any

import wx

__all__ = [
    "append_release_channel_item",
    "installed_app_version",
    "open_for_shell",
]

#: The menu label per app. The access letter differs because each Help menu has
#: different letters free (GATE-14): C is Product Requirements in Radio, and in
#: Cast both C (Check for Updates) and N (Redeem Unlock Code) are taken.
#:
#: No chord, in any of the four apps (keymap.py's help.release_channel: rules 4
#: and 9). The route is the Alt path, written in parentheses rather than after a
#: tab -- wx would parse post-tab text as an accelerator -- the same form QUILL's
#: menu_routes gives its keyless rows. Both menus are "&Help".
_LABELS = {
    "radio": "Release Cha&nnel... (Alt+H, N)",
    "cast": "Re&lease Channel... (Alt+H, L)",
}


def installed_app_version(app_key: str) -> str:
    """The version the installer recorded, falling back to the app's constant."""
    from quill.core.app_version import installed_version

    if app_key == "radio":
        from quill.apps.radio import _VERSION as code
    elif app_key == "cast":
        from quill.apps.podcasts_menu import APP_VERSION as code
    else:
        raise KeyError(app_key)
    return installed_version(code)


def open_for_shell(
    shell: Any, app_key: str, *, check_menu_id: Any = None, parent: Any = None
) -> None:
    """The shared Release Channel window, run through *shell*'s own modal runner.

    *check_menu_id* is the app's Check for Updates menu id: after joining Beta
    or Dev, that command runs once on the new channel (plan 7.5, step 4).
    """
    from quill.ui.updates.flow import open_release_channel

    def _check_now() -> None:
        wx.PostEvent(shell.frame, wx.CommandEvent(wx.wxEVT_MENU, int(check_menu_id)))

    # Over whatever is in front -- a Preferences window opens this too.
    owner = parent if parent is not None else (wx.GetActiveWindow() or shell.frame)
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
    item_id = wx.NewIdRef()
    help_menu.Append(item_id, _LABELS[app_key])
    shell.frame.Bind(
        wx.EVT_MENU,
        lambda _e: open_for_shell(shell, app_key, check_menu_id=check_id),
        id=item_id,
    )
    return item_id
