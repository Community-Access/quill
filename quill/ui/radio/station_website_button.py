"""The Website button, beside Play and Stop on Quill Radio's main window.

A listener asked for it (October 2026): "add the website of the station in the
tab order so that you'd have play, stop and website" -- Double Tap Live's
schedule is on its site, and so are most blindness stations' programme guides.
The browse windows already offer Open Website on a row's menu; the main window,
where people actually listen, had no way to it.

Which station: the one playing, when there is one; otherwise the favorite the
list is on. The button is always there, so Tab order never changes under the
listener, and when the station gave no website pressing it says so.
"""

from __future__ import annotations

from typing import Any

__all__ = ["add_website_button", "press", "target"]

#: B, because the menu bar and the buttons beside this one own the letters of
#: "Website" and "Site" (GATE-14/15).
LABEL = "We&bsite"


def target(host: Any) -> tuple[str, str]:
    """``(station name, its website)``: the playing station, else the selected favorite."""
    controller = getattr(host, "_radio_controller", None)
    station = getattr(getattr(controller, "state", None), "station", None)
    if station is None:
        pick = getattr(host, "_selected_favorite", None)
        favorite = pick() if callable(pick) else None
        station = getattr(favorite, "station", None)
        name = str(getattr(favorite, "display_label", "") or "")
    else:
        name = str(getattr(station, "display_name", "") or getattr(station, "name", "") or "")
    if station is None:
        return ("", "")
    return (name, str(getattr(station, "homepage", "") or "").strip())


def press(host: Any, *, opener: Any = None) -> bool:
    """Open the website, or say why not. Returns whether a page was opened."""
    name, url = target(host)
    if not name:
        host._announce("Play a station, or choose one in Favorites, to open its website.")
        return False
    if not url.lower().startswith(("http://", "https://")):
        host._announce(f"{name} did not give a website.")
        return False
    if opener is None:
        import webbrowser

        opener = webbrowser.open
    if opener(url):
        host._announce(f"Opened the website for {name}.")
        return True
    host._announce(f"Could not open the website for {name}.")
    return False


def add_website_button(host: Any, panel: Any, row: Any, wx: Any) -> Any:
    """Add the button to *row*, right after the transport button."""
    button = wx.Button(panel, label=LABEL)
    button.SetHelpText(
        "Opens the website of the station that is playing, or of the favorite "
        "the list is on, in your web browser -- often where a station keeps its "
        "schedule. If the station gave no website, it tells you."
    )
    button.Bind(wx.EVT_BUTTON, lambda _e: press(host))
    row.Add(button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    host._website_btn = button
    return button
