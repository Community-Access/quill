"""Preferences' YouTube group: Use my YouTube sign-in, and where it comes from.

Kept beside :mod:`quill.apps.radio_preferences` rather than inside it so the
three rows and the one apply step stay together, and so the privacy paragraph
is the shared one from :mod:`quill.core.radio.youtube_signin` -- the same
words the user guide uses -- rather than a copy that drifts.

The setting is stored in its own small file, not in Radio's history: it names
a browser or a file on *this* computer, and Export My Setup leaves it behind.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import youtube_signin

GROUP = "YouTube"

CHECKBOX_HELP = (
    "Off by default. "
    + youtube_signin.PRIVACY_NOTE
    + " If a Chromium browser (Edge, Chrome, Brave, Opera, Vivaldi) will not "
    "share its sign-in, close it and try again, or choose Firefox or a "
    "cookies.txt file below."
)

CHOICE_HELP = (
    "Which browser's YouTube sign-in Quill Radio reads, or a cookies.txt file "
    "you exported yourself. Firefox is the most dependable: Edge and Chrome "
    "lock their sign-in while they are open, and newer versions protect it so "
    "only the browser can read it. Only the browser's name, or the file's "
    "location, is remembered."
)

FILE_HELP = (
    "Pick a cookies.txt file (Netscape format) exported from a browser "
    "extension. Quill Radio remembers only where the file is and reads it "
    "each time it asks YouTube for something; it never copies or changes it. "
    "Then choose A cookies.txt file I choose above, and Save."
)


def rows(app: Any) -> tuple[Any, Any, Any]:
    """``(checkbox, choice, action)`` for the Preferences dialog."""
    from quill.ui.app_preferences_dialog import (
        PreferenceAction,
        PreferenceCheckbox,
        PreferenceChoice,
    )

    settings = youtube_signin.load()
    return (
        PreferenceCheckbox(
            "Use my YouTube sig&n-in from my web browser",
            CHECKBOX_HELP,
            settings.enabled,
            group=GROUP,
        ),
        PreferenceChoice(
            "Read t&he YouTube sign-in from:",
            CHOICE_HELP,
            youtube_signin.choice_labels(),
            youtube_signin.source_index(settings),
            group=GROUP,
        ),
        PreferenceAction(
            "Choose a cookies.t&xt File...",
            FILE_HELP,
            lambda: choose_cookies_file(app),
            group=GROUP,
        ),
    )


def apply(enabled: bool, source_index: int, *, app: Any = None) -> str:
    """Save what Preferences came back with. Returns what to add to the summary."""
    before = youtube_signin.load()
    after = youtube_signin.SignInSettings(
        enabled=bool(enabled),
        source=youtube_signin.source_from_index(source_index),
        cookies_file=before.cookies_file,
    )
    youtube_signin.save(after)
    if app is not None and after != before:
        try:  # My YouTube appears or goes in an open Browse Stations right away
            from quill.ui.radio import browse_refresh

            browse_refresh.reload_open_browse(app, "youtube")
        except Exception:  # noqa: BLE001 - a refresh is never worth a failed save
            pass
    if after.enabled and after.source == youtube_signin.FILE_SOURCE and not after.cookies_file:
        return "YouTube sign-in is on, but no cookies.txt file is chosen yet."
    if after.enabled and not before.enabled:
        return f"My YouTube is under Browse Stations, YouTube, using {after.source_label}."
    if before.enabled and not after.enabled:
        return "YouTube sign-in is off."
    return ""


def choose_cookies_file(app: Any) -> None:
    """The standard file picker; only the path is kept."""
    import wx

    parent = getattr(app, "frame", None)
    dialog = wx.FileDialog(
        parent,
        "Choose a cookies.txt file",
        wildcard="Cookie files (*.txt)|*.txt|All files (*.*)|*.*",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    )
    try:
        shown = getattr(app, "_show_modal_dialog", None)
        result = (
            shown(dialog, "Choose a cookies.txt file") if callable(shown) else dialog.ShowModal()
        )
        if result != wx.ID_OK:
            return
        path = str(dialog.GetPath() or "")
    finally:
        dialog.Destroy()
    if not path:
        return
    current = youtube_signin.load()
    youtube_signin.save(
        youtube_signin.SignInSettings(
            enabled=current.enabled, source=current.source, cookies_file=path
        )
    )
    app._announce(
        "Cookies file chosen. Set Read the YouTube sign-in from to A cookies.txt "
        "file I choose, then Save."
    )


__all__ = ["apply", "choose_cookies_file", "rows"]
