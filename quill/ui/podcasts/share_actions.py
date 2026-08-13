"""Sharing and audio export for QUILL Cast (x.md item 9).

Earshot answers "share this" with a share sheet. The desktop has no such
thing, and pretending otherwise would produce a menu item that opens a dialog
nobody wants. What a desktop listener actually asks for is a **file** they can
put somewhere and an **address** they can paste, so the parity gap closes as
three ordinary commands rather than one imported metaphor:

* **Save Episode Audio As...** -- the useful half. A copy of the audio,
  wherever the listener chooses.
* **Copy Podcast Link** -- the companion to the existing Copy Episode Link.
* **Show in File Explorer** -- for an episode already on disk.

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

from quill.core.podcasts.download_queue import PodcastDownloadQueue
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


def save_episode_audio_as(
    parent: object,
    download_queue: PodcastDownloadQueue,
    download_root: Path,
    show: PodcastShow,
    episode: PodcastEpisode,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Save a copy of the episode's audio wherever the listener chooses.

    The useful half of "sharing" on a desktop. It copies rather than moves:
    QUILL Cast keeps managing its own downloaded copy (retention, storage
    caps, Remove Downloaded Copy all still apply to it), and the saved copy
    is the listener's, outside all of that. Moving the managed file would
    silently break resume and the download's own bookkeeping.

    An episode that is not downloaded yet cannot be copied, so this offers to
    fetch it first and returns -- rather than blocking a UI thread on a
    download of unknown length. The listener runs the command again when it
    lands, which is a far better shape than a modal progress bar they cannot
    escape.
    """
    import shutil

    import wx

    if not episode.downloaded_path or not Path(episode.downloaded_path).exists():
        answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
            f"{episode.title} is not downloaded yet, so there is no audio file to save.\n\n"
            "Download it now? Save Episode Audio As will be ready once it finishes.",
            "Save Episode Audio As",
            wx.ICON_QUESTION | wx.YES_NO | wx.YES_DEFAULT,
            parent,
        )
        if answer != wx.YES:
            return False
        from quill.ui.podcasts.show_actions import enqueue_episode_download

        enqueue_episode_download(download_queue, download_root, show, episode)
        announce(f"Downloading {episode.title}. Try Save Episode Audio As again when it finishes.")
        return False

    source = Path(episode.downloaded_path)
    suggested = _safe_audio_filename(show, episode, source)
    with wx.FileDialog(
        parent,
        message="Save episode audio as",
        defaultFile=suggested,
        wildcard=f"Audio file (*{source.suffix})|*{source.suffix}|All files (*.*)|*.*",
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as dialog:
        if dialog.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        destination = Path(dialog.GetPath())

    try:
        shutil.copy2(source, destination)
    except OSError as error:
        announce(f"Could not save the audio: {error}")
        return False
    announce(f"Saved {episode.title} to {destination.name}")
    return True


#: Characters Windows will not accept in a filename. Replaced rather than
#: stripped so two episodes whose titles differ only by punctuation do not
#: collapse onto the same suggested name.
_UNSAFE_FILENAME_CHARS = '<>:"/\\|?*'


def _safe_audio_filename(show: PodcastShow, episode: PodcastEpisode, source: Path) -> str:
    """A suggested "Show - Episode.ext" filename the OS will actually accept.

    Bounded, because a podcast title plus an episode title can easily exceed
    the path limit -- and a Save dialog that opens pre-filled with a name the
    system rejects is worse than one that opens with a shorter name.
    """
    raw = f"{show.title} - {episode.title}".strip(" -")
    cleaned = "".join(
        " " if character in _UNSAFE_FILENAME_CHARS else character for character in raw
    )
    cleaned = " ".join(cleaned.split()).strip(". ")
    return f"{cleaned[:120] or 'episode'}{source.suffix}"


__all__ = [
    "copy_show_link",
    "reveal_episode_in_file_manager",
    "save_episode_audio_as",
]
