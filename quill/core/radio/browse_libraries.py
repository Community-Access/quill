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
        return [folder(make_id("apple", code), name) for code, name in apple.DEFAULT_STOREFRONTS]
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


def _browse_apple_show(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """A show's episodes, straight from its own RSS feed.

    This is where Apple stops being involved: the collection id resolves to a
    ``feedUrl`` and the publisher's feed supplies everything after it. No key at
    any step, and nothing in the playback path depends on Apple.
    """
    from quill.core.podcasts import apple_podcasts as apple
    from quill.core.podcasts.feed_reader import fetch_and_parse_feed

    if not args or not args[0]:
        return []
    feed_url = apple.resolve_feed_url(args[0], safe_mode=safe_mode)
    if not feed_url:
        return []
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
                    source="Apple Podcasts",
                    is_recording=True,
                ),
                note="transcript available" if episode.transcript_url else "",
            )
        )
    return nodes
