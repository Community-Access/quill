"""What a YouTube row in the browse tree offers, and what those verbs do.

Split out of :mod:`quill.ui.radio.browse_tree_menu` for the reason that module
gives for the podcast verbs living in ``browse_podcast_actions``: one concern,
one module (GATE-11). The YouTube branch grew a third verb -- the three
**Add a ...** items, now on the branch's menu as well as in its list of rows --
and that was the line where "the browse menu" stopped being one subject.

The rule that shapes all three: **a saved thing is removable, and a way in is
findable, from the same menu that plays it.** Following a channel, saving a
playlist and saving a video each happen somewhere else the first time; every
one of them has to be undoable and repeatable from the row itself, or the tree
becomes a place things only accumulate.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import row_actions

#: The three action rows the YouTube branch lists. Right-clicking one of them
#: offers all three, so the branch's menu and its rows agree.
ADD_IDS = ("addchannel", "addplaylist", "addvideo")


def add_handlers(dialog: Any) -> dict:
    """Add a Channel / Playlist / Video -> the browse-tree actions that do them.

    Routed through ``browse_actions.perform`` rather than its private
    functions, so the menu item and the action row can never diverge: they run
    the same code, consent prompt and all.
    """
    from quill.ui.radio import browse_actions

    return {
        row_actions.ADD_YOUTUBE_CHANNEL: lambda: browse_actions.perform(dialog, "addchannel"),
        row_actions.ADD_YOUTUBE_PLAYLIST: lambda: browse_actions.perform(dialog, "addplaylist"),
        row_actions.ADD_YOUTUBE_VIDEO: lambda: browse_actions.perform(dialog, "addvideo"),
    }


def unfollow_channel(dialog: Any, node: Any, args: list[str]) -> None:
    """Stop following a channel, from the same menu that added it."""
    from quill.core.radio.youtube_channels import ChannelStore

    url = args[0] if args else ""
    if not url:
        return
    name = dialog._tree.GetItemText(node).split("  (")[0]
    from quill.core.radio.youtube_channel_alerts import AlertStore

    followed = _followed_url(args) or url
    ChannelStore().remove(followed)
    AlertStore().forget(followed)  # no bell on a channel nobody follows
    _reload(dialog)
    dialog._announce(f"Stopped following {name}.")


def _followed_url(args: list[str]) -> str:
    """The address the channel is followed under, whichever of *args* it is."""
    from quill.core.radio.youtube_channels import ChannelStore, normalize_channel_url

    wanted = [normalize_channel_url(url) for url in args if url]
    for channel in ChannelStore().all():
        if channel.url in wanted:
            return channel.url
    return ""


def channel_handlers(dialog: Any, node: Any, args: list[str], station: Any) -> dict:
    """Follow, Subscribe on YouTube, the bell, and Read Comments."""
    from quill.core.radio import row_actions_youtube as yt
    from quill.ui.radio import youtube_row_account as account

    return {
        yt.FOLLOW_CHANNEL: lambda: follow_channel(dialog, node, args),
        # Subscribes for real through Connect YouTube Account when it can;
        # otherwise the confirm page below, exactly as before.
        yt.SUBSCRIBE_ON_YOUTUBE: lambda: account.subscribe(
            dialog, node, args, lambda: subscribe_on_youtube(dialog, node, args)
        ),
        yt.NOTIFY_CHANNEL: lambda: set_bell(dialog, node, args, on=True),
        yt.STOP_NOTIFY_CHANNEL: lambda: set_bell(dialog, node, args, on=False),
        yt.READ_COMMENTS: lambda: _read_comments(dialog, station),
        yt.LIVE_CHAT: lambda: account.live_chat(dialog, station),
        yt.VIDEO_DETAILS: lambda: account.video_window(dialog, station),
        yt.ABOUT_CHANNEL: lambda: account.about_channel(dialog, node, args),
    }


def _row_name(dialog: Any, node: Any) -> str:
    return str(dialog._tree.GetItemText(node)).split("  (")[0].strip()


def follow_channel(dialog: Any, node: Any, args: list[str]) -> None:
    """Follow a channel found by search or in My YouTube, in Quill Radio only."""
    from quill.core.radio.youtube_channels import ChannelStore

    if not args or not args[0]:
        return
    name = _row_name(dialog, node)
    # The @handle address when there is one: it is the one a person recognises.
    chosen = args[1] if len(args) > 1 and args[1] else args[0]
    if ChannelStore().add(chosen, name=name) is None:
        dialog._announce("That channel's address could not be read, so it was not followed.")
        return
    _reload(dialog)
    dialog._announce(
        f"Following {name} in Quill Radio. Find it under Browse Stations, YouTube. "
        "Notify Me About New Videos is on its menu there."
    )


def subscribe_on_youtube(dialog: Any, node: Any, args: list[str]) -> None:
    """Open YouTube's own subscribe page, after saying what will happen there."""
    from quill.core.radio.row_actions_youtube import subscribe_url

    url = subscribe_url(args[0] if args else "", args[1] if len(args) > 1 else "")
    if not url:
        dialog._announce("That channel's address could not be read.")
        return
    dialog._announce(
        f"Opening {_row_name(dialog, node)} on YouTube in your browser. YouTube will "
        "ask you to confirm the subscription there."
    )
    dialog._open_url(url)


def set_bell(dialog: Any, node: Any, args: list[str], *, on: bool) -> None:
    """Notify Me About New Videos, or stop, for a channel Quill Radio follows."""
    from quill.core.radio.youtube_channel_alerts import AlertStore

    url = _followed_url(args) or (args[0] if args else "")
    if not url:
        return
    AlertStore().set_notifying(url, on)
    name = _row_name(dialog, node)
    if on:
        dialog._announce(
            f"{name}: new videos will notify you. Quill Radio looks whenever it "
            "checks your podcasts."
        )
    else:
        dialog._announce(f"{name}: no more notices about new videos.")


def _read_comments(dialog: Any, station: Any) -> None:
    from quill.ui.radio import youtube_comments_ui

    youtube_comments_ui.open_for_station(dialog, station)


def remove_saved(dialog: Any, node: Any, args: list[str]) -> None:
    """Drop a saved YouTube playlist or video, from the same menu that plays it."""
    from quill.core.radio.youtube_saved import SavedStore

    url = args[0] if args else ""
    if not url:
        return
    name = dialog._tree.GetItemText(node).split("  (")[0]
    SavedStore().remove(url)
    _reload(dialog)
    dialog._announce(f"Removed {name} from YouTube.")


def _reload(dialog: Any) -> None:
    """Re-fetch the YouTube branch so the removed row actually disappears.

    Both verbs used to end with "Refresh to update the list", which asks the
    listener to repair the display themselves and leaves a row that is removed
    and still on screen -- indistinguishable from a removal that failed
    (reported 2026-08-23).
    """
    from quill.ui.radio import browse_delete

    browse_delete.reload_branch(dialog, "youtube")
