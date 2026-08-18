"""The rows in the browse tree that *do* something instead of opening.

``BrowseNode`` has had an ``is_action`` kind since the tree was rebuilt around a
single contract, and until now nothing handled it: **My Servers** and **YouTube
Channels** both offered an "Add a Server..." / "Add a Channel..." row that did
absolutely nothing when activated. That is precisely the failure
:mod:`quill.ui.radio.bounded_playback_ui` exists to prevent -- a control that
silently declines is worse than one that is not offered -- and it was the last
thing standing between those two branches and being usable at all.

Handled here rather than inside ``browse_tree_dialog`` for the reason the whole
tree was refactored: the dialog knows that a row is *something you can open,
something you can play, or something that acts*, and nothing more. A new action
is an entry in :data:`_ACTIONS` and a function here, never a new branch inside
the window.

Three rules the actions share:

* **The address is probed before it is stored.** Adding a branch that turns out
  to be empty, and only discovering that when you open it, is a worse experience
  than being told immediately -- so ``my_servers.probe`` runs first and its
  answer ("4 stations") is what the listener hears.
* **The probe is never on the UI thread.** A small Icecast box on a slow link
  can take the full twelve-second timeout, and a frozen window is not an
  acceptable way to spend it. Both actions submit to the task manager and speak
  when the answer arrives.
* **Safe Mode refuses out loud, per action.** Adding a server is a network
  operation even before anything plays, so it is refused with words rather than
  by a dead row.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

#: The clipboard is offered as the default because the address somebody is
#: adding is almost always the one they just copied from a station's website.
_URL_PREFIXES = ("http://", "https://", "www.")


def is_action_id(node_id: str) -> bool:
    """Whether *node_id* names an action this module knows how to perform."""
    return node_id in _ACTIONS


def perform(host: Any, node_id: str) -> None:
    """Run the action *node_id* names. Unknown ids are ignored deliberately.

    An unknown action is not an error worth showing: the tree can only offer
    what a source put in it, and a source declaring an action nothing handles is
    a build-time mistake, not something to explain to a listener mid-browse.
    """
    action = _ACTIONS.get(node_id)
    if action is not None:
        action(host)


def _clipboard_url(wx: Any) -> str:
    """A URL sitting on the clipboard, or "". Never raises."""
    try:
        data = wx.TextDataObject()
        if not wx.TheClipboard.Open():
            return ""
        try:
            got = wx.TheClipboard.GetData(data)
        finally:
            wx.TheClipboard.Close()
    except Exception:  # noqa: BLE001 - a clipboard is never worth an exception
        return ""
    text = data.GetText().strip() if got else ""
    return text if text.lower().startswith(_URL_PREFIXES) else ""


def _ask(host: Any, *, title: str, prompt: str) -> str:
    """One line of text from the listener, or "" if they cancelled.

    ``wx.TextEntryDialog`` on purpose: it is the platform's own prompt, every
    screen reader already reads it correctly, and a bespoke one-field dialog
    would be a new surface in the inventory for no gain. Same choice, and the
    same contract exemption, as ``favorite_actions``.
    """
    wx = host._wx
    entry = wx.TextEntryDialog(host._win, prompt, title, value=_clipboard_url(wx))
    try:
        if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return ""
        return entry.GetValue().strip()
    finally:
        entry.Destroy()


def _refuse_in_safe_mode(host: Any, what: str) -> bool:
    """True (and says so) when Safe Mode forbids this. Callers stop on True."""
    if not host._safe_mode:
        return False
    host._announce(f"{what} is disabled in Safe Mode. Restart Quill Radio normally to use it.")
    return True


def _reload_branch(host: Any, node_id: str) -> None:
    """Re-fetch the branch that owns this action, so the new row appears.

    Without this the listener adds a server and the tree still shows the list
    they had a moment ago, which reads as the add having failed.
    """
    reload_branch = getattr(host, "_reload_source_branch", None)
    if reload_branch is not None:
        reload_branch(node_id)


# --- My Servers ---------------------------------------------------------------


def _add_server(host: Any) -> None:
    from quill.core.radio import my_servers

    if _refuse_in_safe_mode(host, "Adding a server"):
        return
    url = _ask(
        host,
        title="Add a Server",
        prompt=(
            "Address of the Icecast or SHOUTcast server, for example\n"
            "http://stream.example.org:8000"
        ),
    )
    if not url:
        return
    root = my_servers.normalize_root(url)
    if not root:
        host._announce(
            "That does not look like a server address. It should start with http:// or https://."
        )
        return

    host._announce(f"Checking {root}...")

    def _work(**_kwargs: Any) -> tuple[str, int]:
        return my_servers.probe(root, safe_mode=host._safe_mode)

    def _ok(_op: str, result: object) -> None:
        if not host._tree:  # the window closed while the probe was running
            return
        base, count = result if isinstance(result, tuple) else ("", 0)
        if not base or not count:
            # Deliberately not stored. A branch that is empty on the day it is
            # added is almost always a wrong address, and keeping it means
            # keeping a row that will never do anything.
            host._announce(
                f"Nothing answered at {root}. Check the address, including the port number."
            )
            return
        my_servers.ServerStore().add(base)
        host._announce(f"Added {base}. It has {count} station{'' if count == 1 else 's'}.")
        _reload_branch(host, "myservers")

    def _failed(_op: str, error: BaseException) -> None:
        if host._tree:
            host._announce(f"Could not reach {root}. {error}")

    host._task_manager.submit("radio-add-server", _work, on_success=_ok, on_failure=_failed)


# --- YouTube channels ----------------------------------------------------------


def _add_channel(host: Any) -> None:
    from quill.core.radio import youtube_channels as yt

    if _refuse_in_safe_mode(host, "Adding a channel"):
        return
    url = _ask(
        host,
        title="Add a Channel",
        prompt=(
            "Address of the YouTube channel, for example\nhttps://www.youtube.com/@channelname"
        ),
    )
    if not url:
        return
    normalized = yt.normalize_channel_url(url)
    if not normalized:
        host._announce(
            "That does not look like a channel address. "
            "A channel page looks like https://www.youtube.com/@name."
        )
        return

    host._announce("Checking that channel...")

    def _work(**_kwargs: Any) -> tuple[list, bool]:
        # One shallow request, the same one opening the branch would make, so a
        # channel that cannot be read is caught now rather than after it is
        # stored. Nothing is downloaded and no video is resolved.
        return yt.videos(normalized, page=1, safe_mode=host._safe_mode)

    def _ok(_op: str, result: object) -> None:
        if not host._tree:
            return
        rows = result[0] if isinstance(result, tuple) else []
        if not rows:
            host._announce(
                "Nothing was found at that address. Check that it is a channel page "
                "rather than a single video."
            )
            return
        channel = yt.ChannelStore().add(normalized)
        name = channel.display_name if channel is not None else normalized
        host._announce(f"Added {name}.")
        _reload_branch(host, "youtube")

    def _failed(_op: str, error: BaseException) -> None:
        if host._tree:
            host._announce(f"Could not read that channel. {error}")

    host._task_manager.submit("radio-add-channel", _work, on_success=_ok, on_failure=_failed)


def _add_playlist(host: Any) -> None:
    from quill.core.radio import youtube_saved

    if _refuse_in_safe_mode(host, "Adding a playlist"):
        return
    url = _ask(
        host,
        title="Add a Playlist",
        prompt=(
            "Address of the YouTube playlist, for example\n"
            "https://www.youtube.com/playlist?list=..."
        ),
    )
    if not url:
        return
    normalized = youtube_saved.normalize_playlist_url(url)
    if not normalized:
        host._announce(
            "That does not look like a playlist link. It should carry list= in the address."
        )
        return
    item = youtube_saved.SavedStore().add(youtube_saved.PLAYLIST, normalized)
    if item is not None:
        host._announce("Added the playlist. Open it under YouTube to hear it.")
    _reload_branch(host, "youtube")


def _add_video(host: Any) -> None:
    from quill.core.radio import youtube_saved

    if _refuse_in_safe_mode(host, "Adding a video"):
        return
    url = _ask(
        host,
        title="Add a Video",
        prompt=("Address of the YouTube video, for example\nhttps://www.youtube.com/watch?v=..."),
    )
    if not url:
        return
    normalized = youtube_saved.normalize_video_url(url)
    if not normalized:
        host._announce(
            "That does not look like a video link. A video page looks like "
            "https://www.youtube.com/watch?v=... or https://youtu.be/..."
        )
        return
    item = youtube_saved.SavedStore().add(youtube_saved.VIDEO, normalized)
    if item is not None:
        host._announce("Added the video. It is now a row under YouTube; Enter plays it.")
    _reload_branch(host, "youtube")


# --- Search --------------------------------------------------------------------


def add_search_row(tree: Any, root: Any) -> None:
    """Put Search All Sources... at the top of the browse tree.

    An action row, not a folder -- there is nothing to expand; Enter *does*
    the thing (:func:`_search_all`). Above the sources and outside Choose
    Browse Sources on purpose: hiding every source should not also hide the
    way to search across them.
    """
    row = tree.AppendItem(root, "Search All Sources...")
    tree.SetItemData(
        row, {"node_id": "searchall", "label": "Search All Sources...", "is_action": True}
    )


def _search_all(host: Any) -> None:
    """The tree-top Search All Sources... row: one federated search window.

    Every provider is searched by its own engine (podcasts by podcast search,
    iHeart by iHeart, TuneIn by TuneIn, YouTube by YouTube) and the results
    interleave -- the same window the Station menu's Search Stations opens,
    reached from inside the tree. The frame owns that window; a bare test
    dialog without a frame refuses out loud rather than doing nothing.
    """
    frame = getattr(host, "_download_host", None)
    if frame is None or not hasattr(frame, "open_internet_radio"):
        host._announce("Search is not available in this window.")
        return
    frame.open_internet_radio(focus_search=True, source_facet="")


#: Action node id -> what it does. A new "Add..." row is one entry here.
_ACTIONS: dict[str, Callable[[Any], None]] = {
    "addserver": _add_server,
    "addchannel": _add_channel,
    "addplaylist": _add_playlist,
    "addvideo": _add_video,
    "searchall": _search_all,
}
