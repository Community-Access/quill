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
from quill.core.radio.browse_nodes import make_id, split_id
from quill.core.radio.spotify_search import open_link_label
from quill.ui.radio import browse_download_actions as downloads
from quill.ui.radio import browse_places as places
from quill.ui.radio import browse_transcript
from quill.ui.radio import browse_youtube_menu as yt_menu


def _folder_state(dialog: Any, node: Any, kind: str, args: list[str]) -> row_actions.FolderState:
    """What is known about this folder without fetching anything."""
    from quill.ui.radio import download_command

    loaded = dialog._loaded_stations_under(node)
    savable = [row for row in loaded if download_command.can_download(row)]
    subscribed = False
    unheard = library_episodes = downloaded_files = 0
    if row_actions.is_podcast_show(kind):
        # Only from what is already stored -- resolving the feed is a network
        # call and belongs to the action, never to opening a menu.
        subscribed = _known_subscribed(dialog, kind, args)
        if subscribed and kind == "mypodcastshow":
            # One library read answers all three menu facts (Mark All's dimmed
            # state, Download All Episodes' count, the downloads-folder name),
            # plus one local directory listing for Remove All Downloads.
            from quill.core.paths import app_data_dir
            from quill.core.radio import download_cleanup
            from quill.core.radio.podcast_follow import show_facts_for_feed

            unheard, library_episodes, title = show_facts_for_feed(
                app_data_dir(), args[0] if args else ""
            )
            downloaded_files = download_cleanup.downloaded_file_count(app_data_dir(), title)
    try:
        expanded = bool(dialog._tree.IsExpanded(node))
    except Exception:  # noqa: BLE001 - a menu must never fail on a widget probe
        expanded = False
    from quill.core.radio import browse_sources
    from quill.core.radio.favorites import place_station

    node_id = make_id(kind, *args) if args else kind
    saved_place = bool(dialog._favorites.find(place_station(node_id, "").station_uuid) is not None)
    return row_actions.FolderState(
        saved_place=saved_place,
        loaded_stations=len(loaded),
        savable=len(savable),
        is_podcast_show=row_actions.is_podcast_show(kind),
        subscribed=subscribed,
        is_followed_channel=row_actions.is_followed_channel(kind),
        expanded=expanded,
        # A root branch's id IS its source id (no args); only those rows can
        # be hidden in place.
        root_source=not args and any(kind == nid for nid, _ in browse_sources.ROOT_SOURCES),
        unheard=unheard,
        library_episodes=library_episodes,
        downloaded_files=downloaded_files,
    )


def _known_subscribed(dialog: Any, kind: str, args: list[str]) -> bool:
    """Whether this show's feed is already followed, if we know it offline."""
    if kind == "mypodcastshow":
        # The node id carries the feed itself -- no cache, no directory.
        feed = args[0] if args else ""
    else:
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
        row_actions.CLOSE_FOLDER: lambda: dialog._tree.Collapse(node),
        row_actions.REFRESH: dialog._refresh_selected,
    }
    if station is not None:
        handlers[row_actions.PAUSE] = dialog._controller.toggle_play_pause
        # Stop is its own item on a downloaded row, so it must stop rather
        # than toggle: _play_selected would start playback on a stopped row
        # that is offering Stop only because the file is local.
        handlers[row_actions.STOP] = lambda: downloads.stop_playback(dialog, station)
        handlers[row_actions.REMOVE_DOWNLOAD] = lambda: downloads.remove_download(
            dialog, node, station
        )
        handlers[row_actions.COPY_LINK] = lambda: dialog._copy_text(station.stream_url)
        handlers[row_actions.DETAILS] = lambda: _speak_details(dialog, station)
        handlers[row_actions.OPEN_SITE] = lambda: dialog._open_url(station.homepage)
        handlers[row_actions.DOWNLOAD] = lambda: download_command.download_station(
            # The show's name rides along so a podcast episode files under
            # Podcasts\<Show>\ like Download All's do -- without it the
            # single download landed bare in the root (group="" skips the
            # per-show folder in download_prefs.plan_destination).
            host,
            station,
            group=downloads.show_group(dialog, node, station),
        )
        if dialog._on_report_bad_station is not None:
            handlers[row_actions.REPORT_BAD] = lambda: dialog._on_report_bad_station(station)
    # The playback verbs on the row that IS playing. Routed through the same
    # dispatcher the keys and the player buttons use, so a menu item and its
    # keystroke can never do different things -- and a verb the thing playing
    # cannot do says why instead of doing nothing.
    from quill.ui.radio import transport_keys

    for action_id in (
        row_actions.PLAYING_PREVIOUS_CHAPTER,
        row_actions.PLAYING_NEXT_CHAPTER,
        row_actions.PLAYING_CHAPTER_LIST,
        row_actions.PLAYING_WHERE,
        row_actions.PLAYING_SPEED_UP,
        row_actions.PLAYING_SPEED_DOWN,
        row_actions.PLAYING_SPEED_RESET,
    ):
        handlers[action_id] = lambda aid=action_id: transport_keys.perform(dialog, aid)
    handlers[row_actions.TOGGLE_CAPTIONS] = lambda: places.toggle_captions(host)
    handlers[row_actions.FAVORITE_PLACE_ADD] = lambda: places.save_place(dialog, node, kind, args)
    handlers[row_actions.FAVORITE_PLACE_REMOVE] = lambda: places.forget_place(dialog, node)
    handlers[row_actions.DOWNLOAD_ALL] = lambda: downloads.download_all(dialog, node, host)
    handlers[row_actions.HIDE_SOURCE] = lambda: _hide_source(dialog, kind)
    handlers[row_actions.RESET_SOURCES] = lambda: _reset_sources(dialog)
    handlers[row_actions.SUBSCRIBE_PODCAST] = lambda: _subscribe(dialog, node, kind, args)
    handlers[row_actions.UNSUBSCRIBE_PODCAST] = lambda: unsubscribe(dialog, node, kind, args)
    handlers[row_actions.COPY_FEED] = lambda: _copy_feed(dialog, kind, args)
    handlers[row_actions.UNFOLLOW_CHANNEL] = lambda: yt_menu.unfollow_channel(dialog, node, args)
    handlers[row_actions.REMOVE_SAVED] = lambda: yt_menu.remove_saved(dialog, node, args)
    handlers[row_actions.VIEW_TRANSCRIPT] = lambda: browse_transcript.view(
        dialog, kind, args, station
    )
    handlers.update(yt_menu.add_handlers(dialog))
    # The subscription-library verbs (folders, OPML, Mark All as Played) live
    # in browse_podcast_actions -- one concern, one module (GATE-11).
    from quill.ui.radio import browse_podcast_actions as podcast_acts

    handlers[row_actions.NEW_PODCAST_FOLDER] = lambda: podcast_acts.new_podcast_folder(
        dialog, kind, args
    )
    handlers[row_actions.RENAME_PODCAST_FOLDER] = lambda: podcast_acts.rename_podcast_folder(
        dialog, args
    )
    handlers[row_actions.DELETE_PODCAST_FOLDER] = lambda: podcast_acts.delete_podcast_folder(
        dialog, args
    )
    handlers[row_actions.MOVE_SHOW_TO_FOLDER] = lambda: podcast_acts.move_show_to_folder(
        dialog, args
    )
    handlers[row_actions.MARK_ALL_PLAYED] = lambda: podcast_acts.mark_all_played(dialog, args)
    handlers[row_actions.IMPORT_OPML] = lambda: podcast_acts.import_opml(dialog)
    handlers[row_actions.REFRESH_ALL_PODCASTS] = lambda: podcast_acts.refresh_all_feeds(dialog)
    handlers[row_actions.ADD_PODCAST_URL] = lambda: podcast_acts.add_podcast_by_url_prompt(dialog)
    handlers[row_actions.DOWNLOAD_ALL_EPISODES] = lambda: podcast_acts.download_all_episodes(
        dialog, args
    )
    handlers[row_actions.REMOVE_DOWNLOADS] = lambda: podcast_acts.remove_all_downloads(dialog, args)
    if station is not None:
        handlers[row_actions.MARK_EPISODE_PLAYED] = lambda: podcast_acts.mark_episode_played(
            dialog, station, played=True
        )
        handlers[row_actions.MARK_EPISODE_UNPLAYED] = lambda: podcast_acts.mark_episode_played(
            dialog, station, played=False
        )
        podcast_acts.register_cast_handoffs(handlers, dialog, station)
        handlers[row_actions.RENAME_FAVORITE] = lambda: _rename_favorite(dialog, station)
        if hasattr(host, "open_record_station_dialog"):
            handlers[row_actions.RECORD_STATION] = lambda: host.open_record_station_dialog(
                station=station
            )
            handlers[row_actions.SCHEDULE_RECORDING] = lambda: host._radio_open_schedule_recording(
                station=station
            )
    if hasattr(host, "open_internet_radio"):
        handlers[row_actions.SEARCH_SOURCE] = lambda: host.open_internet_radio(
            focus_search=True,
            source_facet=row_actions.SEARCHABLE_SOURCES.get(kind, ""),
        )
    return handlers


def _rename_favorite(dialog: Any, station: Any) -> None:
    """Rename Favorite... on a saved row: the manager's own prompt, in place."""
    from quill.ui.radio import favorite_actions

    key = str(getattr(station, "station_uuid", "") or "") or str(
        getattr(station, "stream_url", "") or ""
    )
    favorite = dialog._favorites.find(key)
    if favorite is None:
        dialog._announce("That station is not in your favorites.")
        return
    if favorite_actions.rename_favorite(
        dialog._win, dialog._favorites, favorite, announce=dialog._announce
    ):
        dialog._on_favorites_changed()


def _speak_details(dialog: Any, station: Any) -> None:
    """Say the row's source, stream, format and country out loud.

    The details panel shows the same text -- but it is hideable (View > Show
    Station Details), and when it is hidden there was no way to hear any of
    this. Speaking it is the version that works either way.
    """
    dialog._announce(station.details_text.replace(chr(10), ". "))


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
    # PopupMenu pumps events; without this a second context-menu event (the
    # keyboard fallback firing after the tree's own) would stack a second menu.
    if getattr(dialog, "_context_menu_open", False):
        return
    node = target_node(dialog, event)
    if node is None:
        return
    dialog._tree.SelectItem(node)
    data = dialog._node_data(node)
    if data is None:
        return
    node_id = str(data.get("node_id") or "")
    if data.get("is_action"):
        # An action row has no menu of its own -- it *is* one verb. The three
        # YouTube adds are the exception: they are a set, and somebody who
        # right-clicked "Add a Video..." looking for "Add a Playlist..." should
        # find it rather than nothing at all.
        if node_id in yt_menu.ADD_IDS:
            _popup(dialog, row_actions.youtube_add_actions(), yt_menu.add_handlers(dialog))
        return
    kind, args = split_id(node_id)
    station = data.get("station")
    from quill.ui.radio import browse_podcast_actions, download_command

    host = getattr(dialog, "_download_host", dialog)
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
        # Record verbs need the frame (recorder, scheduler); an embedded test
        # dialog without one simply offers no record items.
        can_record=hasattr(host, "open_record_station_dialog"),
        episode_played=browse_podcast_actions.episode_played(station),
        # A saved copy changes the transport verbs and turns Download into
        # Remove Download (row_actions.transport_actions explains why).
        downloaded=downloads.is_downloaded(dialog, node, station),
        # The player's own facts, for the row that IS playing: chapters and
        # captions exist or they do not, and a menu must not offer either as a
        # possibility to be discovered by pressing it.
        has_chapters=places.playing_has(dialog, station, "chapters"),
        has_captions=places.playing_has(dialog, station, "captions"),
    )
    # The listener's own order (Quick Actions). It can only reorder what this
    # row already offers, never add an action the row cannot perform.
    from quill.ui.radio.quick_actions_command import order_row_actions

    context = "node" if dialog._is_folder_data(data) else "station"
    entries = order_row_actions(host, entries, context)
    if not entries:
        return

    _popup(dialog, entries, _handlers(dialog, node, data, kind, args))


def _popup(dialog: Any, entries: list, handlers: dict) -> None:
    """Build and show the popup for *entries*, binding only what has a handler."""
    wx = dialog._wx
    if not entries:
        return
    menu = wx.Menu()
    id_refs = []
    for action in entries:
        handler = handlers.get(action.id)
        if handler is None:
            continue
        item_id = wx.NewIdRef()
        id_refs.append(item_id)
        item = menu.Append(item_id, row_actions.menu_label(action))
        if not action.enabled:
            item.Enable(False)
            # Why it is dimmed, on the item itself (11.2): the status bar
            # shows this and the readers that voice menu help speak it, so a
            # greyed row is no longer a dead end you cannot see around.
            try:
                item.SetHelp(action.unavailable_sentence())
            except Exception:  # noqa: BLE001 - help text is best-effort
                pass
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


def _resolve_feed(dialog: Any, kind: str, args: list[str]) -> str:
    """The show's own RSS address, cached per window after the first ask."""
    if kind in ("mypodcastshow", "pishow"):
        # A subscribed show's node id is the feed address already -- and so is
        # a Podcast Index show's, which is the whole advantage of a directory
        # that indexes feeds rather than store listings.
        return args[0] if args else ""
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


def _subscribe(dialog: Any, node: Any, kind: str, args: list[str]) -> None:
    """Follow this show, into the library Quill Cast reads."""
    dialog._announce("Subscribing...")
    # Artwork and homepage ride along where the directory offers them, so the
    # show arrives in Quill Cast with a tile and a site link rather than a
    # bare title. Same lookup request the feed alone would have cost.
    artwork, homepage = "", ""
    if kind == "pishow":
        # The catalogue already knows this show, and the answer is cached from
        # rendering the row -- so the artwork and site arrive with no second
        # request, and the subscription lands in Quill Cast complete.
        from quill.core.podcasts import podcast_index_catalog as catalog

        feed = args[0] if args else ""
        try:
            facts = catalog.show_facts(feed, safe_mode=dialog._safe_mode)
        except Exception:  # noqa: BLE001 - a menu action reports, never crashes
            facts = None
        if facts is not None:
            artwork, homepage = facts.artwork_url, facts.homepage
    elif kind == "mypodcastshow":
        feed = _resolve_feed(dialog, kind, args)
    else:
        from quill.core.podcasts import apple_podcasts

        try:
            details = apple_podcasts.resolve_show_details(
                args[0] if args else "", safe_mode=dialog._safe_mode
            )
        except Exception:  # noqa: BLE001 - a menu action reports, never crashes
            details = apple_podcasts.ShowDetails()
        feed = details.feed_url or _resolve_feed(dialog, kind, args)
        artwork, homepage = details.artwork_url, details.homepage
        if feed:
            # Seed the per-window cache so the reopened menu can answer
            # "already subscribed?" offline.
            cache = getattr(dialog, "_apple_feed_cache", None)
            if cache is None:
                cache = dialog._apple_feed_cache = {}
            cache.setdefault(args[0] if args else "", feed)
    if not feed:
        dialog._announce("That show's feed could not be found, so it was not subscribed.")
        return
    from quill.core.paths import app_data_dir
    from quill.core.radio.podcast_follow import follow_feed

    title = dialog._tree.GetItemText(node).split("  (")[0]
    result = follow_feed(
        app_data_dir(), feed_url=feed, title=title, homepage=homepage, artwork_url=artwork
    )
    # Subscribing is pressed on an Apple show, outside the Subscriptions
    # subtree, so the branch has to be found rather than walked up to -- and
    # the cursor stays where it is (browse_reveal explains why).
    from quill.ui.radio import browse_reveal

    browse_reveal.refetch_and_reveal(dialog, feed_url=feed)
    dialog._announce(result.spoken)


def unsubscribe(dialog: Any, node: Any, kind: str, args: list[str]) -> None:
    """Drop this show from the shared library, from the same menu slot that
    subscribed it."""
    feed = _resolve_feed(dialog, kind, args)
    if not feed:
        dialog._announce("That show's feed could not be found, so nothing was unsubscribed.")
        return
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.subscriptions import load_library, save_library
    from quill.core.radio.podcast_follow import unfollow_feed
    from quill.ui import undo_last_ui

    # What is about to go, captured before it goes: the show object itself and
    # its place in the library, so Ctrl+Z puts the subscription back exactly
    # where it was rather than re-adding it at the end (11.3).
    data_dir = app_data_dir()
    before = load_library(data_dir)
    doomed = before.find_show_by_feed_url(feed)
    position = before.shows.index(doomed) if doomed is not None else 0
    result = unfollow_feed(data_dir, feed)
    spoken = result.spoken
    if result.removed and doomed is not None:

        def _undo() -> None:
            library = load_library(data_dir)
            library.shows.insert(min(position, len(library.shows)), doomed)
            save_library(data_dir, library)
            from quill.ui.radio import browse_reveal

            browse_reveal.refetch_subscriptions(dialog)

        undo_last_ui.remember(
            "Unsubscribe",
            doomed.title or feed,
            f"{len(doomed.episodes)} episode(s)",
            _undo,
        )
        spoken = undo_last_ui.offer(spoken)
    if result.removed:
        from quill.ui.radio import browse_reveal

        # The row under Subscriptions is stale until the branch reloads, and
        # leaving a show somebody just unsubscribed sitting in the list reads
        # as the unsubscribe having failed.
        if not browse_reveal.refetch_subscriptions(dialog) and kind == "mypodcastshow":
            spoken += " Refresh to update the list."
    dialog._announce(spoken)


def _copy_feed(dialog: Any, kind: str, args: list[str]) -> None:
    feed = _resolve_feed(dialog, kind, args)
    if not feed:
        dialog._announce("That show's feed address could not be found.")
        return
    dialog._copy_text(feed)


def _hide_source(dialog: Any, kind: str) -> None:
    """Hide This Source: drop the branch from the tree, in place.

    Same setting Choose Browse Sources edits (persisted through the dialog's
    ``on_visible_sources_changed``), so the two surfaces can never disagree.
    """
    from quill.core.radio import browse_visibility

    if not browse_visibility.is_enabled(dialog._visible_sources, kind):
        return
    updated = browse_visibility.toggle(dialog._visible_sources, kind)
    _apply_visible_sources(
        dialog,
        updated,
        f"{browse_visibility.label(kind)} hidden. Reset Sources to Default on any "
        "source's menu, or Choose Browse Sources, brings it back.",
    )


def _reset_sources(dialog: Any) -> None:
    """Reset Sources to Default: the standard branch set, hidden ones back."""
    from quill.core.radio import browse_visibility

    _apply_visible_sources(
        dialog,
        browse_visibility.default_enabled(),
        "Browse sources reset to the standard set.",
    )


def _apply_visible_sources(dialog: Any, updated: tuple, spoken: str) -> None:
    dialog._visible_sources = updated
    callback = getattr(dialog, "_on_visible_sources_changed", None)
    if callback is not None:
        callback(updated)
    dialog._rebuild_sources()
    dialog._announce(spoken)
