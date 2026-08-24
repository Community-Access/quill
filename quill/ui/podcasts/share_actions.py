"""Sharing and audio export for QUILL Cast (x.md item 9).

Earshot answers "share this" with a share sheet. The desktop has no such
thing, and pretending otherwise would produce a menu item that opens a dialog
nobody wants. What a desktop listener actually asks for is a **file** they can
put somewhere and an **address** they can paste, so the parity gap closes as
three ordinary commands rather than one imported metaphor:

* **Copy Podcast Link** -- the companion to the existing Copy Episode Link.
* **Show in File Explorer** -- for an episode already on disk.

Save Episode Audio As started here and moved to
:mod:`quill.ui.podcasts.export_audio` when it learned to wait for a download
rather than telling the listener to run the command again (list.md 2.2).

All three are :mod:`quill.core.podcasts.quick_actions` entries rather than
hard-coded menu items, so they can be reordered, made the Enter default, or
reached on Ctrl+1..Ctrl+9 like everything else on those menus.

The invariant across the lot: **QUILL Cast keeps managing its own downloaded
copy.** Saving copies, never moves -- retention, the storage cap, resume and
Remove Downloaded Copy all still apply to the managed file, and the saved copy
is the listener's, outside all of it.

Its own module rather than more of ``show_actions.py``, which was at the
600-line cap: GATE-11 asks for an extraction, and "everything about getting an
episode out of QUILL Cast" is a real seam rather than a convenient one.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.podcasts.models import PodcastEpisode, PodcastShow


def copy_show_link(show: PodcastShow, *, announce: Callable[[str], None]) -> bool:
    """Copy the show's feed address. The companion to Copy Episode Link.

    The feed URL rather than the homepage: a feed address is what another
    podcast app can actually be given, which is the point of copying it. A
    local show has no feed, and says so rather than silently copying nothing.
    """
    import wx

    if not show.feed_url:
        announce(f"{show.title} has no feed address to copy -- it is a local podcast.")
        return False
    if wx.TheClipboard.Open():
        try:
            wx.TheClipboard.SetData(wx.TextDataObject(show.feed_url))
        finally:
            wx.TheClipboard.Close()
    announce(f"Copied the feed link for {show.title}")
    return True


def reveal_episode_in_file_manager(
    episode: PodcastEpisode, *, announce: Callable[[str], None]
) -> bool:
    """Open the downloaded file's folder with the file selected.

    Only meaningful once the episode is on disk; a streamed episode has no
    file to show, and saying so is better than opening an unrelated folder.
    """
    import subprocess

    from quill.core.file_manager import reveal_command

    if not episode.downloaded_path:
        announce("That episode is not downloaded, so there is no file to show.")
        return False
    path = Path(episode.downloaded_path)
    if not path.exists():
        announce("The downloaded file is no longer there. Download it again to get it back.")
        return False
    try:
        subprocess.Popen(reveal_command(path))  # noqa: S603
    except OSError as error:  # noqa: BLE001 - reported, never raised at a menu
        announce(f"Could not open the file manager: {error}")
        return False
    announce(f"Showing {episode.title} in the file manager")
    return True


__all__ = [
    "copy_show_link",
    "reveal_episode_in_file_manager",
]
