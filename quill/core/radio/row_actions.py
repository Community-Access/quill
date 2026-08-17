"""What a browse row offers, decided by *what the row is*.

The context menu used to know three kinds of row: something playable,
something lazily playable, and a folder. That was right when the tree held
radio stations, and quietly wrong once it held podcasts, audiobooks, video
channels and community uploads -- because a podcast show and a Yorkshire
oldies station are not the same object, and offering them the same four items
means the useful action for each is the one that is missing. A listener who
found a podcast in Quill Radio could not subscribe to it. A book folder could
be downloaded but not followed. A YouTube channel could be added but never
dropped from the same menu that added it.

So the menu is computed from the row, here, in one wx-free place that can be
tested without a window:

    actions_for(kind, station=..., folder_state=...) -> list[RowAction]

Each :class:`RowAction` is an *identity plus a label*, never a callback -- the
window binds ids to its own handlers, so this module never imports wx and
never needs to know how a station is played.

Two rules the shapes here follow, both learned in the browse tree already:

* **Absent, not greyed.** A row that cannot be downloaded has no Download
  item; an item that is always present and usually disabled teaches people to
  stop reading the menu. (Asking for it another way still answers *why*.)
* **Never a network request.** Everything answerable here is answerable from
  what the row already carries. A "Download All" that had to fetch a folder's
  contents to learn whether to appear would make opening a menu cost a round
  trip.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# --- action ids ---------------------------------------------------------------
# Stable strings rather than an enum: the UI maps them to handlers, tests
# assert on them, and a new source adds one without touching a type.

PLAY = "play"
STOP = "stop"
FAVORITE_ADD = "favorite.add"
FAVORITE_REMOVE = "favorite.remove"
FAVORITE_FOLDER = "favorite.folder"
COPY_LINK = "copy.link"
COPY_FEED = "copy.feed"
OPEN_SITE = "open.site"
DOWNLOAD = "download"
DOWNLOAD_ALL = "download.all"
REPORT_BAD = "report.bad"
DETAILS = "details"
OPEN_FOLDER = "folder.open"
REFRESH = "folder.refresh"
SUBSCRIBE_PODCAST = "podcast.subscribe"
UNFOLLOW_CHANNEL = "channel.unfollow"


@dataclass(frozen=True, slots=True)
class RowAction:
    """One menu item: what it is, and what it should read as."""

    id: str
    label: str


@dataclass(frozen=True, slots=True)
class FolderState:
    """What the window already knows about a folder, without fetching it.

    Every field answers from rows already loaded, so building a menu never
    reaches the network.
    """

    #: Playable rows already loaded under this folder.
    loaded_stations: int = 0
    #: Of those, how many can actually be saved to disk.
    savable: int = 0
    #: A podcast show, whose episodes come from a publisher's own feed.
    is_podcast_show: bool = False
    #: Already subscribed in the shared podcast library.
    subscribed: bool = False
    #: A channel the listener chose to follow (so it can be unfollowed).
    is_followed_channel: bool = False


#: Node kinds that name a podcast show rather than a shelf of them.
PODCAST_SHOW_KINDS = frozenset({"appleshow"})

#: Node kinds that are a channel the listener follows.
FOLLOWED_CHANNEL_KINDS = frozenset({"youtubechannel"})

#: What a folder of each kind actually holds, for menu wording.
#:
#: Every folder used to offer "Add All Stations to Favorites" -- on a LibriVox
#: book, whose children are chapters; on a podcast show, whose children are
#: episodes; on a YouTube channel, whose children are videos (reported
#: 2026-08-16, when a sweep of all 41 branches found 39 of them saying
#: "Stations" and meaning something else). The menu should name what is
#: actually there, because "Add All Stations" on a book is a sentence that
#: makes a listener wonder what they are about to do.
FOLDER_CONTENTS: dict[str, str] = {
    "apple": "Shows",
    "applechart": "Shows",
    "applegenre": "Shows",
    "appleshow": "Episodes",
    "archive": "Recordings",
    "archiveitem": "Files",
    "audiopub": "Books",
    "audiopubdiscover": "Books",
    "audius": "Tracks",
    "audiustrending": "Tracks",
    "ccmixter": "Tracks",
    "gutenberg": "Books",
    "gutenberglang": "Books",
    "gutenbergtopic": "Books",
    "librivox": "Books",
    "librivoxauthors": "Books",
    "librivoxbook": "Chapters",
    "librivoxgenres": "Books",
    "librivoxrecent": "Books",
    "mixcloud": "Shows",
    "mixcloudcat": "Shows",
    "mixcloudfmt": "Shows",
    "wx": "Forecasts",
    "youtube": "Channels",
    "youtubechannel": "Videos",
    "youtubevideos": "Videos",
}


def contents_noun(kind: str) -> str:
    """What this folder holds, plural and capitalised. Defaults to stations."""
    return FOLDER_CONTENTS.get(kind, "Stations")


def is_podcast_show(kind: str) -> bool:
    return kind in PODCAST_SHOW_KINDS


def is_followed_channel(kind: str) -> bool:
    return kind in FOLLOWED_CHANNEL_KINDS


def station_actions(
    *,
    playing: bool,
    saved: bool,
    has_homepage: bool,
    can_download: bool,
    can_report: bool,
    is_recording: bool,
    open_site_label: str = "Open &Website",
) -> list[RowAction]:
    """The menu for a playable row.

    *is_recording* is what separates a podcast episode or a book chapter from
    a live station: a recording has a beginning and an end, so "Download" is a
    sensible thing to offer and "Report Bad Station" is not.
    """
    actions = [
        RowAction(STOP, "&Stop") if playing else RowAction(PLAY, "&Play"),
        RowAction(FAVORITE_REMOVE, "Remove from &Favorites")
        if saved
        else RowAction(FAVORITE_ADD, "Add to &Favorites"),
        # "De&tails", not "&Details": Download claims D, and two items in one
        # popup answering the same key means one of them never fires.
        RowAction(DETAILS, "Station De&tails..."),
        RowAction(COPY_LINK, "&Copy Link" if is_recording else "&Copy Stream Link"),
    ]
    if has_homepage:
        actions.append(RowAction(OPEN_SITE, open_site_label))
    if can_download:
        actions.append(RowAction(DOWNLOAD, "&Download..."))
    if can_report and not is_recording:
        # A recording that will not play is not a "bad station"; the report
        # form asks about a stream, and answering it about an episode would
        # send a report nobody can act on.
        actions.append(RowAction(REPORT_BAD, "Report &Bad Station..."))
    return actions


def lazy_leaf_actions(*, saved: bool) -> list[RowAction]:
    """A row whose stream is worked out when it is played (TuneIn, and kin)."""
    return [
        RowAction(PLAY, "&Play"),
        RowAction(FAVORITE_REMOVE, "Remove from &Favorites")
        if saved
        else RowAction(FAVORITE_ADD, "Add to &Favorites"),
    ]


def folder_actions(kind: str, state: FolderState) -> list[RowAction]:
    """The menu for a folder, which depends on what kind of folder it is."""
    actions = [RowAction(OPEN_FOLDER, "&Open"), RowAction(REFRESH, "&Refresh")]

    if state.is_podcast_show or is_podcast_show(kind):
        # The one this module exists for: a show found while browsing should
        # be followable, and following it belongs in the shared podcast
        # library so Quill Cast has it too.
        actions.append(
            RowAction(SUBSCRIBE_PODCAST, "Already Subscri&bed")
            if state.subscribed
            else RowAction(SUBSCRIBE_PODCAST, "Su&bscribe to This Podcast")
        )
        actions.append(RowAction(COPY_FEED, "Copy &Feed Address"))

    if is_followed_channel(kind) or state.is_followed_channel:
        actions.append(RowAction(UNFOLLOW_CHANNEL, "Stop Following This &Channel"))

    # "&Add", not "to &Favorites": Copy Feed Address already claims F on a
    # podcast show, and that collision was live on the one menu this module
    # was written for.
    noun = contents_noun(kind)
    if state.loaded_stations:
        actions.append(
            RowAction(FAVORITE_FOLDER, f"&Add All {state.loaded_stations} {noun} to Favorites")
        )
    else:
        actions.append(RowAction(FAVORITE_FOLDER, f"&Add All {noun} to Favorites"))

    if state.savable:
        actions.append(RowAction(DOWNLOAD_ALL, f"&Download All {state.savable} Files..."))
    return actions


def actions_for(
    kind: str,
    *,
    station: Any = None,
    playing: bool = False,
    saved: bool = False,
    can_download: bool = False,
    can_report: bool = False,
    open_site_label: str = "Open &Website",
    is_folder: bool = False,
    resolve_lazily: bool = False,
    folder_state: FolderState | None = None,
) -> list[RowAction]:
    """Every action this row offers, in menu order."""
    if station is not None:
        return station_actions(
            playing=playing,
            saved=saved,
            has_homepage=bool(getattr(station, "homepage", "")),
            can_download=can_download,
            can_report=can_report,
            is_recording=bool(getattr(station, "is_recording", False)),
            open_site_label=open_site_label,
        )
    if resolve_lazily:
        return lazy_leaf_actions(saved=saved)
    if is_folder:
        return folder_actions(kind, folder_state or FolderState())
    return []
