"""The four *libraries* in the browse tree, as opposed to the radio directories.

Apple Podcasts, the Internet Archive, LibriVox and Project Gutenberg answer a
different question from a station directory -- they hold *works* with beginnings
and endings rather than streams that are simply on -- and they behave
differently for it: their rows resume, they can be downloaded, and they are
grouped apart in federated search.

Extracted from ``browse_sources`` under GATE-11 (extract, never rebaseline) when
the empty-versus-broken reporting arrived. The dispatch table still lives there;
these are just the handlers it calls, and keeping the family together makes the
shared shape visible -- every one of them is "walk a catalogue, return
``BrowseNode``s, never raise".

wx-free, strict-typed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from quill.core.radio.browse_nodes import BrowseNode, folder, leaf, make_id
from quill.core.radio.models import RadioStation

if TYPE_CHECKING:
    from quill.core.podcasts.feed_reader import FeedInfo
    from quill.core.podcasts.models import PodcastEpisode
    from quill.core.podcasts.subscriptions import PodcastLibrary

# --- Apple Podcasts -----------------------------------------------------------


def _browse_apple(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.podcasts import apple_podcasts as apple

    if not (args and args[0]):
        # Subscriptions first: the shows already followed are the ones a
        # listener comes back for, and before this folder existed a
        # subscription vanished into Quill Cast with no way to find it from
        # the app that made it ("how do I find those that are subscribed?").
        # The badge is the follow count; the old explanatory note read as a
        # sentence glued to the name on every visit ("Subscriptions (shows
        # you follow, shared with Quill Cast) Closed") and is gone.
        from quill.core.paths import app_data_dir
        from quill.core.podcasts.subscriptions import load_library

        followed = sum(1 for s in load_library(app_data_dir()).shows if s.feed_url)
        return [
            folder(
                make_id("mypodcasts"),
                f"Subscriptions ({followed})" if followed else "Subscriptions",
            ),
            *(folder(make_id("apple", code), name) for code, name in apple.DEFAULT_STOREFRONTS),
        ]
    storefront = args[0]
    # Both chart kinds Apple publishes: the top shows, and the top individual
    # episodes, which answers "what is everyone listening to right now" rather
    # than "which shows are big".
    nodes = [
        folder(make_id("applechart", storefront, kind), label) for kind, label in apple.CHART_KINDS
    ]
    nodes += [
        folder(make_id("applegenre", storefront, genre.genre_id), genre.name)
        for genre in apple.fetch_genres(safe_mode=safe_mode)
    ]
    return nodes


def _browse_apple_chart(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """One of Apple's storefront charts, whole and unfiltered."""
    from quill.core.podcasts import apple_podcasts as apple

    storefront = args[0] if args else "us"
    kind = args[1] if len(args) > 1 else apple.CHART_SHOWS
    return [
        folder(
            make_id("appleshow", show.collection_id),
            show.display_name,
            note="explicit" if show.explicit else "",
        )
        for show in apple.fetch_charts(storefront, kind=kind, safe_mode=safe_mode)
    ]


def _browse_apple_genre(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.podcasts import apple_podcasts as apple

    storefront = args[0] if args else "us"
    genre_id = args[1] if len(args) > 1 else ""
    nodes: list[BrowseNode] = []
    if genre_id:
        node = apple.genres_in(apple.fetch_genres(safe_mode=safe_mode), genre_id)
        for child in node.subgenres if node is not None else ():
            nodes.append(folder(make_id("applegenre", storefront, child.genre_id), child.name))
    for show in apple.fetch_charts(storefront, genre_id=genre_id, safe_mode=safe_mode):
        nodes.append(
            folder(
                make_id("appleshow", show.collection_id),
                show.display_name,
                note="explicit" if show.explicit else "",
            )
        )
    return nodes


def _feed_episode_leaves(feed_url: str, *, safe_mode: bool, source: str) -> list[BrowseNode]:
    """A show's episodes, straight from its own RSS feed."""
    from quill.core.podcasts.feed_reader import fetch_and_parse_feed

    info = fetch_and_parse_feed(feed_url, safe_mode=safe_mode)
    return _episode_leaves(info, feed_url, source=source)


def _episode_leaves(info: FeedInfo, feed_url: str, *, source: str) -> list[BrowseNode]:
    """Render an already-fetched feed's episodes as playable rows.

    Split from the fetch so the Subscriptions path can fold the same fetch
    into the shared library (:func:`_sync_subscribed_episodes`) without
    asking the publisher twice.
    """
    nodes: list[BrowseNode] = []
    for episode in info.episodes:
        if not episode.audio_url:
            continue
        # An episode with a transcript gets a node id that carries the
        # transcript's address and type, so View Transcript on the row can
        # fetch it without playing anything (see browse_tree_menu).
        node_id = (
            make_id("podepisode", episode.transcript_url, episode.transcript_type or "")
            if episode.transcript_url
            else ""
        )
        nodes.append(
            leaf(
                RadioStation(
                    name=episode.title,
                    stream_url=episode.audio_url,
                    homepage=feed_url,
                    source=source,
                    is_recording=True,
                ),
                node_id=node_id,
                note="transcript available" if episode.transcript_url else "",
            )
        )
    return nodes


def _browse_apple_show(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """A show's episodes, straight from its own RSS feed.

    This is where Apple stops being involved: the collection id resolves to a
    ``feedUrl`` and the publisher's feed supplies everything after it. No key at
    any step, and nothing in the playback path depends on Apple.
    """
    from quill.core.podcasts import apple_podcasts as apple

    if not args or not args[0]:
        return []
    feed_url = apple.resolve_feed_url(args[0], safe_mode=safe_mode)
    if not feed_url:
        return []
    return _feed_episode_leaves(feed_url, safe_mode=safe_mode, source="Apple Podcasts")


def _my_podcast_level(library: PodcastLibrary, folder_id: str | None) -> list[BrowseNode]:
    """One level of the shared library: subfolders first, then the shows filed
    there -- the same shape Quill Cast's manager tree shows, because it is the
    same library. Folder badges count the whole subtree, show badges the show;
    both use the shared counters, so the two apps can never disagree.
    """
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.radio_listens import finished_audio_urls
    from quill.core.podcasts.sorting import unheard_count, unheard_count_for_folder

    # Radio's own finished listens, subtracted from every badge on this level:
    # an episode heard to the end HERE is finished now, even though the shared
    # library only learns it at Cast's next merge (the clobber-safe handoff).
    # Without this, finishing an episode left its show counting it unheard.
    heard_here = finished_audio_urls(app_data_dir())

    def show_label(show: PodcastShow) -> str:
        # The unheard badge reads from the shared library's own episode
        # state -- the same count Quill Cast shows. Browsing a show's episodes
        # here syncs that state (see _browse_my_podcast_show), so the badge
        # appears without ever opening Cast.
        name = show.title or show.feed_url
        unheard = unheard_count(show, exclude_audio=heard_here)
        return f"{name} ({unheard} unheard)" if unheard else name

    nodes: list[BrowseNode] = []
    subfolders = sorted(
        (f for f in library.folders if f.parent_folder_id == folder_id),
        key=lambda f: f.name.casefold(),
    )
    for child in subfolders:
        unheard = unheard_count_for_folder(library, child.id, exclude_audio=heard_here)
        nodes.append(
            folder(
                make_id("mypodcastfolder", child.id),
                f"{child.name} ({unheard} unheard)" if unheard else child.name,
            )
        )
    shows = sorted(
        (s for s in library.shows if s.feed_url and s.folder_id == folder_id),
        key=lambda s: (s.title or s.feed_url).casefold(),
    )
    nodes.extend(
        folder(make_id("mypodcastshow", show.feed_url), show_label(show)) for show in shows
    )
    return nodes


def _browse_my_podcasts(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """The shows in the shared podcast library -- the ones Quill Cast has.

    A purely local read: listing what you follow costs no network. Folders
    created in Quill Cast (or arriving inside an imported OPML file) appear
    here as folders; each show's node carries the feed URL itself, so opening
    it goes straight to the publisher's feed with no directory in between.
    """
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.subscriptions import load_library

    return _my_podcast_level(load_library(app_data_dir()), None)


def _browse_my_podcast_folder(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """A library folder's own subfolders and shows; the node id is the folder id."""
    if not args or not args[0]:
        return []
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.subscriptions import load_library

    return _my_podcast_level(load_library(app_data_dir()), args[0])


def _sync_subscribed_episodes(feed_url: str, fetched: list[PodcastEpisode]) -> None:
    """Fold a just-fetched episode list into the shared library, and save.

    This is what makes the unheard badges real from Radio's side: a show
    followed here (or imported from OPML) has an empty episode list in the
    store until someone syncs it, and before this only Quill Cast's refresh
    did. Browsing the show already fetched the feed -- folding the result in
    costs no extra network. ``merge_episodes`` keeps local state (played,
    position) untouched, and the save happens only when episodes were
    actually gained, so an ordinary re-browse never churns the store.
    """
    if not fetched:
        return
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.subscriptions import load_library, merge_episodes, save_library

    data_dir = app_data_dir()
    library = load_library(data_dir)
    show = next((s for s in library.shows if s.feed_url == feed_url), None)
    if show is None:
        return  # browsing an unfollowed feed (Apple discovery) syncs nothing
    if merge_episodes(show, fetched) > 0:
        save_library(data_dir, library)


def _browse_my_podcast_show(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """A subscribed show's episodes; the node id *is* the feed address.

    Capped at the newest ``subscription_episode_limit`` (Preferences; 0 = all).
    Feeds publish newest-first, so the slice is the recent ones -- deliberately
    Radio's one podcast setting, with the full archive living in Quill Cast.
    """
    if not args or not args[0]:
        return []
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.feed_reader import fetch_and_parse_feed
    from quill.core.podcasts.radio_listens import feed_credentials
    from quill.core.radio.history import load_history

    limit = load_history(app_data_dir()).subscription_episode_limit
    # The same same-host credentials Quill Cast attaches: a private feed that
    # works there must list its episodes here, not read as broken.
    username, password = feed_credentials(app_data_dir(), args[0])
    info = fetch_and_parse_feed(args[0], username=username, password=password, safe_mode=safe_mode)
    _sync_subscribed_episodes(args[0], info.episodes)
    leaves = _episode_leaves(info, args[0], source="Subscribed Podcasts")
    return leaves[:limit] if limit > 0 else leaves


# --- AudioPub (community audio) ----------------------------------------------
# v1 is Discover only: the one JSON endpoint AudioPub's own source implements
# for clients. Newest/popular/search/live exist server-side but have no public
# API; the plan of record is to ask the developer for one, not to scrape.


def _browse_audiopub(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    return [
        folder(
            make_id("audiopubdiscover", "1"),
            "Discover",
            note="a random fifty, different every time",
        )
    ]


def _browse_audiopub_discover(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.radio import audiopub

    page = int(args[0]) if args and args[0].isdigit() else 1
    nodes: list[BrowseNode] = [
        leaf(station, note=", ".join(station.tags))
        for station in audiopub.discover(page, safe_mode=safe_mode)
    ]
    if nodes:
        nodes.append(folder(make_id("audiopubdiscover", str(page + 1)), "More to discover"))
    return nodes


# --- Project Gutenberg audio --------------------------------------------------


def _browse_gutenberg(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.radio import gutendex

    nodes = [folder("gutenbergtopic", "All Audiobooks")]
    nodes += [
        folder(make_id("gutenbergtopic", slug), label) for slug, label in gutendex.BROWSE_TOPICS
    ]
    nodes += [
        folder(make_id("gutenberglang", code), f"In {label}")
        for code, label in gutendex.BROWSE_LANGUAGES
    ]
    return nodes


def _gutenberg_page(
    kind: str, filter_value: str, page: int, *, safe_mode: bool
) -> list[BrowseNode]:
    """One gutendex page as rows, chained with a More node while pages remain.

    Gutendex serves 32 records per page and the old handlers fetched exactly
    one, so every topic silently showed its first 32 books and no more
    (reported 2026-08-16). The More row states what it is; a truncated list
    that says nothing reads as the whole answer.
    """
    from quill.core.radio import gutendex

    topic = filter_value if kind == "gutenbergtopic" else ""
    language = filter_value if kind == "gutenberglang" else ""
    rows = gutendex.audiobooks(topic=topic, language=language, page=page, safe_mode=safe_mode)
    nodes: list[BrowseNode] = [leaf(station) for station in rows]
    if len(rows) >= 32:  # a full page: gutendex has more behind it
        nodes.append(folder(make_id(kind, filter_value, str(page + 1)), "More audiobooks"))
    return nodes


def _browse_gutenberg_topic(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    return _gutenberg_page("gutenbergtopic", args[0] if args else "", page, safe_mode=safe_mode)


def _browse_gutenberg_lang(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    return _gutenberg_page("gutenberglang", args[0] if args else "", page, safe_mode=safe_mode)
