"""The context menus of the one window (qc.md section 7), one builder per kind.

Three menus: a **place** (what the place can do as a whole), an **episode
row** in the content list (the transport pair pinned above the listener's
Quick Actions order, exactly as the Podcast Manager offered them, from the
same tables in :mod:`manager_menus`), and a **podcast row** in the Favorites
list (the Manager's show actions, in Quick Actions order, plus the
subscription's own state rows). The tree's own menu stays in
``podcasts_library_actions``.

Order matters here more than in most menus -- a listener learns "third row is
Download" -- so each builder is a function of the host that a test can call
with a fake menu and assert the labels of.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "episode_row_menu",
    "place_menu",
    "place_menu_rows",
    "playlist_row_menu",
    "podcast_row_menu",
]


def _popup(host: Any, menu: Any) -> None:
    control = host._content.control
    try:
        control.PopupMenu(menu)
    finally:
        menu.Destroy()


def _append(host: Any, menu: Any, rows: list[tuple[str, Any]]) -> None:
    wx = host._wx
    for label, run in rows:
        if not label:
            menu.AppendSeparator()
            continue
        item = menu.Append(wx.ID_ANY, label)
        menu.Bind(wx.EVT_MENU, lambda _e, r=run: r(), item)


# -- a place ------------------------------------------------------------------- #


def place_menu_rows(host: Any, place_id: str) -> list[tuple[str, Any]]:
    """What the Applications key offers on a place, as (label, handler)."""
    rows: list[tuple[str, Any]] = []
    if place_id in ("inbox", "new_episodes"):
        rows.append(("Mark &All as Played...", host.podcast_mark_all_played))
    if place_id == "queue":
        rows.append(("&Clear Entire Queue...", host.podcast_clear_entire_queue))
        rows.append(("Play Queue &Shuffled", host.podcast_shuffle_queue))
        rows.append(("Save &Lineup...", host.podcast_save_queue_lineup))
        rows.append(("Appl&y Lineup...", host.podcast_apply_queue_lineup))
    if place_id == "downloads":
        rows.append(("&Pause All Downloads", host.podcast_pause_all_downloads))
        rows.append(("&Resume All Downloads", host.podcast_resume_all_downloads))
        rows.append(("&Free Up Space", host.podcast_free_up_space))
    if place_id == "podcasts":
        rows.append(("&Refresh All Now", host.podcast_refresh_all_feeds))
        rows.append(("&Add Podcast...", host._podcast_open_add_dialog))
        rows.append(("New &Folder...", host._new_library_folder))
    if place_id == "inbox":
        rows.append(("Inbox &Folder...", host.choose_inbox_folder_scope))
    if place_id == "recently_expired":
        rows.append(("Restore &All to the Queue", host._on_restore_all_expired))
    if place_id == "playlists":
        rows.append(("New &Playlist...", host._on_new_manual_playlist))
        rows.append(("New &Smart Playlist...", host._on_new_smart_playlist))
        rows.append(("Add Starter Playlis&ts", host._on_add_starter_playlists))
    if place_id == "notifications":
        rows.append(("Mark All as &Read", host.mark_all_notices_read))
        rows.append(("Clear &List", host.clear_all_notices))
        rows.append(("&Open in a Window...", host.open_notifications))
    if place_id in (
        "inbox",
        "new_episodes",
        "continue_listening",
        "queue",
        "downloads",
        "personal_audio",
    ):
        rows.append(("Choose Col&umns...", lambda: _open_columns(host)))
    rows.append(("", None))
    rows.append(("Re&name This Place...\tF2", lambda: host._on_place_rename(place_id)))
    rows.append(("&Hide This Place\tDelete", lambda: host._on_place_hide(place_id)))
    rows.append(("Move &Up\tAlt+Shift+Up", lambda: host._move_place(place_id, -1)))
    rows.append(("Move &Down\tAlt+Shift+Down", lambda: host._move_place(place_id, 1)))
    rows.append(("&Places...", host.open_places_chooser))
    return rows


def _open_columns(host: Any) -> None:
    from quill.ui.podcasts.list_columns_command import open_list_columns

    open_list_columns(host)


def place_menu(host: Any, place_id: str) -> None:
    wx = host._wx
    menu = wx.Menu()
    _append(host, menu, place_menu_rows(host, place_id))
    places = host._places.box
    try:
        places.PopupMenu(menu)
    finally:
        menu.Destroy()


# -- an episode row ------------------------------------------------------------- #


def resolved_episode_actions(host: Any) -> list[Any]:
    """The selected episode's actions in the listener's Quick Actions order."""
    from quill.ui.podcasts.manager_menus import episode_actions, ordered_actions

    pair = host._selected_episode()
    if pair is None:
        return []
    show, episode = pair
    return ordered_actions(host, "episode", episode_actions(host, show, episode))


def episode_row_menu(host: Any) -> None:
    from quill.ui.podcasts.manager_menus import build_menu

    pair = host._selected_episode()
    if pair is None:
        return
    show, episode = pair
    wx = host._wx
    menu = wx.Menu()
    selected_count = host._episodes.GetSelectedItemCount()
    if selected_count > 1:
        host._append_bulk_episode_items(menu, selected_count)
    # The transport pair and the download-state items act on the player and
    # the transfer, not on the episode, so they stay pinned above the
    # listener's order rather than inside it (as the Manager had them).
    play_item = menu.Append(wx.ID_ANY, "Pla&y/Pause")
    stop_item = menu.Append(wx.ID_ANY, "&Stop")
    menu.Bind(wx.EVT_MENU, lambda _e: host.podcast_toggle_play_pause(), play_item)
    menu.Bind(wx.EVT_MENU, lambda _e: host.podcast_stop(), stop_item)
    queued_item = host._download_queue.get(host._download_item_id(episode))
    in_flight = queued_item is not None and queued_item.status in (
        "queued",
        "downloading",
        "paused",
    )
    pause_label = (
        "Resu&me Download"
        if (queued_item is not None and queued_item.status == "paused")
        else "Pause Do&wnload"
    )
    pause_item = menu.Append(wx.ID_ANY, pause_label)
    pause_item.Enable(in_flight)
    menu.Bind(wx.EVT_MENU, lambda _e: host._on_pause_resume_download(None), pause_item)
    if getattr(host, "_current_place", "") == "recently_expired":
        restore = menu.Append(wx.ID_ANY, "&Restore to the Play Queue")
        menu.Bind(wx.EVT_MENU, lambda _e: host._on_restore_expired((show, episode)), restore)
        forget = menu.Append(wx.ID_ANY, "&Forget This One")
        menu.Bind(wx.EVT_MENU, lambda _e: host._on_forget_expired((show, episode)), forget)
    host._append_transcript_items(menu, show, episode)
    if show.feed_url and not show.is_local:
        # Earshot parity R3: get the file again from wherever the feed says it is.
        from quill.ui.podcasts.refresh_audio_command import refresh_episode_audio

        refresh = menu.Append(wx.ID_ANY, "Refresh Episode Audio...")
        menu.Bind(wx.EVT_MENU, lambda _e: refresh_episode_audio(host), refresh)
    menu.AppendSeparator()
    build_menu(host, menu, resolved_episode_actions(host))
    _popup(host, menu)


# -- a podcast row (Favorites) ---------------------------------------------------- #


def playlist_row_menu(host: Any, playlist_id: str) -> None:
    """A playlist row: Open, Edit Rules (smart), Rename, Delete."""
    playlist = next((p for p in host._podcast_library.playlists if p.id == playlist_id), None)
    if playlist is None:
        return
    rows: list[tuple[str, Any]] = [
        ("&Open\tEnter", lambda: host._open_playlist_in_place(playlist_id)),
    ]
    if playlist.kind == "smart":
        rows.append(("&Edit Rules...", lambda: host._on_edit_playlist_rules(playlist)))
    rows.append(("&Rename Playlist...", lambda: host._on_rename_playlist(playlist)))
    rows.append(("&Delete Playlist...\tDelete", lambda: host._on_delete_playlist(playlist)))
    wx = host._wx
    menu = wx.Menu()
    _append(host, menu, rows)
    _popup(host, menu)


def podcast_row_menu(host: Any) -> None:
    from quill.ui.podcasts.manager_menus import build_menu, ordered_actions, show_actions

    show = host._selected_show()
    if show is None:
        return
    wx = host._wx
    menu = wx.Menu()
    open_item = menu.Append(wx.ID_ANY, "&Open Its Episodes\tEnter")
    menu.Bind(wx.EVT_MENU, lambda _e: host._open_show_in_place(show), open_item)
    pause_label = (
        "&Resume Updates for This Podcast" if show.paused else "&Pause Updates for This Podcast"
    )
    pause_item = menu.Append(wx.ID_ANY, pause_label)
    menu.Bind(wx.EVT_MENU, lambda _e: host._on_toggle_show_paused(show), pause_item)
    # No "Check Now" here: it ran the same handler as Refresh Feed, which the
    # Quick Actions rows below already carry (and can put on a key), so one
    # menu offered the same verb twice under two names.
    schedule_item = menu.Append(wx.ID_ANY, "Change Sc&hedule...")
    menu.Bind(wx.EVT_MENU, lambda _e: host.change_show_schedule(show), schedule_item)
    menu.AppendSeparator()
    build_menu(host, menu, ordered_actions(host, "show", show_actions(host, show)))
    _popup(host, menu)
