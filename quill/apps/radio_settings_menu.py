"""The Station-menu items that decide what the app remembers about you.

Extracted from ``quill/apps/radio.py`` under GATE-11 (extract, never
rebaseline) when Choose Browse Sources and Download Preferences arrived. A
coherent group rather than a slice: every item here opens a small remembered
choice -- which directories search covers, which branches browsing shows, and
the standing rules for the download queue -- and each confirms itself in one
spoken sentence.

Wiring only -- every behaviour lives in ``ui/radio/settings_commands.py``.
"""

from __future__ import annotations

from typing import Any


def build_settings_items(app: Any, station_menu: Any, wx: Any) -> tuple[Any, ...]:
    """Append the remembered-choice commands to *station_menu*, bound to *app*.

    Returns every id ref it created, because the caller must **pin** them: a
    menu id ref that is garbage-collected can be reissued to a different item,
    and the symptom is a random menu entry firing the wrong command.
    """
    # Which directories a search covers. Remembered, and a source that is off
    # is never contacted -- see core/radio/search_sources.py.
    sources_id = wx.NewIdRef()
    station_menu.Append(sources_id, "Search So&urces...\tCtrl+Alt+Shift+U")
    app.frame.Bind(wx.EVT_MENU, lambda _e: app.radio_search_sources(), id=sources_id)
    # Which branches Browse Stations shows, under the same rule: a branch that
    # is off is not in the tree and is never contacted.
    browse_sources_id = wx.NewIdRef()
    station_menu.Append(browse_sources_id, "Ch&oose Browse Sources...\tCtrl+Shift+Alt+O")
    app.frame.Bind(
        wx.EVT_MENU, lambda _e: app.radio_browse_sources_visibility(), id=browse_sources_id
    )
    # The station catalog: the manual half of "updates on demand or
    # automagically" -- the automatic layers live on the minute tick.
    update_catalog_id = wx.NewIdRef()
    station_menu.Append(update_catalog_id, "Update Station Catalo&g\tCtrl+Alt+Shift+G")
    app.frame.Bind(wx.EVT_MENU, lambda _e: app.radio_update_catalog(), id=update_catalog_id)
    return (sources_id, browse_sources_id, update_catalog_id)


def build_download_prefs_item(app: Any, station_menu: Any, wx: Any) -> tuple[Any, ...]:
    """Append Download Preferences to *station_menu*, bound to *app*.

    Standing rules for the download queue: where things land, how they are
    filed, and whether closing to the tray keeps transfers going. Appended
    separately from :func:`build_settings_items` so it can sit beside
    Preferences, where somebody looking for a setting already looks.
    """
    download_prefs_id = wx.NewIdRef()
    station_menu.Append(download_prefs_id, "&Download Preferences...\tCtrl+Alt+Shift+D")
    app.frame.Bind(wx.EVT_MENU, lambda _e: app.radio_download_preferences(), id=download_prefs_id)
    return (download_prefs_id,)


def build_catalog_status_item(app, view_menu, wx):
    """Append Station Catalog Status... to the View menu, bound to *app*.

    The complete cached-versus-live answer lives behind it: every source,
    whether it is stored on this computer, how fresh it is, and why the
    live-only ones are live-only.
    """
    status_id = wx.NewIdRef()
    view_menu.Append(status_id, "Station Catalog &Status...\tCtrl+Alt+Shift+S")
    app.frame.Bind(wx.EVT_MENU, lambda _e: app.radio_catalog_status(), id=status_id)
    # Audio Health sits beside it because they answer the same shape of
    # question -- "what is this installation actually doing?" -- one about the
    # station catalog, one about the audio chain. The catalog one was already
    # here; the audio one had no door at all: media_preflight speaks once at
    # launch and, when nothing is wrong, correctly says nothing, so there was
    # no way to ask.
    audio_id = wx.NewIdRef()
    # Ctrl+Alt+Shift+M, not ...+A: the unlock-gated Audio Description Project
    # menu already claims +A, and two items on one key means one of them
    # silently never fires. M for media, which is what the window reports on.
    view_menu.Append(audio_id, "Audio &Health...\tCtrl+Alt+Shift+M")
    app.frame.Bind(wx.EVT_MENU, lambda _e: app.radio_audio_health(), id=audio_id)
    return (status_id, audio_id)


def build_choose_columns_item(app, view_menu, wx):
    """Append Choose Columns... to the View menu, bound to *app*.

    A report list is read out column by column, so the column set *is* the
    sentence every row speaks. This is where somebody decides it: which
    columns exist on Find Stations and on Recordings, and in what order.

    It sits on View rather than on Station because it is about how the app
    presents a list, not about what a station can do -- the same shelf as
    Show Station Details and Text Size.
    """
    from quill.ui.radio.list_columns_command import open_list_columns

    view_menu.AppendSeparator()
    columns_id = wx.NewIdRef()
    view_menu.Append(columns_id, "Choose Co&lumns...\tCtrl+Alt+Shift+C")
    app.frame.Bind(wx.EVT_MENU, lambda _e: open_list_columns(app), id=columns_id)
    return columns_id
