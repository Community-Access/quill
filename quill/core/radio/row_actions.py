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

from quill.core import dimmed_reason
from quill.core.radio import transport_commands
from quill.core.radio.cast_handoff import CAST_HANDOFFS
from quill.core.radio.row_state import FolderState as FolderState

# --- action ids ---------------------------------------------------------------
# Stable strings rather than an enum: the UI maps them to handlers, tests
# assert on them, and a new source adds one without touching a type.

PLAY = "play"
PAUSE = "pause"
STOP = "stop"
FAVORITE_ADD = "favorite.add"
FAVORITE_REMOVE = "favorite.remove"
FAVORITE_FOLDER = "favorite.folder"
COPY_LINK = "copy.link"
COPY_FEED = "copy.feed"
OPEN_SITE = "open.site"
DOWNLOAD = "download"
DOWNLOAD_ALL = "download.all"
REMOVE_DOWNLOAD = "download.remove"
REPORT_BAD = "report.bad"
DETAILS = "details"
OPEN_FOLDER = "folder.open"
CLOSE_FOLDER = "folder.close"
REFRESH = "folder.refresh"
#: Check every subscribed feed now, paused shows included (list.md 1.7).
REFRESH_ALL_PODCASTS = "podcast.refresh_all"
SUBSCRIBE_PODCAST = "podcast.subscribe"
UNSUBSCRIBE_PODCAST = "podcast.unsubscribe"
UNFOLLOW_CHANNEL = "channel.unfollow"
HIDE_SOURCE = "source.hide"
RESET_SOURCES = "source.reset"
REMOVE_SAVED = "youtube.remove_saved"
#: The YouTube branch's three ways in (rows only while it is empty).
ADD_YOUTUBE_CHANNEL = "youtube.add_channel"
ADD_YOUTUBE_PLAYLIST = "youtube.add_playlist"
ADD_YOUTUBE_VIDEO = "youtube.add_video"
VIEW_TRANSCRIPT = "view.transcript"
NEW_PODCAST_FOLDER = "podcastfolder.new"
RENAME_PODCAST_FOLDER = "podcastfolder.rename"
DELETE_PODCAST_FOLDER = "podcastfolder.delete"
MOVE_SHOW_TO_FOLDER = "podcast.move_to_folder"
MARK_ALL_PLAYED = "podcast.mark_all_played"
IMPORT_OPML = "podcast.import_opml"
ADD_PODCAST_URL = "podcast.add_by_url"
DOWNLOAD_ALL_EPISODES = "podcast.download_all_episodes"
REMOVE_DOWNLOADS = "podcast.remove_downloads"
MARK_EPISODE_PLAYED = "podcast.mark_episode_played"
MARK_EPISODE_UNPLAYED = "podcast.mark_episode_unplayed"
#: The playback verbs a row offers *while it is the thing playing*. They are
#: the same commands the transport keyboard and the Playback menu carry
#: (:mod:`quill.core.radio.transport_commands`) -- the ids are shared, so the
#: menu, the keys and the buttons cannot drift -- but the *labels* are this
#: menu's own, because a context menu has its own crowd of mnemonics to avoid.
PLAYING_PREVIOUS_CHAPTER = "transport.previous_chapter"
PLAYING_NEXT_CHAPTER = "transport.next_chapter"
PLAYING_CHAPTER_LIST = "transport.chapter_list"
PLAYING_WHERE = "transport.announce_position"
PLAYING_SPEED_UP = "transport.speed_up"
PLAYING_SPEED_DOWN = "transport.speed_down"
PLAYING_SPEED_RESET = "transport.speed_reset"
TOGGLE_CAPTIONS = "playback.captions"
FAVORITE_PLACE_ADD = "favorite.place_add"
FAVORITE_PLACE_REMOVE = "favorite.place_remove"
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

    ``reason`` is the other half of that bargain, added 2026-08-24: a dimmed
    item teaches the state only if it *says* the state. One lower-case clause
    from :mod:`quill.core.dimmed_reason`, spent by the menu's help string and
    by any surface that has to refuse the action out loud. A dimmed action
    with no reason fails ``tests/unit/ui/test_dimmed_action_reasons.py``.
    """

    id: str
    label: str
    enabled: bool = True
    reason: str = ""

    def unavailable_sentence(self) -> str:
        """What to say when this action is asked for and cannot run."""
        from quill.core import dimmed_reason

        return dimmed_reason.explain(self.label, self.reason)


#: Node kinds that name a podcast show rather than a shelf of them.
PODCAST_SHOW_KINDS = frozenset({"appleshow", "mypodcastshow", "pishow"})
#: Rows whose node id carries a transcript address, so it needs no playback.
TRANSCRIPT_IN_ID_KINDS = frozenset({"podepisode", "piepisode"})

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
    "pishow": "Episodes",
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


def playing_actions(*, has_chapters: bool, has_captions: bool) -> list[RowAction]:
    """The playback verbs for the row that IS the thing playing.

    Asked for directly: *"add all possible items to the context menu for every
    type including chapters, captions, transcripts"* (2026-08-18). The row you
    are standing on being the row you are hearing is the moment all of these
    mean something, and it is the moment a listener is most likely to want one
    -- so the menu that was four items becomes the whole player, without ever
    offering a verb the thing playing cannot do.

    The *labels* are this menu's own even though the *ids* are the transport
    table's. A context menu carries its own crowd of mnemonics -- Copy Link
    holds C, Details holds T, Download holds D -- so "&Chapters..." and "Where
    Am &I?" (which are right on a Playback menu) would each silently lose to an
    item already here. Ids stay shared so the menu, the keyboard and the
    buttons cannot drift apart.
    """
    actions: list[RowAction] = []
    if has_chapters:
        actions.append(RowAction(PLAYING_PREVIOUS_CHAPTER, "P&revious Chapter"))
        actions.append(RowAction(PLAYING_NEXT_CHAPTER, "&Next Chapter"))
        actions.append(RowAction(PLAYING_CHAPTER_LIST, "Chapter &List..."))
    if has_captions:
        actions.append(RowAction(TOGGLE_CAPTIONS, "Captions &On or Off"))
    # "&A", not "&W": Open Website already holds W on any row with a homepage,
    # and Transcript holds I.
    actions.append(RowAction(PLAYING_WHERE, "Where &Am I?"))
    actions.append(RowAction(PLAYING_SPEED_UP, "Speed &Up"))
    actions.append(RowAction(PLAYING_SPEED_DOWN, "Slow&er"))
    actions.append(RowAction(PLAYING_SPEED_RESET, "Bac&k to Normal Speed"))
    return actions


def menu_label(action: RowAction) -> str:
    """*action*'s label with its keystroke, ready for a popup menu.

    wx renders the text after a tab as an item's accelerator and a screen reader
    announces it -- without binding anything, which is exactly right here: the
    key is already installed on the window by
    :func:`quill.ui.radio.transport_keys.install`, and this only *says so*.

    The reason to say so is the reason the menu-bar rule in CLAUDE.md exists:
    walking a menu to discover there is no shortcut is a cost a listener pays on
    every visit. The playing row's seven verbs all have keys and the context
    menu never mentioned one, so the menu was the only route anybody learned.

    Only the transport ids get a key, and that is the whole point of the lookup:
    Play and Stop on a *row* are "play this station", not the player's own
    Ctrl+P, and labelling them with it would teach a key that does something
    else.
    """
    command = transport_commands.command(action.id)
    return f"{action.label}\t{command.key}" if command is not None else action.label


def transport_actions(*, playing: bool, downloaded: bool) -> list[RowAction]:
    """Play/Stop for a stream; Play, Pause and Stop for a saved file.

    A live station has two states and one verb toggles them, which is why the
    stream menu shows Stop *instead of* Play. A downloaded file has three --
    playing, paused, stopped -- so it gets a Play/Pause toggle and a Stop of
    its own, and both are on the menu at once because pausing an episode to
    answer the door is not the same as abandoning it.
    """
    if not downloaded:
        return [RowAction(STOP, "&Stop") if playing else RowAction(PLAY, "&Play")]
    return [
        RowAction(PAUSE, "&Pause") if playing else RowAction(PLAY, "&Play"),
        RowAction(STOP, "&Stop"),
    ]


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
    downloaded: bool = False,
    has_chapters: bool = False,
    has_captions: bool = False,
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

    *downloaded* says the row has a saved copy on disk, which changes two
    things. The transport verbs become the ones a *file* has -- Play/Pause and
    a separate Stop, because a saved episode has a middle you can stand still
    in, where a live stream only has on and off. And Download becomes Remove
    Download: offering to download a file that is already here is an offer to
    do nothing, and there was no other way to take one episode back off the
    disk (Remove All Downloads takes the whole show).
    """
    actions = [
        *transport_actions(playing=playing, downloaded=downloaded),
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
        actions.append(
            RowAction(REMOVE_DOWNLOAD, "Remo&ve Download")
            if downloaded
            else RowAction(DOWNLOAD, "&Download...")
        )
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
        # The rest of what Cast can do with this episode (cast_handoff).
        actions.extend(RowAction(*row) for row in CAST_HANDOFFS)
    if can_report and not is_recording:
        # A recording that will not play is not a "bad station"; the report
        # form asks about a stream, and answering it about an episode would
        # send a report nobody can act on.
        actions.append(RowAction(REPORT_BAD, "Report &Bad Station..."))
    if playing and is_recording:
        # Last, and only on the row actually playing: these act on the player,
        # not on the row, and putting them above Play/Favorites would push the
        # verbs that act on *this row* down the menu on every other row.
        actions.extend(playing_actions(has_chapters=has_chapters, has_captions=has_captions))
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
            RowAction(
                MARK_ALL_PLAYED,
                "Mark All as Pla&yed...",
                enabled=state.unheard > 0,
                reason=dimmed_reason.nothing_unheard(state.library_episodes),
            )
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
                reason=dimmed_reason.no_episodes_yet(),
            )
        )
        actions.append(
            RowAction(
                REMOVE_DOWNLOADS,
                "Remove All Do&wnloads...",
                enabled=state.downloaded_files > 0,
                reason=dimmed_reason.nothing_downloaded(),
            )
        )

    if kind == "mypodcasts":
        # The Subscriptions root organizes the library in place -- and grows
        # it: pasting a feed address is how a show that no directory lists
        # gets in. On this branch and the Podcasts branch only, never on a
        # show or an episode (they already ARE subscriptions).
        actions.append(RowAction(NEW_PODCAST_FOLDER, "New Fo&lder..."))
        actions.append(RowAction(ADD_PODCAST_URL, "Add a Podcast by &URL..."))
        # Refresh on a *show* re-reads that show. This is the other question --
        # "is there anything new anywhere?" -- which otherwise could only be
        # answered by opening every show in turn, and which the automatic check
        # answers on a cadence somebody may not have turned on.
        actions.append(RowAction(REFRESH_ALL_PODCASTS, "Chec&k All Feeds Now"))

    if kind == "apple" and state.root_source:
        # On the Podcasts branch itself: a whole OPML file's worth of shows
        # becomes subscriptions, folders included, shared with Quill Cast --
        # and the paste-a-feed door, same rule as the Subscriptions root.
        actions.append(RowAction(IMPORT_OPML, "I&mport Podcasts from OPML..."))
        actions.append(RowAction(ADD_PODCAST_URL, "Add a Podcast by &URL..."))

    if kind == "mypodcastfolder":
        # The same verbs Cast's manager offers on a folder, on the folder.
        # Delete promotes contents -- it can never silently unsubscribe.
        actions.append(RowAction(NEW_PODCAST_FOLDER, "New Fo&lder Inside..."))
        actions.append(RowAction(RENAME_PODCAST_FOLDER, "R&ename Folder..."))
        actions.append(RowAction(DELETE_PODCAST_FOLDER, "Dele&te Folder..."))
        actions.append(RowAction(REFRESH_ALL_PODCASTS, "Chec&k All Feeds Now"))

    if is_followed_channel(kind) or state.is_followed_channel:
        # "&P", not "&C": an expanded channel's menu now leads with "&Close".
        actions.append(RowAction(UNFOLLOW_CHANNEL, "Sto&p Following This Channel"))

    if kind == "ytplaylist":
        # A saved playlist: removable from the same menu that plays it.
        actions.append(RowAction(REMOVE_SAVED, "Remo&ve from YouTube"))

    if kind in YOUTUBE_ROWS:
        actions.extend(youtube_add_actions())

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

    if not state.root_source:
        # Favorites held only things you *play*, so the only rows that could be
        # saved were the leaves: you could favorite one episode and not the
        # show ("add to favorites should be in the podcast context menu or
        # frankly all context menus for all types", 2026-08-18). A folder is
        # saved as a *place* -- the browse id, which opens back to exactly
        # here.
        #
        # Not on a root source: TuneIn is permanently in the tree already, and
        # a Favorites entry that duplicates a branch you cannot remove is
        # clutter. "&S" is free on every other folder menu; on a root source it
        # is Search This Source.
        noun = "Show" if (state.is_podcast_show or is_podcast_show(kind)) else "Place"
        actions.append(
            RowAction(FAVORITE_PLACE_REMOVE, f"Remove Thi&s {noun} from Favorites")
            if state.saved_place
            else RowAction(FAVORITE_PLACE_ADD, f"Add Thi&s {noun} to Favorites")
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


#: Every row in the branch offers them; the rows leave once it has content.
YOUTUBE_ROWS = frozenset({"youtube", "youtubechannel", "youtubevideos", "ytplaylist", "ytvideo"})


def youtube_add_actions() -> list[RowAction]:
    """Add a Channel / Playlist / Video, in the order the branch lists them.

    "&e", "&l", "&U" are free on a root source's menu (&A/&C/&O/&R/&S/&H/&t
    are taken) *and* on a saved row's (&V is "Remo&ve from YouTube").
    """
    return [
        RowAction(ADD_YOUTUBE_CHANNEL, "Add a Chann&el..."),
        RowAction(ADD_YOUTUBE_PLAYLIST, "Add a Play&list..."),
        RowAction(ADD_YOUTUBE_VIDEO, "Add a Video &URL..."),
    ]


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
    downloaded: bool = False,
    has_chapters: bool = False,
    has_captions: bool = False,
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
            downloaded=downloaded,
            has_chapters=has_chapters,
            has_captions=has_captions,
        )
        if kind in TRANSCRIPT_IN_ID_KINDS:  # and, on pi rows, unsubscribed
            actions.append(RowAction(VIEW_TRANSCRIPT, "View Transcr&ipt..."))
        else:
            from quill.core.radio.youtube_urls import is_youtube_url

            if is_youtube_url(str(getattr(station, "stream_url", ""))):
                # A YouTube video's captions are its transcript; one resolve
                # (the same request playing would make) fetches them, no
                # playback required.
                actions.append(RowAction(VIEW_TRANSCRIPT, "View Transcr&ipt..."))
        if kind == "ytvideo":  # removable from the menu that plays it
            actions.append(RowAction(REMOVE_SAVED, "Remo&ve from YouTube"))
            actions.extend(youtube_add_actions())
        return actions
    if resolve_lazily:
        return lazy_leaf_actions(saved=saved)
    if is_folder:
        return folder_actions(kind, folder_state or FolderState())
    return []
