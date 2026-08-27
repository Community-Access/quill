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

from quill.core.radio.browse_nodes import make_id

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


def _youtube_allowed(host: Any) -> bool:
    """The one-time YouTube consent, asked from the row that needs it.

    Adding a YouTube link from this tree used to store it without ever asking,
    and the refusal then arrived at the worst possible moment: pressing Enter
    on the saved row answered "this YouTube station needs the one-time consent,
    add it again from Add Custom Station" -- a dead end pointing at a different
    dialog, for a row that looked perfectly ordinary (reported 2026-08-23).
    Asking here, before anything is stored, is the same rule Add YouTube Link
    already follows.

    A dialog embedded in a test has no frame to ask through; nothing is stored
    behind a prompt that cannot be shown, so it is allowed.
    """
    frame = getattr(host, "_download_host", host)
    if not hasattr(frame, "_radio_history") or not hasattr(frame, "_show_message_box"):
        return True
    from quill.ui.radio.youtube_ui import ask_youtube_consent

    return bool(ask_youtube_consent(frame))


def _reload_branch(host: Any, node_id: str, *, select: str = "") -> None:
    """Re-fetch the branch that owns this action, so the new row appears.

    Without this the listener adds a server and the tree still shows the list
    they had a moment ago, which reads as the add having failed.

    *select* names the row to land the cursor on once it arrives -- the thing
    that was just added. Adding something and then having to go and find it is
    the other half of the same complaint.
    """
    reload_branch = getattr(host, "_reload_source_branch", None)
    if reload_branch is None:
        return
    if select:
        # Read by browse_refresh.apply_pending_select when the rows arrive.
        host._pending_select = select
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
            host._announce(f"Could not reach {root}. {error}.")

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
        _reload_branch(host, "youtube", select=make_id("youtubechannel", normalized))

    def _failed(_op: str, error: BaseException) -> None:
        if host._tree:
            host._announce(f"Could not read that channel. {error}.")

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
    if not _youtube_allowed(host):
        return
    item = youtube_saved.SavedStore().add(youtube_saved.PLAYLIST, normalized)
    if item is None:
        return
    host._announce("Added the playlist. Reading its name...")
    _reload_branch(host, "youtube", select=make_id("ytplaylist", normalized, "1"))
    _describe_saved(
        host,
        fetch=lambda: youtube_saved.fetch_playlist_details(normalized),
        fallback="Added the playlist. Open it under YouTube to hear it.",
        tail="Open it to hear its videos.",
        node_kind="ytplaylist",
        node_args=(normalized, "1"),
    )


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
    if not _youtube_allowed(host):
        return
    item = youtube_saved.SavedStore().add(youtube_saved.VIDEO, normalized)
    if item is None:
        return
    # Stored first, described second. A network round trip that fails must
    # never lose the link somebody just pasted -- the row exists and plays
    # either way; the title is what improves when the answer arrives.
    host._announce("Added the video. Reading its details...")
    _reload_branch(host, "youtube", select=make_id("ytvideo", normalized))
    _describe_saved(
        host,
        fetch=lambda: youtube_saved.fetch_video_details(normalized),
        fallback="Added the video. It is now a row under YouTube; Enter plays it.",
        tail="Enter plays it.",
        node_kind="ytvideo",
        node_args=(normalized,),
    )


def _describe_saved(
    host: Any,
    *,
    fetch: Callable[[], Any],
    fallback: str,
    tail: str,
    node_kind: str,
    node_args: tuple[str, ...],
) -> None:
    """Fetch a saved link's own facts off-thread, then say what was added.

    Never on the UI thread: this is the same yt-dlp round trip playing the
    link would make, and a frozen window is not an acceptable way to spend it
    (the rule every action in this module follows). A failure is not an error
    the listener has to act on -- the row is already saved and still plays --
    so it degrades to the address and says so plainly.
    """
    from quill.core.radio import youtube_saved

    def _work(**_kwargs: Any) -> Any:
        return fetch()

    def _ok(_op: str, result: object) -> None:
        if not host._tree:  # the window closed while the request was running
            return
        details = result if isinstance(result, youtube_saved.SavedItem) else None
        if details is None or not details.name:
            host._announce(fallback)
            return
        youtube_saved.SavedStore().describe(details)
        _reload_branch(host, "youtube", select=make_id(node_kind, *node_args))
        spoken = f"Added {details.name}"
        if details.note:
            spoken += f", {details.note}"
        # announce-punctuation: exempt -- every tail below ends in a full stop.
        host._announce(f"{spoken}. {tail}")

    def _failed(_op: str, error: BaseException) -> None:
        if host._tree:
            host._announce(f"{fallback} Its details could not be read: {error}.")

    host._task_manager.submit("radio-youtube-details", _work, on_success=_ok, on_failure=_failed)


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
    """The tree-top Search All Sources... row: search without leaving.

    It used to open the Find Stations window, which answered the question and
    took the tree away to do it. It now searches every source from here and
    puts the answer back into this tree as a Search Results branch -- browse
    rows, with their own ids, so the menu on a found podcast show is the menu
    on a browsed one. See :mod:`quill.ui.radio.browse_search_all`.
    """
    from quill.ui.radio import browse_search_all

    browse_search_all.run(host)


# --- The empty Subscriptions branch's three ways in -----------------------------


def _add_podcast_url(host: Any) -> None:
    from quill.ui.radio import browse_podcast_actions

    browse_podcast_actions.add_podcast_by_url_prompt(host)


def _import_podcasts_opml(host: Any) -> None:
    from quill.ui.radio import browse_podcast_actions

    browse_podcast_actions.import_opml(host)


def _search_podcasts(host: Any) -> None:
    """Search for a Podcast...: the same in-tree search, narrowed to podcasts.

    It left for the Find Stations window too, and from the *emptiest* branch in
    the tree -- somebody with no subscriptions yet, sent to another surface to
    get their first one. The rows it answers with are podcast-show folders, so
    Subscribe is right there on each one.
    """
    from quill.core.radio import federated_browse
    from quill.ui.radio import browse_search_all

    browse_search_all.run(
        host,
        title="Search for a Podcast",
        prompt="Show name, host, or topic:",
        what="the podcast directory",
        targets=federated_browse.targets_of_type("Podcast"),
    )


def _search_podcast_index(host: Any) -> None:
    """Search the Podcast Index..., answered inside the tree.

    The same in-tree search every other search row uses, narrowed to the one
    directory -- so finding a show does not take the tree away from you, and
    the rows it answers with are ordinary browse rows with Subscribe on them.
    """
    from quill.core.radio import federated_browse
    from quill.ui.radio import browse_search_all

    browse_search_all.run(
        host,
        title="Search the Podcast Index",
        prompt="Show name, host, or topic:",
        what="the Podcast Index",
        targets=tuple(
            target for target in federated_browse.TARGETS if target.seed_id == "podcastindex"
        ),
    )


def _tv_refresh(host: Any) -> None:
    """Fetch today's TV catalog now, off-thread, and reload the branch.

    The weekly cache is the right default for a ~28 MB refresh; this is the
    on-demand override, and it says what it is doing because a half-minute
    fetch with nothing on screen changing reads as a hang.
    """
    host._announce(
        "Updating the TV channel list. This is the biggest catalog and can take a minute."
    )

    def _work(**_kwargs: Any) -> int:
        from quill.core.radio import iptv

        return len(iptv.fetch_rows(safe_mode=host._safe_mode, refresh=True))

    def _ok(_op: str, count: object) -> None:
        if not host._tree:
            return
        host._announce(f"TV channel list updated: {count} playable channels.")
        from quill.ui.radio import browse_refresh

        browse_refresh.reload_source_branch(host, "tv")

    def _failed(_op: str, error: BaseException) -> None:
        if host._tree:
            host._announce(f"The TV channel list could not be updated. {error}.")

    host._task_manager.submit("radio-tv-refresh", _work, on_success=_ok, on_failure=_failed)


def _antennaweb(host: Any) -> None:
    """Open AntennaWeb for the over-the-air coverage question.

    A link-out on purpose: the tool has no published API, and scraping an
    undocumented commercial SPA is what the egress policy refuses. Opening the
    listener's browser sends nothing from here -- the site asks its own
    questions once they arrive.
    """
    import webbrowser

    if webbrowser.open("https://www.antennaweb.org/"):
        host._announce(
            "Opened antennaweb.org in your browser. Enter your address or ZIP code "
            "there to see which antenna channels you can receive."
        )
    else:
        host._announce("Your browser could not be opened.")


#: Action node id -> what it does. A new "Add..." row is one entry here.
_ACTIONS: dict[str, Callable[[Any], None]] = {
    "addserver": _add_server,
    "addchannel": _add_channel,
    "addplaylist": _add_playlist,
    "addvideo": _add_video,
    "searchall": _search_all,
    "addpodcasturl": _add_podcast_url,
    "importpodcastsopml": _import_podcasts_opml,
    "searchpodcasts": _search_podcasts,
    "searchpodcastindex": _search_podcast_index,
    "antennaweb": _antennaweb,
    "tvrefresh": _tv_refresh,
}
