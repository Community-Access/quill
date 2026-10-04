"""What a YouTube row offers beyond play: follow, subscribe, the bell, comments.

Extracted from :mod:`quill.core.radio.row_actions` (GATE-11), the same way
:mod:`quill.core.radio.row_actions_podcasts` was: the ids live here, the menu
builder calls :func:`channel_actions` and :func:`video_actions`, and nothing
in either function reaches the network -- whether a channel is followed or
ringing is a local file read the caller already did (``FolderState``).

The channel verbs, and why there are three:

* **Follow This Channel in Quill Radio** / **Stop Following** -- the local
  list under Browse Stations, YouTube. No account involved.
* **Subscribe on YouTube...** -- opens YouTube's own subscribe-confirm page in
  the browser, where YouTube asks you to confirm. Quill never subscribes on
  your behalf: YouTube's private subscribe calls are fragile and against its
  terms, and that page is also where YouTube offers its own bell.
* **Notify Me About New Videos** / **Stop Notifying About New Videos** --
  Quill's own bell, on a channel Quill Radio follows (see
  :mod:`quill.core.radio.youtube_channel_alerts`).

Mnemonics are chosen against the whole folder menu they join, where O/C is
Open or Close, R Refresh, A Add All, S Add This Place, D Download All, P Stop
Following, and e/l/U the three Add a ... rows on the YouTube branch.
"""

from __future__ import annotations

from typing import Any

FOLLOW_CHANNEL = "channel.follow"
SUBSCRIBE_ON_YOUTUBE = "channel.subscribe_youtube"
NOTIFY_CHANNEL = "channel.notify"
STOP_NOTIFY_CHANNEL = "channel.stop_notify"
READ_COMMENTS = "youtube.comments"
#: The account-aware verbs (ui/radio/youtube_row_account).
LIVE_CHAT = "youtube.live_chat"
VIDEO_DETAILS = "youtube.video"
ABOUT_CHANNEL = "channel.about"

#: Folder kinds that are a YouTube channel, followed or not.
CHANNEL_KINDS = frozenset({"youtubechannel", "ytchannel"})

READ_COMMENTS_LABEL = "Read C&omments..."


def channel_actions(kind: str, state: Any, row_action: Any) -> list[Any]:
    """The channel verbs for a folder row; empty for anything else.

    *row_action* is the ``RowAction`` class, passed in so this module does not
    import the one that imports it.
    """
    if kind not in CHANNEL_KINDS:
        return []
    followed = kind == "youtubechannel" or bool(getattr(state, "is_followed_channel", False))
    actions = []
    if followed:
        actions.append(row_action("channel.unfollow", "Sto&p Following This Channel"))
        actions.append(
            row_action(STOP_NOTIFY_CHANNEL, "Stop &Notifying About New Videos")
            if getattr(state, "channel_notify", False)
            else row_action(NOTIFY_CHANNEL, "&Notify Me About New Videos")
        )
    else:
        actions.append(row_action(FOLLOW_CHANNEL, "&Follow This Channel in Quill Radio"))
    actions.append(row_action(SUBSCRIBE_ON_YOUTUBE, "Subscribe on &YouTube..."))
    # The channel's own name, subscribers and description. "&t": every other
    # letter of "About" is already another folder verb's.
    actions.append(row_action(ABOUT_CHANNEL, "Abou&t This Channel..."))
    return actions


def video_actions(station: Any, row_action: Any) -> list[Any]:
    """Read Comments, on any playable row that is a YouTube video."""
    from quill.core.radio.youtube_urls import is_youtube_url, youtube_video_id

    url = str(getattr(station, "stream_url", "") or "")
    if not is_youtube_url(url) or not youtube_video_id(url):
        return []
    # Live Chat and the YouTube Video window take H and Y, the two letters a
    # video row's menu leaves free (with J, Q, X and Z).
    return [
        row_action(READ_COMMENTS, READ_COMMENTS_LABEL),
        row_action(LIVE_CHAT, "Live C&hat..."),
        row_action(VIDEO_DETAILS, "&YouTube Video..."),
    ]


def subscribe_url(channel_url: str, handle_url: str = "") -> str:
    """YouTube's own subscribe-confirm page for a channel (pure).

    The ``@handle`` address when there is one, because it is the address the
    listener would recognise if they looked; ``?sub_confirmation=1`` is what
    makes YouTube ask "Subscribe to ...?" rather than just showing the channel.
    """
    from quill.core.radio.youtube_channels import normalize_channel_url

    base = normalize_channel_url(handle_url) or normalize_channel_url(channel_url)
    return f"{base}?sub_confirmation=1" if base else ""


__all__ = [
    "ABOUT_CHANNEL",
    "CHANNEL_KINDS",
    "LIVE_CHAT",
    "VIDEO_DETAILS",
    "FOLLOW_CHANNEL",
    "NOTIFY_CHANNEL",
    "READ_COMMENTS",
    "STOP_NOTIFY_CHANNEL",
    "SUBSCRIBE_ON_YOUTUBE",
    "channel_actions",
    "subscribe_url",
    "video_actions",
]
