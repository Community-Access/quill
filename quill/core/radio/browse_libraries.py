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

from quill.core.radio.browse_nodes import BrowseNode, folder, leaf, make_id
from quill.core.radio.models import RadioStation

# --- Apple Podcasts -----------------------------------------------------------


def _browse_apple(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    from quill.core.podcasts import apple_podcasts as apple

    if not (args and args[0]):
        # Subscriptions first: the shows already followed are the ones a
        # listener comes back for, and before this folder existed a
        # subscription vanished into Quill Cast with no way to find it from
        # the app that made it ("how do I find those that are subscribed?").
        return [
            folder(
                make_id("mypodcasts"),
                "Subscriptions",
                note="shows you follow, shared with Quill Cast",
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
    nodes: list[BrowseNode] = []
    for episode in info.episodes:
        if not episode.audio_url:
            continue
        nodes.append(
            leaf(
                RadioStation(
                    name=episode.title,
                    stream_url=episode.audio_url,
                    homepage=feed_url,
                    source=source,
                    is_recording=True,
                ),
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


def _browse_my_podcasts(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """The shows in the shared podcast library -- the ones Quill Cast has.

    A purely local read: listing what you follow costs no network. Each show's
    node carries the feed URL itself, so opening it goes straight to the
    publisher's feed with no directory in between.
    """
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.subscriptions import load_library

    shows = load_library(app_data_dir()).shows
    return [
        folder(make_id("mypodcastshow", show.feed_url), show.title or show.feed_url)
        for show in sorted(shows, key=lambda s: (s.title or s.feed_url).casefold())
        if show.feed_url
    ]


def _browse_my_podcast_show(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """A subscribed show's episodes; the node id *is* the feed address.

    Capped at the newest ``subscription_episode_limit`` (Preferences; 0 = all).
    Feeds publish newest-first, so the slice is the recent ones -- deliberately
    Radio's one podcast setting, with the full archive living in Quill Cast.
    """
    if not args or not args[0]:
        return []
    from quill.core.paths import app_data_dir
    from quill.core.radio.history import load_history

    limit = load_history(app_data_dir()).subscription_episode_limit
    leaves = _feed_episode_leaves(args[0], safe_mode=safe_mode, source="Subscribed Podcasts")
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
