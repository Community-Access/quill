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

from quill.core.radio import website_overrides

__all__ = ["add_website_button", "edit_website", "press", "target", "website_for"]

#: B, because the menu bar and the buttons beside this one own the letters of
#: "Website" and "Site" (GATE-14/15).
LABEL = "We&bsite"


def _target_station(host: Any) -> tuple[str, Any]:
    """The playing station, else the selected favorite."""
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
        return ("", None)
    return (name, station)


def website_for(host: Any, station: Any) -> str:
    history = getattr(host, "_radio_history", None)
    overrides = getattr(history, "website_overrides", {})
    return website_overrides.website_for(station, overrides)


def target(host: Any) -> tuple[str, str]:
    """``(station name, website)``: playing station, else selected favorite."""
    name, station = _target_station(host)
    return name, website_for(host, station) if station is not None else ""


def _announce(host: Any, message: str) -> None:
    announce = getattr(host, "_announce", None)
    if callable(announce):
        announce(message)


def _announce_cb(host: Any) -> Any:
    callback = getattr(host, "_announce", None)
    return callback if callable(callback) else None


def _save_override(host: Any, station: Any, url: str) -> bool:
    history = getattr(host, "_radio_history", None)
    key = website_overrides.station_key(station)
    if history is None or not key:
        _announce(host, "This station cannot be saved because it has no stable address.")
        return False
    overrides = getattr(history, "website_overrides", None)
    if not isinstance(overrides, dict):
        _announce(host, "The website could not be saved in this Radio profile.")
        return False
    existed = key in overrides
    previous = overrides.get(key)
    overrides[key] = url
    from quill.ui.radio.history_save import save_history_async

    if not save_history_async(host, history):
        if existed:
            overrides[key] = previous
        else:
            overrides.pop(key, None)
        return False
    return True


def edit_website(
    host: Any,
    station: Any,
    *,
    parent: Any = None,
    allow_empty: bool = True,
    announce_saved: bool = True,
) -> str | None:
    """Edit a station's local website correction; None means cancelled/failed."""
    import wx

    name = str(getattr(station, "display_name", "") or getattr(station, "name", "station"))
    current = website_for(host, station)
    prompt = (
        f"Website address for {name}. Enter an HTTP or HTTPS address. "
        "Leave blank to remove the saved website."
    )
    parent = parent or getattr(host, "frame", None) or getattr(host, "_win", None) or host
    from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

    while True:
        entry = wx.TextEntryDialog(parent, prompt, "Edit Station Website", value=current)
        try:
            apply_modal_ids(
                entry,
                affirmative_id=wx.ID_OK,
                cancel_id=wx.ID_CANCEL,
                escape_id=wx.ID_CANCEL,
            )
            answer = show_modal_dialog(entry, "Edit Station Website", announce=_announce_cb(host))
            if answer != wx.ID_OK:
                return None
            raw = entry.GetValue().strip()
        finally:
            entry.Destroy()
        if not raw:
            if not allow_empty:
                _announce(host, "Enter a website address to continue.")
                continue
            normalized = ""
        else:
            normalized = website_overrides.normalize_website(raw)
            if normalized is None:
                _announce(host, "Enter a valid website address that starts with HTTP or HTTPS.")
                current = raw
                continue
        if not _save_override(host, station, normalized):
            return None
        if announce_saved:
            _announce(
                host,
                f"Website removed for {name}." if not normalized else f"Website saved for {name}.",
            )
        return normalized


def _add_missing_website(host: Any, station: Any, name: str) -> str | None:
    from quill.core.podcasts import ask_prefs
    from quill.ui.confirm_once_dialog import confirm_once

    if not confirm_once(
        getattr(host, "frame", None) or getattr(host, "_win", None) or host,
        title="Add Station Website",
        message=f"No website is saved for {name}. Would you like to add one now?",
        affirmative="&Add Website",
        question_key=ask_prefs.ADD_STATION_WEBSITE_KEY,
        announce=_announce_cb(host),
        quiet_note="adding a station website",
        applies_to="in Quill Radio and QUILL alike",
    ):
        _announce(host, f"No website was opened for {name}.")
        return None
    return edit_website(host, station, allow_empty=False, announce_saved=False)


def press(host: Any, *, opener: Any = None, add_website: Any = None) -> bool:
    """Open the website, or help add a local address when it is missing."""
    name, station = _target_station(host)
    if not name:
        host._announce("Play a station, or choose one in Favorites, to open its website.")
        return False
    url = website_for(host, station)
    if not url:
        url = (
            _add_missing_website(host, station, name)
            if add_website is None
            else add_website(host, station)
        ) or ""
        if not url:
            return False
    if not url.lower().startswith(("http://", "https://")):
        _announce(host, f"{name} does not have a valid website address.")
        return False
    if opener is None:
        import webbrowser

        opener = webbrowser.open
    if opener(url):
        _announce(host, f"Opened the website for {name}.")
        return True
    _announce(host, f"Could not open the website for {name}.")
    return False


def add_website_button(host: Any, panel: Any, row: Any, wx: Any) -> Any:
    """Add the button to *row*, right after the transport button."""
    button = wx.Button(panel, label=LABEL)
    button.SetHelpText(
        "Opens the website of the station that is playing, or of the favorite "
        "the list is on, in your web browser -- often where a station keeps its "
        "schedule. If none is saved, you can add a local website address."
    )
    button.Bind(wx.EVT_BUTTON, lambda _e: press(host))
    row.Add(button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    host._website_btn = button
    return button
