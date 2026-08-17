"""The browse tree's right-click menu, built away from the window.

Extracted from ``browse_tree_dialog`` when **Download...** arrived and that
module hit its GATE-11 ceiling -- and it belongs out here anyway: what a row
offers is a question about the *row*, not about the tree widget.

**What each row offers is now decided in core** by
:mod:`quill.core.radio.row_actions`, which is wx-free and unit-tested without
a window; this module only maps action ids to handlers and builds the popup.
That split is what let the menu stop treating a podcast show, an audiobook,
a followed channel and a Yorkshire oldies station as the same object -- and a
podcast found while browsing can finally be *subscribed to*, which is the one
thing the old menu could not do at all.

The menu is assembled per row rather than shown-and-greyed, with one exception
that matters: a row that cannot be downloaded simply has no *Download...* item,
but asking for one another way still says why. A missing item and a refusal are
different messages and both are needed -- an item that is always present and
usually disabled teaches people to stop reading the menu.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio import row_actions
from quill.core.radio.browse_nodes import split_id
from quill.core.radio.spotify_search import open_link_label


def _folder_state(dialog: Any, node: Any, kind: str, args: list[str]) -> row_actions.FolderState:
    """What is known about this folder without fetching anything."""
    from quill.ui.radio import download_command

    loaded = dialog._loaded_stations_under(node)
    savable = [row for row in loaded if download_command.can_download(row)]
    subscribed = False
    if row_actions.is_podcast_show(kind):
        # Only from what is already stored -- resolving the feed is a network
        # call and belongs to the action, never to opening a menu.
        subscribed = _known_subscribed(dialog, args)
    return row_actions.FolderState(
        loaded_stations=len(loaded),
        savable=len(savable),
        is_podcast_show=row_actions.is_podcast_show(kind),
        subscribed=subscribed,
        is_followed_channel=row_actions.is_followed_channel(kind),
    )


def _known_subscribed(dialog: Any, args: list[str]) -> bool:
    """Whether this show's feed is already followed, if we know it offline."""
    cache = getattr(dialog, "_apple_feed_cache", None)
    feed = (cache or {}).get(args[0] if args else "")
    if not feed:
        return False
    from quill.core.paths import app_data_dir
    from quill.core.radio.podcast_follow import is_followed

    return is_followed(app_data_dir(), feed)


def _handlers(dialog: Any, node: Any, data: dict, kind: str, args: list[str]) -> dict:
    """Action id -> what to run. Only ids that appear get used."""
    station = data.get("station")
    host = getattr(dialog, "_download_host", dialog)
    from quill.ui.radio import download_command

    handlers: dict[str, Callable[[], None]] = {
        row_actions.PLAY: dialog._play_selected,
        row_actions.STOP: dialog._play_selected,
        row_actions.FAVORITE_ADD: dialog._toggle_favorite,
        row_actions.FAVORITE_REMOVE: dialog._toggle_favorite,
        row_actions.FAVORITE_FOLDER: lambda: dialog._favorite_folder(node),
        row_actions.OPEN_FOLDER: lambda: dialog._tree.Expand(node),
        row_actions.REFRESH: dialog._refresh_selected,
    }
    if station is not None:
        handlers[row_actions.COPY_LINK] = lambda: dialog._copy_text(station.stream_url)
        handlers[row_actions.DETAILS] = lambda: _speak_details(dialog, station)
        handlers[row_actions.OPEN_SITE] = lambda: dialog._open_url(station.homepage)
        handlers[row_actions.DOWNLOAD] = lambda: download_command.download_station(host, station)
        if dialog._on_report_bad_station is not None:
            handlers[row_actions.REPORT_BAD] = lambda: dialog._on_report_bad_station(station)
    handlers[row_actions.DOWNLOAD_ALL] = lambda: _download_all(dialog, node, host)
    handlers[row_actions.SUBSCRIBE_PODCAST] = lambda: _subscribe(dialog, node, args)
    handlers[row_actions.COPY_FEED] = lambda: _copy_feed(dialog, args)
    handlers[row_actions.UNFOLLOW_CHANNEL] = lambda: _unfollow(dialog, node, args)
    return handlers


def _speak_details(dialog: Any, station: Any) -> None:
    """Say the row's source, stream, format and country out loud.

    The details panel shows the same text -- but it is hideable (View > Show
    Station Details), and when it is hidden there was no way to hear any of
    this. Speaking it is the version that works either way.
    """
    dialog._announce(station.details_text.replace(chr(10), ". "))


def _download_all(dialog: Any, node: Any, host: Any) -> None:
    from quill.ui.radio import download_command

    rows = [r for r in dialog._loaded_stations_under(node) if download_command.can_download(r)]
    if rows:
        download_command.download_book(host, rows, title=dialog._tree.GetItemText(node))


def target_node(dialog: Any, event: Any) -> Any:
    """The row the menu is *about*, however the listener asked for it.

    ``EVT_TREE_ITEM_MENU`` names its item by hit-testing the mouse. Press
    Shift+F10 or the Applications key and there is no mouse over a row, so wx
    hands back an invalid item -- and the menu that should have opened silently
    did not (reported 2026-08-16: "shift+f10 on a podcast did not show a
    context menu"). Keyboard context menus mean *the selected row*, which is
    the row the listener is on. Right-click still hit-tests, so both routes
    land on the row the user pointed at.
    """
    wx = dialog._wx
    tree = dialog._tree
    node = event.GetItem() if hasattr(event, "GetItem") else None
    if node is not None and node.IsOk():
        return node
    # EVT_CONTEXT_MENU carries a screen position -- or (-1, -1) from the
    # keyboard, which is the signal to use the selection rather than hit-test.
    position = event.GetPosition() if hasattr(event, "GetPosition") else None
    if position is not None and position != wx.DefaultPosition and position.x >= 0:
        hit, _flags = tree.HitTest(tree.ScreenToClient(position))
        if hit is not None and hit.IsOk():
            return hit
    selected = tree.GetSelection()
    return selected if selected is not None and selected.IsOk() else None


def show_for_event(dialog: Any, event: Any) -> None:
    wx = dialog._wx
    # PopupMenu pumps events; without this a second context-menu event (the
    # keyboard fallback firing after the tree's own) would stack a second menu.
    if getattr(dialog, "_context_menu_open", False):
        return
    node = target_node(dialog, event)
    if node is None:
        return
    dialog._tree.SelectItem(node)
    data = dialog._node_data(node)
    if data is None or data.get("is_action"):
        return
    kind, args = split_id(str(data.get("node_id") or ""))
    station = data.get("station")
    from quill.ui.radio import download_command

    entries = row_actions.actions_for(
        kind,
        station=station,
        playing=bool(station is not None and dialog._is_playing(station)),
        saved=bool(station is not None and dialog._favorites.contains(station)),
        can_download=bool(station is not None and download_command.can_download(station)),
        can_report=dialog._on_report_bad_station is not None,
        open_site_label=open_link_label(station) if station is not None else "Open &Website",
        is_folder=dialog._is_folder_data(data),
        resolve_lazily=bool(data.get("resolve_lazily")),
        folder_state=_folder_state(dialog, node, kind, args)
        if dialog._is_folder_data(data)
        else None,
    )
    if not entries:
        return

    handlers = _handlers(dialog, node, data, kind, args)
    menu = wx.Menu()
    id_refs = []
    for action in entries:
        handler = handlers.get(action.id)
        if handler is None:
            continue
        item_id = wx.NewIdRef()
        id_refs.append(item_id)
        menu.Append(item_id, action.label)
        menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
    # A SEPARATE attribute: assigning dialog._menu_id_refs here would drop the
    # menu-bar Close id ref pinned in it, re-exposing the id-reuse bug where
    # a random menu item closes the window.
    dialog._context_menu_id_refs = id_refs  # pinned while the popup can fire
    dialog._context_menu_open = True
    try:
        dialog._tree.PopupMenu(menu)
    finally:
        dialog._context_menu_open = False
        menu.Destroy()


# --- the actions that needed somewhere to live --------------------------------


def _resolve_feed(dialog: Any, args: list[str]) -> str:
    """The show's own RSS address, cached per window after the first ask."""
    collection = args[0] if args else ""
    if not collection:
        return ""
    cache = getattr(dialog, "_apple_feed_cache", None)
    if cache is None:
        cache = dialog._apple_feed_cache = {}
    if collection in cache:
        return str(cache[collection])
    from quill.core.podcasts import apple_podcasts

    try:
        feed = apple_podcasts.resolve_feed_url(collection, safe_mode=dialog._safe_mode)
    except Exception:  # noqa: BLE001 - a menu action reports, never crashes
        feed = ""
    cache[collection] = feed
    return feed


def _subscribe(dialog: Any, node: Any, args: list[str]) -> None:
    """Follow this show, into the library Quill Cast reads."""
    dialog._announce("Subscribing...")
    feed = _resolve_feed(dialog, args)
    if not feed:
        dialog._announce("That show's feed could not be found, so it was not subscribed.")
        return
    from quill.core.paths import app_data_dir
    from quill.core.radio.podcast_follow import follow_feed

    title = dialog._tree.GetItemText(node).split("  (")[0]
    result = follow_feed(app_data_dir(), feed_url=feed, title=title)
    dialog._announce(result.spoken)


def _copy_feed(dialog: Any, args: list[str]) -> None:
    feed = _resolve_feed(dialog, args)
    if not feed:
        dialog._announce("That show's feed address could not be found.")
        return
    dialog._copy_text(feed)


def _unfollow(dialog: Any, node: Any, args: list[str]) -> None:
    """Stop following a channel, from the same menu that added it."""
    from quill.core.radio.youtube_channels import ChannelStore

    url = args[0] if args else ""
    if not url:
        return
    name = dialog._tree.GetItemText(node).split("  (")[0]
    ChannelStore().remove(url)
    dialog._announce(f"Stopped following {name}. Refresh to update the list.")
