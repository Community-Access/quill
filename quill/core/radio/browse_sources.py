"""Every browse source, as one function the tree dialog calls.

``browse(node_id)`` returns that node's children; ``resolve(node_id)`` turns a
lazily-resolved leaf into a playable station. That is the entire surface the UI
needs, which is the point: the Browse Stations dialog no longer contains a
branch per source, so adding the tenth source costs one entry in
:data:`ROOT_SOURCES` and one handler here, not edits in six places inside a wx
module under a size budget.

Everything is wx-free and unit-tested without a UI. Every source keeps its own
Safe Mode refusal and its own reviewed egress site; this module adds no network
call of its own, it only routes.

Node id grammar, all opaque to the caller (see :mod:`browse_nodes`)::

    favorites                       your saved stations and folders
    favorites:<folder>
    popular | trending | recent     Radio Browser rankings
    acb | nfb | reading | soma      flat, mostly bundled
    rbgenre | rbgenre:<tag>         Radio Browser by genre
    rbcountry | rbcountry:<country> ...then states, or stations when there are none
    rbstate:<country>\\t<state>
    rblang | rblang:<language>
    wx | wx:<state-slug>            NOAA Weather Radio
    tunein | tunein:<browse-url>    TuneIn's own remote tree
    tuneinstation:<guide-id>        (leaf, resolved on activation)
    iheart | iheart:<genre-id>      ...then A-Z letters
    iheartletter:<genre-id>\\t<L>
    iheartmarkets | iheartmarkets:<L> | iheartmarket:<market-id>
    rbcodec | rbcodec:<codec>        Radio Browser by codec ("Quality")
    networks | networkgroup:<group> | network:<network-id>
    m3u | m3u:<slug>                Community M3U catalog
    xiph | xiph:<genre>             Xiph / Icecast directory
    apple | apple:<storefront>      Apple Podcasts, keyless
    podcastindex | pitrending | pitrending:<category> | picategories
    pishow:<feed-url>               a Podcast Index show's episodes, unsubscribed
    piepisode:<audio-url>           ...one of them, playable
    applegenre:<storefront>\\t<genre-id>
    appleshow:<collection-id>       ...then that show's episodes
    mypodcasts | mypodcastfolder:<folder-id> | mypodcastshow:<feed-url>
                                    Subscriptions (the shared podcast library)
    archive | archive:<collection>  Internet Archive, nested to any depth
    archiveitem:<identifier>        ...then that item's files
    librivox | librivoxgenre:<g> | librivoxauthors:<L> | librivoxauthor:<name>
    librivoxbook:<id>               ...a book's sections
    gutenberg | gutenbergtopic:<t> | gutenberglang:<code>
    audiopub | audiopubdiscover:<page>  AudioPub community audio (Discover)
    audius | audius:<genre>
    mixcloud | mixcloudfmt:<music|talk> | mixcloudcat:<slug>
    ccmixter | ccmixter:<tag>
    myservers | myservers:<root>    servers the listener added
    youtube | youtubechannel:<url> | youtubevideos:<url>\t<page>
    wikidata | wikidata:<axis> | wikidata:<axis>\t<group> | wikidatadial:<band>
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from quill.core.radio import (
    acb_media,
    iheart,
    m3u_catalog,
    networks,
    nfb_media,
    radio_browser,
    reading_services,
    soma_fm,
    tunein,
    xiph,
)
from quill.core.radio.browse_failure import (
    LAST_FAILURE,
    _thread_key,
)
from quill.core.radio.browse_failure import (
    last_error_was_network as last_error_was_network,
)
from quill.core.radio.browse_failure import (
    remember_failure as _remember_failure,
)

# The free-music catalogs -- Audius, Mixcloud, ccMixter -- live in their own
# module (GATE-11 extraction); registered in _HANDLERS like every other source.
from quill.core.radio.browse_free_music import (
    browse_audius as _browse_audius,
)
from quill.core.radio.browse_free_music import (
    browse_audius_trending as _browse_audius_trending,
)
from quill.core.radio.browse_free_music import (
    browse_ccmixter as _browse_ccmixter,
)
from quill.core.radio.browse_free_music import (
    browse_mixcloud as _browse_mixcloud,
)
from quill.core.radio.browse_free_music import (
    browse_mixcloud_category as _browse_mixcloud_category,
)
from quill.core.radio.browse_free_music import (
    browse_mixcloud_format as _browse_mixcloud_format,
)
from quill.core.radio.browse_helpers import (
    iheart_letter_groups,
    letter_groups,
    wx_playable_stations,
    wx_state_folders,
)
from quill.core.radio.browse_libraries import (
    _browse_apple,
    _browse_apple_chart,
    _browse_apple_genre,
    _browse_apple_show,
    _browse_audiopub,
    _browse_audiopub_discover,
    _browse_gutenberg,
    _browse_gutenberg_lang,
    _browse_gutenberg_topic,
    _browse_my_podcast_folder,
    _browse_my_podcast_show,
    _browse_my_podcasts,
)

# Whether an empty branch was empty or broken (GATE-11 extraction);
# re-exported so callers import one name.
# LibriVox and its Internet Archive fallback (GATE-11 extraction).
from quill.core.radio.browse_librivox import (
    _browse_librivox,
    _browse_librivox_authors,
    _browse_librivox_book,
    _browse_librivox_genres,
    _browse_librivox_recent,
)
from quill.core.radio.browse_librivox import (
    refuse_when_offline as refuse_when_offline,
)
from quill.core.radio.browse_nodes import (
    ARG_SEP,
    BrowseNode,
    action,
    folder,
    lazy_leaf,
    leaf,
    make_id,
    split_id,
)

# The Podcast Index branch: shows you can open without subscribing to them.
from quill.core.radio.browse_podcast_index import (
    browse_categories,
    browse_root,
    browse_show,
    browse_trending,
)
from quill.core.radio.models import RadioStation

#: The top-level branches, in tree order.
ROOT_SOURCES: tuple[tuple[str, str], ...] = (
    ("favorites", "Favorites"),
    ("popular", "Popular Stations"),
    ("trending", "Trending Now"),
    ("recent", "Recently Added or Changed"),
    ("rbcountry", "By Country"),
    ("rblang", "By Language"),
    ("rbgenre", "By Genre"),
    ("rbcodec", "By Quality"),
    ("wx", "Weather / NOAA"),
    ("acb", "ACB Media"),
    ("nfb", "NFB Radio"),
    ("reading", "Radio Reading Services"),
    ("soma", "SomaFM"),
    ("tunein", "TuneIn"),
    ("iheart", "iHeart"),
    ("networks", "Networks"),
    ("m3u", "Community M3U (Music Genres)"),
    ("xiph", "Xiph / Icecast Directory"),
    ("apple", "Podcasts (Apple)"),
    ("podcastindex", "Podcast Index"),
    ("archive", "Internet Archive"),
    ("librivox", "LibriVox Audiobooks"),
    ("gutenberg", "Project Gutenberg Audiobooks"),
    ("audiopub", "AudioPub (Community Audio)"),
    ("audius", "Audius (Independent Music)"),
    ("mixcloud", "Mixcloud (Shows & DJ Sets)"),
    ("ccmixter", "ccMixter (Creative Commons)"),
    ("myservers", "My Servers"),
    ("youtube", "YouTube"),
    ("wikidata", "Explore (Wikidata)"),
)

#: Branches that work with no network at all, so Safe Mode leaves them alone.
LOCAL_SOURCES = frozenset({
    "favorites",
    "acb",
    "nfb",
    "networks",
    "networkgroup",
    # The lists themselves are local; only opening one reaches the network.
    "myservers",
    "youtube",
})


# --- flat station sources -----------------------------------------------------

_FLAT: dict[str, Callable[[bool], list[RadioStation]]] = {
    "popular": lambda safe: radio_browser.popular_stations(safe_mode=safe),
    "trending": lambda safe: radio_browser.trending_stations(safe_mode=safe),
    "recent": lambda safe: radio_browser.recently_changed_stations(safe_mode=safe),
    "acb": lambda _safe: acb_media.acb_media_stations(),
    "nfb": lambda _safe: nfb_media.nfb_media_stations(),
    "reading": lambda safe: reading_services.list_reading_services(safe_mode=safe),
    "soma": lambda safe: soma_fm.search_stations("", safe_mode=safe),
}

#: Sources that expose the shared genre protocol (fetch_genres / genre_display /
#: fetch_genre_stations). One code path for three catalogs.
_GENRE_MODULES = {"rbgenre": radio_browser, "m3u": m3u_catalog, "xiph": xiph}


def _stations(rows: Sequence[RadioStation]) -> list[BrowseNode]:
    return [leaf(station) for station in rows]


# --- per-source handlers ------------------------------------------------------


def _favorite_node(fav: object) -> BrowseNode:
    """One saved favorite as a row: a stream to play, or a place to open.

    A *place* (a podcast show, a book, a followed channel -- see
    :func:`quill.core.radio.favorites.place_station`) comes back as a folder
    carrying the browse id it was saved from, so opening it from Favorites
    lands exactly where opening it from its own source would. Everything the
    row can do afterwards -- subscribe, download all, expand -- follows from
    that id, with no second implementation of any of it.
    """
    from quill.core.radio.favorites import place_node_id

    station = fav.station  # type: ignore[attr-defined]
    node_id = place_node_id(station)
    if not node_id:
        return leaf(station)
    return folder(node_id, fav.display_label, note="saved place")  # type: ignore[attr-defined]


def _browse_favorites(args: list[str], *, safe_mode: bool, favorites: object) -> list[BrowseNode]:
    if favorites is None:
        return []
    ordered = list(favorites.favorites_in_display_order())  # type: ignore[attr-defined]
    if args and args[0]:
        wanted = args[0]
        return [_favorite_node(fav) for fav in ordered if fav.folder == wanted]
    nodes = [_favorite_node(fav) for fav in ordered if not fav.folder]
    for name in favorites.folders_in_display_order():  # type: ignore[attr-defined]
        count = sum(1 for fav in ordered if fav.folder == name)
        nodes.append(folder(make_id("favorites", name), name, child_count=count))
    return nodes


def _browse_genre_source(kind: str, args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    module = _GENRE_MODULES[kind]
    if args and args[0]:
        return _stations(module.fetch_genre_stations(args[0], safe_mode=safe_mode))
    return [
        folder(make_id(kind, slug), module.genre_display(slug))
        for slug in module.fetch_genres(safe_mode=safe_mode)
    ]


def _browse_country(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    if not (args and args[0]):
        return [
            folder(make_id("rbcountry", name), name)
            for name in radio_browser.list_countries(safe_mode=safe_mode)
        ]
    country = args[0]
    states = radio_browser.list_states(country, safe_mode=safe_mode)
    if states:
        return [folder(make_id("rbstate", country, state), state) for state in states]
    # Plenty of countries have no state breakdown at all; showing an empty
    # folder there would be a dead end, so drop straight to the stations.
    return _stations(radio_browser.stations_by_country(country, safe_mode=safe_mode))


def _browse_state(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    country = args[0] if args else ""
    state = args[1] if len(args) > 1 else ""
    return _stations(radio_browser.stations_by_state(state, country=country, safe_mode=safe_mode))


def _browse_language(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    if args and args[0]:
        return _stations(radio_browser.stations_by_language(args[0], safe_mode=safe_mode))
    return [
        folder(make_id("rblang", name), name.title())
        for name in radio_browser.list_languages(safe_mode=safe_mode)
    ]


def _browse_weather(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    if args and args[0]:
        return _stations(wx_playable_stations(args[0], safe_mode=safe_mode))
    return [
        folder(make_id("wx", state.slug), state.name, child_count=state.stations_with_feeds)
        for state in wx_state_folders(safe_mode=safe_mode)
    ]


def _browse_tunein(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    target = args[0] if args else ""
    nodes: list[BrowseNode] = []
    for row in tunein.browse(target, safe_mode=safe_mode):
        if row.is_station:
            nodes.append(
                lazy_leaf(
                    make_id("tuneinstation", row.guide_id),
                    row.title,
                    note="resolves when you play it",
                )
            )
        else:
            nodes.append(folder(make_id("tunein", row.browse_url or row.guide_id), row.title))
    return nodes


def _browse_codec(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """Radio Browser's codec directory as a Quality axis.

    vTuner sells this classification; the open directory publishes it. Each
    folder carries its station count, because a codec with eleven stations and
    one with eight thousand should not look alike before you open them.
    """
    if args and args[0]:
        return _stations(radio_browser.stations_by_codec(args[0], safe_mode=safe_mode))
    return [
        folder(make_id("rbcodec", name), name, child_count=count)
        for name, count in radio_browser.list_codecs(safe_mode=safe_mode)
        if count
    ]


def _browse_iheart_markets(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """iHeart's 317 markets, grouped A-Z by city, then the city's stations.

    radio2.md listed this axis as "plausible, not verified"; it is verified now
    (2026-08-13) and it is the local-radio axis a listener actually wants -- not
    "rock stations somewhere" but "stations in Phoenix".
    """
    markets = iheart.fetch_markets(safe_mode=safe_mode)
    if not (args and args[0]):
        return [
            folder(make_id("iheartmarkets", group), group, child_count=len(rows))
            for group, rows in letter_groups(markets, lambda m: m.city)
        ]
    wanted = args[0]
    for group, rows in letter_groups(markets, lambda m: m.city):
        if group == wanted:
            return [
                folder(
                    make_id("iheartmarket", str(market.market_id)),
                    market.display_name,
                    child_count=market.station_count or None,
                )
                for market in rows
            ]
    return []


def _browse_iheart_market(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    if not args or not args[0]:
        return []
    return _stations(iheart.fetch_market_stations(int(args[0]), safe_mode=safe_mode))


def _browse_iheart(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    if not (args and args[0]):
        # By City first: someone opening iHeart is usually after local radio,
        # and the genre list is the same everywhere.
        nodes = [folder("iheartmarkets", "By City")]
        nodes += [
            folder(make_id("iheart", str(genre.genre_id)), genre.name)
            for genre in iheart.fetch_genres(safe_mode=safe_mode)
        ]
        return nodes
    genre_id = args[0]
    stations = iheart.fetch_genre_stations(int(genre_id), safe_mode=safe_mode)
    return [
        folder(make_id("iheartletter", genre_id, letter), letter, child_count=len(rows))
        for letter, rows in iheart_letter_groups(stations)
    ]


def _browse_iheart_letter(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """Stations under one A-Z group.

    Re-derives them from the genre rather than carrying a fetched payload in the
    node id, because ids must stay stable across sessions for browse-position
    memory. The genre fetch is the same request the parent already made, so with
    the directory cache in front of it this costs nothing.
    """
    genre_id = args[0] if args else ""
    letter = args[1] if len(args) > 1 else ""
    if not genre_id:
        return []
    stations = iheart.fetch_genre_stations(int(genre_id), safe_mode=safe_mode)
    for group, rows in iheart_letter_groups(stations):
        if group == letter:
            return _stations(rows)
    return []


def _browse_networks(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    return [folder(make_id("networkgroup", group), group) for group in networks.groups()]


def _browse_network_group(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    group = args[0] if args else ""
    nodes = []
    for network in networks.networks_in_group(group):
        nodes.append(
            folder(make_id("network", network.network_id), network.display_name, note=network.note)
        )
    return nodes


def _browse_network(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    network = networks.get_network(args[0]) if args else None
    if network is None:
        return []
    return _stations(networks.network_stations(network, safe_mode=safe_mode))


# --- Internet Archive ---------------------------------------------------------


def _browse_archive(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """The Archive's own collection tree, walked with one query shape.

    Sub-collections first, then the recordings filed directly in this
    collection, because a series belongs above its episodes. A ``seen`` set is
    not needed here -- each expansion is one level -- but the *identifier* is
    never the same as its parent's, so a collection that lists itself simply
    shows up once as a child and opens normally.
    """
    from quill.core.radio import internet_archive as ia

    if not (args and args[0]):
        return [
            folder(make_id("archive", identifier), label)
            for identifier, label in ia.ROOT_COLLECTIONS
        ]
    collection = args[0]
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    sub_total, subs = ia.children(collection, collections=True, page=page, safe_mode=safe_mode)
    item_total, items = ia.children(collection, collections=False, page=page, safe_mode=safe_mode)
    nodes = [
        folder(make_id("archive", item.identifier), item.title)
        for item in subs
        if item.identifier != collection
    ]
    nodes += [folder(make_id("archiveitem", item.identifier), item.display_name) for item in items]
    # No silent caps: a folder showing 100 of 8,710 must say so and offer more.
    if item_total > page * ia.PAGE_SIZE or sub_total > page * ia.PAGE_SIZE:
        shown = min(page * ia.PAGE_SIZE, item_total + sub_total)
        nodes.append(
            folder(
                make_id("archive", collection, str(page + 1)),
                "More...",
                note=f"showing {shown} of {item_total + sub_total}",
            )
        )
    return nodes


def _browse_archive_item(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.radio import internet_archive as ia

    if not args or not args[0]:
        return []
    stations = ia.item_files(args[0], safe_mode=safe_mode)
    return [
        leaf(station, note=station.tags[0] if station.tags else "no rights information published")
        for station in stations
    ]


# --- Project Gutenberg --------------------------------------------------------


# --- My Servers ----------------------------------------------------------------


def _browse_my_servers(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """The servers the listener added, and what each is serving right now.

    The branch no directory can give you: the community station, the church, the
    school, the reading service that runs its own Icecast box and was never
    indexed anywhere. Now-playing text rides along on each mount, so you can hear
    what is on before you tune to it.
    """
    from quill.core.radio import my_servers

    if args and args[0]:
        stations = my_servers.mounts(args[0], safe_mode=safe_mode)
        return [leaf(station, note=station.tags[0] if station.tags else "") for station in stations]
    nodes: list[BrowseNode] = []
    for server in my_servers.ServerStore().all():
        nodes.append(folder(make_id("myservers", server.root), server.display_name))
    nodes.append(action("addserver", "Add a Server...", note="Icecast or SHOUTcast"))
    return nodes


# --- YouTube channels ------------------------------------------------------------


def _browse_youtube(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """Everything YouTube the listener added, with no Google account anywhere.

    Channels first (they expand into the most), then saved playlists, then
    saved single videos as playable rows -- and one Add... action per kind, so
    a pasted link of any shape has an obvious way in (QA: "I do not see how I
    can add a YouTube link easily here without searching").
    """
    from quill.core.radio import youtube_channels as yt
    from quill.core.radio import youtube_saved

    if not (args and args[0]):
        nodes = [
            folder(make_id("youtubechannel", channel.url), channel.display_name)
            for channel in yt.ChannelStore().all()
        ]
        saved = youtube_saved.SavedStore()
        nodes += [
            folder(make_id("ytplaylist", item.url, "1"), item.display_name, note=item.note)
            for item in saved.all(youtube_saved.PLAYLIST)
        ]
        for item in saved.all(youtube_saved.VIDEO):
            live = item.is_live or not item.url.startswith("https://www.youtube.com/watch")
            nodes.append(
                leaf(
                    RadioStation(
                        name=item.display_name,
                        stream_url=item.url,
                        homepage=item.url,
                        source="YouTube",
                        # A watch link is a finished video (seeks, resumes); a
                        # channel-live page is a broadcast that is simply on.
                        is_recording=not live,
                        # What the video is *about*, straight into the details
                        # panel -- the one thing an address could never say.
                        notes=item.description,
                    ),
                    node_id=make_id("ytvideo", item.url),
                    # "TED, 20 minutes 3 seconds", spoken after the title.
                    note=item.note,
                )
            )
        if not nodes:
            # Only while there is nothing here. Three permanent "Add a ..."
            # rows at the bottom of a growing list are three rows to arrow
            # past on every visit, for a thing you do rarely -- and they are
            # on this branch's context menu (and every row's) now, which is
            # where a verb belongs once the list has content in it. Same shape
            # as the empty Subscriptions branch's three ways in.
            nodes.append(action("addchannel", "Add a Channel...", note="paste a channel address"))
            nodes.append(action("addplaylist", "Add a Playlist...", note="paste a playlist link"))
            nodes.append(action("addvideo", "Add a Video...", note="paste a video link"))
        return nodes
    return []


def _browse_youtube_channel(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.radio import youtube_channels as yt

    if not args or not args[0]:
        return []
    url = args[0]
    nodes: list[BrowseNode] = [folder(make_id("youtubevideos", url, "1"), "Uploads")]
    for title, playlist_url in yt.playlists(url, safe_mode=safe_mode):
        nodes.append(folder(make_id("youtubevideos", playlist_url, "1"), title))
    return nodes


def _browse_youtube_videos(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.radio import youtube_channels as yt

    if not args or not args[0]:
        return []
    url = args[0]
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    rows, more = yt.videos(url, page=page, safe_mode=safe_mode)
    nodes = [leaf(station) for station in rows]
    if more:
        # A channel with four thousand uploads must not try to be one level.
        nodes.append(folder(make_id("youtubevideos", url, str(page + 1)), "More..."))
    return nodes


# --- Explore (Wikidata) ----------------------------------------------------------


def _browse_wikidata(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """Axes derived from Wikidata, matched conservatively to real stations.

    Derived, and labelled as such: Wikidata supplies the *organisation* and
    Radio Browser supplies every stream, so nothing here changes how a station
    plays, records, or is favourited.
    """
    from quill.core.radio import wikidata

    if not (args and args[0]):
        nodes = [
            folder(make_id("wikidata", key), label, note="from Wikidata")
            for key, label, _prop in wikidata.AXES
        ]
        nodes.append(folder("wikidatadial", "On the Dial", note="by frequency"))
        return nodes
    axis = args[0]
    stations = wikidata.stations_for_axis(axis, safe_mode=safe_mode)
    if len(args) > 1 and args[1]:
        wanted = args[1]
        chosen = [s for s in stations if s.grouping == wanted]
        rows = wikidata.playable(chosen, country="", safe_mode=safe_mode)
        # Radio Browser leads, because it answers from the set that can actually
        # play; the call-sign matches then top up anything it did not carry.
        # Every axis offered here is one Radio Browser can answer -- By Owner is
        # gone precisely because ownership is not a field it carries, leaving the
        # call-sign route alone to fill the folder, which it managed about a
        # quarter of the time (removed 2026-08-17).
        lead: list = []
        if axis == "city":
            lead = wikidata.stations_in_place(wanted, safe_mode=safe_mode)
        elif axis == "format":
            lead = wikidata.stations_with_format(wanted, safe_mode=safe_mode)
        if lead:
            seen = set()
            merged = []
            for station in [*lead, *rows]:
                if station.stream_url in seen:
                    continue
                seen.add(station.stream_url)
                merged.append(station)
            rows = merged
        return _stations(rows)
    # No number here, in either direction. Wikidata's count is not what the
    # folder holds -- Arizona announced "13" and opened to one row (reported
    # 2026-08-16) -- and now that a place or a format is asked of Radio Browser
    # directly, the folder usually holds *more* than Wikidata listed. child_count
    # reads as a promise about the contents, so neither figure earns it; the note
    # says what the folder is instead.
    note = "stations for this place" if axis == "city" else "stations with this format"
    return [
        folder(make_id("wikidata", axis, grouping), grouping, note=note)
        for grouping, _count in wikidata.groupings(stations)
    ]


def _browse_wikidata_dial(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """Browsing by frequency: how radio worked for a century, and absent from
    every internet radio client."""
    from quill.core.radio import wikidata

    stations = wikidata.stations_for_axis("city", safe_mode=safe_mode)
    if args and args[0]:
        wanted = args[0]
        chosen = [s for s in stations if wikidata.band_of(s.frequency_mhz) == wanted]
        return _stations(wikidata.playable(chosen, safe_mode=safe_mode))
    counts: dict[str, int] = {}
    for station in stations:
        band = wikidata.band_of(station.frequency_mhz)
        if band:
            counts[band] = counts.get(band, 0) + 1
    return [
        # Same honesty as the axes above: the number is what Wikidata knows,
        # and only stations with a matching stream can actually play.
        folder(
            make_id("wikidatadial", label),
            label,
            note=f"{counts.get(label, 0)} known; those with a stream can play",
        )
        for label, _low, _high in wikidata.DIAL_BANDS
        if counts.get(label)
    ]


# --- dispatch -----------------------------------------------------------------

_HANDLERS: dict[str, Callable[..., list[BrowseNode]]] = {
    "rbcountry": _browse_country,
    "rbstate": _browse_state,
    "rblang": _browse_language,
    "wx": _browse_weather,
    "tunein": _browse_tunein,
    "rbcodec": _browse_codec,
    "iheart": _browse_iheart,
    "iheartletter": _browse_iheart_letter,
    "iheartmarkets": _browse_iheart_markets,
    "iheartmarket": _browse_iheart_market,
    "applechart": _browse_apple_chart,
    "archive": _browse_archive,
    "archiveitem": _browse_archive_item,
    "librivox": _browse_librivox,
    "librivoxrecent": _browse_librivox_recent,
    "librivoxgenres": _browse_librivox_genres,
    "librivoxauthors": _browse_librivox_authors,
    "librivoxbook": _browse_librivox_book,
    "gutenberg": _browse_gutenberg,
    "gutenbergtopic": _browse_gutenberg_topic,
    "gutenberglang": _browse_gutenberg_lang,
    "audius": _browse_audius,
    "audiustrending": _browse_audius_trending,
    "mixcloud": _browse_mixcloud,
    "mixcloudfmt": _browse_mixcloud_format,
    "mixcloudcat": _browse_mixcloud_category,
    "ccmixter": _browse_ccmixter,
    "myservers": _browse_my_servers,
    "youtube": _browse_youtube,
    "youtubechannel": _browse_youtube_channel,
    "youtubevideos": _browse_youtube_videos,
    # A saved playlist enumerates exactly like a channel playlist; its own
    # kind exists so the row can offer Remove from YouTube.
    "ytplaylist": _browse_youtube_videos,
    "wikidata": _browse_wikidata,
    "wikidatadial": _browse_wikidata_dial,
    "networks": _browse_networks,
    "networkgroup": _browse_network_group,
    "network": _browse_network,
    "apple": _browse_apple,
    # The Podcast Index branch (GATE-11 extraction, browse_podcast_index.py):
    # shows you can open without subscribing to them.
    "podcastindex": browse_root,
    "pitrending": browse_trending,
    "picategories": browse_categories,
    "pishow": browse_show,
    "applegenre": _browse_apple_genre,
    "appleshow": _browse_apple_show,
    "mypodcasts": _browse_my_podcasts,
    "mypodcastfolder": _browse_my_podcast_folder,
    "mypodcastshow": _browse_my_podcast_show,
    "audiopub": _browse_audiopub,
    "audiopubdiscover": _browse_audiopub_discover,
}


def is_expandable(node_id: str) -> bool:
    """True when *node_id* names a folder this module can open (pure)."""
    kind, _args = split_id(node_id)
    return kind in _HANDLERS or kind in _FLAT or kind in _GENRE_MODULES or kind == "favorites"


def browse(
    node_id: str,
    *,
    safe_mode: bool = False,
    favorites: object = None,
    catalog: object = None,
) -> list[BrowseNode]:
    """The children of *node_id*.

    Never raises for a source problem: a directory that is down, refusing in
    Safe Mode, or returning nonsense all yield an empty list, because a browse
    branch that throws takes the window with it. The caller distinguishes "this
    folder is empty" from "this source could not be reached" by asking
    :func:`last_error_was_network`, or simply by saying the honest thing --
    see the dialog's empty-branch message.

    ``catalog`` (a ``CatalogStore``) is consulted first for the kinds it can
    answer -- one chokepoint here, not a branch per handler. ``None`` or a
    decline runs the live path unchanged; rankings invert (live first,
    catalog fallback labeled with its age).
    """
    kind, args = split_id(node_id)
    # This call's verdict is about THIS call. The marker used to be cleared only
    # when a folder came back non-empty, so a genuinely empty folder opened
    # straight after a broken one inherited the broken one's answer and said
    # "could not be reached" about a source that had replied perfectly well.
    # Clearing on entry keeps the signal (anything recorded below belongs to
    # this call) without the staleness.
    LAST_FAILURE.pop(_thread_key(), None)
    if catalog is not None:
        from quill.core.radio.catalog import read as catalog_read

        if kind in catalog_read.AXIS_KINDS or kind in catalog_read.LIBRARY_KINDS:
            served = catalog_read.serve(catalog, kind, args)  # type: ignore[arg-type]
            if served is not None:
                LAST_FAILURE.pop(_thread_key(), None)
                return served
        if kind == "catalogbook" and len(args) >= 2:
            return catalog_read.book_sections(catalog, args[0], args[1])  # type: ignore[arg-type]
    try:
        if kind == "favorites":
            return _browse_favorites(args, safe_mode=safe_mode, favorites=favorites)
        if kind in _FLAT and not args:
            result = _stations(_FLAT[kind](safe_mode))
        elif kind in _GENRE_MODULES:
            result = _browse_genre_source(kind, args, safe_mode=safe_mode)
        else:
            handler = _HANDLERS.get(kind)
            if handler is None:
                return []
            result = handler(args, safe_mode=safe_mode)
    except Exception as error:  # noqa: BLE001 - every source has its own error type
        _remember_failure(error)
        return _rankings_rescue(kind, catalog) or []
    if result:
        # Only a listing that actually arrived clears the record. A handler
        # whose cache layer swallowed an outage returns [] without raising
        # (directory_cache never throws into a browse tree), and popping here
        # unconditionally threw away the one signal that told "empty folder"
        # from "source is down".
        LAST_FAILURE.pop(_thread_key(), None)
    return result


def _rankings_rescue(kind: str, catalog: object) -> list[BrowseNode] | None:
    """Popular/Trending from the vote snapshot when live cannot answer,
    labeled "as of <age>" (decision of 2026-08-15). Anything else: None."""
    if catalog is None:
        return None
    from quill.core.radio.catalog import read as catalog_read

    if kind not in catalog_read.RANKING_KINDS:
        return None
    return catalog_read.rankings_fallback(catalog, kind)  # type: ignore[arg-type]


def resolve(node_id: str, *, safe_mode: bool = False) -> RadioStation | None:
    """Turn a lazily-resolved leaf into a playable station, or ``None``.

    Only TuneIn needs this today: its rows carry a guide id until play time.
    ``None`` rather than an exception for "could not resolve", so the caller
    says "could not play that station" instead of crashing a tree.
    """
    kind, args = split_id(node_id)
    if kind != "tuneinstation" or not args:
        return None
    try:
        streams = tunein.resolve_station_streams(args[0], safe_mode=safe_mode)
    except Exception:  # noqa: BLE001
        return None
    if not streams:
        return None
    return RadioStation(name="", stream_url=tunein.best_stream(streams), source="TuneIn")


def visible_roots(enabled: object = None) -> tuple[tuple[str, str], ...]:
    """The root branches a listener has chosen to see (pure).

    ``None`` means "never set", which yields the defaults. The rule this
    enforces is the same one search follows: **a source that is off is not in
    the tree at all**, so it is never opened and therefore never contacted --
    this is not a display filter over branches that would have been fetched
    anyway.
    """
    from quill.core.radio import browse_visibility

    chosen = set(browse_visibility.normalize(enabled))
    return tuple((node_id, label) for node_id, label in ROOT_SOURCES if node_id in chosen)


def source_label(node_id: str) -> str:
    """The display label for a root source id (pure), or ``""``."""
    for candidate, label in ROOT_SOURCES:
        if candidate == node_id:
            return label
    return ""


def needs_network(node_id: str) -> bool:
    """True when opening *node_id* would make a request (pure).

    Safe Mode keeps the local branches working -- Favorites, ACB Media, NFB
    Radio, and the Networks folder structure -- and refuses the rest out loud
    rather than showing them as empty.
    """
    kind, _args = split_id(node_id)
    return kind not in LOCAL_SOURCES


__all__ = [
    "ARG_SEP",
    "LOCAL_SOURCES",
    "ROOT_SOURCES",
    "BrowseNode",
    "action",
    "browse",
    "is_expandable",
    "make_id",
    "needs_network",
    "resolve",
    "source_label",
    "split_id",
]
