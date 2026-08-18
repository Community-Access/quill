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
CLOSE_FOLDER = "folder.close"
REFRESH = "folder.refresh"
SUBSCRIBE_PODCAST = "podcast.subscribe"
UNSUBSCRIBE_PODCAST = "podcast.unsubscribe"
UNFOLLOW_CHANNEL = "channel.unfollow"
HIDE_SOURCE = "source.hide"
RESET_SOURCES = "source.reset"
REMOVE_SAVED = "youtube.remove_saved"
VIEW_TRANSCRIPT = "view.transcript"
NEW_PODCAST_FOLDER = "podcastfolder.new"
RENAME_PODCAST_FOLDER = "podcastfolder.rename"
DELETE_PODCAST_FOLDER = "podcastfolder.delete"
MOVE_SHOW_TO_FOLDER = "podcast.move_to_folder"
MARK_ALL_PLAYED = "podcast.mark_all_played"
IMPORT_OPML = "podcast.import_opml"
DOWNLOAD_ALL_EPISODES = "podcast.download_all_episodes"
REMOVE_DOWNLOADS = "podcast.remove_downloads"
MARK_EPISODE_PLAYED = "podcast.mark_episode_played"
MARK_EPISODE_UNPLAYED = "podcast.mark_episode_unplayed"
RECORD_STATION = "station.record"
SCHEDULE_RECORDING = "station.schedule_recording"
RENAME_FAVORITE = "favorite.rename"
SEARCH_SOURCE = "source.search"

#: Root sources whose contents Find Stations can search with the provider's
#: own engine, mapped to the Source facet the search dialog opens on. This is
#: what makes "Search This Source..." intelligent: standing on Podcasts
#: searches podcasts, standing on iHeart searches iHeart -- each through the
#: same federated search window the Station menu opens, pre-narrowed.
SEARCHABLE_SOURCES: dict[str, str] = {
    "popular": "Radio Browser",
    "trending": "Radio Browser",
    "recent": "Radio Browser",
    "rbcountry": "Radio Browser",
    "rblang": "Radio Browser",
    "rbgenre": "Radio Browser",
    "rbcodec": "Radio Browser",
    "acb": "ACB Media",
    "soma": "SomaFM",
    "tunein": "TuneIn",
    "iheart": "iHeart",
    "apple": "Podcasts",
    "youtube": "YouTube",
    # These two must equal the modules' CATEGORY_LABELs -- the facet dropdown
    # is built from those constants, and a mismatched string opens the dialog
    # on "All sources" silently.
    "m3u": "Community M3U",
    "xiph": "Xiph",
}


@dataclass(frozen=True, slots=True)
class RowAction:
    """One menu item: what it is, and what it should read as.

    ``enabled`` is the one sanctioned departure from "a row that cannot do a
    thing has no item for it": Mark All as Played with nothing unheard is a
    *state* of a verb the row genuinely owns, and a dimmed item teaches that
    state -- where a vanishing one would read as the feature coming and going.
    """

    id: str
    label: str
    enabled: bool = True


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
    #: Whether the tree row is currently expanded (Open reads as Close then).
    expanded: bool = False
    #: A top-level source branch (Popular Stations, Podcasts, ...) -- the
    #: rows that can be hidden in place instead of via Choose Browse Sources.
    root_source: bool = False
    #: Unplayed episodes in this subscribed show, from the shared library
    #: (a local read). Drives Mark All as Played's enabled state: the verb
    #: is always on a subscribed show's menu, dimmed when nothing is unheard.
    unheard: int = 0
    #: Episodes the shared library holds for this subscribed show (a local
    #: read). Lets Download All Episodes appear before the branch is ever
    #: expanded -- the library already knows the list.
    library_episodes: int = 0
    #: Files sitting in this show's downloads folder on disk (a local read).
    #: Drives Remove All Downloads: always on a subscribed show's menu,
    #: dimmed when there is nothing to remove -- same rule as Mark All.
    downloaded_files: int = 0


#: Node kinds that name a podcast show rather than a shelf of them.
PODCAST_SHOW_KINDS = frozenset({"appleshow", "mypodcastshow"})

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
    "mypodcasts": "Shows",
    "mypodcastfolder": "Shows",
    "mypodcastshow": "Episodes",
    "ytplaylist": "Videos",
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
    can_record: bool = False,
    episode_played: bool | None = None,
) -> list[RowAction]:
    """The menu for a playable row.

    *is_recording* is what separates a podcast episode or a book chapter from
    a live station: a recording has a beginning and an end, so "Download" is a
    sensible thing to offer and "Report Bad Station" is not. The reverse also
    holds: a live station has no end, so *recording* it is the sensible verb
    (*can_record*), where Download honestly is not (downloadable.LIVE_REASON
    says exactly this when asked). *episode_played* is three-valued: ``None``
    for a row that is not a subscribed podcast episode (no mark item at all),
    else the episode's played state, which picks which direction of the
    toggle the menu offers.
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
    if saved:
        # The same custom-name prompt the Favorites manager offers, from the
        # row that is already saved -- blank restores the directory's name.
        actions.append(RowAction(RENAME_FAVORITE, "Rena&me Favorite..."))
    if has_homepage:
        actions.append(RowAction(OPEN_SITE, open_site_label))
    if can_download:
        actions.append(RowAction(DOWNLOAD, "&Download..."))
    if can_record and not is_recording:
        # Record answers the want Download cannot on a live stream: keep it.
        actions.append(RowAction(RECORD_STATION, "&Record This Station..."))
        actions.append(RowAction(SCHEDULE_RECORDING, "Schedule Recordin&g..."))
    if episode_played is not None:
        actions.append(
            RowAction(MARK_EPISODE_UNPLAYED, "Mark Episode as Unpla&yed")
            if episode_played
            else RowAction(MARK_EPISODE_PLAYED, "Mark Episode as Pla&yed")
        )
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
    # An expanded row's first action is the one that still does something:
    # "Open" on an already-open folder read as either broken or a lie.
    actions = [
        RowAction(CLOSE_FOLDER, "&Close") if state.expanded else RowAction(OPEN_FOLDER, "&Open"),
        RowAction(REFRESH, "&Refresh"),
    ]

    if state.is_podcast_show or is_podcast_show(kind):
        # The one this module exists for: a show found while browsing should
        # be followable, and following it belongs in the shared podcast
        # library so Quill Cast has it too. Subscribed, the same slot turns
        # into a real Unsubscribe -- "Already Subscribed" was a menu item
        # whose only power was to repeat itself.
        actions.append(
            RowAction(UNSUBSCRIBE_PODCAST, "Unsu&bscribe from This Podcast")
            if state.subscribed
            else RowAction(SUBSCRIBE_PODCAST, "Su&bscribe to This Podcast")
        )
        actions.append(RowAction(COPY_FEED, "Copy &Feed Address"))

    if kind == "mypodcastshow" and state.subscribed:
        # Filing lives where the shows live: the same shared folders Quill
        # Cast's manager edits, from the row a listener is already on.
        actions.append(RowAction(MOVE_SHOW_TO_FOLDER, "Mo&ve to Folder..."))
        # Always present, dimmed when there is nothing unheard: the same verb
        # Quill Cast's Episode menu carries, acting on the same shared state.
        actions.append(
            RowAction(MARK_ALL_PLAYED, "Mark All as Pla&yed...", enabled=state.unheard > 0)
        )
        # The download pair, same shape as Quill Cast's show menu. The count
        # comes from the shared library, so the verb works without ever
        # expanding the branch; both dim rather than vanish (state of a verb
        # the row owns, like Mark All above).
        count = state.library_episodes
        actions.append(
            RowAction(
                DOWNLOAD_ALL_EPISODES,
                f"Download All {count} Episo&des..." if count else "Download All Episo&des...",
                enabled=count > 0,
            )
        )
        actions.append(
            RowAction(
                REMOVE_DOWNLOADS,
                "Remove All Do&wnloads...",
                enabled=state.downloaded_files > 0,
            )
        )

    if kind == "mypodcasts":
        # The Subscriptions root organizes the library in place.
        actions.append(RowAction(NEW_PODCAST_FOLDER, "New Fo&lder..."))

    if kind == "apple" and state.root_source:
        # On the Podcasts branch itself: a whole OPML file's worth of shows
        # becomes subscriptions, folders included, shared with Quill Cast.
        actions.append(RowAction(IMPORT_OPML, "I&mport Podcasts from OPML..."))

    if kind == "mypodcastfolder":
        # The same verbs Cast's manager offers on a folder, on the folder.
        # Delete promotes contents -- it can never silently unsubscribe.
        actions.append(RowAction(NEW_PODCAST_FOLDER, "New Fo&lder Inside..."))
        actions.append(RowAction(RENAME_PODCAST_FOLDER, "R&ename Folder..."))
        actions.append(RowAction(DELETE_PODCAST_FOLDER, "Dele&te Folder..."))

    if is_followed_channel(kind) or state.is_followed_channel:
        # "&P", not "&C": an expanded channel's menu now leads with "&Close".
        actions.append(RowAction(UNFOLLOW_CHANNEL, "Sto&p Following This Channel"))

    if kind == "ytplaylist":
        # A saved playlist: removable from the same menu that plays it.
        actions.append(RowAction(REMOVE_SAVED, "Remo&ve from YouTube"))

    # "&Add", not "to &Favorites": Copy Feed Address already claims F on a
    # podcast show, and that collision was live on the one menu this module
    # was written for. Only when something is actually loaded: with nothing
    # under the row yet, "Add All Episodes to Favorites" adds nothing, and the
    # honest menu leaves it out (Open loads the rows, and then it appears).
    if state.loaded_stations:
        noun = contents_noun(kind)
        actions.append(
            RowAction(FAVORITE_FOLDER, f"&Add All {state.loaded_stations} {noun} to Favorites")
        )

    if state.savable and kind != "mypodcastshow":
        # A subscribed show's menu already carries Download All Episodes
        # (library-counted, above); a second download-all row for the same
        # files would be the menu disagreeing with itself about the count.
        actions.append(RowAction(DOWNLOAD_ALL, f"&Download All {state.savable} Files..."))

    if state.root_source and kind in SEARCHABLE_SOURCES:
        # The provider's own search, pre-narrowed to this source -- the
        # intelligent half of the tree-top Search All Sources row.
        actions.append(RowAction(SEARCH_SOURCE, "&Search This Source..."))

    if state.root_source:
        # Hiding in place: the same rule as Choose Browse Sources (a hidden
        # branch is not in the tree and never contacted), one right-click
        # nearer. Reset rides along so the way back is on the same menu that
        # hid things -- nobody should need to remember which dialog restores
        # the defaults.
        actions.append(RowAction(HIDE_SOURCE, "&Hide This Source"))
        actions.append(RowAction(RESET_SOURCES, "Rese&t Sources to Default"))
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
    can_record: bool = False,
    episode_played: bool | None = None,
) -> list[RowAction]:
    """Every action this row offers, in menu order."""
    if station is not None:
        actions = station_actions(
            playing=playing,
            saved=saved,
            has_homepage=bool(getattr(station, "homepage", "")),
            can_download=can_download,
            can_report=can_report,
            is_recording=bool(getattr(station, "is_recording", False)),
            open_site_label=open_site_label,
            can_record=can_record,
            episode_played=episode_played,
        )
        if kind == "podepisode":
            # The row's node id carries the feed's transcript address, so the
            # transcript is readable without playing the episode.
            actions.append(RowAction(VIEW_TRANSCRIPT, "View Transcr&ipt..."))
        else:
            from quill.core.radio.youtube_urls import is_youtube_url

            if is_youtube_url(str(getattr(station, "stream_url", ""))):
                # A YouTube video's captions are its transcript; one resolve
                # (the same request playing would make) fetches them, no
                # playback required.
                actions.append(RowAction(VIEW_TRANSCRIPT, "View Transcr&ipt..."))
        if kind == "ytvideo":
            # A saved single video: removable from the same menu, like a
            # followed channel.
            actions.append(RowAction(REMOVE_SAVED, "Remo&ve from YouTube"))
        return actions
    if resolve_lazily:
        return lazy_leaf_actions(saved=saved)
    if is_folder:
        return folder_actions(kind, folder_state or FolderState())
    return []
