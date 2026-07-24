"""The gentle "that app isn't installed yet -- shall I get it?" flow.

Shared by every launch site (QUILL's Companion Apps menu, the standalone apps'
AppShell "Open <sibling>" items, the Weather menu's "Open the Quill Weather
App"). When a sibling app is already installed this just opens it; when it is
not, and this is a build that can add one (frozen installer/portable), it warmly
offers to download and install it, then -- for a portable extract -- opens it
right away. Works in every direction: Radio<->Weather, QUILL<->either.

The ``host`` supplies ``_wx``, ``_announce``, ``_show_message_box`` and
``_task_manager`` (MainFrame and AppShellFrame both do). The download runs on the
task manager so the UI never blocks; the completion callback is marshalled back
to the UI thread by the task manager.
"""

from __future__ import annotations

from typing import Any


def try_open_or_offer(host: Any, app_key: str) -> None:
    """Open sibling ``app_key``; if it isn't installed, offer to get it."""
    from quill.core import companion_install as ci
    from quill.core.app_launcher import app_name, launch_app

    name = app_name(app_key)
    if launch_app(app_key):
        host._announce(f"Opening {name}.")
        return

    # Nothing we can fetch (running from source, or an unknown app): keep the
    # honest, non-alarming message that was here before.
    if not ci.can_offer_download(app_key):
        host._announce(f"{name} could not be opened; it may not be installed.")
        return

    wx = host._wx
    prompt = (
        f"{name} isn't installed yet. It's a free companion app that works hand "
        f"in hand with this one. Would you like to download and install it now?"
    )
    answer = host._show_message_box(prompt, name, wx.YES_NO | wx.ICON_QUESTION)
    if answer != wx.YES:
        host._announce(f"No problem. You can get {name} any time from this menu.")
        return

    host._announce(f"Getting {name}. I'll download it and let you know when it's ready.")

    def _work(**_kwargs: object) -> object:
        asset = ci.fetch_companion_asset(app_key)
        if asset is None:
            return None
        return ci.obtain_companion(asset)

    def _done(_op: str, result: object) -> None:
        _finish_companion(host, app_key, result)

    host._task_manager.submit("companion-install", _work, on_success=_done, on_failure=None)


def _finish_companion(host: Any, app_key: str, result: object) -> None:
    """UI-thread completion: launch a freshly-unpacked portable app, report an
    installer that's running, or -- if the fetch failed -- offer the web page."""
    import webbrowser

    from quill.core import companion_install as ci
    from quill.core.app_launcher import app_name, launch_app

    wx = host._wx
    name = app_name(app_key)

    if result is None:
        if (
            host._show_message_box(
                f"I couldn't fetch {name} automatically. Open its download page in "
                "your web browser instead?",
                name,
                wx.YES_NO | wx.ICON_INFORMATION,
            )
            == wx.YES
        ):
            webbrowser.open(ci.release_page_url())
        return

    if not getattr(result, "ok", False):
        host._announce(getattr(result, "message", f"Could not download {name}."))
        return

    if getattr(result, "kind", "") == "portable":
        # The sibling now sits in an adjacent folder; launch_app finds it.
        if launch_app(app_key):
            host._announce(f"{name} is ready. Opening it now.")
        else:
            host._announce(f"{name} is installed and ready to open from this menu.")
        return

    # Installer flavor: it's running (UAC); the user finishes it, then reopens.
    host._announce(getattr(result, "message", f"The {name} installer is running."))
