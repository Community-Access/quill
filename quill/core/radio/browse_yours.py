"""The listener's own additions, and the Wikidata explorer, as browse handlers.

Extracted from :mod:`quill.core.radio.browse_sources` under GATE-11 the moment
that module crossed its ratcheted budget again (2026-08-27) -- the same
extraction its own budget entry has named since 2026-08-13, joining
``browse_free_music``, ``browse_libraries`` and ``browse_directories``.

What lives here: **My Servers** (Icecast/SHOUTcast servers the listener added),
the **YouTube** branch (saved videos, playlists and followed channels), and
**Explore (Wikidata)**. Every client stays in its own module; this is the tree
shape and nothing else. wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence

from quill.core.radio.browse_nodes import BrowseNode, action, folder, leaf, make_id
from quill.core.radio.models import RadioStation


def _stations(rows: Sequence[RadioStation]) -> list[BrowseNode]:
    return [leaf(station) for station in rows]


def browse_my_servers(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
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


def browse_youtube(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
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


def browse_youtube_channel(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.radio import youtube_channels as yt

    if not args or not args[0]:
        return []
    url = args[0]
    nodes: list[BrowseNode] = [folder(make_id("youtubevideos", url, "1"), "Uploads")]
    for title, playlist_url in yt.playlists(url, safe_mode=safe_mode):
        nodes.append(folder(make_id("youtubevideos", playlist_url, "1"), title))
    return nodes


def browse_youtube_videos(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
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


def browse_wikidata(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
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


def browse_wikidata_dial(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
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
