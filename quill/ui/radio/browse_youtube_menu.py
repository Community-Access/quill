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
    ChannelStore().remove(url)
    _reload(dialog)
    dialog._announce(f"Stopped following {name}.")


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
