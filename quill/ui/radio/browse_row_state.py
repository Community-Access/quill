"""What the browse window already knows about a row, before any menu is built.

Extracted from :mod:`quill.ui.radio.browse_tree_menu` under GATE-11 (extract,
never rebaseline) when a subscribed show's menu gained its alert toggle. The
seam is a real one and was overdue: that module is about *what a row does* --
action id to handler, and the popup -- while everything here answers *what a
row is*, which is the question :class:`~quill.core.radio.row_state.FolderState`
was created to carry into wx-free code.

**The property worth stating once:** every fact here comes from rows already
loaded or from a local library read. Opening a context menu must never cost a
network round trip, because it happens on the way to something else and a
listener has no way to tell a slow menu from a stuck one.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import row_actions
from quill.core.radio.browse_nodes import make_id

__all__ = ["folder_state", "has_reminder", "known_subscribed"]


def has_reminder(station: Any) -> bool:
    """Whether this row already carries a reminder. False for anything odd.

    Read here rather than passed in because it is one cheap file read and the
    alternative is threading a store through every caller of the menu builder
    for the sake of one boolean.
    """
    from quill.ui.radio import row_reminders_wiring

    return row_reminders_wiring.has_reminder(station)


def folder_state(dialog: Any, node: Any, kind: str, args: list[str]) -> row_actions.FolderState:
    """What is known about this folder without fetching anything."""
    from quill.ui.radio import download_command

    loaded = dialog._loaded_stations_under(node)
    savable = [row for row in loaded if download_command.can_download(row)]
    subscribed = False
    alerts_on = False
    unheard = library_episodes = downloaded_files = 0
    if row_actions.is_podcast_show(kind):
        # Only from what is already stored -- resolving the feed is a network
        # call and belongs to the action, never to opening a menu.
        subscribed = known_subscribed(dialog, kind, args)
        if subscribed and kind == "mypodcastshow":
            # One library read answers every menu fact: Mark All's dimmed
            # state, Download All Episodes' count, the downloads-folder name,
            # and which way the alert toggle points. Plus one local directory
            # listing for Remove All Downloads.
            from quill.core.paths import app_data_dir
            from quill.core.radio import download_cleanup
            from quill.core.radio.podcast_follow import show_menu_facts

            unheard, library_episodes, title, alert = show_menu_facts(
                app_data_dir(), args[0] if args else ""
            )
            from quill.core.podcasts import episode_alerts

            alerts_on = alert == episode_alerts.ALERT_ON
            downloaded_files = download_cleanup.downloaded_file_count(app_data_dir(), title)
    try:
        expanded = bool(dialog._tree.IsExpanded(node))
    except Exception:  # noqa: BLE001 - a menu must never fail on a widget probe
        expanded = False
    from quill.core.radio import browse_sources, source_options
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
        has_options=not args and bool(source_options.options_for(kind)),
        unheard=unheard,
        library_episodes=library_episodes,
        downloaded_files=downloaded_files,
        alerts_on=alerts_on,
    )


def known_subscribed(dialog: Any, kind: str, args: list[str]) -> bool:
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
